"use client";

/**
 * ChatSessionCard — 상담 세션 목록에서 클릭 시 해당 채팅으로 이동.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import { MessageSquareHeart, ChevronRight } from "lucide-react";
import type { ChatSession } from "@/types";
import { cn } from "@/lib/utils";

function relativeDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const diffDays = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "오늘";
  if (diffDays === 1) return "어제";
  if (diffDays < 7) return `${diffDays}일 전`;
  return `${d.getMonth() + 1}월 ${d.getDate()}일`;
}

interface ChatSessionCardProps {
  session: ChatSession;
}

export function ChatSessionCard({ session }: ChatSessionCardProps) {
  const router = useRouter();

  return (
    <button
      type="button"
      onClick={() => router.push(`/chat?session=${session.session_id}`)}
      className={cn(
        "flex w-full items-center gap-4 rounded-xl border border-surface-border bg-surface p-4 text-left shadow-card",
        "transition-shadow hover:border-primary-200 hover:shadow-card-hover",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
      )}
    >
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-50 text-primary-600">
        <MessageSquareHeart className="h-5 w-5" />
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-ink">
          {session.title}
        </p>
        {session.last_message && (
          <p className="mt-0.5 truncate text-xs text-ink-secondary">
            {session.last_message}
          </p>
        )}
        <p className="mt-1 text-xs text-ink-tertiary">
          {relativeDate(session.updated_at)}
        </p>
      </div>

      <ChevronRight className="h-4 w-4 shrink-0 text-ink-tertiary" />
    </button>
  );
}

export function ChatSessionCardSkeleton() {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-surface-border bg-surface p-4 shadow-card">
      <div className="h-10 w-10 animate-pulse rounded-full bg-surface-subtle" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-36 animate-pulse rounded bg-surface-subtle" />
        <div className="h-3 w-56 animate-pulse rounded bg-surface-subtle" />
      </div>
    </div>
  );
}
