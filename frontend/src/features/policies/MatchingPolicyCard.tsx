"use client";

import Link from "next/link";
import { useState } from "react";
import { Bookmark, ChevronDown, ClipboardList, Sparkles } from "lucide-react";

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
  estimatedProbability?: number | null;
  isBookmarked: boolean;
  onBookmarkToggle?: (policyId: string) => void;
  dday?: string | null;
  statusTag?: "new" | "hot" | "urgent" | null;
  tier?: "L1" | "L2";
  className?: string;
}

function StatusBadge({
  tag,
}: {
  tag: NonNullable<MatchingPolicyCardProps["statusTag"]>;
}) {
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
  estimatedProbability,
  isBookmarked,
  onBookmarkToggle,
  dday,
  statusTag,
  tier,
  className,
}: MatchingPolicyCardProps) {
  const [expanded, setExpanded] = useState(false);
  const isL2 = tier === "L2";

  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            {isL2 ? (
              <>
                <TrafficLightBadge status={matchLevel} />
                {statusTag ? <StatusBadge tag={statusTag} /> : null}
              </>
            ) : (
              <span className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-[11px] font-semibold text-blue-800">
                1차 후보군
              </span>
            )}

            {dday ? (
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
            ) : null}
          </div>

          {isL2 ? (
            <div className="flex items-center gap-2">
              {estimatedProbability != null ? (
                <span className="numeric rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-[11px] font-semibold text-green-800">
                  추정 가능성 {estimatedProbability}%
                </span>
              ) : null}
              <span className="numeric text-sm font-bold text-primary-700">
                적합도 {Math.round(matchScore)}점
              </span>
            </div>
          ) : null}
        </div>

        <Link
          href={`/policies/${policyId}`}
          className="text-base font-bold leading-snug text-ink hover:text-primary-700 sm:text-lg"
        >
          {title}
        </Link>

        {isL2 ? (
          <p className="text-xs text-ink-secondary sm:text-sm">
            <span className="font-semibold text-primary-700">매칭 근거: </span>
            {reason}
          </p>
        ) : (
          <p className="text-xs text-ink-secondary sm:text-sm">
            1차 정보 기준으로 조건이 어느 정도 맞는 후보입니다.
            <span className="font-semibold text-primary-700"> 재무 정보를 입력하면 실제 가능성을 더 정확히 볼 수 있어요.</span>
          </p>
        )}
      </CardHeader>

      <CardContent className="pt-0">
        <div className="flex flex-wrap items-center gap-2">
          {isL2 ? (
            <button
              type="button"
              onClick={() => setExpanded((value) => !value)}
              aria-expanded={expanded}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border border-primary-100 bg-primary-50 px-3 py-1 text-xs font-semibold text-primary-700 transition-colors hover:bg-primary-100"
              )}
            >
              <Sparkles className="h-3.5 w-3.5" />
              추천 근거 보기
              <ChevronDown
                className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")}
              />
            </button>
          ) : (
            <Button asChild size="sm" variant="primary">
              <Link href="/profile">
                <ClipboardList className="h-3.5 w-3.5" />
                추가 정보 입력
              </Link>
            </Button>
          )}

          <Button asChild variant="ghost" size="sm">
            <Link href={`/policies/${policyId}`}>상세 보기</Link>
          </Button>

          <Button
            variant="secondary"
            size="sm"
            className="ml-auto"
            aria-label={isBookmarked ? "북마크 해제" : "북마크 추가"}
            onClick={() => onBookmarkToggle?.(policyId)}
          >
            <Bookmark
              className={cn(isBookmarked && "fill-primary-600 text-primary-600")}
            />
            <span className="hidden sm:inline">{isBookmarked ? "저장됨" : "북마크"}</span>
          </Button>
        </div>

        {isL2 && expanded ? (
          <div className="mt-3 rounded-lg border border-primary-100 bg-primary-50/60 p-3 text-xs text-ink sm:text-sm">
            <p className="mb-1 font-semibold text-primary-800">추천 근거</p>
            <ul className="list-disc space-y-0.5 pl-4 text-ink-secondary">
              <li>{reason}</li>
              <li>
                상세 조건과 신청 요건은{" "}
                <Link href={`/policies/${policyId}`} className="text-primary-700 underline">
                  정책 상세 페이지
                </Link>
                에서 다시 확인해 주세요.
              </li>
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
