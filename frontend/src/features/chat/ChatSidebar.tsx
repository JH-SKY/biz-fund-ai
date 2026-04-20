"use client";

import { Pencil, Trash2, MessageSquareHeart, ChevronLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { ChatSession } from "@/types";

function formatRelative(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return "오늘";
  if (diffDays === 1) return "어제";
  if (diffDays < 7) return `${diffDays}일 전`;
  return `${d.getMonth() + 1}월 ${d.getDate()}일`;
}

interface Props {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading: boolean;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  /** 모바일: 닫기 */
  onClose?: () => void;
  className?: string;
}

export function ChatSidebar({
  sessions,
  activeSessionId,
  isLoading,
  onNewSession,
  onSelectSession,
  onDeleteSession,
  onClose,
  className,
}: Props) {
  return (
    <aside
      className={cn(
        "flex h-full w-64 shrink-0 flex-col border-r border-surface-border bg-surface-muted",
        className
      )}
    >
      {/* 헤더 */}
      <div className="flex items-center justify-between border-b border-surface-border px-4 py-3">
        <div className="flex items-center gap-2">
          <MessageSquareHeart className="h-4 w-4 text-primary-600" />
          <span className="text-sm font-bold text-ink">상담 내역</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="primary"
            size="sm"
            onClick={onNewSession}
            aria-label="새 상담 시작"
          >
            <Pencil />
            <span className="hidden sm:inline">새 상담</span>
          </Button>
          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              aria-label="사이드바 닫기"
              className="lg:hidden"
            >
              <ChevronLeft />
            </Button>
          )}
        </div>
      </div>

      {/* 세션 목록 */}
      <nav className="flex-1 overflow-y-auto p-2" aria-label="상담 세션 목록">
        {isLoading ? (
          <div className="space-y-1.5 p-2">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-12 animate-pulse rounded-lg bg-surface-subtle"
              />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <p className="px-3 py-6 text-center text-xs text-ink-tertiary">
            아직 상담 내역이 없어요.
            <br />
            비즈몽에게 첫 질문을 해보세요!
          </p>
        ) : (
          <ul className="space-y-0.5">
            {sessions.map((s) => {
              const isActive = s.session_id === activeSessionId;
              return (
                <li key={s.session_id}>
                  <div
                    className={cn(
                      "group flex cursor-pointer items-start justify-between rounded-lg px-3 py-2.5 transition-colors",
                      isActive
                        ? "bg-primary-50 text-primary-800"
                        : "text-ink-secondary hover:bg-surface-subtle"
                    )}
                    role="button"
                    tabIndex={0}
                    onClick={() => onSelectSession(s.session_id)}
                    onKeyDown={(e) =>
                      e.key === "Enter" && onSelectSession(s.session_id)
                    }
                  >
                    <div className="min-w-0 flex-1">
                      <p
                        className={cn(
                          "truncate text-xs font-semibold leading-tight",
                          isActive ? "text-primary-800" : "text-ink"
                        )}
                      >
                        {s.title || "새 상담"}
                      </p>
                      {s.last_message && (
                        <p className="mt-0.5 truncate text-[11px] text-ink-tertiary">
                          {s.last_message}
                        </p>
                      )}
                      <p className="mt-0.5 text-[11px] text-ink-tertiary">
                        {formatRelative(s.updated_at)}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="ml-1 shrink-0 rounded p-0.5 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-danger-50 hover:text-danger-600"
                      aria-label="세션 삭제"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(s.session_id);
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </nav>

      {/* 푸터 안내 */}
      <div className="border-t border-surface-border px-4 py-3">
        <p className="text-[11px] leading-relaxed text-ink-tertiary">
          채팅 중 입력하신 정보는 암호화되어 보관되며, 상담 목적 이외에 사용되지 않습니다.
        </p>
      </div>
    </aside>
  );
}
