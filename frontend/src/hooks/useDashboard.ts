/**
 * 대시보드(PAGE 04) 전용 React Query 훅 모음.
 *
 * 설계 원칙
 *  - 활성 bizId 가 없으면 (= 온보딩 미완료) 쿼리를 `enabled: false` 로 막는다.
 *  - 각 쿼리는 독립적으로 로딩/오류 상태를 갖도록 분리한다 (섹션별 스켈레톤 노출용).
 *  - queryKey 는 `[도메인, 하위리소스, 의존값]` 3단 구조로 정규화.
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import {
  businessService,
  diagnosisService,
  documentService,
  policyService,
} from "@/lib/services";
import { useBusinessStore } from "@/stores/business-store";

// ── Query Keys ────────────────────────────────────────────────────────
export const dashboardKeys = {
  business: ["business", "me"] as const,
  recommendedPolicies: (bizId: string | null) =>
    ["policies", "recommend", bizId] as const,
  bookmarkedPolicies: (bizId: string | null) =>
    ["policies", "bookmarks", bizId] as const,
  diagnosisHistory: (bizId: string | null) =>
    ["diagnoses", "history", bizId] as const,
  myDocuments: (bizId: string | null) =>
    ["documents", "list", bizId] as const,
};

// ── 내 사업장 정보 ────────────────────────────────────────────────────
export function useMyBusiness() {
  return useQuery({
    queryKey: dashboardKeys.business,
    queryFn: () => businessService.fetchMyBusiness(),
    staleTime: 60 * 1000,
    retry: (count, err) => {
      // 404: 온보딩 미완료 — 재시도 불필요
      const status = (err as { status?: number })?.status;
      if (status === 404) return false;
      return count < 1;
    },
  });
}

// ── 추천 정책 (원픽 포함) ────────────────────────────────────────────
export function useRecommendedPolicies(options?: { size?: number }) {
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery({
    queryKey: dashboardKeys.recommendedPolicies(bizId),
    queryFn: () =>
      policyService.fetchRecommendedPolicies(1, options?.size ?? 10),
    enabled: Boolean(bizId),
    staleTime: 60 * 1000,
  });
}

// ── 진단 이력 (최신 진단 요약용) ──────────────────────────────────────
export function useDiagnosisHistory() {
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery({
    queryKey: dashboardKeys.diagnosisHistory(bizId),
    queryFn: () => diagnosisService.fetchHistory(),
    enabled: Boolean(bizId),
    staleTime: 60 * 1000,
  });
}

// ── 서류 목록 ─────────────────────────────────────────────────────────
export function useMyDocuments() {
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery({
    queryKey: dashboardKeys.myDocuments(bizId),
    queryFn: () => documentService.fetchMyDocuments(),
    enabled: Boolean(bizId),
    staleTime: 60 * 1000,
  });
}

// ── 북마크 토글 Mutation ─────────────────────────────────────────────
export function useToggleBookmark() {
  const qc = useQueryClient();
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useMutation({
    mutationFn: (policyId: string) => policyService.toggleBookmark(policyId),
    onSuccess: () => {
      // 추천 목록/북마크 목록 캐시 무효화
      qc.invalidateQueries({
        queryKey: dashboardKeys.recommendedPolicies(bizId),
      });
      qc.invalidateQueries({
        queryKey: dashboardKeys.bookmarkedPolicies(bizId),
      });
    },
  });
}
