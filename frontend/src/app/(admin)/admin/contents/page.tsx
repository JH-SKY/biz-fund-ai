"use client";

/**
 * /admin/contents — 비즈픽 콘텐츠 관리.
 *
 * 기능 (PAGE 12 ③)
 *  - 비즈픽 게시글 리스트 + 발행 상태 배지
 *  - 생성 Dialog: 수동 입력 or AI 카드뉴스 자동 생성(정책 URL → 3줄 요약 + body)
 *  - 수정/삭제
 *  - 연관 정책 AI 자동 제안 버튼
 */

import * as React from "react";
import {
  Edit3,
  Newspaper,
  Plus,
  Sparkles,
  Trash2,
  Wand2,
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
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  useAdminContents,
  useCreateContent,
  useDeleteContent,
  useGenerateCardNews,
  useSuggestRelatedPolicies,
  useUpdateContent,
} from "@/hooks/useAdmin";
import { useToast } from "@/providers/ToastProvider";
import type {
  AiRelatedPoliciesResponse,
  ApiError,
  BizPickContentCreateRequest,
  BizPickContentListItem,
} from "@/types";

export default function AdminContentsPage() {
  return (
    <AdminGuard>
      <AdminShell>
        <ContentsContent />
      </AdminShell>
    </AdminGuard>
  );
}

function ContentsContent() {
  const toast = useToast();
  const [page, setPage] = React.useState(1);
  const [editorOpen, setEditorOpen] = React.useState(false);
  const [editTarget, setEditTarget] =
    React.useState<BizPickContentListItem | null>(null);

  const { data, isLoading, isError, error, refetch } = useAdminContents({
    page,
    size: 20,
  });
  const deleteMut = useDeleteContent();

  const items = data?.items ?? [];
  const totalCount = data?.total_count ?? 0;
  const totalPages = data?.total_pages ?? 1;

  const handleDelete = (id: string) => {
    if (!confirm("이 콘텐츠를 삭제하시겠습니까?")) return;
    deleteMut.mutate(id, {
      onSuccess: () => toast.success("콘텐츠가 삭제되었습니다."),
      onError: (err) =>
        toast.error("삭제 실패", { message: (err as unknown as ApiError).message }),
    });
  };

  const openNew = () => {
    setEditTarget(null);
    setEditorOpen(true);
  };

  const openEdit = (item: BizPickContentListItem) => {
    setEditTarget(item);
    setEditorOpen(true);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">비즈픽 콘텐츠 관리</h2>
          <p className="mt-0.5 text-sm text-ink-secondary">
            AI 카드 뉴스 자동 생성과 노코드 에디터로 비즈픽 게시글을 발행합니다.
          </p>
        </div>
        <Button onClick={openNew}>
          <Plus className="h-4 w-4" />
          새 콘텐츠 만들기
        </Button>
      </div>

      <Card>
        <CardContent className="flex items-center justify-between p-4 text-sm text-ink-secondary">
          <span>총 {totalCount.toLocaleString()}개 콘텐츠</span>
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
          icon={Newspaper}
          title="등록된 비즈픽 콘텐츠가 없습니다"
          description="AI 카드뉴스 자동 생성으로 빠르게 시작해보세요."
          action={
            <Button onClick={openNew}>
              <Sparkles className="h-4 w-4" />
              AI로 초안 만들기
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <Card key={item.content_id}>
              {item.thumbnail_url && (
                // 썸네일 — next/image 미사용 (관리자 화면은 외부 도메인 유연성 우선)
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={item.thumbnail_url}
                  alt=""
                  className="h-40 w-full rounded-t-xl object-cover"
                />
              )}
              <CardContent className="space-y-2 p-4">
                <div className="flex items-center gap-2">
                  <Badge variant="primary" size="sm">
                    {item.category}
                  </Badge>
                  <Badge
                    variant={item.is_published ? "success" : "outline"}
                    size="sm"
                  >
                    {item.is_published ? "발행됨" : "임시저장"}
                  </Badge>
                  {item.scheduled_at && (
                    <Badge variant="accent" size="sm">
                      예약
                    </Badge>
                  )}
                </div>
                <h3 className="line-clamp-2 text-sm font-semibold text-ink">
                  {item.title}
                </h3>
                <div className="flex items-center justify-between text-[11px] text-ink-tertiary">
                  <span>
                    ♥ {item.like_count} · 👁 {item.view_count}
                  </span>
                  <span className="numeric">
                    {new Date(item.updated_at).toLocaleDateString("ko-KR")}
                  </span>
                </div>
                <div className="flex gap-2 pt-1">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="flex-1"
                    onClick={() => openEdit(item)}
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                    수정
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(item.content_id)}
                    className="text-danger-600 hover:bg-danger-50"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <AdminPagination
          page={page}
          totalPages={totalPages}
          onChange={setPage}
        />
      )}

      <ContentEditorDialog
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        target={editTarget}
      />
    </div>
  );
}

// ── 에디터 Dialog ─────────────────────────────────────────────────
function ContentEditorDialog({
  open,
  onClose,
  target,
}: {
  open: boolean;
  onClose: () => void;
  target: BizPickContentListItem | null;
}) {
  const toast = useToast();
  const createMut = useCreateContent();
  const updateMut = useUpdateContent();
  const aiGenMut = useGenerateCardNews();
  const aiRelatedMut = useSuggestRelatedPolicies();

  const [form, setForm] = React.useState<BizPickContentCreateRequest>({
    title: "",
    body_html: "",
    thumbnail_url: "",
    category: "융자",
    tags: [],
    related_policy_ids: [],
    is_published: false,
    scheduled_at: null,
  });
  const [tagsInput, setTagsInput] = React.useState("");
  const [aiInput, setAiInput] = React.useState("");
  const [relatedSuggestions, setRelatedSuggestions] = React.useState<
    AiRelatedPoliciesResponse["items"]
  >([]);
  const updateForm = React.useCallback(
    (patch: Partial<BizPickContentCreateRequest>) => {
      setForm((prev) => ({ ...prev, ...patch }));
    },
    []
  );

  // Sync when opened
  React.useEffect(() => {
    if (!open) return;
    if (target) {
      setForm({
        title: target.title,
        body_html: "",
        thumbnail_url: target.thumbnail_url ?? "",
        category: target.category,
        tags: [],
        related_policy_ids: [],
        is_published: target.is_published,
        scheduled_at: target.scheduled_at ?? null,
      });
      setTagsInput("");
    } else {
      setForm({
        title: "",
        body_html: "",
        thumbnail_url: "",
        category: "융자",
        tags: [],
        related_policy_ids: [],
        is_published: false,
        scheduled_at: null,
      });
      setTagsInput("");
    }
    setAiInput("");
    setRelatedSuggestions([]);
  }, [open, target]);

  const handleAiGenerate = () => {
    if (!aiInput.trim()) {
      toast.warning("정책 URL 또는 원문 텍스트를 입력해주세요.");
      return;
    }
    const isUrl = /^https?:\/\//i.test(aiInput.trim());
    aiGenMut.mutate(
      isUrl
        ? { policy_url: aiInput.trim() }
        : { raw_text: aiInput.trim() },
      {
        onSuccess: (res) => {
          setForm((prev) => ({
            ...prev,
            title: res.suggested_title,
            body_html: res.body_html,
            category: res.suggested_category || prev.category,
            tags: res.suggested_tags ?? [],
            thumbnail_url: res.suggested_thumbnail_url ?? prev.thumbnail_url,
          }));
          setTagsInput((res.suggested_tags ?? []).join(", "));
          toast.success("AI 초안이 작성되었습니다.", {
            message: res.three_line_summary.join(" / "),
          });
        },
        onError: (err) =>
          toast.error("AI 초안 생성 실패", {
            message: (err as unknown as ApiError).message,
          }),
      }
    );
  };

  const handleAiSuggestRelated = () => {
    if (!form.body_html.trim()) {
      toast.warning("먼저 본문을 작성해주세요.");
      return;
    }
    aiRelatedMut.mutate(
      { content_body: form.body_html, limit: 5 },
      {
        onSuccess: (res) => {
          setRelatedSuggestions(res.items);
          toast.success(`${res.items.length}개 관련 정책을 찾았습니다.`);
        },
        onError: (err) =>
          toast.error("추천 실패", { message: (err as unknown as ApiError).message }),
      }
    );
  };

  const toggleRelated = (policyId: string) => {
    setForm((prev) => {
      const cur = prev.related_policy_ids ?? [];
      return {
        ...prev,
        related_policy_ids: cur.includes(policyId)
          ? cur.filter((id) => id !== policyId)
          : [...cur, policyId],
      };
    });
  };

  const isPending = createMut.isPending || updateMut.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.body_html.trim()) {
      toast.warning("제목과 본문은 필수입니다.");
      return;
    }
    const payload: BizPickContentCreateRequest = {
      ...form,
      tags: tagsInput
        .split(/[,#\s]+/)
        .map((t) => t.trim())
        .filter(Boolean),
    };
    if (target) {
      updateMut.mutate(
        { contentId: target.content_id, body: payload },
        {
          onSuccess: () => {
            toast.success("콘텐츠가 수정되었습니다.");
            onClose();
          },
          onError: (err) =>
            toast.error("수정 실패", { message: (err as unknown as ApiError).message }),
        }
      );
    } else {
      createMut.mutate(payload, {
        onSuccess: () => {
          toast.success("콘텐츠가 등록되었습니다.");
          onClose();
        },
        onError: (err) =>
          toast.error("등록 실패", { message: (err as unknown as ApiError).message }),
      });
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => !v && onClose()}
      title={target ? "콘텐츠 수정" : "새 콘텐츠 만들기"}
      description="정책 URL을 붙여넣으면 AI가 3줄 요약 + 카드 뉴스 초안을 자동으로 작성합니다."
      className="sm:w-[min(56rem,calc(100vw-2rem))]"
      footer={
        <>
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={isPending}
          >
            취소
          </Button>
          <Button
            type="submit"
            form="content-form"
            loading={isPending}
            disabled={isPending}
          >
            {target ? "저장" : "발행"}
          </Button>
        </>
      }
    >
      <form id="content-form" onSubmit={handleSubmit} className="space-y-4">
        {/* AI 카드뉴스 생성 */}
        <div className="rounded-lg border border-primary-200 bg-primary-50/40 p-3">
          <div className="flex items-center gap-2">
            <Wand2 className="h-4 w-4 text-primary-600" />
            <p className="text-sm font-semibold text-primary-900">
              AI 카드뉴스 초안 생성
            </p>
          </div>
          <p className="mt-1 text-xs text-ink-secondary">
            공고 URL 또는 공고 원문 텍스트를 붙여넣으세요.
          </p>
          <div className="mt-2 flex gap-2">
            <Input
              value={aiInput}
              onChange={(e) => setAiInput(e.target.value)}
              placeholder="https://www.bizinfo.go.kr/... 또는 공고 본문 붙여넣기"
            />
            <Button
              type="button"
              onClick={handleAiGenerate}
              disabled={aiGenMut.isPending}
              loading={aiGenMut.isPending}
            >
              <Sparkles className="h-4 w-4" />
              초안 생성
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[2fr_1fr]">
          <div className="space-y-1.5">
            <Label htmlFor="c-title">제목 *</Label>
            <Input
              id="c-title"
              value={form.title}
              onChange={(e) => updateForm({ title: e.target.value })}
              placeholder="사장님 눈높이 제목"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="c-category">카테고리</Label>
            <Input
              id="c-category"
              value={form.category}
              onChange={(e) => updateForm({ category: e.target.value })}
              placeholder="융자 / 보조금 / 보증 / R&D"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="c-thumb">썸네일 URL</Label>
          <Input
            id="c-thumb"
            value={form.thumbnail_url ?? ""}
            onChange={(e) => updateForm({ thumbnail_url: e.target.value })}
            placeholder="https://..."
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="c-body">본문 (HTML) *</Label>
          <textarea
            id="c-body"
            rows={10}
            value={form.body_html}
            onChange={(e) => updateForm({ body_html: e.target.value })}
            className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 font-mono text-xs leading-relaxed outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            placeholder="<h2>핵심 요약</h2><p>...</p>"
          />
          {form.body_html && (
            <details className="rounded-md border border-surface-border">
              <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-ink-secondary">
                미리보기
              </summary>
              <div
                className="prose prose-sm max-w-none border-t border-surface-border bg-surface-muted p-4 text-ink"
                // biz-pick 본문은 AI/관리자 생성이라 신뢰 가능 — 추후 DOMPurify 적용 고려
                dangerouslySetInnerHTML={{ __html: form.body_html }}
              />
            </details>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="c-tags">태그 (쉼표/공백 구분)</Label>
          <Input
            id="c-tags"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            placeholder="창업자금, 저금리, 소상공인"
          />
        </div>

        {/* 관련 정책 AI 추천 */}
        <div className="rounded-lg border border-accent-200 bg-accent-50/40 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent-600" />
              <p className="text-sm font-semibold text-accent-700">
                관련 정책 자동 제안
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              variant="accent"
              onClick={handleAiSuggestRelated}
              loading={aiRelatedMut.isPending}
              disabled={aiRelatedMut.isPending}
            >
              AI 추천받기
            </Button>
          </div>
          {relatedSuggestions.length > 0 && (
            <ul className="mt-3 space-y-1.5">
              {relatedSuggestions.map((s) => {
                const checked =
                  form.related_policy_ids?.includes(s.policy_id) ?? false;
                return (
                  <li key={s.policy_id}>
                    <label
                      className={cn(
                        "flex cursor-pointer items-start gap-2 rounded-md border p-2 text-sm",
                        checked
                          ? "border-primary-500 bg-primary-50"
                          : "border-surface-border bg-surface hover:border-primary-200"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleRelated(s.policy_id)}
                        className="mt-0.5 h-4 w-4 rounded border-surface-border text-primary-600 focus:ring-primary-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-ink">{s.title}</p>
                          <Badge variant="outline" size="sm">
                            {s.score.toFixed(0)}점
                          </Badge>
                        </div>
                        <p className="mt-0.5 text-xs text-ink-secondary">
                          {s.reason}
                        </p>
                      </div>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!form.is_published}
              onChange={(e) => updateForm({ is_published: e.target.checked })}
              className="h-4 w-4 rounded border-surface-border text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm">즉시 발행</span>
          </label>
          <div className="flex items-center gap-2">
            <Label htmlFor="c-schedule" className="mb-0 text-sm">
              예약 발행
            </Label>
            <Input
              id="c-schedule"
              type="datetime-local"
              className="h-9"
              value={form.scheduled_at ?? ""}
              onChange={(e) => updateForm({ scheduled_at: e.target.value || null })}
            />
          </div>
        </div>
      </form>
    </Dialog>
  );
}
