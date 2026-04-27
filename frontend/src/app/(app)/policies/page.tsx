"use client";

/**
 * [P05] /policies — 전체 정책 공고 리스트 (Policy Explorer).
 *
 * 핵심 기능
 *  - 통합 검색: 키워드, 지역, 카테고리, 기관
 *    · 서버 지원: keyword / region / category (backend PolicySearchParams)
 *    · 클라이언트 후처리: agency(현재 list item 에 agency 필드 부재 → 추후 확장)
 *  - 정렬: 최신 / 지원금 높은순 / 마감 임박순 (클라이언트 측)
 *  - 마감 공고 처리: 기본 숨김 + "마감 포함" 토글; 마감 카드는 리스트 하단 & 회색 처리
 *  - 북마크 토글, 페이지네이션(prev/next)
 *
 * 접근 권한: 로그인 유저 전용 — 인증 가드는 (app) 레이아웃 레벨에서 추후 적용.
 */

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PolicyCard } from "@/components/shared/PolicyCard";
import {
  EMPTY_POLICY_FILTER,
  PolicyFilters,
  type PolicyFilterState,
} from "@/features/policies/PolicyFilters";
import { PolicyEmptyState } from "@/features/policies/PolicyEmptyState";
import { PolicyListSkeleton } from "@/features/policies/PolicyListSkeleton";
import { PolicyPageTabs } from "@/features/policies/PolicyPageTabs";
import {
  PolicySortBar,
  type PolicySortKey,
} from "@/features/policies/PolicySortBar";
import { useBookmarkToggle, usePolicySearch } from "@/hooks/usePolicies";
import type { PolicyListItem } from "@/types";

const PAGE_SIZE = 12;

function isClosed(item: PolicyListItem): boolean {
  if (!item.closed_at) return false;
  if (item.closed_at.startsWith("9999")) return false; // 상시접수
  return new Date(item.closed_at).getTime() < Date.now();
}

function sortPolicies(
  items: PolicyListItem[],
  sort: PolicySortKey
): PolicyListItem[] {
  const arr = [...items];
  if (sort === "deadline_asc") {
    arr.sort((a, b) => a.closed_at.localeCompare(b.closed_at));
  } else if (sort === "amount_desc") {
    // list item 에 support_amount 가 없으므로 현재는 no-op. (향후 필드 확장 시 갱신)
  }
  // "latest" 는 백엔드 기본 정렬을 신뢰
  return arr;
}

export default function PoliciesPage() {
  const [filter, setFilter] = useState<PolicyFilterState>(EMPTY_POLICY_FILTER);
  const [sort, setSort] = useState<PolicySortKey>("latest");
  const [includeClosed, setIncludeClosed] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, refetch } = usePolicySearch({
    keyword: filter.keyword || undefined,
    region: filter.region || undefined,
    category: filter.category || undefined,
    page,
    size: PAGE_SIZE,
  });

  const bookmarkMutation = useBookmarkToggle();

  const totalCount = data?.total_count ?? 0;
  const totalPages = data?.total_pages ?? 1;

  const { displayItems } = useMemo(() => {
    const _items = data?.items ?? [];
    const sorted = sortPolicies(_items, sort);
    const active = sorted.filter((p) => !isClosed(p));
    const closed = sorted.filter((p) => isClosed(p));
    return {
      displayItems: includeClosed ? [...active, ...closed] : active,
    };
  }, [data?.items, sort, includeClosed]);

  // 필터 변경 시 페이지 리셋
  const handleFilterChange = (next: PolicyFilterState) => {
    setFilter(next);
    setPage(1);
  };

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1>정책 공고 탐색</h1>
        <p className="text-sm text-ink-secondary">
          조건을 조합해 내 사업장에 꼭 맞는 정책을 찾아보세요.
        </p>
      </header>

      <PolicyPageTabs active="all" />

      <PolicyFilters value={filter} onChange={handleFilterChange} />

      <div className="space-y-3">
        <PolicySortBar
          totalCount={totalCount}
          sort={sort}
          onSortChange={setSort}
          includeClosed={includeClosed}
          onIncludeClosedChange={setIncludeClosed}
        />

        {isLoading ? (
          <PolicyListSkeleton />
        ) : isError ? (
          <div className="rounded-xl border border-danger-200 bg-danger-50 p-6 text-sm text-danger-800">
            정책을 불러오지 못했습니다.
            <Button variant="link" size="sm" onClick={() => refetch()}>
              다시 시도
            </Button>
          </div>
        ) : displayItems.length === 0 ? (
          <PolicyEmptyState
            onReset={() => handleFilterChange(EMPTY_POLICY_FILTER)}
          />
        ) : (
          <ul className="space-y-3">
            {displayItems.map((item) => {
              const closed = isClosed(item);
              return (
                <li
                  key={item.policy_id}
                  className={closed ? "opacity-50" : undefined}
                >
                  <PolicyCard
                    policyId={item.policy_id}
                    title={item.title}
                    agencyName={item.category ?? undefined}
                    endDate={item.closed_at}
                    isBookmarked={item.is_bookmarked}
                    onBookmarkToggle={(id) => bookmarkMutation.mutate(id)}
                  />
                </li>
              );
            })}
          </ul>
        )}

        {totalPages > 1 && !isLoading && !isError && displayItems.length > 0 && (
          <nav
            aria-label="페이지네이션"
            className="flex items-center justify-center gap-2 pt-4"
          >
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft /> 이전
            </Button>
            <span className="numeric min-w-[80px] text-center text-sm text-ink-secondary">
              {page} / {totalPages}
            </span>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              다음 <ChevronRight />
            </Button>
          </nav>
        )}
      </div>
    </div>
  );
}
