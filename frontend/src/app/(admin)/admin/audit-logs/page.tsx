"use client";

/**
 * /admin/audit-logs — 관리자 데이터 수정 이력 (감사 로그).
 *
 * PAGE 12 §4 예외 상황 및 보안 정책:
 *  "로직이나 정책 데이터를 수정한 관리자와 수정 시간을 기록(Log)하여 사고 방지."
 */

import * as React from "react";
import { ScrollText } from "lucide-react";

import { AdminGuard, AdminShell } from "@/components/admin";
import {
  AdminEmptyState,
  AdminErrorState,
  AdminPagination,
  AdminTableSkeleton,
} from "@/features/admin";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useAdminAuditLogs } from "@/hooks/useAdmin";
import type { ApiError, AuditLogItem, Paginated } from "@/types";

export default function AdminAuditLogsPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <AuditLogsContent />
      </AdminShell>
    </AdminGuard>
  );
}

function AuditLogsContent() {
  const [page, setPage] = React.useState(1);
  const { data, isLoading, isError, error, refetch } = useAdminAuditLogs(
    page,
    25
  );

  // 백엔드가 배열 또는 Paginated 로 줄 수 있어 유연하게 처리
  const items: AuditLogItem[] = Array.isArray(data)
    ? data
    : ((data as Paginated<AuditLogItem> | undefined)?.items ?? []);
  const totalCount = Array.isArray(data)
    ? data.length
    : ((data as Paginated<AuditLogItem> | undefined)?.total_count ?? 0);
  const totalPages = Array.isArray(data)
    ? 1
    : ((data as Paginated<AuditLogItem> | undefined)?.total_pages ?? 1);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-ink">감사 로그</h2>
        <p className="mt-0.5 text-sm text-ink-secondary">
          모든 관리자 활동은 감사를 위해 영구 기록됩니다.
        </p>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6">
              <AdminTableSkeleton rows={8} />
            </div>
          ) : isError ? (
            <div className="p-6">
              <AdminErrorState
                message={(error as unknown as ApiError)?.message}
                onRetry={() => refetch()}
              />
            </div>
          ) : items.length === 0 ? (
            <AdminEmptyState
              icon={ScrollText}
              title="기록된 감사 로그가 없습니다"
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-muted text-xs font-semibold uppercase text-ink-secondary">
                  <tr>
                    <th className="px-4 py-3 text-left">시각</th>
                    <th className="px-4 py-3 text-left">관리자</th>
                    <th className="px-4 py-3 text-left">작업</th>
                    <th className="px-4 py-3 text-left">대상</th>
                    <th className="px-4 py-3 text-left">IP</th>
                    <th className="px-4 py-3 text-left">변경 내용</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {items.map((log) => (
                    <tr key={log.audit_id} className="hover:bg-surface-muted/50">
                      <td className="px-4 py-3 text-xs text-ink-secondary whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString("ko-KR")}
                      </td>
                      <td className="px-4 py-3 font-medium text-ink">
                        {log.admin_name ?? log.admin_id.slice(0, 8)}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="primary" size="sm">
                          {log.action}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-ink-secondary">
                          {log.target}
                        </span>
                        {log.target_id && (
                          <span className="ml-1 text-[11px] text-ink-tertiary numeric">
                            #{log.target_id.slice(0, 8)}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-ink-tertiary numeric">
                        {log.ip_address ?? "—"}
                      </td>
                      <td className="max-w-md px-4 py-3">
                        {log.diff ? (
                          <details className="group">
                            <summary className="cursor-pointer text-xs text-primary-600 hover:underline">
                              변경사항 보기
                            </summary>
                            <pre className="mt-2 max-h-56 overflow-auto rounded-md bg-surface-muted p-2 text-[11px] text-ink-secondary">
                              {JSON.stringify(log.diff, null, 2)}
                            </pre>
                          </details>
                        ) : (
                          <span className="text-xs text-ink-tertiary">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {totalCount > 0 && (
        <p className="text-right text-xs text-ink-tertiary numeric">
          {totalCount.toLocaleString()}건
        </p>
      )}

      {totalPages > 1 && (
        <AdminPagination
          page={page}
          totalPages={totalPages}
          onChange={setPage}
        />
      )}
    </div>
  );
}
