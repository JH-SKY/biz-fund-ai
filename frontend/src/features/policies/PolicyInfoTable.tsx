"use client";

/**
 * 정책 핵심 정보 요약 테이블.
 * - 지원 대상 / 지원 금액 / 지원 내용(카테고리) / 접수 기간 / 필수 서류
 */

import { cn } from "@/lib/utils";

interface Row {
  label: string;
  value: React.ReactNode;
}

interface Props {
  rows: Row[];
  className?: string;
}

export function PolicyInfoTable({ rows, className }: Props) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-xl border border-surface-border bg-surface shadow-card",
        className
      )}
      aria-label="정책 핵심 정보"
    >
      <header className="border-b border-surface-border bg-surface-subtle px-4 py-3">
        <h2 className="text-sm font-bold text-ink">핵심 정보</h2>
      </header>
      <dl className="divide-y divide-surface-border">
        {rows.map((row) => (
          <div
            key={row.label}
            className="grid grid-cols-[100px_1fr] gap-3 px-4 py-3 sm:grid-cols-[140px_1fr] sm:px-5"
          >
            <dt className="text-xs font-semibold text-ink-secondary sm:text-sm">
              {row.label}
            </dt>
            <dd className="text-sm text-ink">{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
