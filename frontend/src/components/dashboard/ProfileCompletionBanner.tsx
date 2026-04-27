"use client";

/**
 * 대시보드 재무정보 입력 유도 배너.
 *
 * - L1(기본 프로필만 입력된 상태) 사용자에게만 표시
 * - 재무 정보를 입력해야 정밀 진단과 완전 맞춤 추천(확률·시뮬)을 받을 수 있다고 안내
 * - 닫기(X) 버튼으로 세션 동안 숨길 수 있음
 */

import { useState } from "react";
import Link from "next/link";
import { BarChart2, ChevronRight, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  /** L1: 기본 프로필만 / L2: 재무 포함 완성 */
  tier: "L1" | "L2" | undefined;
}

export function ProfileCompletionBanner({ tier }: Props) {
  const [dismissed, setDismissed] = useState(false);

  if (tier !== "L1" || dismissed) return null;

  return (
    <div
      role="status"
      aria-label="추가 정보 입력 안내"
      className="relative rounded-xl border border-primary-200 bg-gradient-to-r from-primary-50 to-blue-50 px-4 py-4"
    >
      {/* 닫기 버튼 */}
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
            재무정보를 입력하면 훨씬 정확한 추천이 가능해요
          </p>
          <p className="mt-0.5 text-xs text-ink-secondary leading-relaxed">
            지금은 사업장 기본정보 기반의{" "}
            <span className="font-semibold text-primary-700">1차 맞춤</span>입니다.
            매출·부채·체납 여부를 입력하면 아래가 모두 활성화돼요.
          </p>
          <ul className="mt-2 space-y-0.5 text-xs text-ink-secondary">
            <li className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary-400" />
              정밀 진단 (부채비율·신호등 점수·개선 포인트)
            </li>
            <li className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary-400" />
              추정 수혜 확률 (공고별 % 표시)
            </li>
            <li className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary-400" />
              시뮬레이션 (&ldquo;부채 줄이면 확률 10% 상승&rdquo; 등)
            </li>
          </ul>

          <Button
            asChild
            size="sm"
            variant="primary"
            className="mt-3"
          >
            <Link href="/profile">
              재무정보 입력하기
              <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
