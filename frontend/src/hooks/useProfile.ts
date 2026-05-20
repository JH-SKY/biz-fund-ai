"use client";

/**
 * 마이페이지(프로필) React Query 훅 모음.
 *
 *  useProfileBusiness()           → 사업장 정보 조회 + 수정
 *  useFinanceList()               → 재무 스냅샷 목록
 *  useCreateFinance()             → 재무 추가
 *  useUpdateFinance()             → 재무 수정
 *  useDeleteFinance()             → 재무 삭제
 *  useNotificationSettings()      → 알림 설정 조회
 *  useUpdateNotificationSettings()→ 알림 설정 수정
 *  useDeleteAccount()             → 회원 탈퇴
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { businessService, profileService } from "@/lib/services";
import { queryKeys } from "@/lib/query-keys";
import { useBusinessStore } from "@/stores/business-store";
import type {
  BusinessUpdateRequest,
  FinanceCreateRequest,
  FinanceUpdateRequest,
  UpdateNotificationSettingsRequest,
} from "@/types";

export const PROFILE_KEYS = {
  business: queryKeys.business.me,
  finances: queryKeys.business.finances,
  notificationSettings: queryKeys.profile.notificationSettings,
};

export function useProfileBusiness() {
  return useQuery({
    queryKey: PROFILE_KEYS.business,
    queryFn: () => businessService.fetchMyBusiness(),
    staleTime: 60_000,
  });
}

export function useUpdateBusiness() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: BusinessUpdateRequest) =>
      businessService.updateMyBusiness(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PROFILE_KEYS.business });
      qc.invalidateQueries({ queryKey: queryKeys.policies.all });
      qc.invalidateQueries({ queryKey: queryKeys.diagnoses.all });
    },
  });
}

export function useFinanceList() {
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery({
    queryKey: PROFILE_KEYS.finances(bizId),
    queryFn: () => profileService.fetchFinances(),
    enabled: Boolean(bizId),
    staleTime: 60_000,
  });
}

export function useCreateFinance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: FinanceCreateRequest) =>
      profileService.createFinance(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["businesses", "finance"] });
      qc.invalidateQueries({ queryKey: queryKeys.policies.all });
      qc.invalidateQueries({ queryKey: queryKeys.diagnoses.all });
    },
  });
}

export function useUpdateFinance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      year,
      body,
    }: {
      year: number;
      body: FinanceUpdateRequest;
    }) => profileService.updateFinance(year, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["businesses", "finance"] });
      qc.invalidateQueries({ queryKey: queryKeys.policies.all });
      qc.invalidateQueries({ queryKey: queryKeys.diagnoses.all });
    },
  });
}

export function useDeleteFinance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (year: number) => profileService.deleteFinance(year),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["businesses", "finance"] });
      qc.invalidateQueries({ queryKey: queryKeys.policies.all });
      qc.invalidateQueries({ queryKey: queryKeys.diagnoses.all });
    },
  });
}

export function useNotificationSettings() {
  return useQuery({
    queryKey: PROFILE_KEYS.notificationSettings,
    queryFn: () => profileService.fetchNotificationSettings(),
    staleTime: 30_000,
  });
}

export function useUpdateNotificationSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateNotificationSettingsRequest) =>
      profileService.updateNotificationSettings(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PROFILE_KEYS.notificationSettings });
    },
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: () => profileService.deleteAccount(),
  });
}
