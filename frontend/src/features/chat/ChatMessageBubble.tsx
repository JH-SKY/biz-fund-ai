"use client";

import { Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentResultCard } from "./agent-cards/AgentResultCard";
import type { ChatDisplayMessage } from "@/types";

function BizmongAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-600 text-white shadow-sm">
      <Bot className="h-4 w-4" />
    </div>
  );
}

interface Props {
  message: Exclude<ChatDisplayMessage, { kind: "loading" }>;
  /** 현재 스트리밍 중인지 여부 — true 이면 커서 깜박임 */
  isStreaming?: boolean;
}

export function ChatMessageBubble({ message, isStreaming = false }: Props) {
  const isUser = message.kind === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className={cn(
            "max-w-[80%] rounded-2xl rounded-br-sm px-4 py-3",
            "bg-primary-600 text-white shadow-sm",
            "text-sm leading-relaxed"
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  // Agent message
  return (
    <div className="flex items-start gap-3">
      <BizmongAvatar />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        {/* 텍스트 요약 버블 */}
        {(message.content || isStreaming) && (
          <div
            className={cn(
              "rounded-2xl rounded-tl-sm border border-surface-border bg-surface px-4 py-3",
              "text-sm leading-relaxed text-ink shadow-card"
            )}
          >
            <p className="whitespace-pre-wrap">
              {message.content}
              {/* 스트리밍 커서 */}
              {isStreaming && (
                <span className="inline-block w-0.5 h-4 ml-0.5 bg-primary-600 align-middle animate-pulse" />
              )}
            </p>
          </div>
        )}
        {/* 에이전트 결과 카드 — 스트리밍 완료 후에만 표시 */}
        {!isStreaming && message.agent_type && (
          <AgentResultCard
            agentType={message.agent_type}
            diagnosisReport={message.diagnosis_report}
            simulationReport={message.simulation_report}
            statsInsight={message.stats_insight}
            ragResults={message.rag_results}
          />
        )}
      </div>
    </div>
  );
}
