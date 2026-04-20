"use client";

/**
 * /picks — 비즈픽 홈 (Biz-Pick Home). [P05]
 *
 * 레이아웃 (.cursorrules P05 + PAGE 08)
 *  ┌────────────────────────────────────┐
 *  │  비즈픽  🗞️                        │
 *  │  사장님 맞춤 정책 카드 뉴스          │
 *  ├────────────────────────────────────┤
 *  │  [최신순] [인기순]   (정렬 토글)    │
 *  │  [전체][세무/회계][정책/법률]...    │
 *  ├────────────────────────────────────┤
 *  │  카드 그리드 (2열 mobile, 3열 lg)   │
 *  ├────────────────────────────────────┤
 *  │  [이전] [1][2][3] [다음]            │
 *  └────────────────────────────────────┘
 *
 * 카드 클릭 → BizPickDetailModal (상세 Dialog)
 * ♥ 클릭 → useLikeBizPick (Optimistic Update)
 */

import * as React from "react";
import { Newspaper } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  BizPickCard,
  BizPickCardSkeleton,
  BizPickEmptyState,
} from "@/features/picks/BizPickCard";
import { BizPickDetailModal } from "@/features/picks/BizPickDetailModal";
import { useBizPickList, useLikeBizPick } from "@/hooks/useBizPick";
import type { BizPickListParams } from "@/lib/services/biz-pick.service";

// PAGE 08 카테고리 + 커서룰즈 카테고리 통합
const CATEGORIES: Array<{ code: string; label: string }> = [
  { code: "ALL", label: "전체" },
  { code: "세무/회계", label: "세무·회계" },
  { code: "정책/법률", label: "정책·법률" },
  { code: "마케팅/지원", label: "마케팅·지원" },
  { code: "성공사례", label: "성공 사례" },
];

const SORT_OPTIONS: Array<{ value: BizPickListParams["sort"]; label: string }> =
  [
    { value: "latest", label: "최신순" },
    { value: "popular", label: "인기순" },
  ];

const PAGE_SIZE = 9;

export default function BizPickPage() {
  const [category, setCategory] = React.useState("ALL");
  const [sort, setSort] = React.useState<BizPickListParams["sort"]>("latest");
  const [page, setPage] = React.useState(1);

  // 선택된 게시글 ID (Detail 모달 트리거)
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [selectedPreview, setSelectedPreview] = React.useState<{
    isLiked: boolean;
    likeCount: number;
  } | null>(null);

  const params: BizPickListParams = {
    category: category === "ALL" ? undefined : category,
    sort,
    page,
    size: PAGE_SIZE,
  };

  const { data, isLoading, isError } = useBizPickList(params);
  const likeMutation = useLikeBizPick();

  const items = data?.items ?? [];
  const totalCount = data?.total_count ?? 0;
  const totalPages = data?.total_pages ?? 1;

  const handleCategoryChange = (code: string) => {
    setCategory(code);
    setPage(1);
  };

  const handleSortChange = (v: BizPickListParams["sort"]) => {
    setSort(v);
    setPage(1);
  };

  const handleSelect = (id: string, isLiked: boolean, likeCount: number) => {
    setSelectedId(id);
    setSelectedPreview({ isLiked, likeCount });
  };

  const handleLike = (contentId: string) => {
    likeMutation.mutate(contentId);
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-ink">
          <Newspaper className="h-6 w-6 text-primary-600" />
          비즈픽
        </h1>
        <p className="mt-1 text-sm text-ink-secondary">
          사장님 맞춤 정책·세무·마케팅 카드 뉴스 — AI가 쉽게 번역했습니다.
        </p>
      </div>

      {/* 정렬 + 카테고리 필터 */}
      <div className="space-y-3">
        {/* 정렬 */}
        <div className="flex items-center gap-2">
          {SORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleSortChange(opt.value)}
              className={cn(
                "rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors",
                sort === opt.value
                  ? "bg-ink text-white"
                  : "bg-surface-muted text-ink-secondary hover:bg-surface-border"
              )}
            >
              {opt.label}
            </button>
          ))}
          {totalCount > 0 && (
            <span className="ml-auto text-xs text-ink-tertiary numeric">
              {totalCount.toLocaleString()}개
            </span>
          )}
        </div>

        {/* 카테고리 탭 */}
        <div
          role="tablist"
          aria-label="카테고리"
          className="flex items-center gap-2 overflow-x-auto pb-1"
        >
          {CATEGORIES.map((cat) => (
            <button
              key={cat.code}
              role="tab"
              aria-selected={category === cat.code}
              type="button"
              onClick={() => handleCategoryChange(cat.code)}
              className={cn(
                "flex-shrink-0 rounded-full border px-4 py-1.5 text-sm font-semibold transition-colors",
                category === cat.code
                  ? "border-primary-600 bg-primary-600 text-white"
                  : "border-surface-border bg-surface text-ink-secondary hover:border-primary-200 hover:text-ink"
              )}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* 카드 그리드 */}
      {isError ? (
        <div className="rounded-xl border border-danger-100 bg-danger-50 p-6 text-center text-sm text-danger-600">
          콘텐츠를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {isLoading
            ? Array.from({ length: PAGE_SIZE }).map((_, i) => (
                <BizPickCardSkeleton key={i} />
              ))
            : items.length === 0
              ? (
                  <BizPickEmptyState
                    category={category === "ALL" ? undefined : category}
                  />
                )
              : items.map((item) => (
                  <BizPickCard
                    key={item.content_id}
                    contentId={item.content_id}
                    title={item.title}
                    thumbnailUrl={item.thumbnail_url}
                    category={item.category}
                    viewCount={item.view_count}
                    likeCount={item.like_count}
                    isLiked={item.is_liked}
                    createdAt={item.created_at}
                    onSelect={() =>
                      handleSelect(
                        item.content_id,
                        item.is_liked,
                        item.like_count
                      )
                    }
                    onLike={() => handleLike(item.content_id)}
                    likeDisabled={likeMutation.isPending}
                  />
                ))}
        </div>
      )}

      {/* 페이지네이션 */}
      {!isLoading && totalPages > 1 && (
        <nav
          aria-label="페이지 내비게이션"
          className="flex items-center justify-center gap-1"
        >
          <Button
            variant="secondary"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            aria-label="이전"
          >
            ← 이전
          </Button>
          {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
            const half = 3;
            let start = Math.max(1, page - half);
            const end = Math.min(totalPages, start + 6);
            if (end - start < 6) start = Math.max(1, end - 6);
            const p = start + i;
            if (p > totalPages) return null;
            return (
              <button
                key={p}
                type="button"
                onClick={() => setPage(p)}
                aria-current={p === page ? "page" : undefined}
                className={cn(
                  "inline-flex h-8 min-w-8 items-center justify-center rounded-md px-2 text-sm font-medium transition-colors",
                  p === page
                    ? "bg-primary-600 text-white"
                    : "text-ink-secondary hover:bg-surface-muted"
                )}
              >
                {p}
              </button>
            );
          })}
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            aria-label="다음"
          >
            다음 →
          </Button>
        </nav>
      )}

      {/* 상세 모달 */}
      <BizPickDetailModal
        contentId={selectedId}
        previewLiked={selectedPreview?.isLiked}
        previewLikeCount={selectedPreview?.likeCount}
        onClose={() => {
          setSelectedId(null);
          setSelectedPreview(null);
        }}
      />
    </div>
  );
}
