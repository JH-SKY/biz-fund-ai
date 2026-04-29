"use client";

/**
 * 관리자 도메인 TanStack Query 훅 모음.
 *
 * 모든 쿼리 키는 ["admin", ...] 접두어를 사용하여 일반 유저 쿼리와 격리한다.
 * invalidate 는 큰 단위("admin" 전체) → 세부 단위("admin","users") 순으로 선택.
 */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { adminService } from "@/lib/services";
import type {
  AdminChatLogsParams,
  AdminLoginRequest,
  AdminPolicyCreateRequest,
  AdminPolicyUpdateRequest,
  AdminUsersParams,
  AiCardNewsGenerateRequest,
  AiRelatedPoliciesRequest,
  BizPickContentCreateRequest,
  BizPickContentUpdateRequest,
  CorrectionNoteRequest,
  FeedbackListParams,
  AgentMonitoringFilters,
  MonitoringRange,
  PolicySyncRunParams,
} from "@/types";
import type { DebugOutputItem, DebugOutputFiles } from "@/lib/services/admin.service";

// ── Query Keys ────────────────────────────────────────────────────
export const ADMIN_KEYS = {
  all: ["admin"] as const,
  dashboard: () => ["admin", "dashboard"] as const,
  users: (params: AdminUsersParams) => ["admin", "users", params] as const,
  chatLogs: (params: AdminChatLogsParams) =>
    ["admin", "chat-logs", params] as const,
  audit: (page: number, size: number) =>
    ["admin", "audit-logs", page, size] as const,
  batchStatus: () => ["admin", "batch", "status"] as const,
  batchLogs: (jobId: string) => ["admin", "batch", "logs", jobId] as const,
  contents: (params: { page?: number; size?: number; category?: string }) =>
    ["admin", "contents", params] as const,
  contentDetail: (id: string) => ["admin", "contents", "detail", id] as const,
  feedback: (params: FeedbackListParams) =>
    ["admin", "feedback", params] as const,
  feedbackContext: (id: string) =>
    ["admin", "feedback", "context", id] as const,
  corrections: (page: number, size: number) =>
    ["admin", "corrections", page, size] as const,
  health: () => ["admin", "monitoring", "health"] as const,
  latency: (range: MonitoringRange) =>
    ["admin", "monitoring", "latency", range] as const,
  cost: (date?: string) => ["admin", "monitoring", "cost", date ?? "today"] as const,
  agentOverview: (range: MonitoringRange, filters: AgentMonitoringFilters) =>
    ["admin", "monitoring", "agent-overview", range, filters] as const,
  agentNodes: (range: MonitoringRange, filters: AgentMonitoringFilters) =>
    ["admin", "monitoring", "agent-nodes", range, filters] as const,
  agentRuns: (
    params: { range?: MonitoringRange; page?: number; size?: number } & AgentMonitoringFilters
  ) =>
    ["admin", "monitoring", "agent-runs", params] as const,
  agentRunDetail: (runId: string) =>
    ["admin", "monitoring", "agent-run-detail", runId] as const,
  unmetDemand: (page: number, size: number) =>
    ["admin", "insights", "unmet-demand", page, size] as const,
  conversion: (from?: string, to?: string) =>
    ["admin", "insights", "conversion", from ?? "", to ?? ""] as const,
};

// ── 인증 ──────────────────────────────────────────────────────────
export function useAdminLogin() {
  return useMutation({
    mutationFn: (body: AdminLoginRequest) => adminService.auth.login(body),
  });
}

// ── 대시보드 ──────────────────────────────────────────────────────
export function useAdminDashboard() {
  return useQuery({
    queryKey: ADMIN_KEYS.dashboard(),
    queryFn: () => adminService.stats.dashboard(),
    staleTime: 30_000,
  });
}

// ── 유저 관리 ────────────────────────────────────────────────────
export function useAdminUsers(params: AdminUsersParams) {
  return useQuery({
    queryKey: ADMIN_KEYS.users(params),
    queryFn: () => adminService.users.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useSetUserActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      userId,
      isActive,
    }: {
      userId: string;
      isActive: boolean;
    }) => adminService.users.setActive(userId, isActive),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
}

// ── 채팅 모니터링 ─────────────────────────────────────────────────
export function useAdminChatLogs(params: AdminChatLogsParams) {
  return useQuery({
    queryKey: ADMIN_KEYS.chatLogs(params),
    queryFn: () => adminService.chatLogs.list(params),
    placeholderData: keepPreviousData,
  });
}

// ── 감사 로그 ─────────────────────────────────────────────────────
export function useAdminAuditLogs(page = 1, size = 20) {
  return useQuery({
    queryKey: ADMIN_KEYS.audit(page, size),
    queryFn: () => adminService.audit.list({ page, size }),
    placeholderData: keepPreviousData,
  });
}

// ── 배치 ──────────────────────────────────────────────────────────
export function useBatchStatus() {
  return useQuery({
    queryKey: ADMIN_KEYS.batchStatus(),
    queryFn: () => adminService.batch.status(),
    refetchInterval: (query) => {
      const hasRunning = query.state.data?.some((j) => j.status === "RUNNING");
      return hasRunning ? 3_000 : 30_000;
    },
  });
}

export function useBatchLogs(jobId: string | null) {
  return useQuery({
    queryKey: ADMIN_KEYS.batchLogs(jobId ?? ""),
    queryFn: () => adminService.batch.logs(jobId!),
    enabled: !!jobId,
  });
}

// ── 정책 관리 ────────────────────────────────────────────────────
export function useCreatePolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AdminPolicyCreateRequest) =>
      adminService.policies.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin"] });
      qc.invalidateQueries({ queryKey: ["policies"] });
    },
  });
}

export function useUpdatePolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      policyId,
      body,
    }: {
      policyId: string;
      body: AdminPolicyUpdateRequest;
    }) => adminService.policies.update(policyId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin"] });
      qc.invalidateQueries({ queryKey: ["policies"] });
    },
  });
}

export function useSyncBootstrap() {
  return useMutation({ mutationFn: () => adminService.policies.syncBootstrap() });
}
export function useSyncDaily() {
  return useMutation({ mutationFn: () => adminService.policies.syncDaily() });
}
export function useSyncRun() {
  return useMutation({
    mutationFn: (params: PolicySyncRunParams) =>
      adminService.policies.syncRun(params),
  });
}
export function useEmbedAll() {
  return useMutation({
    mutationFn: (limit?: number) => adminService.policies.embedAll(limit),
  });
}

export function useSyncFull() {
  return useMutation({
    mutationFn: (params: { with_ai?: boolean; rows_per_page?: number } = {}) =>
      adminService.policies.syncFull(params),
  });
}

export function useTestSyncOne() {
  return useMutation({
    mutationFn: () => adminService.policies.testSyncOne(),
  });
}

export function useDebugOutputs(enabled = true) {
  return useQuery<{ items: DebugOutputItem[] }>({
    queryKey: ["admin", "debug-output"],
    queryFn: () => adminService.policies.listDebugOutputs(),
    enabled,
    staleTime: 0,
  });
}

export function useDebugOutput(originId: string | null) {
  return useQuery<DebugOutputFiles>({
    queryKey: ["admin", "debug-output", originId],
    queryFn: () => adminService.policies.getDebugOutput(originId!),
    enabled: !!originId,
  });
}

// ── 비즈픽 콘텐츠 ────────────────────────────────────────────────
export function useAdminContents(params: {
  page?: number;
  size?: number;
  category?: string;
}) {
  return useQuery({
    queryKey: ADMIN_KEYS.contents(params),
    queryFn: () => adminService.contents.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useAdminContentDetail(contentId: string | null) {
  return useQuery({
    queryKey: ADMIN_KEYS.contentDetail(contentId ?? ""),
    queryFn: () => adminService.contents.detail(contentId!),
    enabled: !!contentId,
  });
}

export function useCreateContent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: BizPickContentCreateRequest) =>
      adminService.contents.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "contents"] });
    },
  });
}

export function useUpdateContent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentId,
      body,
    }: {
      contentId: string;
      body: BizPickContentUpdateRequest;
    }) => adminService.contents.update(contentId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "contents"] });
    },
  });
}

export function useDeleteContent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (contentId: string) => adminService.contents.remove(contentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "contents"] });
    },
  });
}

export function useGenerateCardNews() {
  return useMutation({
    mutationFn: (body: AiCardNewsGenerateRequest) =>
      adminService.contents.generateDraft(body),
  });
}

export function useSuggestRelatedPolicies() {
  return useMutation({
    mutationFn: (body: AiRelatedPoliciesRequest) =>
      adminService.contents.suggestRelated(body),
  });
}

// ── 피드백 / 로직 디버깅 ─────────────────────────────────────────
export function useAdminFeedback(params: FeedbackListParams) {
  return useQuery({
    queryKey: ADMIN_KEYS.feedback(params),
    queryFn: () => adminService.feedback.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useFeedbackContext(feedbackId: string | null) {
  return useQuery({
    queryKey: ADMIN_KEYS.feedbackContext(feedbackId ?? ""),
    queryFn: () => adminService.feedback.context(feedbackId!),
    enabled: !!feedbackId,
  });
}

export function useCreateCorrection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      feedbackId,
      body,
    }: {
      feedbackId: string;
      body: CorrectionNoteRequest;
    }) => adminService.feedback.createCorrection(feedbackId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "feedback"] });
      qc.invalidateQueries({ queryKey: ["admin", "corrections"] });
    },
  });
}

export function useCorrections(page = 1, size = 20) {
  return useQuery({
    queryKey: ADMIN_KEYS.corrections(page, size),
    queryFn: () => adminService.feedback.listCorrections({ page, size }),
    placeholderData: keepPreviousData,
  });
}

// ── 모니터링 ──────────────────────────────────────────────────────
export function useSystemHealth() {
  return useQuery({
    queryKey: ADMIN_KEYS.health(),
    queryFn: () => adminService.monitoring.health(),
    refetchInterval: 15_000,
  });
}

export function useLatencyTimeSeries(range: MonitoringRange = "24h") {
  return useQuery({
    queryKey: ADMIN_KEYS.latency(range),
    queryFn: () => adminService.monitoring.latency(range),
    refetchInterval: 60_000,
  });
}

export function useTokenCost(date?: string) {
  return useQuery({
    queryKey: ADMIN_KEYS.cost(date),
    queryFn: () => adminService.monitoring.cost(date),
    refetchInterval: 60_000,
  });
}

export function useAgentOverview(
  range: MonitoringRange = "24h",
  filters: AgentMonitoringFilters = {}
) {
  return useQuery({
    queryKey: ADMIN_KEYS.agentOverview(range, filters),
    queryFn: () => adminService.monitoring.agentOverview(range, filters),
    refetchInterval: 60_000,
  });
}

export function useAgentNodes(
  range: MonitoringRange = "24h",
  filters: AgentMonitoringFilters = {}
) {
  return useQuery({
    queryKey: ADMIN_KEYS.agentNodes(range, filters),
    queryFn: () => adminService.monitoring.agentNodes(range, filters),
    refetchInterval: 60_000,
  });
}

export function useAgentRuns(
  params: { range?: MonitoringRange; page?: number; size?: number } & AgentMonitoringFilters
) {
  return useQuery({
    queryKey: ADMIN_KEYS.agentRuns(params),
    queryFn: () => adminService.monitoring.agentRuns(params),
    placeholderData: keepPreviousData,
    refetchInterval: 60_000,
  });
}

export function useAgentRunDetail(runId: string | null) {
  return useQuery({
    queryKey: ADMIN_KEYS.agentRunDetail(runId ?? ""),
    queryFn: () => adminService.monitoring.agentRunDetail(runId!),
    enabled: !!runId,
    refetchInterval: 60_000,
  });
}

// ── 비즈니스 인사이트 ────────────────────────────────────────────
export function useUnmetDemand(page = 1, size = 30) {
  return useQuery({
    queryKey: ADMIN_KEYS.unmetDemand(page, size),
    queryFn: () => adminService.insights.unmetDemand({ page, size }),
    placeholderData: keepPreviousData,
  });
}

export function useConversionStats(from?: string, to?: string) {
  return useQuery({
    queryKey: ADMIN_KEYS.conversion(from, to),
    queryFn: () => adminService.insights.conversion({ from, to }),
  });
}
