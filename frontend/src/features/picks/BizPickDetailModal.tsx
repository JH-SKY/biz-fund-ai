"use client";

/**
 * BizPickDetailModal — 비즈픽 게시글 상세 다이얼로그.
 *
 * 구성 (.cursorrules P05)
 *  - ai_full_explanation (body_html) 렌더링
 *  - 태그 배지
 *  - 관련 정책 링크 (→ /policies/{id})
 *  - Like 버튼 (useLikeBizPick 훅 연계)
 *  - 원문 사이트 링크 (apply_url)
 *
 * Dialog 컴포넌트 재사용 — 넓이 최대 4xl.
 */

import Link from "next/link";
import {
  ArrowUpRight,
  Eye,
  Heart,
  Tag,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useBizPickDetail, useLikeBizPick } from "@/hooks/useBizPick";

interface BizPickDetailModalProps {
  contentId: string | null;
  /** 목록에서 이미 보유한 is_liked / like_count (초기값 — 상세 로딩 전 표시용) */
  previewLiked?: boolean;
  previewLikeCount?: number;
  onClose: () => void;
}

export function BizPickDetailModal({
  contentId,
  previewLiked,
  previewLikeCount,
  onClose,
}: BizPickDetailModalProps) {
  const { data, isLoading } = useBizPickDetail(contentId);
  const likeMutation = useLikeBizPick();

  const isLiked = data?.is_liked ?? previewLiked ?? false;
  const likeCount = data?.like_count ?? previewLikeCount ?? 0;

  return (
    <Dialog
      open={!!contentId}
      onOpenChange={(open) => !open && onClose()}
      className="sm:max-w-4xl"
      footer={
        <div className="flex w-full items-center justify-between gap-3">
          {/* 좋아요 */}
          <button
            type="button"
            disabled={likeMutation.isPending || !contentId}
            onClick={() => contentId && likeMutation.mutate(contentId)}
            aria-label={isLiked ? "좋아요 취소" : "좋아요"}
            aria-pressed={isLiked}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm font-semibold transition-colors",
              isLiked
                ? "border-danger-300 bg-danger-50 text-danger-500"
                : "border-surface-border bg-surface text-ink-secondary hover:border-danger-300 hover:bg-danger-50 hover:text-danger-400",
              "disabled:pointer-events-none disabled:opacity-60"
            )}
          >
            <Heart
              className={cn(
                "h-4 w-4",
                isLiked && "fill-danger-500"
              )}
            />
            <span className="numeric">{likeCount.toLocaleString()}</span>
          </button>

          <Button variant="ghost" onClick={onClose}>
            닫기
          </Button>
        </div>
      }
    >
      {isLoading ? (
        <div className="space-y-4">
          <div className="h-6 w-3/4 animate-pulse rounded bg-surface-subtle" />
          <div className="h-60 animate-pulse rounded-xl bg-surface-subtle" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-surface-subtle" />
        </div>
      ) : !data ? null : (
        <div className="space-y-5">
          {/* 제목 */}
          <h2 className="text-xl font-bold leading-snug text-ink">
            {data.title}
          </h2>

          {/* 메타 */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-ink-secondary">
            <span className="flex items-center gap-1">
              <Eye className="h-3.5 w-3.5" />
              <span className="numeric">{data.view_count.toLocaleString()}</span>
            </span>
            <span className="text-ink-tertiary">by {data.author}</span>
          </div>

          {/* 태그 */}
          {data.tags.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <Tag className="h-3.5 w-3.5 text-ink-tertiary" />
              {data.tags.map((t) => (
                <Badge key={t} variant="outline" size="sm">
                  #{t}
                </Badge>
              ))}
            </div>
          )}

          {/* 본문 HTML */}
          <div
            className="prose prose-sm max-w-none leading-relaxed text-ink
              prose-headings:font-bold prose-headings:text-ink
              prose-a:text-primary-600 prose-a:no-underline hover:prose-a:underline
              prose-strong:text-ink
              prose-ul:pl-5 prose-li:marker:text-primary-500"
            dangerouslySetInnerHTML={{ __html: data.body_html }}
          />

          {/* 관련 정책 */}
          {data.related_policies.length > 0 && (
            <div className="rounded-xl border border-primary-100 bg-primary-50/60 p-4">
              <p className="mb-3 flex items-center gap-2 text-sm font-bold text-primary-900">
                <ArrowUpRight className="h-4 w-4" />
                관련 지원금 바로 신청하기
              </p>
              <ul className="space-y-2">
                {data.related_policies.map((p) => (
                  <li key={p.id}>
                    <Link
                      href={`/policies/${p.id}`}
                      onClick={onClose}
                      className="flex items-center justify-between rounded-lg border border-primary-200 bg-surface px-3 py-2 text-sm font-medium text-primary-700 transition-colors hover:border-primary-400 hover:bg-primary-50"
                    >
                      <span>{p.title}</span>
                      <ArrowUpRight className="h-4 w-4 shrink-0" />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Dialog>
  );
}
