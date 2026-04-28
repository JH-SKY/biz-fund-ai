"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PanelLeft, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ChatSidebar } from "@/features/chat/ChatSidebar";
import { ChatInput, BIZMONG_QUICK_REPLIES } from "@/features/chat/ChatInput";
import { ChatMessageBubble } from "@/features/chat/ChatMessageBubble";
import { AgentLoadingBubble } from "@/features/chat/AgentLoadingBubble";
import {
  useChatMessages,
  useChatSessions,
  useCreateSession,
  useDeleteSession,
} from "@/hooks/useChat";
import { chatService } from "@/lib/services";
import { useToast } from "@/providers/ToastProvider";
import type { ChatDisplayMessage } from "@/types";
import { cn } from "@/lib/utils";

function useScrollToBottom(dep: unknown) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [dep]);
  return ref;
}

function mapHistoryToDisplayMessages(
  items: { role: string; content: string; created_at: string }[]
): ChatDisplayMessage[] {
  return items
    .filter((item) => item.role === "user" || item.role === "assistant")
    .map((item, index) =>
      item.role === "user"
        ? {
            kind: "user" as const,
            id: `history-user-${index}-${item.created_at}`,
            content: item.content,
            created_at: item.created_at,
          }
        : {
            kind: "agent" as const,
            id: `history-agent-${index}-${item.created_at}`,
            content: item.content,
            agent_type: undefined,
            diagnosis_report: null,
            simulation_report: null,
            stats_insight: null,
            rag_results: null,
            created_at: item.created_at,
          }
    );
}

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const toast = useToast();

  const sessionParam = searchParams?.get("session") ?? null;
  const policyIdParam = searchParams?.get("policyId") ?? null;

  const [activeSessionId, setActiveSessionId] = useState<string | null>(sessionParam);
  const [messages, setMessages] = useState<ChatDisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);

  const scrollRef = useScrollToBottom(messages);

  const sessionsQ = useChatSessions();
  const historyQ = useChatMessages(activeSessionId);
  const createSessionMut = useCreateSession();
  const deleteMut = useDeleteSession();

  useEffect(() => {
    setActiveSessionId(sessionParam);
  }, [sessionParam]);

  useEffect(() => {
    if (policyIdParam && !activeSessionId) {
      setInput("이 정책이 우리 사업장에 어떤 의미인지 쉽게 설명해줘");
    }
  }, [policyIdParam, activeSessionId]);

  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }
    if (!historyQ.data) return;
    setMessages(mapHistoryToDisplayMessages(historyQ.data));
  }, [activeSessionId, historyQ.data]);

  const createNewSession = useCallback(
    async (initialMessage: string) => {
      try {
        const data = await createSessionMut.mutateAsync({
          initial_message: initialMessage,
        });
        setActiveSessionId(data.session_id);
        router.replace(`/chat?session=${data.session_id}`, { scroll: false });
        return data.session_id;
      } catch {
        toast.error("상담 세션을 만들지 못했습니다.", {
          message: "잠시 후 다시 시도해 주세요.",
        });
        return null;
      }
    },
    [createSessionMut, router, toast]
  );

  const ensureTempAgentMessage = useCallback((tempId: string, initialContent = "") => {
    setMessages((prev) => {
      const exists = prev.some((message) => message.kind === "agent" && message.id === tempId);
      const withoutLoading = prev.filter((message) => message.kind !== "loading");
      if (exists) {
        return withoutLoading.map((message) =>
          message.kind === "agent" && message.id === tempId
            ? { ...message, content: initialContent || message.content }
            : message
        );
      }
      return [
        ...withoutLoading,
        {
          kind: "agent" as const,
          id: tempId,
          content: initialContent,
          agent_type: undefined,
          diagnosis_report: null,
          simulation_report: null,
          stats_insight: null,
          rag_results: null,
          created_at: new Date().toISOString(),
        },
      ];
    });
  }, []);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming) return;

    setInput("");
    const tempId = `streaming-${Date.now()}`;
    const userMessage: ChatDisplayMessage = {
      kind: "user",
      id: `user-${Date.now()}`,
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage, { kind: "loading" }]);

    try {
      let sessionId = activeSessionId;
      if (!sessionId) {
        sessionId = await createNewSession(text);
        if (!sessionId) {
          setMessages((prev) => prev.filter((message) => message.kind !== "loading"));
          return;
        }
      }

      setIsStreaming(true);
      setStreamingMsgId(tempId);

      await chatService.streamAgentMessage(sessionId, text, {
        onStatus: (statusText) => {
          ensureTempAgentMessage(tempId, statusText);
        },
        onToken: (token) => {
          setMessages((prev) => {
            const withoutLoading = prev.filter((message) => message.kind !== "loading");
            const index = withoutLoading.findIndex(
              (message) => message.kind === "agent" && message.id === tempId
            );
            if (index === -1) {
              return [
                ...withoutLoading,
                {
                  kind: "agent" as const,
                  id: tempId,
                  content: token,
                  agent_type: undefined,
                  diagnosis_report: null,
                  simulation_report: null,
                  stats_insight: null,
                  rag_results: null,
                  created_at: new Date().toISOString(),
                },
              ];
            }
            return withoutLoading.map((message) =>
              message.kind === "agent" && message.id === tempId
                ? { ...message, content: message.content + token }
                : message
            );
          });
        },
        onDone: (event) => {
          setMessages((prev) => {
            const withoutLoading = prev.filter((message) => message.kind !== "loading");
            const next = withoutLoading.map((message) =>
              message.kind === "agent" && message.id === tempId
                ? {
                    kind: "agent" as const,
                    id: event.message_id,
                    content: event.content,
                    agent_type: event.agent_type,
                    diagnosis_report: event.diagnosis_report,
                    simulation_report: event.simulation_report,
                    stats_insight: event.stats_insight,
                    rag_results: event.rag_results,
                    created_at: new Date().toISOString(),
                  }
                : message
            );

            const replaced = next.some(
              (message) => message.kind === "agent" && message.id === event.message_id
            );
            if (replaced) return next;

            return [
              ...next,
              {
                kind: "agent" as const,
                id: event.message_id,
                content: event.content,
                agent_type: event.agent_type,
                diagnosis_report: event.diagnosis_report,
                simulation_report: event.simulation_report,
                stats_insight: event.stats_insight,
                rag_results: event.rag_results,
                created_at: new Date().toISOString(),
              },
            ];
          });
          void historyQ.refetch();
          void sessionsQ.refetch();
        },
        onError: (error) => {
          setMessages((prev) =>
            prev.filter(
              (message) =>
                message.kind !== "loading" &&
                !(message.kind === "agent" && message.id === tempId)
            )
          );
          toast.error("비즈몽 답변을 받지 못했습니다.", {
            message: "잠시 후 같은 질문을 다시 보내주세요.",
          });
          console.error("[BizMong SSE]", error);
        },
      });
    } catch {
      setMessages((prev) => prev.filter((message) => message.kind !== "loading"));
      toast.error("비즈몽 답변을 받지 못했습니다.", {
        message: "잠시 후 다시 시도해 주세요.",
      });
    } finally {
      setIsStreaming(false);
      setStreamingMsgId(null);
    }
  }, [
    input,
    isStreaming,
    activeSessionId,
    createNewSession,
    ensureTempAgentMessage,
    historyQ,
    sessionsQ,
    toast,
  ]);

  const handleSelectSession = useCallback(
    (id: string) => {
      setActiveSessionId(id);
      setMessages([]);
      setSidebarOpen(false);
      router.replace(`/chat?session=${id}`, { scroll: false });
    },
    [router]
  );

  const handleDeleteSession = useCallback(
    async (id: string) => {
      await deleteMut.mutateAsync(id);
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
        router.replace("/chat", { scroll: false });
      }
      toast.success("상담 세션을 삭제했습니다.");
    },
    [activeSessionId, deleteMut, router, toast]
  );

  const handleNewSession = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
    setSidebarOpen(false);
    setInput("");
    router.replace("/chat", { scroll: false });
  }, [router]);

  const emptyPrompts = useMemo(
    () =>
      policyIdParam
        ? [
            "이 공고가 우리 사업장에 왜 맞을 수 있는지 설명해줘",
            "공고 내용이 어려운데 쉽게 풀어줘",
            "이 정책 신청 전에 먼저 확인할 조건이 뭐야?",
            "정밀진단을 받고 나면 뭐가 더 정확해져?",
          ]
        : BIZMONG_QUICK_REPLIES,
    [policyIdParam]
  );

  return (
    <div
      className={cn(
        "-mx-4 -my-4 flex overflow-hidden lg:-mx-8 lg:-my-6",
        "h-[calc(100dvh-4rem)] lg:h-[calc(100dvh-4rem)]"
      )}
    >
      <div
        className={cn(
          "absolute inset-y-0 left-0 z-30 transition-transform lg:relative lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <ChatSidebar
          sessions={sessionsQ.data ?? []}
          activeSessionId={activeSessionId}
          isLoading={sessionsQ.isLoading}
          onNewSession={handleNewSession}
          onSelectSession={handleSelectSession}
          onDeleteSession={handleDeleteSession}
          onClose={() => setSidebarOpen(false)}
          className="h-full"
        />
      </div>

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex flex-1 flex-col overflow-hidden bg-surface">
        <div className="flex h-12 shrink-0 items-center gap-3 border-b border-surface-border px-4">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="상담 목록 열기"
          >
            <PanelLeft className="h-4 w-4" />
          </Button>

          <div className="flex-1">
            <p className="text-sm font-bold text-ink">비즈몽 상담</p>
            <p className="text-[11px] text-ink-tertiary">
              정책자금 해석과 사업장 고민 상담을 도와드리는 전문 비서
            </p>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={handleNewSession}
            aria-label="새 상담 시작"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-5">
          {messages.length === 0 && !historyQ.isLoading && (
            <div className="flex h-full flex-col items-center justify-center gap-4 pb-10 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-600 text-white shadow-elevated">
                <span className="text-2xl">몽</span>
              </div>
              <div>
                <p className="text-lg font-bold text-ink">비즈몽이 옆에서 같이 보겠습니다</p>
                <p className="mt-1 text-sm text-ink-secondary">
                  공고 문구를 쉽게 풀어드리고, 정책자금 용어를 설명하고,
                  사업장 상황에서 무엇부터 챙겨야 할지 같이 정리해드릴게요.
                </p>
              </div>
              <div className="grid w-full max-w-md grid-cols-1 gap-2 sm:grid-cols-2">
                {emptyPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setInput(prompt)}
                    className={cn(
                      "rounded-xl border border-surface-border bg-surface px-3 py-2.5 text-left text-xs font-medium text-ink-secondary shadow-card transition-colors",
                      "hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700"
                    )}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {historyQ.isLoading && activeSessionId && messages.length === 0 ? (
            <AgentLoadingBubble />
          ) : null}

          {messages.map((message, index) =>
            message.kind === "loading" ? (
              <AgentLoadingBubble key={`loading-${index}`} />
            ) : (
              <ChatMessageBubble
                key={message.id}
                message={message}
                isStreaming={message.kind === "agent" && message.id === streamingMsgId}
              />
            )
          )}
        </div>

        <ChatInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          isLoading={isStreaming}
          disabled={isStreaming}
        />
      </div>
    </div>
  );
}
