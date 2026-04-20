/**
 * 채팅(비즈몽) 도메인 API 서비스.
 *
 * 백엔드 매핑 (backend/src/app/api/v1/chat_router.py)
 *  POST  /chats/sessions                          → createSession
 *  GET   /chats/sessions                          → getSessions
 *  POST  /chats/sessions/{id}/messages            → sendMessage (기본)
 *  GET   /chats/sessions/{id}/messages            → getMessages
 *  POST  /chats/sessions/{id}/agent-message       → sendAgentMessage ← 핵심
 *  PATCH /chats/sessions/{id}/summary             → autoSummary
 *  DELETE /chats/sessions/{id}                    → deleteSession
 */

import apiClient from "@/lib/api-client";
import type {
  AgentMessageResponse,
  ChatSession,
  CreateSessionRequest,
  CreateSessionResponseData,
  SendMessageRequest,
} from "@/types";

export const chatService = {
  createSession: (req: CreateSessionRequest) =>
    apiClient.post<CreateSessionResponseData>("/chats/sessions", req),

  getSessions: () => apiClient.get<ChatSession[]>("/chats/sessions"),

  sendAgentMessage: (sessionId: string, req: SendMessageRequest) =>
    apiClient.post<AgentMessageResponse>(
      `/chats/sessions/${sessionId}/agent-message`,
      req
    ),

  getMessages: (sessionId: string) =>
    apiClient.get<{ role: string; content: string }[]>(
      `/chats/sessions/${sessionId}/messages`
    ),

  autoSummary: (sessionId: string) =>
    apiClient.patch<{ new_title: string }>(
      `/chats/sessions/${sessionId}/summary`
    ),

  deleteSession: (sessionId: string) =>
    apiClient.delete<void>(`/chats/sessions/${sessionId}`),
};
