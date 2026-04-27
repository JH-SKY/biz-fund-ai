"use client";

/**
 * 정책 상세 — 최상단 AI 맞춤 브리핑 섹션.
 *
 * tier 에 따라 두 가지 모드로 동작합니다.
 *  L2(재무 입력 완료) — 신호등·적합도·매칭 근거 표시
 *  L1(기본 프로필만) — 점수·신호등 없음, "신청 대상 가능성" + 진단 유도 CTA
 *
 * 요약 짤림 방지: 기본 300자 미리보기 + "더 보기/접기" 토글
 */

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, Sparkles, TriangleAlert } from "lucide-react";

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
  /** L1: 기본 프로필만 / L2: 재무 포함 완성. undefined 는 L1 취급 */
  tier?: "L1" | "L2";
}

function aiCommentOf(level?: MatchLevel | null, tier?: "L1" | "L2"): string {
  if (tier !== "L2") {
    return "이 공고의 신청 대상에 해당할 수 있습니다. 재무정보를 입력하면 실제 수혜 가능 여부를 알려드려요.";
  }
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

const PREVIEW_CHARS = 300;

export function PolicyDetailHero({
  title,
  content,
  matchLevel,
  matchScore,
  reason,
  hasBusinessProfile = true,
  tier,
}: Props) {
  const [summaryExpanded, setSummaryExpanded] = useState(false);

  const isL2 = tier === "L2";
  const hasScore = isL2 && typeof matchScore === "number" && matchLevel;

  const cleanContent = content ? content.replace(/\s+/g, " ").trim() : "";
  const isLong = cleanContent.length > PREVIEW_CHARS;
  const previewContent = isLong && !summaryExpanded
    ? cleanContent.slice(0, PREVIEW_CHARS) + "…"
    : cleanContent;

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

      {/* 적합도 영역 — tier 분기 */}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        {hasScore ? (
          // L2: 신호등 + 점수 표시
          <>
            <TrafficLightBadge status={matchLevel!} />
            <span className="numeric rounded-full bg-white/90 border border-surface-border px-3 py-1 text-sm font-bold text-primary-700">
              적합도 {Math.round(matchScore!)}점
            </span>
          </>
        ) : isL2 ? (
          // L2인데 데이터 없음 (로딩 중 등)
          <span className="text-xs text-ink-tertiary">AI 적합도 분석 중입니다.</span>
        ) : hasBusinessProfile ? (
          // L1: 신청 가능 배지 + 진단 유도 CTA
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
              신청 가능 공고
            </span>
            <Button asChild variant="primary" size="sm">
              <Link href="/profile">
                진단받고 수혜 여부 확인 →
              </Link>
            </Button>
          </div>
        ) : (
          // 온보딩 미완료
          <Button asChild variant="primary" size="sm">
            <Link href="/onboarding">
              내 사업장 정보 입력하고 적합도 확인하기
            </Link>
          </Button>
        )}
      </div>

      <p className="mt-4 text-sm font-semibold text-ink sm:text-base">
        {aiCommentOf(matchLevel, tier)}
      </p>

      {/* L2에서만 매칭 근거 표시 */}
      {isL2 && reason && (
        <p className="mt-1 text-xs text-ink-secondary sm:text-sm">
          <span className="font-semibold text-primary-700">매칭 근거 · </span>
          {reason}
        </p>
      )}

      {/* 비즈몽 요약 — 긴 텍스트 expand/collapse */}
      {cleanContent && (
        <div className="mt-4 rounded-xl bg-white/80 p-4 text-sm leading-relaxed text-ink-secondary backdrop-blur-sm">
          <p className="mb-1 text-xs font-semibold text-primary-700">비즈몽 요약</p>
          <p className="whitespace-pre-line">{previewContent}</p>
          {isLong && (
            <button
              type="button"
              onClick={() => setSummaryExpanded((v) => !v)}
              className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary-600 hover:text-primary-800"
            >
              {summaryExpanded ? (
                <>접기 <ChevronUp className="h-3 w-3" /></>
              ) : (
                <>더 보기 <ChevronDown className="h-3 w-3" /></>
              )}
            </button>
          )}
        </div>
      )}

      <p className="mt-4 flex items-start gap-1.5 text-[11px] text-ink-tertiary">
        <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" />
        AI 요약은 참고용이며, 최종 공고문을 반드시 확인해주세요.
      </p>
    </section>
  );
}
