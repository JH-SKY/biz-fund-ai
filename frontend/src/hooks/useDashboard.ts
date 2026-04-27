"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { businessService, diagnosisService, policyService } from "@/lib/services";
import { useBusinessStore } from "@/stores/business-store";

export const dashboardKeys = {
  business: ["business", "me"] as const,
  recommendedPolicies: (bizId: string | null) =>
    ["policies", "recommend", bizId] as const,
  bookmarkedPolicies: (bizId: string | null) =>
    ["policies", "bookmarks", bizId] as const,
  diagnosisHistory: (bizId: string | null) =>
    ["diagnoses", "history", bizId] as const,
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
  return useQuery({
    queryKey: dashboardKeys.recommendedPolicies(bizId),
    queryFn: () => policyService.fetchRecommendedPolicies(1, options?.size ?? 10),
    enabled: Boolean(bizId),
    staleTime: 60 * 1000,
  });
}

export function useDiagnosisHistory() {
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery({
    queryKey: dashboardKeys.diagnosisHistory(bizId),
    queryFn: () => diagnosisService.fetchHistory(),
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
