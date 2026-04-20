"use client";

import { cn } from "@/lib/utils";
import type { SystemHealth } from "@/types";

interface SystemStatusBadgeProps {
  status: SystemHealth | string;
  size?: "sm" | "md";
}

const STATUS_META: Record<
  string,
  { dot: string; label: string; bg: string; text: string }
> = {
  HEALTHY: {
    dot: "bg-success-500",
    label: "정상",
    bg: "bg-success-50",
    text: "text-success-600",
  },
  DEGRADED: {
    dot: "bg-accent-500",
    label: "지연",
    bg: "bg-accent-50",
    text: "text-accent-700",
  },
  DOWN: {
    dot: "bg-danger-500",
    label: "장애",
    bg: "bg-danger-50",
    text: "text-danger-600",
  },
  UNKNOWN: {
    dot: "bg-ink-tertiary",
    label: "확인 중",
    bg: "bg-surface-subtle",
    text: "text-ink-secondary",
  },
};

export function SystemStatusBadge({
  status,
  size = "md",
}: SystemStatusBadgeProps) {
  const meta = STATUS_META[status] ?? STATUS_META.UNKNOWN;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold",
        meta.bg,
        meta.text,
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-3 py-1 text-sm"
      )}
    >
      <span
        className={cn(
          "inline-block rounded-full",
          meta.dot,
          size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2",
          status === "HEALTHY" && "animate-pulse"
        )}
      />
      {meta.label}
    </span>
  );
}

export function mapBatchStatusToTone(status: string) {
  switch (status) {
    case "SUCCESS":
      return { label: "성공", className: "bg-success-50 text-success-600" };
    case "RUNNING":
      return { label: "실행 중", className: "bg-primary-50 text-primary-700" };
    case "FAILED":
      return { label: "실패", className: "bg-danger-50 text-danger-600" };
    case "PENDING":
      return { label: "대기", className: "bg-surface-subtle text-ink-secondary" };
    case "SCHEDULED":
      return { label: "예약됨", className: "bg-accent-50 text-accent-700" };
    default:
      return {
        label: status,
        className: "bg-surface-subtle text-ink-secondary",
      };
  }
}
