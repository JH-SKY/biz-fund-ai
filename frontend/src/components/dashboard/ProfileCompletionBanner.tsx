"use client";

import { useState } from "react";
import Link from "next/link";
import { BarChart2, ChevronRight, X } from "lucide-react";

import { Button } from "@/components/ui/button";

interface Props {
  tier: "L1" | "L2" | undefined;
}

export function ProfileCompletionBanner({ tier }: Props) {
  const [dismissed, setDismissed] = useState(false);

  if (tier !== "L1" || dismissed) return null;

  return (
    <div
      role="status"
      aria-label="정밀진단 안내"
      className="relative rounded-xl border border-primary-200 bg-gradient-to-r from-primary-50 to-blue-50 px-4 py-4"
    >
      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label="닫기"
        className="absolute right-3 top-3 rounded-full p-1 text-ink-tertiary hover:bg-primary-100 hover:text-ink"
      >
        <X className="h-3.5 w-3.5" />
      </button>

      <div className="flex items-start gap-3 pr-6">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-100">
          <BarChart2 className="h-4 w-4 text-primary-700" />
        </div>

        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-primary-900">
            먼저 정밀진단을 받으면 맞춤 정책 추천이 훨씬 정확해집니다.
          </p>
          <p className="mt-0.5 text-xs leading-relaxed text-ink-secondary">
            지금은 사업 기본 정보만 반영한 1차 후보 추천 단계입니다. 정밀진단에서 매출, 부채,
            체납 여부를 입력하면 그 정보가 바로 맞춤 정책 추천에도 반영됩니다.
          </p>
          <ul className="mt-2 space-y-0.5 text-xs text-ink-secondary">
            <li className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary-400" />
              내 사업장 상태를 먼저 진단
            </li>
            <li className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary-400" />
              진단 후 정책 자격 조건까지 반영한 정밀 추천 제공
            </li>
          </ul>

          <Button asChild size="sm" variant="primary" className="mt-3">
            <Link href={"/diagnosis" as never}>
              정밀진단 받기
              <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
