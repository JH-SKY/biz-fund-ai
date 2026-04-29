"use client";

import { useRouter } from "next/navigation";
import { Bot } from "lucide-react";

import { Button } from "@/components/ui/button";
import { chatService } from "@/lib/services";
import { cn } from "@/lib/utils";
import type { ChatDisplayMessage } from "@/types";
import { AgentResultCard } from "./agent-cards/AgentResultCard";

function BizmongAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-600 text-white shadow-sm">
      <Bot className="h-4 w-4" />
    </div>
  );
}

interface Props {
  message: Exclude<ChatDisplayMessage, { kind: "loading" }>;
  isStreaming?: boolean;
  sessionId?: string | null;
}

export function ChatMessageBubble({ message, isStreaming = false, sessionId }: Props) {
  const router = useRouter();
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

  const handleTrackedMove = async (ctaType: string, targetPath: string) => {
    if (!sessionId) {
      router.push(targetPath as never);
      return;
    }

    try {
      await chatService.trackCtaEvent(sessionId, {
        assistant_message_id: message.id,
        cta_type: ctaType,
        target_path: targetPath,
        metadata: {
          agent_type: message.agent_type ?? null,
          source: "chat_message_bubble",
        },
      });
    } catch (error) {
      console.error("[BizMong CTA]", error);
    } finally {
      router.push(targetPath as never);
    }
  };

  return (
    <div className="flex items-start gap-3">
      <BizmongAvatar />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        {(message.content || isStreaming) && (
          <div
            className={cn(
              "rounded-2xl rounded-tl-sm border border-surface-border bg-surface px-4 py-3",
              "text-sm leading-relaxed text-ink shadow-card"
            )}
          >
            <p className="whitespace-pre-wrap">
              {message.content}
              {isStreaming && (
                <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-primary-600 align-middle" />
              )}
            </p>
          </div>
        )}

        {!isStreaming && message.agent_type && (
          <AgentResultCard
            agentType={message.agent_type}
            statsInsight={message.stats_insight}
            ragResults={message.rag_results}
            sessionId={sessionId}
            assistantMessageId={message.id}
          />
        )}

        {!isStreaming && sessionId ? (
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void handleTrackedMove("DIAGNOSIS_PAGE", "/diagnosis")}
            >
              정밀진단으로 이동
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void handleTrackedMove("MATCHING_PAGE", "/policies/matching")}
            >
              맞춤정책추천 보기
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
