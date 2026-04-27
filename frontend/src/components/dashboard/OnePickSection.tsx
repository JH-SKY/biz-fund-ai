"use client";

import Link from "next/link";

import { PolicyCard } from "@/components/shared/PolicyCard";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { PolicyRecommendItem } from "@/types";

interface Props {
  items: PolicyRecommendItem[] | undefined;
  tier: "L1" | "L2" | undefined;
  isLoading: boolean;
  onBookmarkToggle: (policyId: string) => void;
}

export function OnePickSection({ items, tier, isLoading, onBookmarkToggle }: Props) {
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

  if (tier !== "L2") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>진단 후 원픽</CardTitle>
          <CardDescription>
            정밀진단이 끝나면 가장 가능성 높은 정책 1건을 더 자신 있게 추천해드릴게요.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-ink-tertiary">
            지금은 사업 기본 정보만 있어서 원픽을 확정하지 않고 후보 정책만 먼저 보여드립니다.
          </p>
          <Button asChild variant="primary" size="sm" className="mt-3">
            <Link href={"/diagnosis" as never}>정밀진단 받기</Link>
          </Button>
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
          <CardDescription>아직 확실하게 추천할 정책을 찾지 못했습니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-ink-tertiary">
            입력한 사업 정보와 재무 상태를 다시 점검한 뒤 한 번 더 추천해 보세요.
          </p>
        </CardContent>
      </Card>
    );
  }

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
