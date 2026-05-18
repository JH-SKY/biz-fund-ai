"use client";

/**
 * /admin/policies — 정책 관리.
 *
 * 기능
 *  - 5종 수집 트리거 버튼: bootstrap / daily / run(파라미터) / 파이프라인 테스트 / embed-all
 *  - 전수 수집 버튼: POST /admin/policies/sync/full (백그라운드 실행, 즉시 응답)
 *  - 동기화 현황 Dialog: 실시간 폴링으로 진행 상황 표시
 *  - 파이프라인 테스트: POST /admin/test-sync-one → 랜덤 1건 수집 후 결과 토스트 + 디버그 파일 자동 열기
 *  - 응답 목록: debug_output 폴더 목록 조회 → 3개 파일 내용 뷰어
 *  - 전체 정책 검색 + 테이블 조회
 *  - 신규 정책 등록 / 정책 수정 Dialog
 */

import * as React from "react";
import {
  Activity,
  Brain,
  Calendar,
  ChevronRight,
  CloudDownload,
  Database,
  Download,
  Edit3,
  FileJson,
  FileText,
  FlaskConical,
  Layers,
  List,
  Play,
  Plus,
  RefreshCw,
  Search,
  X,
} from "lucide-react";

import { AdminGuard, AdminShell } from "@/components/admin";
import {
  AdminEmptyState,
  AdminErrorState,
  AdminPagination,
  AdminTableSkeleton,
  mapBatchStatusToTone,
} from "@/features/admin";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { usePolicyDetail, usePolicySearch } from "@/hooks/usePolicies";
import {
  useBatchStatus,
  useCreatePolicy,
  useDebugOutput,
  useDebugOutputs,
  useEmbedAll,
  useSyncBootstrap,
  useSyncDaily,
  useSyncFull,
  useSyncRun,
  useTestSyncOne,
  useUpdatePolicy,
} from "@/hooks/useAdmin";
import { useToast } from "@/providers/ToastProvider";
import type {
  AdminPolicyCreateRequest,
  AdminPolicyUpdateRequest,
  ApiError,
  BatchStatusItem,
  PolicyListItem,
  PolicySyncRunParams,
} from "@/types";
import type { DebugOutputItem } from "@/lib/services/admin.service";

export default function AdminPoliciesPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <PoliciesContent />
      </AdminShell>
    </AdminGuard>
  );
}

function PoliciesContent() {
  const toast = useToast();
  const [keywordInput, setKeywordInput] = React.useState("");
  const [keyword, setKeyword] = React.useState("");
  const [page, setPage] = React.useState(1);

  const [createOpen, setCreateOpen] = React.useState(false);
  const [editTarget, setEditTarget] = React.useState<PolicyListItem | null>(null);
  const [syncRunOpen, setSyncRunOpen] = React.useState(false);
  const [debugListOpen, setDebugListOpen] = React.useState(false);
  const [debugViewOriginId, setDebugViewOriginId] = React.useState<string | null>(null);
  const [syncMonitorOpen, setSyncMonitorOpen] = React.useState(false);

  React.useEffect(() => {
    const t = setTimeout(() => {
      setKeyword(keywordInput.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [keywordInput]);

  const { data, isLoading, isError, error, refetch } = usePolicySearch({
    keyword: keyword || undefined,
    page,
    size: 20,
  });

  // 배치 상태 (RUNNING 중이면 3초 폴링)
  const { data: batchData } = useBatchStatus();
  const syncJobs = (batchData ?? []).filter(
    (j) =>
      j.job_name === "POLICY_FULL_SYNC" ||
      j.job_name === "POLICY_BOOTSTRAP" ||
      j.job_name === "POLICY_ADMIN_MANUAL" ||
      j.job_name === "POLICY_DAILY_SYNC"
  );
  const runningJob = syncJobs.find((j) => j.status === "RUNNING");
  const lastDoneJob = syncJobs
    .filter((j) => j.status === "SUCCESS" || j.status === "FAILED")
    .sort((a, b) => (b.last_run ?? "").localeCompare(a.last_run ?? ""))[0];

  const policies = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;
  const totalCount = data?.total_count ?? 0;

  // 트리거 mutations
  const bootstrap = useSyncBootstrap();
  const daily = useSyncDaily();
  const embedAll = useEmbedAll();
  const testSyncOne = useTestSyncOne();
  const syncFull = useSyncFull();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleBgTrigger = async (label: string, fn: () => Promise<any>) => {
    try {
      await fn();
      toast.success(`${label} 시작됨`, {
        message: "백그라운드에서 수집 중입니다. 정책 수집 현황에서 진행상황을 확인하세요.",
      });
    } catch (err) {
      toast.error(`${label} 실패`, { message: (err as unknown as ApiError).message });
    }
  };

  const handleTestSyncOne = async () => {
    try {
      const res = await testSyncOne.mutateAsync();
      const statusLabel = res.ai_status === "SUCCESS" ? "성공" : res.ai_status;
      toast.success("파이프라인 테스트 완료", {
        message: `AI: ${statusLabel} · 페이지: ${res.tested_page} · ${res.origin_id.slice(0, 8)}...`,
      });
      setDebugViewOriginId(res.origin_id);
    } catch (err) {
      toast.error("파이프라인 테스트 실패", { message: (err as unknown as ApiError).message });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">정책 관리</h2>
          <p className="mt-0.5 text-sm text-ink-secondary">
            정책 공고를 수집·수정·임베딩합니다.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setDebugListOpen(true)}>
            <List className="h-4 w-4" />
            응답 목록
          </Button>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" />
            정책 수기 등록
          </Button>
        </div>
      </div>

      {/* 데이터 수집 트리거 */}
      <Card className="border-primary-200 bg-primary-50/30">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <Database className="h-4 w-4 text-primary-600" />
                정책 데이터 수집 & 임베딩
              </CardTitle>
              <CardDescription className="mt-1">
                외부 API(기업마당)에서 정책을 가져오거나, 기존 정책을 벡터화합니다.
              </CardDescription>
            </div>
            <div className="flex flex-col items-end gap-1 shrink-0">
              {runningJob ? (
                <button
                  type="button"
                  onClick={() => setSyncMonitorOpen(true)}
                  className="flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-200 transition-colors"
                >
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
                  수집 중 · 현황 보기
                </button>
              ) : lastDoneJob ? (
                <span className="text-[11px] text-ink-tertiary">
                  마지막 동기화:{" "}
                  {lastDoneJob.last_run
                    ? new Date(lastDoneJob.last_run).toLocaleString("ko-KR")
                    : "—"}{" "}
                  <span
                    className={cn(
                      "font-semibold",
                      lastDoneJob.status === "SUCCESS" ? "text-green-600" : "text-red-500"
                    )}
                  >
                    {lastDoneJob.status === "SUCCESS" ? "완료" : "실패"}
                  </span>
                </span>
              ) : null}
              {(runningJob || lastDoneJob) && (
                <button
                  type="button"
                  onClick={() => setSyncMonitorOpen(true)}
                  className="text-[11px] text-primary-600 hover:underline"
                >
                  <Activity className="inline h-3 w-3 mr-0.5" />
                  동기화 현황 보기
                </button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <SyncTriggerButton
            icon={CloudDownload}
            label="부트스트랩 적재"
            hint="1,000건 대량"
            loading={bootstrap.isPending}
            onClick={() => handleBgTrigger("부트스트랩 적재", () => bootstrap.mutateAsync())}
          />
          <SyncTriggerButton
            icon={Download}
            label="전수 수집"
            hint="전체 공고 자동"
            loading={syncFull.isPending}
            highlight
            onClick={() => handleBgTrigger("전수 수집", () => syncFull.mutateAsync({}))}
          />
          <SyncTriggerButton
            icon={Calendar}
            label="일일 동기화"
            hint="오늘 신규 공고만"
            loading={daily.isPending}
            onClick={() => handleBgTrigger("일일 동기화", () => daily.mutateAsync())}
          />
          <SyncTriggerButton
            icon={Play}
            label="범위 지정 수집"
            hint="페이지·날짜 지정"
            onClick={() => setSyncRunOpen(true)}
          />
          <SyncTriggerButton
            icon={FlaskConical}
            label="파이프라인 테스트"
            hint="랜덤 1건 전체 검증"
            loading={testSyncOne.isPending}
            onClick={handleTestSyncOne}
          />
          <SyncTriggerButton
            icon={Brain}
            label="전체 임베딩"
            hint="미임베딩 일괄"
            loading={embedAll.isPending}
            onClick={() => handleBgTrigger("임베딩", () => embedAll.mutateAsync(undefined))}
          />
        </CardContent>
      </Card>

      {/* 검색 + 리스트 */}
      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <div className="flex-1">
            <Input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              placeholder="정책명 검색"
              leftIcon={<Search className="h-4 w-4" />}
            />
          </div>
          <span className="text-xs text-ink-tertiary numeric">
            {totalCount.toLocaleString()}건
          </span>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6">
              <AdminTableSkeleton rows={6} />
            </div>
          ) : isError ? (
            <div className="p-6">
              <AdminErrorState
                message={(error as unknown as ApiError)?.message}
                onRetry={() => refetch()}
              />
            </div>
          ) : policies.length === 0 ? (
            <AdminEmptyState
              icon={Layers}
              title="조회된 정책이 없습니다"
              description="수집 트리거 버튼으로 정책을 추가해보세요."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-muted text-xs font-semibold uppercase text-ink-secondary">
                  <tr>
                    <th className="px-4 py-3 text-left">제목</th>
                    <th className="px-4 py-3 text-left">카테고리</th>
                    <th className="px-4 py-3 text-left">마감</th>
                    <th className="px-4 py-3 text-right">관리</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {policies.map((p) => (
                    <tr key={p.policy_id} className="hover:bg-surface-muted/50">
                      <td className="px-4 py-3">
                        <p className="font-medium text-ink">{p.title}</p>
                        <p className="text-[11px] text-ink-tertiary numeric">
                          #{p.policy_id.slice(0, 8)}
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        {p.category ? (
                          <Badge variant="outline" size="sm">
                            {p.category}
                          </Badge>
                        ) : (
                          <span className="text-ink-tertiary">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-ink-tertiary numeric">
                        {p.closed_at === "9999-12-31"
                          ? "상시접수"
                          : new Date(p.closed_at).toLocaleDateString("ko-KR")}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setEditTarget(p)}
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                          수정
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <AdminPagination
          page={page}
          totalPages={totalPages}
          onChange={setPage}
        />
      )}

      {/* 신규 등록 Dialog */}
      <PolicyFormDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        mode="create"
      />

      {/* 수정 Dialog */}
      <PolicyFormDialog
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        mode="edit"
        target={editTarget}
      />

      {/* 범위 수집 Dialog */}
      <SyncRunDialog
        open={syncRunOpen}
        onClose={() => setSyncRunOpen(false)}
        onComplete={() => refetch()}
      />

      {/* 동기화 현황 Dialog */}
      <SyncMonitorDialog
        open={syncMonitorOpen}
        onClose={() => setSyncMonitorOpen(false)}
        jobs={syncJobs}
      />

      {/* 디버그 출력 목록 Dialog */}
      <DebugOutputListDialog
        open={debugListOpen}
        onClose={() => setDebugListOpen(false)}
        onSelect={(originId) => setDebugViewOriginId(originId)}
      />

      {/* 디버그 파일 뷰어 Dialog */}
      <DebugFileViewerDialog
        originId={debugViewOriginId}
        onClose={() => setDebugViewOriginId(null)}
      />
    </div>
  );
}

// ── 수집 트리거 버튼 ────────────────────────────────────────────────
function SyncTriggerButton({
  icon: Icon,
  label,
  hint,
  onClick,
  loading,
  highlight,
}: {
  icon: React.ElementType;
  label: string;
  hint: string;
  onClick: () => void;
  loading?: boolean;
  highlight?: boolean;
}) {
  const baseColor = highlight
    ? "border-green-300 bg-green-50/40 hover:border-green-500 hover:bg-green-50"
    : "border-primary-200 bg-surface hover:border-primary-400 hover:bg-primary-50";
  const iconColor = highlight
    ? "bg-green-100 text-green-700 group-hover:bg-green-600 group-hover:text-white"
    : "bg-primary-100 text-primary-700 group-hover:bg-primary-600 group-hover:text-white";

  return (
    <button
      type="button"
      disabled={loading}
      onClick={onClick}
      className={`group flex items-center gap-3 rounded-lg border p-3 text-left transition-colors disabled:opacity-60 ${baseColor}`}
    >
      <div className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${iconColor}`}>
        {loading ? (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
        ) : (
          <Icon className="h-5 w-5" />
        )}
      </div>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-ink">{label}</p>
        <p className="text-xs text-ink-tertiary">{hint}</p>
      </div>
    </button>
  );
}

// ── 동기화 현황 Dialog ──────────────────────────────────────────────
function SyncMonitorDialog({
  open,
  onClose,
  jobs,
}: {
  open: boolean;
  onClose: () => void;
  jobs: BatchStatusItem[];
}) {
  const JOB_LABELS: Record<string, string> = {
    POLICY_FULL_SYNC: "전수 수집",
    POLICY_BOOTSTRAP: "부트스트랩 적재",
    POLICY_ADMIN_MANUAL: "범위 지정 수집",
    POLICY_DAILY_SYNC: "일일 동기화",
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => !v && onClose()}
      title={
        <span className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-blue-600" />
          동기화 현황
        </span>
      }
      description="수집 작업의 실시간 진행 상황입니다. 실행 중일 때 자동으로 갱신됩니다."
      className="sm:max-w-lg"
      footer={
        <Button type="button" variant="ghost" onClick={onClose}>
          닫기
        </Button>
      }
    >
      <div className="space-y-3">
        {jobs.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-ink-tertiary">
            <Database className="h-8 w-8 opacity-30" />
            <p className="text-sm">실행된 수집 작업이 없습니다.</p>
          </div>
        ) : (
          jobs.map((job) => {
            const tone = mapBatchStatusToTone(String(job.status));
            const pct =
              job.total_count && job.processed_count != null && job.total_count > 0
                ? Math.min(100, Math.round((job.processed_count / job.total_count) * 100))
                : null;

            return (
              <div
                key={job.job_id}
                className="rounded-lg border border-surface-border bg-surface p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-ink">
                    {JOB_LABELS[job.job_name] ?? job.job_name}
                  </span>
                  <span className={cn("rounded-md px-2 py-0.5 text-xs font-semibold", tone.className)}>
                    {tone.label}
                  </span>
                </div>

                {/* 진행 바 */}
                {job.status === "RUNNING" && pct !== null && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-ink-tertiary">
                      <span>진행 중</span>
                      <span className="numeric">{pct}%</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-surface-muted">
                      <div
                        className="h-full rounded-full bg-blue-500 transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* 4종 카운터 */}
                <div className="grid grid-cols-4 gap-2 text-center">
                  {[
                    { label: "전체", value: job.total_count },
                    { label: "처리", value: job.processed_count },
                    { label: "성공", value: job.success_count },
                    { label: "실패", value: job.fail_count },
                  ].map(({ label, value }) => (
                    <div key={label} className="rounded bg-surface-muted px-2 py-1.5">
                      <p className="text-[10px] text-ink-tertiary">{label}</p>
                      <p className="text-sm font-bold text-ink numeric">
                        {value != null ? value.toLocaleString() : "—"}
                      </p>
                    </div>
                  ))}
                </div>

                {job.last_run && (
                  <p className="text-[11px] text-ink-tertiary">
                    시작:{" "}
                    {new Date(job.last_run).toLocaleString("ko-KR")}
                    {job.duration_ms != null &&
                      ` · 소요 ${(job.duration_ms / 1000).toFixed(1)}초`}
                  </p>
                )}
              </div>
            );
          })
        )}
      </div>
    </Dialog>
  );
}

// ── 디버그 출력 목록 Dialog ─────────────────────────────────────────
function DebugOutputListDialog({
  open,
  onClose,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  onSelect: (originId: string) => void;
}) {
  const { data, isLoading, refetch } = useDebugOutputs(open);
  const items: DebugOutputItem[] = data?.items ?? [];

  const FILE_LABELS: Record<string, string> = {
    "1_api_raw.json": "API 원본",
    "2_ai_input.txt": "AI 입력",
    "3_ai_result.json": "AI 결과",
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => !v && onClose()}
      title="파이프라인 테스트 이력"
      description="test-sync-one 실행 기록입니다. 항목을 클릭하면 단계별 파일을 확인할 수 있습니다."
      className="sm:max-w-lg"
      footer={
        <Button type="button" variant="ghost" onClick={onClose}>
          닫기
        </Button>
      }
    >
      <div className="space-y-2">
        <div className="flex items-center justify-between pb-1">
          <span className="text-xs text-ink-tertiary">{items.length}건</span>
          <button
            type="button"
            onClick={() => refetch()}
            className="flex items-center gap-1 text-xs text-ink-secondary hover:text-ink"
          >
            <RefreshCw className="h-3 w-3" />
            새로고침
          </button>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-surface-muted" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-ink-tertiary">
            <FlaskConical className="h-8 w-8 opacity-40" />
            <p className="text-sm">테스트 이력이 없습니다.</p>
            <p className="text-xs">파이프라인 테스트 버튼을 눌러 시작하세요.</p>
          </div>
        ) : (
          <ul className="divide-y divide-surface-border overflow-hidden rounded-lg border border-surface-border">
            {items.map((item) => (
              <li key={item.origin_id}>
                <button
                  type="button"
                  onClick={() => {
                    onSelect(item.origin_id);
                    onClose();
                  }}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-muted/60 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-sm font-medium text-ink truncate">
                      {item.origin_id}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {item.files.map((f) => (
                        <span
                          key={f}
                          className="inline-flex items-center gap-1 rounded-full bg-primary-100 px-2 py-0.5 text-[10px] font-medium text-primary-700"
                        >
                          {FILE_LABELS[f] ?? f}
                        </span>
                      ))}
                      {(["1_api_raw.json", "2_ai_input.txt", "3_ai_result.json"] as const)
                        .filter((f) => !item.files.includes(f))
                        .map((f) => (
                          <span
                            key={f}
                            className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-500"
                          >
                            {FILE_LABELS[f] ?? f} 없음
                          </span>
                        ))}
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 flex-shrink-0 text-ink-tertiary" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Dialog>
  );
}

// ── 디버그 파일 뷰어 Dialog ─────────────────────────────────────────
const DEBUG_TABS = [
  { key: "1_api_raw.json" as const, label: "1. API 원본", icon: FileJson, lang: "json" },
  { key: "2_ai_input.txt" as const, label: "2. AI 입력", icon: FileText, lang: "text" },
  { key: "3_ai_result.json" as const, label: "3. AI 결과", icon: FileJson, lang: "json" },
];

function DebugFileViewerDialog({
  originId,
  onClose,
}: {
  originId: string | null;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = React.useState<string>("1_api_raw.json");
  const { data, isLoading } = useDebugOutput(originId);

  React.useEffect(() => {
    if (originId) setActiveTab("1_api_raw.json");
  }, [originId]);

  const formatContent = (content: string | null, lang: string): string => {
    if (!content) return "";
    if (lang === "json") {
      try {
        return JSON.stringify(JSON.parse(content), null, 2);
      } catch {
        return content;
      }
    }
    return content;
  };

  const getStatusBadge = () => {
    if (!data) return null;
    const hasAll = DEBUG_TABS.every((t) => data[t.key] !== null);
    const hasNone = DEBUG_TABS.every((t) => data[t.key] === null);
    if (hasAll)
      return (
        <span className="rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-medium text-green-700">
          3개 파일 모두 정상
        </span>
      );
    if (hasNone)
      return (
        <span className="rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-medium text-red-600">
          파일 없음
        </span>
      );
    return (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700">
        일부 파일 누락
      </span>
    );
  };

  return (
    <Dialog
      open={!!originId}
      onOpenChange={(v) => !v && onClose()}
      title={
        <span className="flex items-center gap-2">
          <FlaskConical className="h-4 w-4 text-amber-600" />
          디버그 파일 뷰어
          {getStatusBadge()}
        </span>
      }
      description={
        originId ? (
          <span className="font-mono text-xs">{originId}</span>
        ) : undefined
      }
      className="sm:max-w-3xl"
      footer={
        <Button type="button" variant="ghost" onClick={onClose}>
          <X className="h-4 w-4" />
          닫기
        </Button>
      }
    >
      {isLoading ? (
        <div className="space-y-3">
          <div className="h-8 w-64 animate-pulse rounded bg-surface-muted" />
          <div className="h-64 animate-pulse rounded-lg bg-surface-muted" />
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex gap-1 rounded-lg bg-surface-muted p-1">
            {DEBUG_TABS.map((tab) => {
              const hasFile = data?.[tab.key] !== null && data?.[tab.key] !== undefined;
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-surface text-ink shadow-sm"
                      : "text-ink-secondary hover:text-ink"
                  }`}
                >
                  <tab.icon className="h-3.5 w-3.5" />
                  {tab.label}
                  {!hasFile && (
                    <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
                  )}
                </button>
              );
            })}
          </div>

          {(() => {
            const tab = DEBUG_TABS.find((t) => t.key === activeTab) ?? DEBUG_TABS[0];
            const content = formatContent((data?.[tab.key] as string | null) ?? null, tab.lang);
            if (!content) {
              return (
                <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-surface-border py-12 text-ink-tertiary">
                  <tab.icon className="h-8 w-8 opacity-30" />
                  <p className="text-sm">파일이 없습니다.</p>
                  <p className="text-xs">
                    {activeTab === "1_api_raw.json" && "API 호출이 실패했거나 파일이 저장되지 않았습니다."}
                    {activeTab === "2_ai_input.txt" && "파싱 단계에서 실패하여 AI에게 전달되지 않았습니다."}
                    {activeTab === "3_ai_result.json" && "AI 구조화가 실패하거나 아직 완료되지 않았습니다."}
                  </p>
                </div>
              );
            }
            return (
              <div className="relative">
                <div className="absolute right-2 top-2 z-10">
                  <button
                    type="button"
                    onClick={() => navigator.clipboard.writeText(content)}
                    className="rounded bg-surface/80 px-2 py-1 text-[10px] text-ink-secondary hover:text-ink backdrop-blur"
                  >
                    복사
                  </button>
                </div>
                <pre className="max-h-[480px] overflow-auto rounded-lg bg-gray-950 p-4 text-xs leading-relaxed text-green-300 font-mono">
                  <code>{content}</code>
                </pre>
              </div>
            );
          })()}
        </div>
      )}
    </Dialog>
  );
}

// ── 정책 생성/수정 Dialog ─────────────────────────────────────────
function PolicyFormDialog({
  open,
  onClose,
  mode,
  target,
}: {
  open: boolean;
  onClose: () => void;
  mode: "create" | "edit";
  target?: PolicyListItem | null;
}) {
  const toast = useToast();
  const createMut = useCreatePolicy();
  const updateMut = useUpdatePolicy();
  const { data: detailData } = usePolicyDetail(target?.policy_id);

  const [form, setForm] = React.useState<AdminPolicyCreateRequest>({
    title: "",
    content: "",
    agency_name: "",
    category: "",
    apply_url: "",
    closed_at: "",
    support_amount: "",
  });

  React.useEffect(() => {
    if (open && target) {
      const detail = detailData;
      setForm({
        title: detail?.title ?? target.title,
        content: detail?.content ?? "",
        agency_name: detail?.agency_name ?? "",
        category: detail?.category ?? target.category ?? "",
        apply_url: detail?.apply_url ?? "",
        closed_at: detail?.closed_at ?? target.closed_at,
        support_amount: detail?.support_amount ?? "",
      });
    }
    if (open && !target) {
      setForm({
        title: "",
        content: "",
        agency_name: "",
        category: "",
        apply_url: "",
        closed_at: "",
        support_amount: "",
      });
    }
  }, [detailData, open, target]);

  const isPending = createMut.isPending || updateMut.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.agency_name.trim()) {
      toast.warning("제목과 주관기관은 필수입니다.");
      return;
    }
    const payload = { ...form };
    if (mode === "create") {
      createMut.mutate(payload, {
        onSuccess: () => {
          toast.success("정책이 등록되었습니다.");
          onClose();
        },
        onError: (err) =>
          toast.error("등록 실패", { message: (err as unknown as ApiError).message }),
      });
    } else if (target) {
      const body: AdminPolicyUpdateRequest = payload;
      updateMut.mutate(
        { policyId: target.policy_id, body },
        {
          onSuccess: () => {
            toast.success("정책이 수정되었습니다.");
            onClose();
          },
          onError: (err) =>
            toast.error("수정 실패", { message: (err as unknown as ApiError).message }),
        }
      );
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => !v && onClose()}
      title={mode === "create" ? "정책 수기 등록" : "정책 수정"}
      description="외부 API로 수집되지 않는 공고를 직접 등록하거나 기존 공고를 보정합니다."
      className="sm:max-w-2xl"
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>
            취소
          </Button>
          <Button type="submit" form="policy-form" loading={isPending} disabled={isPending}>
            {mode === "create" ? "등록" : "저장"}
          </Button>
        </>
      }
    >
      <form id="policy-form" onSubmit={handleSubmit} className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="p-title">제목 *</Label>
          <Input
            id="p-title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="예: 소상공인 경영안정자금"
            required
          />
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="p-agency">주관기관 *</Label>
            <Input
              id="p-agency"
              value={form.agency_name}
              onChange={(e) => setForm({ ...form, agency_name: e.target.value })}
              placeholder="소상공인시장진흥공단"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-category">카테고리</Label>
            <Input
              id="p-category"
              value={form.category ?? ""}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              placeholder="융자 / 보조금 / 보증 ..."
            />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="p-amount">지원 금액</Label>
            <Input
              id="p-amount"
              value={form.support_amount ?? ""}
              onChange={(e) => setForm({ ...form, support_amount: e.target.value })}
              placeholder="최대 7천만원"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-closed">마감일 (YYYY-MM-DD)</Label>
            <Input
              id="p-closed"
              value={form.closed_at ?? ""}
              onChange={(e) => setForm({ ...form, closed_at: e.target.value })}
              placeholder="2026-12-31"
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="p-url">신청 URL</Label>
          <Input
            id="p-url"
            value={form.apply_url ?? ""}
            onChange={(e) => setForm({ ...form, apply_url: e.target.value })}
            placeholder="https://..."
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="p-content">본문</Label>
          <textarea
            id="p-content"
            rows={6}
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            placeholder="정책 상세 설명..."
          />
        </div>
      </form>
    </Dialog>
  );
}

// ── 범위 수집 Dialog ───────────────────────────────────────────────
function SyncRunDialog({
  open,
  onClose,
  onComplete,
}: {
  open: boolean;
  onClose: () => void;
  onComplete: () => void;
}) {
  const toast = useToast();
  const { mutate, isPending } = useSyncRun();
  const [params, setParams] = React.useState<PolicySyncRunParams>({
    page_start: 1,
    page_end: 10,
    rows_per_page: 20,
    with_ai: false,
    date_from: "",
    date_to: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutate(
      {
        ...params,
        date_from: params.date_from || undefined,
        date_to: params.date_to || undefined,
      },
      {
        onSuccess: () => {
          toast.success("범위 수집 시작됨", {
            message: "백그라운드에서 수집 중입니다.",
          });
          onComplete();
          onClose();
        },
        onError: (err) => {
          toast.error("수집 실패", { message: (err as unknown as ApiError).message });
        },
      }
    );
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => !v && onClose()}
      title="범위 지정 정책 수집"
      description="기업마당 API 페이지·날짜 범위를 지정하여 수집합니다."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>
            취소
          </Button>
          <Button type="submit" form="sync-run-form" loading={isPending} disabled={isPending}>
            <Play className="h-4 w-4" />
            실행
          </Button>
        </>
      }
    >
      <form id="sync-run-form" onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1.5">
            <Label>시작 페이지</Label>
            <Input
              type="number"
              min={1}
              value={params.page_start ?? 1}
              onChange={(e) => setParams({ ...params, page_start: Number(e.target.value) })}
            />
          </div>
          <div className="space-y-1.5">
            <Label>끝 페이지</Label>
            <Input
              type="number"
              min={1}
              value={params.page_end ?? 10}
              onChange={(e) => setParams({ ...params, page_end: Number(e.target.value) })}
            />
          </div>
          <div className="space-y-1.5">
            <Label>페이지당 건수</Label>
            <Input
              type="number"
              min={1}
              max={100}
              value={params.rows_per_page ?? 20}
              onChange={(e) => setParams({ ...params, rows_per_page: Number(e.target.value) })}
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>시작일 (옵션)</Label>
            <Input
              type="date"
              value={params.date_from ?? ""}
              onChange={(e) => setParams({ ...params, date_from: e.target.value })}
            />
          </div>
          <div className="space-y-1.5">
            <Label>종료일 (옵션)</Label>
            <Input
              type="date"
              value={params.date_to ?? ""}
              onChange={(e) => setParams({ ...params, date_to: e.target.value })}
            />
          </div>
        </div>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={params.with_ai ?? false}
            onChange={(e) => setParams({ ...params, with_ai: e.target.checked })}
            className="h-4 w-4 rounded border-surface-border text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm text-ink">수집 후 AI 임베딩까지 자동 실행</span>
        </label>
      </form>
    </Dialog>
  );
}
