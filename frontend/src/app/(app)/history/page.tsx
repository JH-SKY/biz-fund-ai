"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { MessageSquareHeart, FileText, History } from "lucide-react";
import { Tabs } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TimelineItem, TimelineItemSkeleton } from "@/features/history/TimelineItem";
import { ChatSessionCard, ChatSessionCardSkeleton } from "@/features/history/ChatSessionCard";
import { useChatSessionHistory, useApplicationHistory } from "@/hooks/useHistory";

const TABS = [
  { value: "all", label: "전체" },
  { value: "chat", label: "상담 내역" },
  { value: "application", label: "신청 이력" },
];

const APP_STATUS_META: Record<
  string,
  { label: string; variant: "default" | "success" | "warning" | "danger" | "primary" }
> = {
  INTERESTED: { label: "관심", variant: "default" },
  SUBMITTED: { label: "신청완료", variant: "primary" },
  APPROVED: { label: "승인", variant: "success" },
  REJECTED: { label: "반려", variant: "danger" },
};

export default function HistoryPage() {
  const router = useRouter();
  const [tab, setTab] = React.useState("all");

  const {
    data: sessions,
    isLoading: sessionsLoading,
  } = useChatSessionHistory();

  const {
    data: applications,
    isLoading: appsLoading,
  } = useApplicationHistory();

  const isLoading = sessionsLoading || appsLoading;

  // 전체 탭: 채팅 세션 + 신청 이력을 updated_at 기준 혼합 정렬
  const allItems = React.useMemo(() => {
    const chatItems = (sessions ?? []).map((s) => ({
      kind: "chat" as const,
      id: s.session_id,
      title: s.title,
      description: s.last_message,
      date: s.updated_at,
    }));
    const appItems = (applications ?? []).map((a) => ({
      kind: "application" as const,
      id: a.application_id,
      title: a.policy_title,
      description: `신청 상태: ${APP_STATUS_META[a.status]?.label ?? a.status}`,
      date: a.updated_at,
      status: a.status,
      policyId: a.policy_id,
    }));
    return [...chatItems, ...appItems].sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );
  }, [sessions, applications]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">비즈-히스토리</h1>
        <p className="mt-1 text-sm text-ink-secondary">
          상담 내역과 정책 신청 이력을 확인합니다.
        </p>
      </div>

      <Tabs value={tab} onValueChange={setTab} items={TABS} variant="underline" />

      {/* ── 전체 탭 ── */}
      {tab === "all" && (
        <div>
          {isLoading ? (
            <div>
              {Array.from({ length: 4 }).map((_, i) => (
                <TimelineItemSkeleton key={i} isLast={i === 3} />
              ))}
            </div>
          ) : allItems.length === 0 ? (
            <EmptyHistory />
          ) : (
            <div>
              {allItems.map((item, idx) => (
                <TimelineItem
                  key={item.id}
                  isLast={idx === allItems.length - 1}
                  icon={
                    item.kind === "chat" ? (
                      <MessageSquareHeart className="h-5 w-5 text-primary-600" />
                    ) : (
                      <FileText className="h-5 w-5 text-success-600" />
                    )
                  }
                  iconBg={
                    item.kind === "chat" ? "bg-primary-50" : "bg-success-50"
                  }
                  title={item.title}
                  description={item.description}
                  timestamp={item.date}
                  clickable
                  onClick={() => {
                    if (item.kind === "chat")
                      router.push(`/chat?session=${item.id}`);
                    else
                      router.push(`/policies/${item.policyId}`);
                  }}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── 상담 내역 탭 ── */}
      {tab === "chat" && (
        <div className="space-y-3">
          {sessionsLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <ChatSessionCardSkeleton key={i} />
            ))
          ) : !sessions || sessions.length === 0 ? (
            <EmptyHistory
              message="상담 내역이 없습니다"
              cta="첫 상담 시작하기"
              onCta={() => router.push("/chat")}
            />
          ) : (
            sessions.map((s) => (
              <ChatSessionCard key={s.session_id} session={s} />
            ))
          )}
        </div>
      )}

      {/* ── 신청 이력 탭 ── */}
      {tab === "application" && (
        <div className="space-y-3">
          {appsLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <ChatSessionCardSkeleton key={i} />
            ))
          ) : !applications || applications.length === 0 ? (
            <EmptyHistory
              message="신청 이력이 없습니다"
              cta="정책 탐색하기"
              onCta={() => router.push("/policies/matching")}
            />
          ) : (
            applications.map((app) => {
              const meta = APP_STATUS_META[app.status] ?? {
                label: app.status,
                variant: "default" as const,
              };
              return (
                <button
                  key={app.application_id}
                  type="button"
                  onClick={() => router.push(`/policies/${app.policy_id}`)}
                  className="flex w-full items-center gap-4 rounded-xl border border-surface-border bg-surface p-4 text-left shadow-card transition-shadow hover:border-primary-200 hover:shadow-card-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-success-50 text-success-600">
                    <FileText className="h-5 w-5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-ink">
                      {app.policy_title}
                    </p>
                    <p className="mt-1 text-xs text-ink-tertiary">
                      {app.applied_at
                        ? new Date(app.applied_at).toLocaleDateString("ko-KR")
                        : "신청일 미기재"}
                    </p>
                  </div>
                  <Badge variant={meta.variant} size="sm">
                    {meta.label}
                  </Badge>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

function EmptyHistory({
  message = "내역이 없습니다",
  cta,
  onCta,
}: {
  message?: string;
  cta?: string;
  onCta?: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-surface-border bg-surface px-6 py-20 text-center">
      <History className="h-12 w-12 text-ink-tertiary" />
      <div className="space-y-1">
        <p className="text-base font-semibold text-ink">{message}</p>
        <p className="text-sm text-ink-secondary">
          활동 내역이 쌓이면 이곳에서 확인할 수 있어요.
        </p>
      </div>
      {cta && onCta && (
        <Button variant="outline" onClick={onCta}>
          {cta}
        </Button>
      )}
    </div>
  );
}
