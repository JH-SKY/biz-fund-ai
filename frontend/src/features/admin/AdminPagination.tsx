"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface AdminPaginationProps {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
  maxVisible?: number;
}

export function AdminPagination({
  page,
  totalPages,
  onChange,
  maxVisible = 7,
}: AdminPaginationProps) {
  if (totalPages <= 1) return null;

  const half = Math.floor(maxVisible / 2);
  let start = Math.max(1, page - half);
  const end = Math.min(totalPages, start + maxVisible - 1);
  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1);
  }
  const pages: number[] = [];
  for (let i = start; i <= end; i++) pages.push(i);

  const btn =
    "inline-flex h-8 min-w-8 items-center justify-center rounded-md px-2 text-sm font-medium transition-colors";

  return (
    <nav
      aria-label="페이지 네비게이션"
      className="flex items-center justify-center gap-1"
    >
      <button
        type="button"
        onClick={() => onChange(Math.max(1, page - 1))}
        disabled={page <= 1}
        className={cn(btn, "text-ink-secondary hover:bg-surface-muted disabled:opacity-40")}
        aria-label="이전"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      {start > 1 && (
        <>
          <button
            type="button"
            onClick={() => onChange(1)}
            className={cn(btn, "text-ink-secondary hover:bg-surface-muted")}
          >
            1
          </button>
          {start > 2 && (
            <span className="px-1 text-sm text-ink-tertiary">…</span>
          )}
        </>
      )}

      {pages.map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => onChange(p)}
          aria-current={p === page ? "page" : undefined}
          className={cn(
            btn,
            p === page
              ? "bg-primary-600 text-white"
              : "text-ink-secondary hover:bg-surface-muted"
          )}
        >
          {p}
        </button>
      ))}

      {end < totalPages && (
        <>
          {end < totalPages - 1 && (
            <span className="px-1 text-sm text-ink-tertiary">…</span>
          )}
          <button
            type="button"
            onClick={() => onChange(totalPages)}
            className={cn(btn, "text-ink-secondary hover:bg-surface-muted")}
          >
            {totalPages}
          </button>
        </>
      )}

      <button
        type="button"
        onClick={() => onChange(Math.min(totalPages, page + 1))}
        disabled={page >= totalPages}
        className={cn(btn, "text-ink-secondary hover:bg-surface-muted disabled:opacity-40")}
        aria-label="다음"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </nav>
  );
}
