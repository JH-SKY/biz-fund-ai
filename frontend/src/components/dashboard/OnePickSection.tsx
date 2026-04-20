"use client";

/**
 * 원픽(One-Pick) 섹션 — AI 추천 1위 정책 강조 배치.
 *  - data 가 없으면 "추천 준비 중" 빈 상태 노출
 *  - 로딩 중에는 스켈레톤
 */

import { PolicyCard } from "@/components/shared/PolicyCard";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { PolicyRecommendItem } from "@/types";

interface Props {
  items: PolicyRecommendItem[] | undefined;
  isLoading: boolean;
  onBookmarkToggle: (policyId: string) => void;
}

export function OnePickSection({ items, isLoading, onBookmarkToggle }: Props) {
  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-4 w-24 rounded bg-surface-subtle" />
          <div className="mt-2 h-6 w-48 rounded bg-surface-subtle" />
        </CardHeader>
        <CardContent>
          <div className="h-16 rounded bg-surface-subtle" />
        </CardContent>
      </Card>
    );
  }

  const top = items?.[0];
  if (!top) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>오늘의 원픽</CardTitle>
          <CardDescription>
            사장님께 딱 맞는 정책을 분석하고 있어요.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-ink-tertiary">
            프로필 입력이 끝나면 AI가 우선순위 1위 정책을 뽑아드립니다.
          </p>
        </CardContent>
      </Card>
    );
  }

  // PolicyRecommendItem 은 agency / closed_at 등이 없으므로 가용 필드만 사용.
  return (
    <PolicyCard
      variant="onePick"
      policyId={top.policy_id}
      title={top.title}
      trafficLight={top.match_level}
      score={top.match_score}
      isBookmarked={top.is_bookmarked}
      onBookmarkToggle={onBookmarkToggle}
    />
  );
}
