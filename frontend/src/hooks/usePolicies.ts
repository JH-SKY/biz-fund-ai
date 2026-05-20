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
import { queryKeys } from "@/lib/query-keys";
import { useBusinessStore } from "@/stores/business-store";
import type {
  BookmarkToggleResponse,
  PolicySearchParams,
} from "@/types";

export const POLICY_KEYS = {
  all: queryKeys.policies.all,
  list: (params: PolicySearchParams) =>
    queryKeys.policies.list(params),
  recommend: (bizId: string | null, page = 1, size = 50) =>
    queryKeys.policies.recommend(bizId, page, size),
  bookmarks: (bizId: string | null, page = 1, size = 10) =>
    queryKeys.policies.bookmarks(bizId, page, size),
  detail: queryKeys.policies.detail,
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
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery({
    queryKey: POLICY_KEYS.recommend(bizId, 1, 50),
    queryFn: () => policyService.fetchRecommendedPolicies(1, 50),
    enabled: Boolean(bizId),
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
