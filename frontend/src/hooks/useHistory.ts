"use client";

/**
 * 비즈-히스토리 React Query 훅 모음.
 *
 *  useChatSessionHistory()   → 상담 세션 목록 (created_at 역순)
 *  useApplicationHistory()   → 정책 신청 이력
 */

import { useQuery } from "@tanstack/react-query";
import { chatService } from "@/lib/services";
import apiClient from "@/lib/api-client";
import type { ApplicationItem } from "@/types";
import { useBusinessStore } from "@/stores/business-store";

export const HISTORY_KEYS = {
  chatSessions: ["history", "chat-sessions"] as const,
  applications: (bizId: string | null) =>
    ["history", "applications", bizId] as const,
};

export function useChatSessionHistory() {
  return useQuery({
    queryKey: HISTORY_KEYS.chatSessions,
    queryFn: () => chatService.getSessions(),
    staleTime: 30_000,
  });
}

export function useApplicationHistory() {
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery({
    queryKey: HISTORY_KEYS.applications(bizId),
    queryFn: () =>
      apiClient.get<ApplicationItem[]>(`/businesses/${bizId}/applications`),
    enabled: Boolean(bizId),
    staleTime: 60_000,
  });
}
