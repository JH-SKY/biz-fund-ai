"use client";

/**
 * /admin/batch — 배치 작업 현황 모니터링.
 *
 * 기능
 *  - job 카드 그리드 (상태별 색상 배지)
 *  - RUNNING 상태 job은 3초 자동 갱신 (useBatchStatus 내부에서 처리)
 *  - RUNNING job에 progress bar + 4종 카운터 표시
 *  - 로그 보기 Dialog
 */

import * as React from "react";
import {
  Clock,
  Cpu,
  FileText,
  RefreshCw,
  Terminal,
  Timer,
} from "lucide-react";

import { AdminGuard, AdminShell } from "@/components/admin";
import {
  AdminEmptyState,
  AdminErrorState,
  AdminTableSkeleton,
  mapBatchStatusToTone,
} from "@/features/admin";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useBatchLogs, useBatchStatus } from "@/hooks/useAdmin";
import type { ApiError } from "@/types";

export default function AdminBatchPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <BatchContent />
      </AdminShell>
    </AdminGuard>
  );
}

function BatchContent() {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useBatchStatus();
  const [openJobId, setOpenJobId] = React.useState<string | null>(null);

  const jobs = data ?? [];
  const hasRunning = jobs.some((j) => j.status === "RUNNING");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">정책 수집 현황</h2>
          <p className="mt-0.5 text-sm text-ink-secondary">
            정책 수집·임베딩 등 모든 수집 job을 실시간으로 감시합니다.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {hasRunning && (
            <span className="flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
              실행 중 · 3초 자동 갱신
            </span>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
            새로고침
          </Button>
        </div>
      </div>

      {isLoading ? (
        <AdminTableSkeleton rows={4} />
      ) : isError ? (
        <AdminErrorState
          message={(error as unknown as ApiError)?.message}
          onRetry={() => refetch()}
        />
      ) : jobs.length === 0 ? (
        <AdminEmptyState icon={Cpu} title="아직 수집 이력이 없습니다" />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {jobs.map((job) => {
            const tone = mapBatchStatusToTone(String(job.status));
            const isRunning = job.status === "RUNNING";
            const pct =
              job.total_count && job.processed_count != null && job.total_count > 0
                ? Math.min(100, Math.round((job.processed_count / job.total_count) * 100))
                : null;

            return (
              <Card key={job.job_id} className={isRunning ? "border-blue-300 shadow-md" : ""}>
                <CardHeader className="flex flex-row items-start justify-between pb-2">
                  <div className="min-w-0">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Cpu className={cn("h-4 w-4", isRunning ? "text-blue-600" : "text-primary-600")} />
                      <span className="truncate">{job.job_name}</span>
                    </CardTitle>
                    <CardDescription className="truncate text-[11px]">
                      #{job.job_id}
                    </CardDescription>
                  </div>
                  <span
                    className={cn(
                      "rounded-md px-2 py-1 text-xs font-semibold shrink-0",
                      tone.className
                    )}
                  >
                    {tone.label}
                  </span>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  {/* 진행 바 (RUNNING + total_count 있을 때) */}
                  {isRunning && pct !== null && (
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px] text-ink-tertiary">
                        <span>진행률</span>
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
                  {(job.total_count != null || job.processed_count != null) && (
                    <div className="grid grid-cols-4 gap-1 text-center">
                      {[
                        { label: "전체", value: job.total_count },
                        { label: "처리", value: job.processed_count },
                        { label: "성공", value: job.success_count },
                        { label: "실패", value: job.fail_count },
                      ].map(({ label, value }) => (
                        <div key={label} className="rounded bg-surface-muted px-1 py-1.5">
                          <p className="text-[9px] text-ink-tertiary">{label}</p>
                          <p className="text-xs font-bold text-ink numeric">
                            {value != null ? value.toLocaleString() : "—"}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center gap-2 text-ink-secondary">
                    <Clock className="h-3.5 w-3.5 text-ink-tertiary" />
                    <span>마지막 실행</span>
                    <span className="ml-auto numeric text-xs">
                      {job.last_run
                        ? new Date(job.last_run).toLocaleString("ko-KR")
                        : "—"}
                    </span>
                  </div>
                  {job.next_run && (
                    <div className="flex items-center gap-2 text-ink-secondary">
                      <Timer className="h-3.5 w-3.5 text-ink-tertiary" />
                      <span>다음 실행</span>
                      <span className="ml-auto numeric text-xs">
                        {new Date(job.next_run).toLocaleString("ko-KR")}
                      </span>
                    </div>
                  )}
                  {job.duration_ms != null && (
                    <div className="flex items-center gap-2 text-ink-secondary">
                      <FileText className="h-3.5 w-3.5 text-ink-tertiary" />
                      <span>소요 시간</span>
                      <span className="ml-auto numeric text-xs">
                        {(job.duration_ms / 1000).toFixed(1)}초
                      </span>
                    </div>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2 w-full justify-center"
                    onClick={() => setOpenJobId(job.job_id)}
                  >
                    <Terminal className="h-3.5 w-3.5" />
                    실행 로그 보기
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <BatchLogsDialog
        jobId={openJobId}
        onClose={() => setOpenJobId(null)}
      />
    </div>
  );
}

function BatchLogsDialog({
  jobId,
  onClose,
}: {
  jobId: string | null;
  onClose: () => void;
}) {
  const { data, isLoading, isError, error } = useBatchLogs(jobId);

  return (
    <Dialog
      open={!!jobId}
      onOpenChange={(open) => !open && onClose()}
      title="배치 실행 로그"
      description={jobId ? `#${jobId}` : undefined}
      className="sm:max-w-3xl"
    >
      {isLoading ? (
        <AdminTableSkeleton rows={6} />
      ) : isError ? (
        <AdminErrorState message={(error as unknown as ApiError)?.message} />
      ) : !data ? (
        <p className="text-sm text-ink-tertiary">로그를 불러오는 중…</p>
      ) : (
        <pre className="max-h-[60vh] overflow-auto rounded-lg bg-ink p-4 text-[11px] leading-relaxed text-white/90">
          {data.raw_log || "(로그 비어있음)"}
        </pre>
      )}
    </Dialog>
  );
}
