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

interface NotificationListResponse {
  items: NotificationItem[];
  total_count: number;
}

export const notificationService = {
  fetchNotifications: () =>
    apiClient
      .get<NotificationListResponse>("/notifications")
      .then((response) => response.items),

  markAsRead: (notiId: string) =>
    apiClient.patch<void>(`/notifications/${notiId}/read`, {}),

  markAllRead: () => apiClient.post<void>("/notifications/read-all", {}),
};
