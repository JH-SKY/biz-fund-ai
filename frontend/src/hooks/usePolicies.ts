"use client";

/**
 * 정책(Policy) 도메인 TanStack Query 훅 묶음.
 *
 * 하는 일
 *  - policyService 를 래핑하여 React 컴포넌트에서 선언형으로 사용할 수 있게 함.
 *  - 북마크 Mutation 은 Optimistic Update + 관련 쿼리 invalidate.
 */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { policyService } from "@/lib/services";
import type {
  BookmarkToggleResponse,
  PolicySearchParams,
} from "@/types";

export const POLICY_KEYS = {
  all: ["policies"] as const,
  list: (params: PolicySearchParams) =>
    ["policies", "list", params] as const,
  recommend: () => ["policies", "recommend"] as const,
  bookmarks: () => ["policies", "bookmarks"] as const,
  detail: (id: string) => ["policies", "detail", id] as const,
};

/** [P05] 전체 리스트 & 검색 — keyword/region/category/page/size 파라미터 */
export function usePolicySearch(params: PolicySearchParams) {
  return useQuery({
    queryKey: POLICY_KEYS.list(params),
    queryFn: () => policyService.searchPolicies(params),
    placeholderData: keepPreviousData,
  });
}

/** [P06] 맞춤 추천 (/policies/recommend) */
export function useRecommendedPolicies() {
  return useQuery({
    queryKey: POLICY_KEYS.recommend(),
    queryFn: () => policyService.fetchRecommendedPolicies(1, 50),
  });
}

/** [P07] 상세 */
export function usePolicyDetail(policyId: string | undefined) {
  return useQuery({
    queryKey: POLICY_KEYS.detail(policyId ?? ""),
    queryFn: () => policyService.fetchPolicyDetail(policyId!),
    enabled: !!policyId,
  });
}

/** 북마크 토글 — Optimistic Update */
export function useBookmarkToggle() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (policyId: string) => policyService.toggleBookmark(policyId),
    onSuccess: (data: BookmarkToggleResponse) => {
      // 관련 쿼리 최소 침습 갱신:
      // - 상세 쿼리 캐시만 즉시 업데이트 (목록은 next revalidation 시 반영)
      qc.setQueryData(POLICY_KEYS.detail(data.policy_id), (prev: unknown) => {
        if (!prev || typeof prev !== "object") return prev;
        return { ...prev, is_bookmarked: data.is_bookmarked };
      });
      qc.invalidateQueries({ queryKey: POLICY_KEYS.all });
    },
  });
}
