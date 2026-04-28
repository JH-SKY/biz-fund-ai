/**
 * 채팅(비즈몽) 도메인 API 서비스.
 *
 * 백엔드 매핑 (backend/src/app/api/v1/chat_router.py)
 *  POST  /chats/sessions                          → createSession
 *  GET   /chats/sessions                          → getSessions
 *  POST  /chats/sessions/{id}/messages            → sendMessage (기본)
 *  GET   /chats/sessions/{id}/messages            → getMessages
 *  POST  /chats/sessions/{id}/agent-message       → sendAgentMessage (non-streaming)
 *  POST  /chats/sessions/{id}/stream              → streamAgentMessage (SSE) ← 신규
 *  PATCH /chats/sessions/{id}/summary             → autoSummary
 *  DELETE /chats/sessions/{id}                    → deleteSession
 */

import apiClient from "@/lib/api-client";
import { tokenStorage } from "@/lib/api-client";
import { getActiveBizIdNonReactive } from "@/stores/business-store";
import type {
  AgentMessageResponse,
  ChatSession,
  CreateSessionRequest,
  CreateSessionResponseData,
  SendMessageRequest,
  SseEvent,
} from "@/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
    apiClient.get<{ role: string; content: string; created_at: string }[]>(
      `/chats/sessions/${sessionId}/messages`
    ),

  autoSummary: (sessionId: string) =>
    apiClient.patch<{ new_title: string }>(
      `/chats/sessions/${sessionId}/summary`
    ),

  deleteSession: (sessionId: string) =>
    apiClient.delete<void>(`/chats/sessions/${sessionId}`),

  /**
   * SSE 기반 스트리밍 메시지 전송.
   * `fetch` + ReadableStream 으로 text/event-stream 을 직접 파싱한다.
   * (EventSource 는 POST 를 지원하지 않으므로 fetch 방식 사용)
   *
   * @param sessionId  세션 UUID
   * @param message    사용자 메시지
   * @param callbacks  이벤트별 핸들러
   */
  async streamAgentMessage(
    sessionId: string,
    message: string,
    callbacks: {
      onStatus?: (text: string) => void;
      onToken?: (content: string) => void;
      onDone?: (event: Extract<SseEvent, { type: "done" }>) => void;
      onError?: (err: Error) => void;
    }
  ): Promise<void> {
    const token = tokenStorage.getAccess();
    const bizId = getActiveBizIdNonReactive();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (bizId) headers["X-Business-Id"] = bizId;

    let response: Response;
    try {
      response = await fetch(
        `${BASE_URL}/chats/sessions/${sessionId}/stream`,
        {
          method: "POST",
          headers,
          body: JSON.stringify({ message }),
        }
      );
    } catch (err) {
      callbacks.onError?.(err instanceof Error ? err : new Error(String(err)));
      return;
    }

    if (!response.ok) {
      callbacks.onError?.(new Error(`HTTP ${response.status}`));
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      callbacks.onError?.(new Error("ReadableStream 없음"));
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const block of lines) {
          const dataLine = block
            .split("\n")
            .find((l) => l.startsWith("data: "));
          if (!dataLine) continue;

          const raw = dataLine.slice(6).trim();
          if (!raw) continue;

          try {
            const evt = JSON.parse(raw) as SseEvent;
            if (evt.type === "status") callbacks.onStatus?.(evt.text);
            else if (evt.type === "token") callbacks.onToken?.(evt.content);
            else if (evt.type === "done") callbacks.onDone?.(evt);
          } catch {
            /* JSON 파싱 오류 무시 */
          }
        }
      }
    } catch (err) {
      callbacks.onError?.(err instanceof Error ? err : new Error(String(err)));
    } finally {
      reader.releaseLock();
    }
  },
};
