"use client";

/**
 * NotificationItem — 알림 아이템 컴포넌트.
 *
 * 타입별 아이콘·색상, 읽음/미읽음 dot indicator, 클릭 시 이동.
 */

import * as React from "react";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import { Bell, Clock, Zap, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NotificationItem as NotificationItemType } from "@/types";

const TYPE_META: Record<
  string,
  { icon: React.ElementType; colorClass: string; bgClass: string }
> = {
  POLICY_MATCH: {
    icon: Zap,
    colorClass: "text-primary-600",
    bgClass: "bg-primary-50",
  },
  CHAT_ANSWER: {
    icon: Bell,
    colorClass: "text-success-600",
    bgClass: "bg-success-50",
  },
  DEADLINE: {
    icon: Clock,
    colorClass: "text-accent-600",
    bgClass: "bg-accent-50",
  },
  SYSTEM: {
    icon: Info,
    colorClass: "text-ink-secondary",
    bgClass: "bg-surface-subtle",
  },
};

function relativeTime(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return iso;
  const diffMs = Date.now() - then.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "방금";
  if (diffMin < 60) return `${diffMin}분 전`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}시간 전`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay}일 전`;
  return `${then.getMonth() + 1}월 ${then.getDate()}일`;
}

interface NotificationItemProps {
  item: NotificationItemType;
  onRead: () => void;
}

export function NotificationItem({ item, onRead }: NotificationItemProps) {
  const router = useRouter();
  const meta = TYPE_META[item.type] ?? TYPE_META.SYSTEM;
  const Icon = meta.icon;

  function handleClick() {
    if (!item.is_read) onRead();
    if (item.deep_link) router.push(item.deep_link as Route);
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        "flex w-full items-start gap-4 rounded-xl px-4 py-4 text-left transition-colors",
        "hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500",
        !item.is_read && "bg-primary-50/40"
      )}
    >
      {/* 타입 아이콘 */}
      <span
        className={cn(
          "mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
          meta.bgClass
        )}
      >
        <Icon className={cn("h-5 w-5", meta.colorClass)} />
      </span>

      <div className="min-w-0 flex-1 space-y-0.5">
        <p
          className={cn(
            "text-sm font-semibold leading-snug text-ink",
            !item.is_read && "font-bold"
          )}
        >
          {item.title}
        </p>
        <p className="line-clamp-2 text-sm text-ink-secondary">{item.content}</p>
        <p className="text-xs text-ink-tertiary">{relativeTime(item.created_at)}</p>
      </div>

      {/* 미읽음 dot */}
      {!item.is_read && (
        <span
          aria-label="읽지 않은 알림"
          className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-primary-600"
        />
      )}
    </button>
  );
}

export function NotificationItemSkeleton() {
  return (
    <div className="flex items-start gap-4 px-4 py-4">
      <div className="h-10 w-10 animate-pulse rounded-full bg-surface-subtle" />
      <div className="flex-1 space-y-2 pt-1">
        <div className="h-4 w-48 animate-pulse rounded bg-surface-subtle" />
        <div className="h-3 w-64 animate-pulse rounded bg-surface-subtle" />
        <div className="h-3 w-16 animate-pulse rounded bg-surface-subtle" />
      </div>
    </div>
  );
}
