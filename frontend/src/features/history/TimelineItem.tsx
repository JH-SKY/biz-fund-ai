"use client";

/**
 * TimelineItem — 타임라인 단일 이벤트 아이템.
 *
 * 세로 선 + 아이콘 + 내용 구조.
 */

import * as React from "react";
import { cn } from "@/lib/utils";

interface TimelineItemProps {
  icon: React.ReactNode;
  iconBg?: string;
  title: string;
  description?: string;
  timestamp: string;
  isLast?: boolean;
  onClick?: () => void;
  clickable?: boolean;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function TimelineItem({
  icon,
  iconBg = "bg-primary-50",
  title,
  description,
  timestamp,
  isLast = false,
  onClick,
  clickable,
}: TimelineItemProps) {
  const Wrapper = clickable ? "button" : "div";

  return (
    <div className="flex gap-4">
      {/* 아이콘 + 세로선 */}
      <div className="flex flex-col items-center">
        <span
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
            iconBg
          )}
        >
          {icon}
        </span>
        {!isLast && (
          <span className="mt-1 w-px flex-1 bg-surface-border" />
        )}
      </div>

      {/* 내용 */}
      <Wrapper
        type={clickable ? "button" : undefined}
        onClick={onClick}
        className={cn(
          "mb-6 min-w-0 flex-1 rounded-xl border border-surface-border bg-surface p-4 shadow-card",
          clickable &&
            "cursor-pointer text-left transition-shadow hover:shadow-card-hover hover:border-primary-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
        )}
      >
        <p className="text-sm font-semibold text-ink">{title}</p>
        {description && (
          <p className="mt-0.5 line-clamp-2 text-xs text-ink-secondary">
            {description}
          </p>
        )}
        <p className="mt-1.5 text-xs text-ink-tertiary numeric">
          {formatDateTime(timestamp)}
        </p>
      </Wrapper>
    </div>
  );
}

export function TimelineItemSkeleton({ isLast }: { isLast?: boolean }) {
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <div className="h-10 w-10 animate-pulse rounded-full bg-surface-subtle" />
        {!isLast && <span className="mt-1 w-px flex-1 bg-surface-border" />}
      </div>
      <div className="mb-6 flex-1 space-y-2 rounded-xl border border-surface-border bg-surface p-4 shadow-card">
        <div className="h-4 w-40 animate-pulse rounded bg-surface-subtle" />
        <div className="h-3 w-56 animate-pulse rounded bg-surface-subtle" />
        <div className="h-3 w-28 animate-pulse rounded bg-surface-subtle" />
      </div>
    </div>
  );
}
