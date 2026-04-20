"use client";

import Link from "next/link";
import { FileSearch } from "lucide-react";

import { Button } from "@/components/ui/button";

interface PolicyEmptyStateProps {
  title?: string;
  description?: string;
  onReset?: () => void;
}

export function PolicyEmptyState({
  title = "해당 조건에 맞는 공고가 없습니다.",
  description = "다른 필터를 선택하거나 키워드를 바꿔보세요.",
  onReset,
}: PolicyEmptyStateProps) {
  return (
    <div className="rounded-xl border border-dashed border-surface-border bg-surface p-10 text-center">
      <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-surface-muted">
        <FileSearch className="h-6 w-6 text-ink-tertiary" />
      </div>
      <h3 className="text-lg">{title}</h3>
      <p className="mt-1 text-sm text-ink-secondary">{description}</p>
      <div className="mt-5 flex items-center justify-center gap-2">
        {onReset && (
          <Button variant="secondary" size="sm" onClick={onReset}>
            필터 초기화
          </Button>
        )}
        <Button asChild variant="primary" size="sm">
          <Link href="/policies/matching">맞춤 정책 보기</Link>
        </Button>
      </div>
    </div>
  );
}
