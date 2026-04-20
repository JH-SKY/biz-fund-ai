"use client";

/**
 * 맞춤 정책 카드 (P06 전용).
 *
 * PolicyCard 와의 차이점
 *  - 매칭 점수 + 신호등을 카드 상단에 강조
 *  - 비즈몽 AI 요약 배지 → 클릭 시 펼쳐지는 영역
 *  - 매칭 사유(reason) 를 본문에 노출
 *  - 내부 Link 로 상세(/policies/:id) 이동
 */

import Link from "next/link";
import { useState } from "react";
import { Bookmark, ChevronDown, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { TrafficLightBadge } from "@/components/shared/TrafficLightBadge";
import { cn } from "@/lib/utils";
import type { MatchLevel } from "@/types";

export interface MatchingPolicyCardProps {
  policyId: string;
  title: string;
  matchLevel: MatchLevel;
  matchScore: number;
  reason: string;
  isBookmarked: boolean;
  onBookmarkToggle?: (policyId: string) => void;
  /** D-Day (예: "D-7", "상시모집", "마감"); 없으면 미표시 */
  dday?: string | null;
  /** [신규] / [인기] 등 상태 태그 */
  statusTag?: "new" | "hot" | "urgent" | null;
  className?: string;
}

function StatusBadge({ tag }: { tag: NonNullable<MatchingPolicyCardProps["statusTag"]> }) {
  const map = {
    new: { label: "신규", variant: "success" as const },
    hot: { label: "인기", variant: "accent" as const },
    urgent: { label: "마감임박", variant: "danger" as const },
  };
  const { label, variant } = map[tag];
  return (
    <Badge variant={variant} size="sm">
      {label}
    </Badge>
  );
}

export function MatchingPolicyCard({
  policyId,
  title,
  matchLevel,
  matchScore,
  reason,
  isBookmarked,
  onBookmarkToggle,
  dday,
  statusTag,
  className,
}: MatchingPolicyCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <TrafficLightBadge status={matchLevel} />
            {statusTag && <StatusBadge tag={statusTag} />}
            {dday && (
              <span
                className={cn(
                  "numeric rounded-full border px-2 py-0.5 text-[11px] font-semibold",
                  dday === "마감"
                    ? "border-surface-border text-ink-tertiary"
                    : dday.startsWith("D-")
                    ? "border-accent-300 bg-accent-50 text-accent-800"
                    : "border-success-200 bg-success-50 text-success-800"
                )}
              >
                {dday}
              </span>
            )}
          </div>
          <span className="numeric text-sm font-bold text-primary-700">
            적합도 {Math.round(matchScore)}점
          </span>
        </div>
        <Link
          href={`/policies/${policyId}`}
          className="text-base font-bold leading-snug text-ink hover:text-primary-700 sm:text-lg"
        >
          {title}
        </Link>
        <p className="text-xs text-ink-secondary sm:text-sm">
          <span className="font-semibold text-primary-700">매칭 근거 · </span>
          {reason}
        </p>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition-colors",
              "bg-primary-50 text-primary-700 hover:bg-primary-100 border border-primary-100"
            )}
          >
            <Sparkles className="h-3.5 w-3.5" />
            비즈몽 3줄 요약
            <ChevronDown
              className={cn(
                "h-3.5 w-3.5 transition-transform",
                expanded && "rotate-180"
              )}
            />
          </button>

          <Button asChild variant="ghost" size="sm">
            <Link href={`/policies/${policyId}`}>상세 보기 →</Link>
          </Button>

          <Button
            variant="secondary"
            size="sm"
            className="ml-auto"
            aria-label={isBookmarked ? "북마크 해제" : "관심 정책 저장"}
            onClick={() => onBookmarkToggle?.(policyId)}
          >
            <Bookmark
              className={cn(isBookmarked && "fill-primary-600 text-primary-600")}
            />
            <span className="hidden sm:inline">
              {isBookmarked ? "저장됨" : "관심"}
            </span>
          </Button>
        </div>

        {expanded && (
          <div className="mt-3 rounded-lg border border-primary-100 bg-primary-50/60 p-3 text-xs text-ink sm:text-sm">
            <p className="mb-1 font-semibold text-primary-800">비즈몽 요약</p>
            <ul className="list-disc space-y-0.5 pl-4 text-ink-secondary">
              <li>{reason}</li>
              <li>
                상세 조건과 필요 서류는{" "}
                <Link
                  href={`/policies/${policyId}`}
                  className="text-primary-700 underline"
                >
                  상세 페이지
                </Link>
                에서 확인하실 수 있어요.
              </li>
              <li className="text-[11px] text-ink-tertiary">
                ※ AI 요약은 참고용이며, 최종 내용은 공고문을 반드시 확인해주세요.
              </li>
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
