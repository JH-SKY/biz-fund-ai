"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { businessService, diagnosisService, policyService } from "@/lib/services";
import { queryKeys } from "@/lib/query-keys";
import { useBusinessStore } from "@/stores/business-store";

export const dashboardKeys = {
  business: queryKeys.business.me,
  recommendedPolicies: (bizId: string | null) =>
    queryKeys.policies.recommend(bizId),
  bookmarkedPolicies: (bizId: string | null) =>
    queryKeys.policies.bookmarks(bizId),
  diagnosisHistory: queryKeys.diagnoses.history,
};

export function useMyBusiness() {
  return useQuery({
    queryKey: dashboardKeys.business,
    queryFn: () => businessService.fetchMyBusiness(),
    staleTime: 60 * 1000,
    retry: (count, err) => {
      const status = (err as { status?: number })?.status;
      if (status === 404) return false;
      return count < 1;
    },
  });
}

export function useRecommendedPolicies(options?: { size?: number }) {
  const bizId = useBusinessStore((s) => s.activeBizId);
  const size = options?.size ?? 10;
  return useQuery({
    queryKey: queryKeys.policies.recommend(bizId, 1, size),
    queryFn: () => policyService.fetchRecommendedPolicies(1, size),
    enabled: Boolean(bizId),
    staleTime: 60 * 1000,
  });
}

export function useDiagnosisHistory() {
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery({
    queryKey: dashboardKeys.diagnosisHistory(bizId),
    queryFn: () => diagnosisService.fetchHistory(1),
    enabled: Boolean(bizId),
    staleTime: 60 * 1000,
  });
}

export function useToggleBookmark() {
  const qc = useQueryClient();
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useMutation({
    mutationFn: (policyId: string) => policyService.toggleBookmark(policyId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: dashboardKeys.recommendedPolicies(bizId),
      });
      qc.invalidateQueries({
        queryKey: dashboardKeys.bookmarkedPolicies(bizId),
      });
    },
  });
}
