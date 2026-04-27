"use client";

/**
 * [P07] /chat — 비즈몽 AI 에이전트 채팅 (Biz-Mong Chat)
 *
 * 레이아웃 (.cursorrules §P07)
 *  Desktop(lg+): [세션 사이드바 w-64] + [채팅 영역 flex-1]
 *  Mobile      : 채팅 영역만 표시 + 상단 "세션" 버튼으로 사이드바 슬라이드
 *
 * URL 파라미터
 *  ?session={id}               → 기존 세션 재개
 *  ?mode=document&policyId={id}→ 서류 준비 모드로 신규 세션 시작
 *
 * 상태 관리
 *  - 세션 목록: React Query (useChatSessions)
 *  - 현재 메시지: local useState (실시간 낙관적 추가)
 *  - AI 전송: useSendAgentMessage mutation
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PanelLeft, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ChatSidebar } from "@/features/chat/ChatSidebar";
import { ChatInput } from "@/features/chat/ChatInput";
import { ChatMessageBubble } from "@/features/chat/ChatMessageBubble";
import { AgentLoadingBubble } from "@/features/chat/AgentLoadingBubble";
import {
  useChatSessions,
  useCreateSession,
  useDeleteSession,
} from "@/hooks/useChat";
import { chatService } from "@/lib/services";
import { useToast } from "@/providers/ToastProvider";
import type { ChatDisplayMessage } from "@/types";
import { cn } from "@/lib/utils";

/** 스크롤 자동으로 최하단 이동 */
function useScrollToBottom(dep: unknown) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [dep]);
  return ref;
}

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const toast = useToast();

  // URL 파라미터
  const sessionParam = searchParams?.get("session") ?? null;
  const modeParam = searchParams?.get("mode") ?? null;
  const policyIdParam = searchParams?.get("policyId") ?? null;

  // 세션 상태
  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    sessionParam
  );
  const [messages, setMessages] = useState<ChatDisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);
  const [showGreetingReplies, setShowGreetingReplies] = useState(false);

  /** 인사 응답 후 보여줄 4개 빠른 답변 */
  const GREETING_QUICK_REPLIES = [
    "내 사업장 진단해줘",
    "정책 자금 검색해줘",
    "시뮬레이션 분석해줘",
    "우리 업종 통계 알려줘",
  ];

  const scrollRef = useScrollToBottom(messages);

  // Queries / Mutations
  const sessionsQ = useChatSessions();
  const createSessionMut = useCreateSession();
  const deleteMut = useDeleteSession();

  // ── 세션 생성 ──────────────────────────────────────────────────────
  const createNewSession = useCallback(
    async (initialMessage: string) => {
      try {
        const data = await createSessionMut.mutateAsync({ initial_message: initialMessage });
        setActiveSessionId(data.session_id);
        router.replace(`/chat?session=${data.session_id}`, { scroll: false });
        return data.session_id;
      } catch {
        toast.error("세션 생성에 실패했습니다.", { message: "잠시 후 다시 시도해주세요." });
        return null;
      }
    },
    [createSessionMut, router, toast]
  );

  // ── mode=document 자동 시작 ────────────────────────────────────────
  useEffect(() => {
    if (modeParam === "document" && policyIdParam && !activeSessionId) {
      const initMsg = `${decodeURIComponent(policyIdParam)} 정책의 서류 준비를 도와줘.`;
      setInput(initMsg);
    }
  }, [modeParam, policyIdParam, activeSessionId]);

  // ── 메시지 전송 (SSE 스트리밍) ──────────────────────────────────────
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput("");
    setShowGreetingReplies(false);

    // 1. 유저 메시지 즉시 표시 + 로딩 버블
    const userMsg: ChatDisplayMessage = {
      kind: "user",
      id: `u-${Date.now()}`,
      content: text,
      created_at: new Date().toISOString(),
    };
    const tempId = `streaming-${Date.now()}`;
    setMessages((prev) => [...prev, userMsg, { kind: "loading" }]);

    try {
      // 2. 세션 없으면 생성
      let sid = activeSessionId;
      if (!sid) {
        sid = await createNewSession(text);
        if (!sid) return;
      }

      // 3. SSE 스트리밍 시작
      setIsStreaming(true);
      let statusText = "";

      await chatService.streamAgentMessage(sid, text, {
        onStatus: (text) => {
          statusText = text;
          // 로딩 버블을 상태 텍스트로 교체
          setMessages((prev) => {
            const without = prev.filter((m) => m.kind !== "loading");
            return [
              ...without,
              {
                kind: "agent" as const,
                id: tempId,
                content: statusText,
                agent_type: undefined,
                diagnosis_report: null,
                simulation_report: null,
                stats_insight: null,
                rag_results: null,
                created_at: new Date().toISOString(),
              },
            ];
          });
          setStreamingMsgId(tempId);
        },
        onToken: (token) => {
          // 토큰을 스트리밍 메시지에 누적
          setMessages((prev) => {
            const idx = prev.findIndex((m) => m.kind === "agent" && m.id === tempId);
            if (idx === -1) {
              // 최초 토큰: 로딩 버블 제거 + 스트리밍 버블 생성
              const without = prev.filter((m) => m.kind !== "loading");
              return [
                ...without,
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
            // 기존 스트리밍 버블에 토큰 누적
            return prev.map((m) =>
              m.kind === "agent" && m.id === tempId
                ? { ...m, content: m.content + token }
                : m
            );
          });
          setStreamingMsgId(tempId);
        },
        onDone: (evt) => {
          setMessages((prev) => {
            // 임시 ID → 실제 메시지 ID 로 교체 + 최종 데이터 반영
            return prev.map((m) => {
              if (m.kind === "agent" && m.id === tempId) {
                return {
                  kind: "agent" as const,
                  id: evt.message_id,
                  content: evt.content,
                  agent_type: evt.agent_type,
                  diagnosis_report: evt.diagnosis_report,
                  simulation_report: evt.simulation_report,
                  stats_insight: evt.stats_insight,
                  rag_results: evt.rag_results,
                  created_at: new Date().toISOString(),
                };
              }
              return m;
            });
          });
          if (evt.agent_type === "greeting") setShowGreetingReplies(true);
        },
        onError: (err) => {
          setMessages((prev) =>
            prev.filter((m) => !(m.kind === "agent" && m.id === tempId) && m.kind !== "loading")
          );
          toast.error("응답을 받지 못했습니다.", {
            message: "죄송해요, 잠시 후 다시 시도해주세요.",
          });
          console.error("[SSE] 에러:", err);
        },
      });
    } catch {
      setMessages((prev) => prev.filter((m) => m.kind !== "loading"));
      toast.error("응답을 받지 못했습니다.", {
        message: "죄송해요, 제가 아직 배우는 중이라서요. 다시 시도해주세요.",
      });
    } finally {
      setIsStreaming(false);
      setStreamingMsgId(null);
    }
  }, [input, activeSessionId, isStreaming, createNewSession, toast]);

  // ── 세션 선택 ──────────────────────────────────────────────────────
  const handleSelectSession = useCallback(
    (id: string) => {
      setActiveSessionId(id);
      setMessages([]);
      setShowGreetingReplies(false);
      setSidebarOpen(false);
      router.replace(`/chat?session=${id}`, { scroll: false });
    },
    [router]
  );

  // ── 세션 삭제 ──────────────────────────────────────────────────────
  const handleDeleteSession = useCallback(
    async (id: string) => {
      await deleteMut.mutateAsync(id);
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
        setShowGreetingReplies(false);
        router.replace("/chat", { scroll: false });
      }
      toast.success("상담 세션이 삭제됐습니다.");
    },
    [activeSessionId, deleteMut, router, toast]
  );

  // ── 새 상담 ────────────────────────────────────────────────────────
  const handleNewSession = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
    setShowGreetingReplies(false);
    setSidebarOpen(false);
    router.replace("/chat", { scroll: false });
  }, [router]);

  const isLoading = isStreaming;

  return (
    <div
      className={cn(
        // AppShell 내부 패딩을 제거하고 전체 높이 활용
        "-mx-4 -my-4 flex overflow-hidden lg:-mx-8 lg:-my-6",
        "h-[calc(100dvh-4rem)] lg:h-[calc(100dvh-4rem)]"
      )}
    >
      {/* ── 세션 사이드바 ───────────────────────────────────── */}
      {/* 데스크탑: 항상 표시 / 모바일: overlay */}
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

      {/* 모바일 오버레이 배경 */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── 채팅 메인 영역 ─────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden bg-surface">
        {/* 채팅 헤더 */}
        <div className="flex h-12 shrink-0 items-center gap-3 border-b border-surface-border px-4">
          {/* 모바일: 사이드바 열기 버튼 */}
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
            <p className="text-sm font-bold text-ink">비즈몽 AI 상담</p>
            <p className="text-[11px] text-ink-tertiary">
              정책자금 진단 · 시뮬레이션 · 검색 · 통계를 한 번에
            </p>
          </div>
          {activeSessionId && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleNewSession}
              aria-label="새 상담 시작"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* 메시지 스크롤 영역 */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-5 space-y-4"
        >
          {/* 빈 상태: 상담 시작 안내 */}
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center gap-4 pb-10 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-600 text-white shadow-elevated">
                <span className="text-2xl">🤖</span>
              </div>
              <div>
                <p className="text-lg font-bold text-ink">
                  안녕하세요! 비즈몽입니다 👋
                </p>
                <p className="mt-1 text-sm text-ink-secondary">
                  정책자금 진단, 서류 준비, 업계 통계까지
                  <br />
                  무엇이든 물어보세요.
                </p>
              </div>
              {/* 추천 시작 프롬프트 */}
              <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
                {[
                  "내 사업장 정책자금 진단해줘",
                  "소상공인 경영안정자금 설명해줘",
                  "특허 취득하면 점수 얼마나 올라?",
                  "우리 업종 평균 매출 알려줘",
                ].map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => {
                      setInput(prompt);
                      setTimeout(handleSend, 50);
                    }}
                    className={cn(
                      "rounded-xl border border-surface-border bg-surface px-3 py-2.5",
                      "text-left text-xs font-medium text-ink-secondary shadow-card",
                      "transition-colors hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700"
                    )}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 메시지 렌더링 */}
          {messages.map((msg, idx) =>
            msg.kind === "loading" ? (
              <AgentLoadingBubble key={`loading-${idx}`} />
            ) : (
              <ChatMessageBubble
                key={msg.id}
                message={msg}
                isStreaming={msg.kind === "agent" && msg.id === streamingMsgId}
              />
            )
          )}

          {/* 인사 응답 후 빠른 선택지 */}
          {showGreetingReplies && !isStreaming && (
            <div className="flex flex-wrap gap-2 pl-11">
              {GREETING_QUICK_REPLIES.map((reply) => (
                <button
                  key={reply}
                  type="button"
                  onClick={() => {
                    setInput(reply);
                    setTimeout(handleSend, 50);
                  }}
                  className={cn(
                    "rounded-full border border-primary-200 bg-primary-50",
                    "px-3 py-1.5 text-xs font-semibold text-primary-700",
                    "transition-colors hover:bg-primary-100"
                  )}
                >
                  {reply}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 입력창 */}
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          isLoading={isLoading}
          disabled={isLoading}
        />
      </div>
    </div>
  );
}
