/**
 * 관리자 도메인 서비스 — 모든 엔드포인트는 admin-api-client 를 통해 호출.
 *
 * 엔드포인트 매핑 (PAGE 12 기획안 + 기존 Admin API 명세)
 *  인증:
 *    POST   /admin/login
 *  대시보드:
 *    GET    /admin/stats/dashboard
 *  유저 관리:
 *    GET    /admin/users
 *  채팅 모니터링:
 *    GET    /admin/chats/logs
 *  감사 로그:
 *    GET    /admin/audit-logs
 *  배치:
 *    GET    /admin/batch/status
 *    GET    /admin/batch/logs/{jobId}
 *  정책:
 *    POST   /admin/policies
 *    PATCH  /admin/policies/{id}
 *    POST   /admin/policies/sync/bootstrap
 *    POST   /admin/policies/sync/daily
 *    POST   /admin/policies/sync/run
 *    POST   /admin/policies/embed/all
 *  비즈픽 콘텐츠:
 *    GET    /admin/contents
 *    POST   /admin/contents
 *    PATCH  /admin/contents/{id}
 *    POST   /admin/contents/generate           (AI 카드뉴스 초안)
 *    POST   /admin/contents/suggest-related    (AI 연관 정책 추천)
 *  피드백 / 로직 디버깅:
 *    GET    /admin/feedback
 *    GET    /admin/feedback/{id}/context
 *    POST   /admin/feedback/{id}/correction
 *    GET    /admin/corrections
 *  모니터링:
 *    GET    /admin/monitoring/health
 *    GET    /admin/monitoring/latency
 *    GET    /admin/monitoring/cost
 *  인사이트:
 *    GET    /admin/insights/unmet-demand
 *    GET    /admin/insights/conversion
 */

import adminApiClient from "@/lib/admin-api-client";
import type {
  AdminChatLogsParams,
  AdminLoginRequest,
  AdminLoginResponse,
  AdminPolicyCreateRequest,
  AdminPolicyUpdateRequest,
  AdminUserItem,
  AdminUsersParams,
  AiCardNewsGenerateRequest,
  AiCardNewsGenerateResponse,
  AiRelatedPoliciesRequest,
  AiRelatedPoliciesResponse,
  AuditLogItem,
  BatchLogDetail,
  BatchStatusItem,
  BizPickContentCreateRequest,
  BizPickContentListItem,
  BizPickContentUpdateRequest,
  BizPickDetail,
  ChatMonitorItem,
  ConversionStats,
  CorrectionNoteItem,
  CorrectionNoteRequest,
  DashboardStats,
  FeedbackContextDetail,
  FeedbackItem,
  FeedbackListParams,
  LatencyTimeSeries,
  MonitoringRange,
  Paginated,
  PolicyDetail,
  PolicyEmbedResult,
  PolicySyncResult,
  PolicySyncRunParams,
  SystemHealthStatus,
  TokenCostSummary,
  UnmetDemandResponse,
} from "@/types";

export type TestSyncOneResult = {
  status: string;
  ai_status: string;
  db_saved: boolean;
  total_count: number;
  tested_page: number;
  origin_id: string;
  error?: Record<string, unknown> | null;
  debug_output_dir?: string | null;
};

export type DebugOutputItem = {
  origin_id: string;
  files: string[];
};

export type DebugOutputFiles = {
  "1_api_raw.json": string | null;
  "2_ai_input.txt": string | null;
  "3_ai_result.json": string | null;
};

// ── 9-0. 인증 ────────────────────────────────────────────────────
export const adminAuthService = {
  login(body: AdminLoginRequest) {
    return adminApiClient.post<AdminLoginResponse>("/admin/login", body);
  },
  logout() {
    return adminApiClient.post<{ success: boolean }>("/admin/logout");
  },
};

// ── 9-1. 대시보드 통계 ────────────────────────────────────────────
export const adminStatsService = {
  dashboard() {
    return adminApiClient.get<DashboardStats>("/admin/stats/dashboard");
  },
};

// ── 9-2. 유저 관리 ────────────────────────────────────────────────
export const adminUsersService = {
  list(params: AdminUsersParams = {}) {
    return adminApiClient.get<Paginated<AdminUserItem>>("/admin/users", {
      params,
    });
  },
  setActive(userId: string, isActive: boolean) {
    return adminApiClient.patch<AdminUserItem>(`/admin/users/${userId}`, {
      is_active: isActive,
    });
  },
};

// ── 9-3. 채팅 모니터링 ────────────────────────────────────────────
export const adminChatLogsService = {
  list(params: AdminChatLogsParams = {}) {
    return adminApiClient.get<Paginated<ChatMonitorItem>>(
      "/admin/chats/logs",
      { params }
    );
  },
};

// ── 9-4. 감사 로그 ────────────────────────────────────────────────
export const adminAuditService = {
  list(params: { page?: number; size?: number } = {}) {
    return adminApiClient.get<Paginated<AuditLogItem> | AuditLogItem[]>(
      "/admin/audit-logs",
      { params }
    );
  },
};

// ── 9-5. 배치 작업 ────────────────────────────────────────────────
export const adminBatchService = {
  status() {
    return adminApiClient.get<BatchStatusItem[]>("/admin/batch/status");
  },
  logs(jobId: string) {
    return adminApiClient.get<BatchLogDetail>(`/admin/batch/logs/${jobId}`);
  },
};

// ── 9-6. 정책 관리 ────────────────────────────────────────────────
export const adminPolicyService = {
  create(body: AdminPolicyCreateRequest) {
    return adminApiClient.post<PolicyDetail>("/admin/policies", body);
  },
  update(policyId: string, body: AdminPolicyUpdateRequest) {
    return adminApiClient.patch<PolicyDetail>(
      `/admin/policies/${policyId}`,
      body
    );
  },
  syncBootstrap() {
    return adminApiClient.post<PolicySyncResult>(
      "/admin/policies/sync/bootstrap"
    );
  },
  syncDaily() {
    return adminApiClient.post<PolicySyncResult>("/admin/policies/sync/daily");
  },
  syncRun(params: PolicySyncRunParams) {
    return adminApiClient.post<PolicySyncResult>(
      "/admin/policies/sync/run",
      null,
      { params }
    );
  },
  embedAll(limit?: number) {
    return adminApiClient.post<PolicyEmbedResult>(
      "/admin/policies/embed/all",
      null,
      { params: limit !== undefined ? { limit } : undefined }
    );
  },
  testSyncOne() {
    return adminApiClient.post<TestSyncOneResult>("/admin/test-sync-one");
  },
  listDebugOutputs() {
    return adminApiClient.get<{ items: DebugOutputItem[] }>("/admin/debug-output");
  },
  getDebugOutput(originId: string) {
    return adminApiClient.get<DebugOutputFiles>(`/admin/debug-output/${originId}`);
  },
  syncFull(params: { with_ai?: boolean; rows_per_page?: number } = {}) {
    return adminApiClient.post<{ status: string; message?: string }>(
      "/admin/policies/sync/full",
      null,
      { params }
    );
  },
};

// ── 9-7. 비즈픽 콘텐츠 관리 ──────────────────────────────────────
export const adminContentService = {
  list(params: { page?: number; size?: number; category?: string } = {}) {
    return adminApiClient.get<Paginated<BizPickContentListItem>>(
      "/admin/contents",
      { params }
    );
  },
  detail(contentId: string) {
    return adminApiClient.get<BizPickDetail>(`/admin/contents/${contentId}`);
  },
  create(body: BizPickContentCreateRequest) {
    return adminApiClient.post<BizPickDetail>("/admin/contents", body);
  },
  update(contentId: string, body: BizPickContentUpdateRequest) {
    return adminApiClient.patch<BizPickDetail>(
      `/admin/contents/${contentId}`,
      body
    );
  },
  remove(contentId: string) {
    return adminApiClient.delete<{ success: boolean }>(
      `/admin/contents/${contentId}`
    );
  },
  generateDraft(body: AiCardNewsGenerateRequest) {
    return adminApiClient.post<AiCardNewsGenerateResponse>(
      "/admin/contents/generate",
      body
    );
  },
  suggestRelated(body: AiRelatedPoliciesRequest) {
    return adminApiClient.post<AiRelatedPoliciesResponse>(
      "/admin/contents/suggest-related",
      body
    );
  },
};

// ── 9-8. 피드백 / 로직 디버깅 ────────────────────────────────────
export const adminFeedbackService = {
  list(params: FeedbackListParams = {}) {
    return adminApiClient.get<Paginated<FeedbackItem>>("/admin/feedback", {
      params,
    });
  },
  context(feedbackId: string) {
    return adminApiClient.get<FeedbackContextDetail>(
      `/admin/feedback/${feedbackId}/context`
    );
  },
  createCorrection(feedbackId: string, body: CorrectionNoteRequest) {
    return adminApiClient.post<CorrectionNoteItem>(
      `/admin/feedback/${feedbackId}/correction`,
      body
    );
  },
  listCorrections(params: { page?: number; size?: number } = {}) {
    return adminApiClient.get<Paginated<CorrectionNoteItem>>(
      "/admin/corrections",
      { params }
    );
  },
};

// ── 9-9. 시스템 건강 & 비용 모니터링 ─────────────────────────────
export const adminMonitoringService = {
  health() {
    return adminApiClient.get<SystemHealthStatus>("/admin/monitoring/health");
  },
  latency(range: MonitoringRange = "24h") {
    return adminApiClient.get<LatencyTimeSeries>("/admin/monitoring/latency", {
      params: { range },
    });
  },
  cost(date?: string) {
    return adminApiClient.get<TokenCostSummary>("/admin/monitoring/cost", {
      params: date ? { date } : undefined,
    });
  },
};

// ── 9-10. 비즈니스 인사이트 ──────────────────────────────────────
export const adminInsightsService = {
  unmetDemand(params: { page?: number; size?: number } = {}) {
    return adminApiClient.get<UnmetDemandResponse>(
      "/admin/insights/unmet-demand",
      { params }
    );
  },
  conversion(params: { from?: string; to?: string } = {}) {
    return adminApiClient.get<ConversionStats>(
      "/admin/insights/conversion",
      { params }
    );
  },
};

// 편의상 모든 서비스를 하나로 묶은 facade
export const adminService = {
  auth: adminAuthService,
  stats: adminStatsService,
  users: adminUsersService,
  chatLogs: adminChatLogsService,
  audit: adminAuditService,
  batch: adminBatchService,
  policies: adminPolicyService,
  contents: adminContentService,
  feedback: adminFeedbackService,
  monitoring: adminMonitoringService,
  insights: adminInsightsService,
};
