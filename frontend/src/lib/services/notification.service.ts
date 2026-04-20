/**
 * 알림(notification) 도메인 API.
 *
 * 백엔드 매핑
 *  - GET  /notifications           → fetchNotifications
 *  - PATCH /notifications/{id}/read → markAsRead
 *  - POST /notifications/read-all  → markAllRead
 */

import apiClient from "@/lib/api-client";
import type { NotificationItem } from "@/types";

export const notificationService = {
  fetchNotifications: () =>
    apiClient.get<NotificationItem[]>("/notifications"),

  markAsRead: (notiId: string) =>
    apiClient.patch<void>(`/notifications/${notiId}/read`, {}),

  markAllRead: () => apiClient.post<void>("/notifications/read-all", {}),
};
