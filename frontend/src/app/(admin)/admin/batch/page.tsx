"use client";

/**
 * /admin/batch — 배치 작업 현황 모니터링.
 *
 * 기능
 *  - job 카드 그리드 (상태별 색상 배지)
 *  - 실행 중인 job 은 refetchInterval 로 자동 갱신 (15초)
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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">배치 작업 현황</h2>
          <p className="mt-0.5 text-sm text-ink-secondary">
            정책 수집·임베딩·알림 발송 등 모든 배치 job 을 실시간으로 감시합니다.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw
            className={cn("h-4 w-4", isFetching && "animate-spin")}
          />
          새로고침
        </Button>
      </div>

      {isLoading ? (
        <AdminTableSkeleton rows={4} />
      ) : isError ? (
        <AdminErrorState
          message={(error as unknown as ApiError)?.message}
          onRetry={() => refetch()}
        />
      ) : jobs.length === 0 ? (
        <AdminEmptyState icon={Cpu} title="등록된 배치 작업이 없습니다" />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {jobs.map((job) => {
            const tone = mapBatchStatusToTone(String(job.status));
            return (
              <Card key={job.job_id}>
                <CardHeader className="flex flex-row items-start justify-between">
                  <div className="min-w-0">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Cpu className="h-4 w-4 text-primary-600" />
                      <span className="truncate">{job.job_name}</span>
                    </CardTitle>
                    <CardDescription className="truncate">
                      #{job.job_id}
                    </CardDescription>
                  </div>
                  <span
                    className={cn(
                      "rounded-md px-2 py-1 text-xs font-semibold",
                      tone.className
                    )}
                  >
                    {tone.label}
                  </span>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-ink-secondary">
                    <Clock className="h-3.5 w-3.5 text-ink-tertiary" />
                    <span>마지막 실행</span>
                    <span className="ml-auto numeric">
                      {job.last_run
                        ? new Date(job.last_run).toLocaleString("ko-KR")
                        : "—"}
                    </span>
                  </div>
                  {job.next_run && (
                    <div className="flex items-center gap-2 text-ink-secondary">
                      <Timer className="h-3.5 w-3.5 text-ink-tertiary" />
                      <span>다음 실행</span>
                      <span className="ml-auto numeric">
                        {new Date(job.next_run).toLocaleString("ko-KR")}
                      </span>
                    </div>
                  )}
                  {job.duration_ms != null && (
                    <div className="flex items-center gap-2 text-ink-secondary">
                      <FileText className="h-3.5 w-3.5 text-ink-tertiary" />
                      <span>소요 시간</span>
                      <span className="ml-auto numeric">
                        {(job.duration_ms / 1000).toFixed(1)}초
                      </span>
                    </div>
                  )}
                  {job.processed_count != null && (
                    <div className="flex items-center gap-2 text-ink-secondary">
                      <FileText className="h-3.5 w-3.5 text-ink-tertiary" />
                      <span>처리 건수</span>
                      <span className="ml-auto numeric">
                        {job.processed_count.toLocaleString()}
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
