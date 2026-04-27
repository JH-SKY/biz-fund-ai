"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  matchedCount: number | null;
  tier: "L1" | "L2" | undefined;
  isLoading?: boolean;
}

export function MatchSummaryCard({ matchedCount, tier, isLoading }: Props) {
  const isPrecise = tier === "L2";

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-accent-500" />
          <p className="text-xs font-semibold uppercase tracking-wider text-accent-600">
            AI 맞춤 추천
          </p>
        </div>
        <CardTitle>
          {isPrecise ? "정밀진단을 반영한 맞춤 정책" : "지금은 1차 후보 정책만 보여드리고 있어요"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="h-16 w-48 animate-pulse rounded bg-surface-subtle" />
        ) : matchedCount == null || matchedCount === 0 ? (
          <div className="rounded-lg border border-dashed border-surface-border bg-surface-muted p-4">
            <p className="text-sm text-ink-secondary">
              {isPrecise
                ? "현재 조건에 맞는 정책을 아직 찾지 못했습니다."
                : "정밀진단 전이라 확신도 높은 정책만 먼저 추리는 중입니다."}
            </p>
            <p className="text-xs text-ink-tertiary">
              {isPrecise
                ? "사업 정보나 조건을 조금 더 보완하면 다시 넓게 찾을 수 있습니다."
                : "정밀진단을 마치면 사업장 상태까지 반영한 추천으로 다시 계산합니다."}
            </p>
          </div>
        ) : (
          <div className="flex items-baseline gap-2">
            <span className="numeric text-5xl font-extrabold text-primary-700 sm:text-6xl">
              {matchedCount.toLocaleString()}
            </span>
            <span className="text-lg font-bold text-ink">건</span>
            <span className="ml-2 text-sm text-ink-secondary">
              {isPrecise ? "정밀 추천 정책이 준비되어 있어요" : "후보 정책이 먼저 추려졌어요"}
            </span>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <Button asChild variant="primary" size="lg" className="w-full sm:w-auto">
            <Link href={(isPrecise ? "/policies/matching" : "/diagnosis") as never}>
              <Sparkles />
              {isPrecise ? "맞춤 정책 보러가기" : "정밀진단 받고 정교하게 추천받기"}
            </Link>
          </Button>
          {!isPrecise ? (
            <Button asChild variant="ghost" size="lg" className="w-full sm:w-auto">
              <Link href={"/policies/matching" as never}>후보 정책만 먼저 보기</Link>
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
