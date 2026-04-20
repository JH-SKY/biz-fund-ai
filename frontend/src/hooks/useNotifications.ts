"use client";

/**
 * 알림(비즈-핑) React Query 훅 모음.
 *
 *  useNotificationList() → 알림 목록
 *  useMarkAsRead()       → 개별 읽음 처리
 *  useMarkAllRead()      → 전체 읽음 처리
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationService } from "@/lib/services";

export const NOTIFICATION_KEYS = {
  list: ["notifications", "list"] as const,
};

export function useNotificationList() {
  return useQuery({
    queryKey: NOTIFICATION_KEYS.list,
    queryFn: () => notificationService.fetchNotifications(),
    staleTime: 30_000,
  });
}

export function useMarkAsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (notiId: string) => notificationService.markAsRead(notiId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: NOTIFICATION_KEYS.list });
    },
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationService.markAllRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: NOTIFICATION_KEYS.list });
    },
  });
}
