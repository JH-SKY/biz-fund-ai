/**
 * 사업장(business) 도메인 API 서비스.
 *
 * 백엔드 엔드포인트 매핑 (backend/src/app/api/v1/business_router.py)
 *  - GET  /businesses/me                 → fetchMyBusiness
 *  - PATCH /businesses/me                → updateMyBusiness
 *  - POST /onboarding/verify-biz         → verifyBizNumber
 *  - POST /onboarding/register           → registerBusiness
 *  - GET  /businesses/finance/history    → fetchFinanceHistory
 *
 * 모든 호출은 apiClient 의 응답 인터셉터에서 envelope 가 벗겨진 상태로 반환된다.
 */

import apiClient from "@/lib/api-client";
import type {
  BusinessInfo,
  BusinessUpdateRequest,
  FinanceSnapshot,
  OnboardingRegisterRequest,
  OnboardingRegisterResponseData,
  VerifyBizNumberRequest,
  VerifyBizNumberResponseData,
} from "@/types";

export const businessService = {
  fetchMyBusiness: () => apiClient.get<BusinessInfo>("/businesses/me"),

  updateMyBusiness: (body: BusinessUpdateRequest) =>
    apiClient.patch<void>("/businesses/me", body),

  verifyBizNumber: (body: VerifyBizNumberRequest) =>
    apiClient.post<VerifyBizNumberResponseData>(
      "/onboarding/verify-biz",
      body
    ),

  registerBusiness: (body: OnboardingRegisterRequest) =>
    apiClient.post<OnboardingRegisterResponseData>(
      "/onboarding/register",
      body
    ),

  fetchFinanceHistory: () =>
    apiClient.get<FinanceSnapshot[]>("/businesses/finance/history"),
};
