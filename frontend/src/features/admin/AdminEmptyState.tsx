"use client";

import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

interface AdminEmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function AdminEmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
}: AdminEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-surface-border bg-surface px-6 py-16 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-subtle text-ink-tertiary">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {description && (
        <p className="max-w-md text-sm text-ink-secondary">{description}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function AdminTableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-12 animate-pulse rounded-lg bg-surface-subtle"
        />
      ))}
    </div>
  );
}

export function AdminErrorState({
  message,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-xl border border-danger-100 bg-danger-50 px-6 py-10 text-center">
      <h3 className="text-base font-semibold text-danger-600">
        데이터를 불러오지 못했습니다
      </h3>
      {message && (
        <p className="mt-1 text-sm text-danger-500">{message}</p>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 inline-flex items-center rounded-md border border-danger-500 px-3 py-1.5 text-sm font-semibold text-danger-600 hover:bg-danger-100"
        >
          다시 시도
        </button>
      )}
    </div>
  );
}
