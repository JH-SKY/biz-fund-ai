/**
 * 프로필(마이페이지) 전용 API — 재무 스냅샷 CRUD + 계정 설정.
 *
 * 백엔드 엔드포인트 매핑
 *  - GET    /businesses/finance/history      → fetchFinances
 *  - POST   /businesses/finance              → createFinance
 *  - PATCH  /businesses/finance/{id}        → updateFinance
 *  - DELETE /businesses/finance/{id}        → deleteFinance
 *  - GET    /auth/me/notification-settings  → fetchNotificationSettings
 *  - PATCH  /auth/me/notification-settings  → updateNotificationSettings
 *  - DELETE /auth/me                        → deleteAccount
 */

import apiClient from "@/lib/api-client";
import type {
  FinanceSnapshot,
  FinanceCreateRequest,
  FinanceUpdateRequest,
  NotificationSettings,
  UpdateNotificationSettingsRequest,
} from "@/types";

export const profileService = {
  fetchFinances: () =>
    apiClient.get<FinanceSnapshot[]>("/businesses/finance/history"),

  createFinance: (body: FinanceCreateRequest) =>
    apiClient.post<FinanceSnapshot>("/businesses/finance", body),

  updateFinance: (year: number, body: FinanceUpdateRequest) =>
    apiClient.patch<void>(`/businesses/finance/${year}`, body),

  deleteFinance: (year: number) =>
    apiClient.delete<void>(`/businesses/finance/${year}`),

  fetchNotificationSettings: () =>
    apiClient.get<NotificationSettings>("/notifications/settings"),

  updateNotificationSettings: (body: UpdateNotificationSettingsRequest) =>
    apiClient.patch<void>("/notifications/settings", body),

  deleteAccount: () => apiClient.delete<void>("/users/withdraw"),
};
