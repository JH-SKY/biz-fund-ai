"use client";

/**
 * 정책 상세 — 최상단 AI 맞춤 브리핑 섹션.
 *
 * 구성
 *  - 신호등(매칭 등급) + 적합도 점수 배지
 *  - AI 멘트 (예: "사장님, 이 정책은 수혜 가능성이 매우 높아요!")
 *  - 공고 요약 (content 상위 3~4줄 미리보기)
 *  - "AI 요약은 참고용" 디스클레이머
 *
 * 적합도 데이터가 없는 상태(미온보딩 유저 등) 에는 CTA 를 노출한다.
 */

import Link from "next/link";
import { Sparkles, TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { TrafficLightBadge } from "@/components/shared/TrafficLightBadge";
import { cn } from "@/lib/utils";
import type { MatchLevel } from "@/types";

interface Props {
  title: string;
  content: string;
  matchLevel?: MatchLevel | null;
  matchScore?: number | null;
  reason?: string | null;
  hasBusinessProfile?: boolean;
}

function aiCommentOf(level?: MatchLevel | null): string {
  switch (level) {
    case "GREEN":
      return "사장님, 이 정책은 현재 조건에서 수혜 가능성이 매우 높습니다! (비즈몽 응원)";
    case "YELLOW":
      return "일부 조건을 보완하면 충분히 노려볼 만한 정책이에요.";
    case "RED":
      return "현재 조건에서는 다소 어려울 수 있지만, 유사 정책을 함께 추천드려요.";
    default:
      return "이 정책의 핵심 내용을 비즈몽이 한눈에 정리해드려요.";
  }
}

function previewOf(content: string, maxChars = 220): string {
  if (!content) return "";
  // 공백·줄바꿈 정리 + 앞부분만
  const clean = content.replace(/\s+/g, " ").trim();
  return clean.length > maxChars ? clean.slice(0, maxChars) + "…" : clean;
}

export function PolicyDetailHero({
  title,
  content,
  matchLevel,
  matchScore,
  reason,
  hasBusinessProfile = true,
}: Props) {
  const hasScore = typeof matchScore === "number" && matchLevel;
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-2xl border p-5 sm:p-6",
        hasScore && matchLevel === "GREEN"
          ? "border-success-200 bg-gradient-to-br from-success-50 via-surface to-surface"
          : hasScore && matchLevel === "YELLOW"
          ? "border-warning-200 bg-gradient-to-br from-warning-50 via-surface to-surface"
          : hasScore && matchLevel === "RED"
          ? "border-danger-200 bg-gradient-to-br from-danger-50 via-surface to-surface"
          : "border-primary-200 bg-gradient-to-br from-primary-50 via-surface to-surface"
      )}
    >
      <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-white/80 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-primary-700 border border-primary-200">
        <Sparkles className="h-3 w-3" />
        비즈몽 AI 맞춤 브리핑
      </div>

      <h1 className="text-xl leading-tight sm:text-2xl">{title}</h1>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        {hasScore ? (
          <>
            <TrafficLightBadge status={matchLevel!} />
            <span className="numeric rounded-full bg-white/90 border border-surface-border px-3 py-1 text-sm font-bold text-primary-700">
              적합도 {Math.round(matchScore!)}점
            </span>
          </>
        ) : hasBusinessProfile ? (
          <span className="text-xs text-ink-tertiary">
            AI 적합도 분석 중입니다.
          </span>
        ) : (
          <Button asChild variant="primary" size="sm">
            <Link href="/onboarding">
              내 사업장 정보 입력하고 적합도 확인하기
            </Link>
          </Button>
        )}
      </div>

      <p className="mt-4 text-sm font-semibold text-ink sm:text-base">
        {aiCommentOf(matchLevel)}
      </p>
      {reason && (
        <p className="mt-1 text-xs text-ink-secondary sm:text-sm">
          <span className="font-semibold text-primary-700">매칭 근거 · </span>
          {reason}
        </p>
      )}

      {content && (
        <div className="mt-4 rounded-xl bg-white/80 p-4 text-sm leading-relaxed text-ink-secondary backdrop-blur-sm">
          <p className="mb-1 text-xs font-semibold text-primary-700">
            비즈몽 요약
          </p>
          <p>{previewOf(content)}</p>
        </div>
      )}

      <p className="mt-4 flex items-start gap-1.5 text-[11px] text-ink-tertiary">
        <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" />
        AI 요약은 참고용이며, 최종 공고문을 반드시 확인해주세요.
      </p>
    </section>
  );
}
