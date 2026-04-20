"use client";

/**
 * 맞춤 정책 건수 + 비즈몽 AI 연결 CTA.
 *  - 큰 숫자로 '이 만큼 혜택 가능' 메시지를 최상단에 전달 (.cursorrules 원칙: 결론 먼저)
 *  - 데이터 없을 때는 온보딩 / 조건 수정 유도 문구 노출
 */

import Link from "next/link";
import { MessageSquareHeart, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface Props {
  matchedCount: number | null;
  isLoading?: boolean;
}

export function MatchSummaryCard({ matchedCount, isLoading }: Props) {
  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-accent-500" />
          <p className="text-xs font-semibold uppercase tracking-wider text-accent-600">
            AI 맞춤 브리핑
          </p>
        </div>
        <CardTitle>지금 사장님이 받을 수 있는 정책</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="h-16 w-48 animate-pulse rounded bg-surface-subtle" />
        ) : matchedCount == null || matchedCount === 0 ? (
          <div className="rounded-lg border border-dashed border-surface-border bg-surface-muted p-4">
            <p className="text-sm text-ink-secondary">
              조건에 맞는 공고를 아직 찾지 못했어요.
            </p>
            <p className="text-xs text-ink-tertiary">
              프로필(업종·지역·직원 수)을 더 자세히 입력하면 더 많은 정책을 찾아드려요.
            </p>
            <Button asChild variant="ghost" size="sm" className="mt-2 -ml-2">
              <Link href="/profile">조건 수정하러 가기 →</Link>
            </Button>
          </div>
        ) : (
          <div className="flex items-baseline gap-2">
            <span className="numeric text-5xl font-extrabold text-primary-700 sm:text-6xl">
              {matchedCount.toLocaleString()}
            </span>
            <span className="text-lg font-bold text-ink">건</span>
            <span className="ml-2 text-sm text-ink-secondary">
              의 맞춤 공고가 기다리고 있어요
            </span>
          </div>
        )}

        <Button asChild variant="primary" size="lg" className="w-full sm:w-auto">
          <Link href="/chat">
            <MessageSquareHeart />
            비즈몽 AI 비서에게 물어보기
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
