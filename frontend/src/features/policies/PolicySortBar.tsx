"use client";

/**
 * 정책 리스트 정렬 바.
 * - 결과 개수 + 정렬 Select
 * - "마감 포함" 토글(기본 off): 마감된 공고 노출 여부
 */

import { Select } from "@/components/ui/select";

export type PolicySortKey = "latest" | "amount_desc" | "deadline_asc";

const SORT_OPTIONS = [
  { value: "latest", label: "최신순" },
  { value: "amount_desc", label: "지원금 높은 순" },
  { value: "deadline_asc", label: "마감 임박순" },
];

interface PolicySortBarProps {
  totalCount: number;
  sort: PolicySortKey;
  onSortChange: (sort: PolicySortKey) => void;
  includeClosed: boolean;
  onIncludeClosedChange: (v: boolean) => void;
}

export function PolicySortBar({
  totalCount,
  sort,
  onSortChange,
  includeClosed,
  onIncludeClosedChange,
}: PolicySortBarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 py-2">
      <p className="text-sm text-ink-secondary">
        총{" "}
        <span className="font-bold text-ink numeric">
          {totalCount.toLocaleString()}
        </span>
        건
      </p>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-1.5 text-xs text-ink-secondary cursor-pointer select-none">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-surface-border text-primary-600 focus:ring-primary-500"
            checked={includeClosed}
            onChange={(e) => onIncludeClosedChange(e.target.checked)}
          />
          마감 포함
        </label>

        <Select
          className="h-9 min-w-[140px]"
          options={SORT_OPTIONS}
          value={sort}
          onChange={(e) => onSortChange(e.target.value as PolicySortKey)}
          aria-label="정렬 기준"
        />
      </div>
    </div>
  );
}
