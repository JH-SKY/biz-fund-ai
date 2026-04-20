"use client";

/**
 * PolicyCard — 정책 카드 공용 컴포넌트 (.cursorrules §3.1).
 *
 *  ┌───────────────────────────────────────┐
 *  │ 🟢 [기관명]                            │
 *  │ 정책 제목                              │
 *  │ 💰 최대 7천만원  📍 전국  ⏰ D-30      │
 *  │ [80점] [신청하기↗] [북마크 ♡]         │
 *  └───────────────────────────────────────┘
 *
 * `variant="onePick"` 일 때는 상단에 액센트 라벨/그라데이션을 추가하여
 * 대시보드 우측 '원픽' 강조 배치에 사용한다.
 */

import Link from "next/link";
import { ArrowUpRight, Bookmark, Calendar, MapPin, Wallet } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { TrafficLightBadge } from "@/components/shared/TrafficLightBadge";
import { cn } from "@/lib/utils";

export interface PolicyCardProps {
  policyId: string;
  title: string;
  agencyName?: string;
  maxSupport?: number | null;
  region?: string;
  endDate?: string; // ISO 8601
  score?: number; // 매칭 점수 0~100
  trafficLight?: "green" | "yellow" | "red" | "GREEN" | "YELLOW" | "RED";
  isBookmarked?: boolean;
  onBookmarkToggle?: (policyId: string) => void;
  variant?: "default" | "onePick";
  className?: string;
}

function formatDday(endDate?: string): string | null {
  if (!endDate) return null;
  // 상시접수 (9999-12-31)
  if (endDate.startsWith("9999")) return "상시모집";
  const today = new Date();
  const target = new Date(endDate);
  if (Number.isNaN(target.getTime())) return null;
  const diff = Math.ceil(
    (target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
  );
  if (diff < 0) return "마감";
  if (diff === 0) return "D-Day";
  return `D-${diff}`;
}

function formatMoney(amount?: number | null): string | null {
  if (amount == null) return null;
  const eok = Math.floor(amount / 100_000_000);
  const manRem = Math.floor((amount % 100_000_000) / 10_000);
  if (eok > 0 && manRem === 0) return `최대 ${eok}억원`;
  if (eok > 0) return `최대 ${eok}억 ${manRem.toLocaleString()}만원`;
  if (manRem > 0) return `최대 ${manRem.toLocaleString()}만원`;
  return `최대 ${amount.toLocaleString()}원`;
}

export function PolicyCard({
  policyId,
  title,
  agencyName,
  maxSupport,
  region,
  endDate,
  score,
  trafficLight,
  isBookmarked = false,
  onBookmarkToggle,
  variant = "default",
  className,
}: PolicyCardProps) {
  const dday = formatDday(endDate);
  const money = formatMoney(maxSupport);
  const isOnePick = variant === "onePick";

  return (
    <Card
      className={cn(
        "overflow-hidden",
        isOnePick &&
          "border-accent-200 bg-gradient-to-br from-accent-50/60 via-surface to-surface",
        className
      )}
    >
      {isOnePick && (
        <div className="bg-accent-500/95 px-4 py-1.5 text-[11px] font-bold uppercase tracking-wider text-white">
          🏆 오늘의 원픽 — AI 추천
        </div>
      )}

      <CardHeader className="gap-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            {trafficLight && <TrafficLightBadge status={trafficLight} />}
            {agencyName && (
              <Badge variant="outline" size="sm">
                {agencyName}
              </Badge>
            )}
          </div>
          {typeof score === "number" && (
            <span className="numeric text-sm font-bold text-primary-700">
              {Math.round(score)}점
            </span>
          )}
        </div>
        <Link
          href={`/policies/${policyId}`}
          className="text-base font-bold leading-snug text-ink hover:text-primary-700 sm:text-lg"
        >
          {title}
        </Link>
      </CardHeader>

      <CardContent className="pt-0">
        <dl className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-ink-secondary">
          {money && (
            <div className="flex items-center gap-1">
              <Wallet className="h-3.5 w-3.5 text-primary-500" />
              <dd className="numeric">{money}</dd>
            </div>
          )}
          {region && (
            <div className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5 text-primary-500" />
              <dd>{region}</dd>
            </div>
          )}
          {dday && (
            <div className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5 text-primary-500" />
              <dd
                className={cn(
                  "numeric",
                  dday === "마감" && "text-ink-tertiary",
                  dday.startsWith("D-") && "font-semibold text-accent-700"
                )}
              >
                {dday}
              </dd>
            </div>
          )}
        </dl>
      </CardContent>

      <CardFooter>
        <Button asChild variant={isOnePick ? "accent" : "primary"} size="sm">
          <Link href={`/policies/${policyId}`}>
            신청하기 <ArrowUpRight />
          </Link>
        </Button>
        <Button
          variant="secondary"
          size="sm"
          aria-label={isBookmarked ? "북마크 해제" : "북마크 추가"}
          onClick={() => onBookmarkToggle?.(policyId)}
        >
          <Bookmark
            className={cn(isBookmarked && "fill-primary-600 text-primary-600")}
          />
          <span className="hidden sm:inline">
            {isBookmarked ? "북마크됨" : "북마크"}
          </span>
        </Button>
      </CardFooter>
    </Card>
  );
}
