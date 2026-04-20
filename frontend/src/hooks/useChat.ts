"use client";

/**
 * 채팅(비즈몽) React Query 훅 모음.
 *
 *  useChatSessions()        → 세션 목록 (사이드바)
 *  useChatMessages()        → 특정 세션 히스토리 로드
 *  useCreateSession()       → 새 세션 생성 mutation
 *  useSendAgentMessage()    → BizMong 에이전트 메시지 mutation
 *  useDeleteSession()       → 세션 삭제 mutation
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { chatService } from "@/lib/services";

export const CHAT_KEYS = {
  sessions: ["chat", "sessions"] as const,
  messages: (sessionId: string) => ["chat", "messages", sessionId] as const,
};

export function useChatSessions() {
  return useQuery({
    queryKey: CHAT_KEYS.sessions,
    queryFn: () => chatService.getSessions(),
    staleTime: 30_000,
  });
}

export function useChatMessages(sessionId: string | null) {
  return useQuery({
    queryKey: CHAT_KEYS.messages(sessionId ?? ""),
    queryFn: () => chatService.getMessages(sessionId!),
    enabled: Boolean(sessionId),
    staleTime: Infinity, // 히스토리는 세션 내에서 변경 없음
  });
}

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: chatService.createSession,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: CHAT_KEYS.sessions });
    },
  });
}

export function useSendAgentMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      message,
    }: {
      sessionId: string;
      message: string;
    }) => chatService.sendAgentMessage(sessionId, { message }),
    onSuccess: (_, vars) => {
      // 세션 목록의 last_message 등 최신화
      qc.invalidateQueries({ queryKey: CHAT_KEYS.sessions });
      // 히스토리 캐시 무효화 (다음에 재로드 시 반영)
      qc.invalidateQueries({
        queryKey: CHAT_KEYS.messages(vars.sessionId),
      });
    },
  });
}

export function useDeleteSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: chatService.deleteSession,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: CHAT_KEYS.sessions });
    },
  });
}

export function useAutoSummary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: chatService.autoSummary,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: CHAT_KEYS.sessions });
    },
  });
}
