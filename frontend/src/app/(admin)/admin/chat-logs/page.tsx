"use client";

/**
 * /admin/chat-logs — 비즈몽 채팅 모니터링.
 *
 * 기능
 *  - user_id 필터 (옵션)
 *  - 세션별 user_msg/ai_res 페어 리스트
 *  - 페이지네이션
 */

import * as React from "react";
import { MessageSquareText, Search } from "lucide-react";

import { AdminGuard, AdminShell } from "@/components/admin";
import {
  AdminEmptyState,
  AdminErrorState,
  AdminPagination,
  AdminTableSkeleton,
} from "@/features/admin";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAdminChatLogs } from "@/hooks/useAdmin";
import type { ApiError } from "@/types";

export default function AdminChatLogsPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <ChatLogsContent />
      </AdminShell>
    </AdminGuard>
  );
}

function ChatLogsContent() {
  const [userInput, setUserInput] = React.useState("");
  const [userId, setUserId] = React.useState<string>("");
  const [page, setPage] = React.useState(1);

  React.useEffect(() => {
    const t = setTimeout(() => {
      setUserId(userInput.trim());
      setPage(1);
    }, 400);
    return () => clearTimeout(t);
  }, [userInput]);

  const { data, isLoading, isError, error, refetch } = useAdminChatLogs({
    user_id: userId || undefined,
    page,
    size: 25,
  });

  const items = data?.items ?? [];
  const totalCount = data?.total_count ?? 0;
  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-ink">채팅 모니터링</h2>
        <p className="mt-0.5 text-sm text-ink-secondary">
          비즈몽 AI와 사용자 간의 대화 로그를 검토합니다.
        </p>
      </div>

      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <div className="flex-1">
            <Input
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              placeholder="특정 사용자 ID로 필터링 (UUID)"
              leftIcon={<Search className="h-4 w-4" />}
            />
          </div>
          <span className="text-xs text-ink-tertiary numeric">
            {totalCount.toLocaleString()}건
          </span>
        </CardContent>
      </Card>

      {isLoading ? (
        <Card>
          <CardContent className="p-6">
            <AdminTableSkeleton rows={6} />
          </CardContent>
        </Card>
      ) : isError ? (
        <AdminErrorState
          message={(error as unknown as ApiError)?.message}
          onRetry={() => refetch()}
        />
      ) : items.length === 0 ? (
        <AdminEmptyState
          icon={MessageSquareText}
          title="조회된 채팅 로그가 없습니다"
          description="사용자가 비즈몽과 대화하면 이 영역에 표시됩니다."
        />
      ) : (
        <ul className="space-y-3">
          {items.map((log) => (
            <li key={`${log.session_id}-${log.timestamp}`}>
              <Card>
                <CardContent className="space-y-3 p-4">
                  <div className="flex flex-wrap items-center gap-2 border-b border-surface-border pb-2">
                    <Badge variant="primary" size="sm">
                      {log.user_name ?? log.user_id.slice(0, 8)}
                    </Badge>
                    {log.agent_type && (
                      <Badge variant="accent" size="sm">
                        {String(log.agent_type).toUpperCase()}
                      </Badge>
                    )}
                    <span className="ml-auto text-[11px] text-ink-tertiary">
                      {new Date(log.timestamp).toLocaleString("ko-KR")} ·
                      session {log.session_id.slice(0, 8)}
                    </span>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase text-ink-tertiary">
                      사용자
                    </p>
                    <p className="mt-1 whitespace-pre-wrap rounded-md bg-primary-50 px-3 py-2 text-sm text-primary-900">
                      {log.user_msg}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase text-ink-tertiary">
                      비즈몽
                    </p>
                    <p className="mt-1 whitespace-pre-wrap rounded-md bg-surface-muted px-3 py-2 text-sm text-ink">
                      {log.ai_res}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
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
