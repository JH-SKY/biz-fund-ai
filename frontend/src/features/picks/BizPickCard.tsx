"use client";

/**
 * BizPickCard — 비즈픽 매거진형 카드.
 *
 * 디자인 (.cursorrules P05 + PAGE 08)
 *  ┌─────────────────────────────────┐
 *  │  [썸네일 이미지 — 상단 60%]      │
 *  │  #세무  #마케팅                  │
 *  │  "서류 3개로 7천만원 받는 법"     │
 *  │  💰 최대 7천만원  📍 전국        │
 *  │  👁 1,204   ♥ 42   Apr 19      │
 *  └─────────────────────────────────┘
 *
 * - 카드 클릭 → onSelect (부모에서 Detail 모달 열기)
 * - ♥ 버튼 → onLike (optimistic update는 훅에서 처리)
 */

import * as React from "react";
import { Eye, Heart } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface BizPickCardProps {
  contentId: string;
  title: string;
  thumbnailUrl: string | null;
  category: string;
  viewCount: number;
  likeCount: number;
  isLiked: boolean;
  createdAt: string;
  onSelect: () => void;
  onLike: () => void;
  likeDisabled?: boolean;
}

function relativeDate(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return iso;
  const diffDays = Math.floor(
    (Date.now() - then.getTime()) / (1000 * 60 * 60 * 24)
  );
  if (diffDays === 0) return "오늘";
  if (diffDays === 1) return "어제";
  if (diffDays < 7) return `${diffDays}일 전`;
  return `${then.getMonth() + 1}월 ${then.getDate()}일`;
}

export function BizPickCard({
  // contentId is for keying at list level only
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  contentId: _,
  title,
  thumbnailUrl,
  category,
  viewCount,
  likeCount,
  isLiked,
  createdAt,
  onSelect,
  onLike,
  likeDisabled,
}: BizPickCardProps) {
  return (
    <article className="group flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-card transition-shadow hover:shadow-card-hover">
      {/* 썸네일 */}
      <button
        type="button"
        onClick={onSelect}
        className="relative h-44 w-full flex-shrink-0 overflow-hidden bg-primary-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        aria-label={`${title} 자세히 보기`}
      >
        {thumbnailUrl ? (
          // 관리자가 업로드한 이미지이므로 외부 도메인 필요 — img 태그 사용
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={thumbnailUrl}
            alt=""
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          /* 썸네일 없을 때 타이틀 텍스트 카드 */
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary-600 to-primary-800 p-4">
            <p className="line-clamp-3 text-center text-sm font-bold leading-snug text-white">
              {title}
            </p>
          </div>
        )}
        {/* 카테고리 배지 overlay */}
        <span className="absolute left-3 top-3 rounded-full bg-white/90 px-2.5 py-0.5 text-[11px] font-semibold text-primary-700 shadow-sm backdrop-blur-sm">
          {category}
        </span>
      </button>

      {/* 본문 영역 */}
      <div className="flex flex-1 flex-col gap-2 p-4">
        <button
          type="button"
          onClick={onSelect}
          className="text-left text-sm font-bold leading-snug text-ink line-clamp-3 hover:text-primary-700 focus-visible:outline-none"
        >
          {title}
        </button>

        {/* 하단 메타 */}
        <div className="mt-auto flex items-center justify-between pt-1">
          <div className="flex items-center gap-3 text-[11px] text-ink-tertiary">
            <span className="flex items-center gap-1">
              <Eye className="h-3 w-3" />
              <span className="numeric">{viewCount.toLocaleString()}</span>
            </span>
            <span>{relativeDate(createdAt)}</span>
          </div>

          {/* ♥ 좋아요 */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onLike();
            }}
            disabled={likeDisabled}
            aria-label={isLiked ? "좋아요 취소" : "좋아요"}
            aria-pressed={isLiked}
            className={cn(
              "flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold transition-colors",
              isLiked
                ? "bg-danger-50 text-danger-500"
                : "bg-surface-muted text-ink-tertiary hover:bg-danger-50 hover:text-danger-400",
              "disabled:pointer-events-none disabled:opacity-60"
            )}
          >
            <Heart
              className={cn("h-3.5 w-3.5", isLiked && "fill-danger-500")}
            />
            <span className="numeric">{likeCount}</span>
          </button>
        </div>
      </div>
    </article>
  );
}

/** 스켈레톤 카드 (로딩 중) */
export function BizPickCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-card">
      <div className="h-44 w-full animate-pulse bg-surface-subtle" />
      <div className="space-y-3 p-4">
        <div className="h-4 w-full animate-pulse rounded bg-surface-subtle" />
        <div className="h-4 w-4/5 animate-pulse rounded bg-surface-subtle" />
        <div className="h-3 w-2/5 animate-pulse rounded bg-surface-subtle" />
      </div>
    </div>
  );
}

/** 빈 상태 */
export function BizPickEmptyState({ category }: { category?: string }) {
  return (
    <div className="col-span-full flex flex-col items-center gap-3 rounded-2xl border border-dashed border-surface-border bg-surface px-6 py-16 text-center">
      <p className="text-4xl">🗞️</p>
      <p className="text-base font-semibold text-ink">
        {category && category !== "ALL"
          ? `'${category}' 카테고리의 콘텐츠가 없습니다`
          : "등록된 비즈픽 콘텐츠가 없습니다"}
      </p>
      <p className="text-sm text-ink-secondary">
        곧 새로운 정보를 업데이트할 예정입니다.
      </p>
    </div>
  );
}

// Badge re-export (카테고리 필터에서도 씀)
export { Badge };
