"use client";

/**
 * /admin/feedback — 로직 디버깅 & 피드백 센터.
 *
 * 기능 (PAGE 12 ①)
 *  - 👎 피드백 목록 (사유별 필터)
 *  - 선택한 피드백의 "대화 맥락 + 매칭 로직" 복기
 *  - 오답 정정 노트 작성 → POST /admin/feedback/{id}/correction
 */

import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  MessageCircleWarning,
  RefreshCw,
  Send,
  Sparkles,
} from "lucide-react";

import { AdminGuard, AdminShell } from "@/components/admin";
import {
  AdminEmptyState,
  AdminErrorState,
  AdminPagination,
  AdminTableSkeleton,
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
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Tabs } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useToast } from "@/providers/ToastProvider";
import {
  useAdminFeedback,
  useCreateCorrection,
  useFeedbackContext,
} from "@/hooks/useAdmin";
import type { FeedbackReason, ApiError, AgentType } from "@/types";
import { FeedbackReason as FR } from "@/types";

export default function AdminFeedbackPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <FeedbackContent />
      </AdminShell>
    </AdminGuard>
  );
}

const REASON_OPTIONS: Array<{ value: FeedbackReason | "ALL"; label: string }> = [
  { value: "ALL", label: "전체 사유" },
  { value: FR.INFO_WRONG, label: "정보 오류" },
  { value: FR.NOT_APPLICABLE, label: "실제 상황과 다름" },
  { value: FR.DIFFICULT_TERM, label: "용어 어려움" },
  { value: FR.OTHER, label: "기타" },
];

function FeedbackContent() {
  const [reason, setReason] = React.useState<FeedbackReason | "ALL">("ALL");
  const [page, setPage] = React.useState(1);
  const [tab, setTab] = React.useState<"UNRESOLVED" | "RESOLVED">("UNRESOLVED");
  const [selectedId, setSelectedId] = React.useState<string | null>(null);

  const { data, isLoading, isError, error, refetch } = useAdminFeedback({
    reason: reason === "ALL" ? undefined : reason,
    is_resolved: tab === "RESOLVED",
    page,
    size: 20,
  });

  const items = React.useMemo(() => data?.items ?? [], [data?.items]);
  const totalPages = data?.total_pages ?? 1;
  const totalCount = data?.total_count ?? 0;

  // 자동으로 첫 항목 선택
  React.useEffect(() => {
    if (!selectedId && items.length > 0) {
      setSelectedId(items[0].feedback_id);
    }
  }, [items, selectedId]);

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">
            로직 디버깅 · 피드백 센터
          </h2>
          <p className="mt-0.5 text-sm text-ink-secondary">
            👎 피드백을 분석해 매칭 로직의 오탐지를 즉시 교정하세요.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => refetch()}
          disabled={isLoading}
        >
          <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          새로고침
        </Button>
      </div>

      {/* 필터 바 */}
      <Card>
        <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
          <Tabs
            value={tab}
            onValueChange={(v) => {
              setTab(v as "UNRESOLVED" | "RESOLVED");
              setPage(1);
              setSelectedId(null);
            }}
            items={[
              { value: "UNRESOLVED", label: "미해결" },
              { value: "RESOLVED", label: "해결됨" },
            ]}
          />
          <div className="flex items-center gap-2 sm:ml-auto">
            <Label className="text-xs text-ink-secondary">사유</Label>
            <Select
              className="h-9 min-w-[180px]"
              options={REASON_OPTIONS.map((o) => ({
                value: o.value,
                label: o.label,
              }))}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value as FeedbackReason | "ALL");
                setPage(1);
                setSelectedId(null);
              }}
            />
            <span className="text-xs text-ink-tertiary numeric">
              총 {totalCount.toLocaleString()}건
            </span>
          </div>
        </CardContent>
      </Card>

      {/* 본문 2열 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,360px)_1fr]">
        {/* 좌측: 피드백 리스트 */}
        <Card className="lg:sticky lg:top-20 lg:max-h-[calc(100dvh-8rem)] lg:overflow-hidden">
          <CardHeader className="py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <AlertTriangle className="h-4 w-4 text-danger-500" />
              피드백 목록
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-y-auto p-0 lg:max-h-[calc(100dvh-14rem)]">
            {isLoading ? (
              <div className="p-4">
                <AdminTableSkeleton rows={6} />
              </div>
            ) : isError ? (
              <div className="p-4">
                <AdminErrorState
                  message={(error as unknown as ApiError)?.message}
                  onRetry={() => refetch()}
                />
              </div>
            ) : items.length === 0 ? (
              <AdminEmptyState
                icon={MessageCircleWarning}
                title={
                  tab === "UNRESOLVED"
                    ? "미해결 피드백이 없습니다"
                    : "해결된 피드백이 없습니다"
                }
                description="사용자가 👎를 누르면 여기에 수집됩니다."
              />
            ) : (
              <ul className="divide-y divide-surface-border">
                {items.map((fb) => {
                  const active = fb.feedback_id === selectedId;
                  return (
                    <li key={fb.feedback_id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(fb.feedback_id)}
                        className={cn(
                          "block w-full px-4 py-3 text-left transition-colors",
                          active
                            ? "bg-primary-50"
                            : "hover:bg-surface-muted"
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <Badge variant="danger" size="sm">
                            {fb.reason_label}
                          </Badge>
                          <span className="text-[11px] text-ink-tertiary">
                            {new Date(fb.created_at).toLocaleDateString(
                              "ko-KR"
                            )}
                          </span>
                        </div>
                        <p
                          className={cn(
                            "mt-1.5 line-clamp-2 text-sm",
                            active
                              ? "text-primary-900"
                              : "text-ink"
                          )}
                        >
                          {fb.ai_response_snippet}
                        </p>
                        <p className="mt-1 text-[11px] text-ink-tertiary">
                          {fb.user_name ?? fb.user_id.slice(0, 8)}
                        </p>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
          {totalPages > 1 && (
            <div className="border-t border-surface-border p-3">
              <AdminPagination
                page={page}
                totalPages={totalPages}
                onChange={setPage}
                maxVisible={5}
              />
            </div>
          )}
        </Card>

        {/* 우측: 상세 + 정정 노트 */}
        <div className="min-w-0">
          {selectedId ? (
            <FeedbackDetail feedbackId={selectedId} />
          ) : (
            <AdminEmptyState
              icon={MessageCircleWarning}
              title="피드백을 선택하세요"
              description="좌측 목록에서 피드백을 선택하면 대화 맥락과 매칭 로직을 확인할 수 있습니다."
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ── 상세 패널 ─────────────────────────────────────────────────────
function FeedbackDetail({ feedbackId }: { feedbackId: string }) {
  const toast = useToast();
  const { data, isLoading, isError, error, refetch } =
    useFeedbackContext(feedbackId);
  const { mutate: submitCorrection, isPending: isSubmitting } =
    useCreateCorrection();

  const [pattern, setPattern] = React.useState("");
  const [expected, setExpected] = React.useState("");
  const [appliesTo, setAppliesTo] = React.useState<AgentType | "ALL">("ALL");

  React.useEffect(() => {
    setPattern("");
    setExpected("");
    setAppliesTo("ALL");
  }, [feedbackId]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <AdminTableSkeleton rows={6} />
        </CardContent>
      </Card>
    );
  }
  if (isError || !data) {
    return (
      <AdminErrorState
        message={(error as unknown as ApiError)?.message}
        onRetry={() => refetch()}
      />
    );
  }

  const { feedback, conversation, matching_logic_snapshot } = data;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!pattern.trim() || !expected.trim()) {
      toast.warning("질문 패턴과 정답을 모두 입력해주세요.");
      return;
    }
    submitCorrection(
      {
        feedbackId,
        body: {
          feedback_id: feedbackId,
          question_pattern: pattern.trim(),
          expected_answer: expected.trim(),
          applies_to_agent: appliesTo,
          is_active: true,
        },
      },
      {
        onSuccess: () => {
          toast.success("정정 노트가 로직에 반영되었습니다.");
          setPattern("");
          setExpected("");
        },
        onError: (err) => {
          toast.error("정정 실패", {
            message: (err as unknown as ApiError).message,
          });
        },
      }
    );
  };

  return (
    <div className="space-y-4">
      {/* 피드백 요약 */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Badge variant="danger">{feedback.reason_label}</Badge>
            {feedback.is_resolved && (
              <Badge variant="success">
                <CheckCircle2 className="h-3 w-3" />
                해결됨
              </Badge>
            )}
            <span className="ml-auto text-xs text-ink-tertiary">
              {new Date(feedback.created_at).toLocaleString("ko-KR")}
            </span>
          </div>
          <CardTitle className="mt-1 text-base">
            {feedback.user_name ?? feedback.user_id} 사용자의 피드백
          </CardTitle>
          {feedback.user_comment && (
            <CardDescription className="mt-2">
              “{feedback.user_comment}”
            </CardDescription>
          )}
        </CardHeader>
      </Card>

      {/* 대화 맥락 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">대화 맥락 복기</CardTitle>
          <CardDescription>
            피드백이 남겨진 시점의 전체 대화입니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {conversation.length === 0 ? (
            <p className="text-sm text-ink-tertiary">
              복원 가능한 대화 기록이 없습니다.
            </p>
          ) : (
            conversation.map((msg) => (
              <div
                key={msg.message_id}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm",
                  msg.role === "user"
                    ? "ml-8 bg-primary-50 text-primary-900"
                    : msg.role === "assistant"
                      ? "mr-8 bg-surface-muted text-ink"
                      : "bg-accent-50 text-accent-700"
                )}
              >
                <div className="mb-0.5 flex items-center justify-between gap-2 text-[11px] text-ink-tertiary">
                  <span className="font-semibold">
                    {msg.role === "user"
                      ? "사용자"
                      : msg.role === "assistant"
                        ? "비즈몽"
                        : "시스템"}
                  </span>
                  <span>
                    {new Date(msg.created_at).toLocaleTimeString("ko-KR")}
                  </span>
                </div>
                <p className="whitespace-pre-wrap leading-relaxed">
                  {msg.content}
                </p>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* 매칭 로직 스냅샷 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">당시 적용된 매칭 로직</CardTitle>
          <CardDescription>
            스냅샷 시각:{" "}
            {new Date(matching_logic_snapshot.applied_at).toLocaleString(
              "ko-KR"
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase text-ink-tertiary">
              적용 규칙
            </p>
            {matching_logic_snapshot.rules.length === 0 ? (
              <p className="text-sm text-ink-tertiary">—</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {matching_logic_snapshot.rules.map((r) => (
                  <li
                    key={r.rule_id}
                    className="flex items-center justify-between rounded-md bg-surface-muted px-3 py-1.5"
                  >
                    <span className="text-ink">{r.description}</span>
                    <span className="text-xs text-ink-tertiary numeric">
                      weight {r.weight}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase text-ink-tertiary">
              매칭된 정책
            </p>
            {matching_logic_snapshot.matched_policies.length === 0 ? (
              <p className="text-sm text-ink-tertiary">—</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {matching_logic_snapshot.matched_policies.map((p) => (
                  <li
                    key={p.policy_id}
                    className="flex items-center justify-between rounded-md border border-surface-border px-3 py-1.5"
                  >
                    <span className="truncate">{p.title}</span>
                    <span className="text-xs font-semibold text-primary-700 numeric">
                      {p.score.toFixed(0)}점
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 오답 정정 노트 */}
      <Card className="border-primary-200 bg-primary-50/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4 text-primary-600" />
            오답 정정 노트
          </CardTitle>
          <CardDescription>
            아래 내용은 저장 즉시 매칭 로직에 반영됩니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="pattern">이런 질문이 올 때</Label>
              <textarea
                id="pattern"
                rows={2}
                className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                placeholder="예: 카페 창업 자금 얼마까지 받을 수 있나요?"
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="expected">이렇게 대답해</Label>
              <textarea
                id="expected"
                rows={4}
                className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                placeholder="예: 소상공인 창업자금은 최대 7천만원까지 가능하며, 업력 6개월 이상이 필수 조건입니다. …"
                value={expected}
                onChange={(e) => setExpected(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="applies-to">적용 대상 에이전트</Label>
              <Select
                id="applies-to"
                className="h-10"
                value={appliesTo}
                onChange={(e) =>
                  setAppliesTo(e.target.value as AgentType | "ALL")
                }
                options={[
                  { value: "ALL", label: "전체 에이전트" },
                  { value: "diagnosis", label: "진단(Diagnosis)" },
                  { value: "rag", label: "정책 검색(RAG)" },
                  { value: "simulator", label: "시뮬레이터" },
                  { value: "stats", label: "통계" },
                ]}
              />
            </div>
            <Button
              type="submit"
              className="w-full"
              loading={isSubmitting}
              disabled={isSubmitting}
            >
              <Send className="h-4 w-4" />
              정정 노트 저장 & 즉시 반영
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
