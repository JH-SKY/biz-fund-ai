"use client";

/**
 * 핵심 정보 카드 — 이달의 꿀팁 / 비즈-픽 진입 유도.
 * (고정 문구 + 링크. 실시간 콘텐츠는 /picks 에서 제공)
 */

import Link from "next/link";
import { ArrowRight, Newspaper } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function InsightTipCard() {
  return (
    <Card className="bg-gradient-to-br from-primary-50 via-surface to-surface">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Newspaper className="h-4 w-4 text-primary-600" />
          <p className="text-xs font-semibold uppercase tracking-wider text-primary-700">
            오늘의 꿀팁
          </p>
        </div>
        <CardTitle>정책자금 처음이세요?</CardTitle>
        <CardDescription>
          &ldquo;서류 3개로 최대 7천만원&rdquo; — 소상공인 경영안정자금부터 시작하세요.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-ink-secondary">
          비즈-픽에서 사장님 눈높이에 맞춘 정책 카드 뉴스를 매주 업데이트 해드려요.
        </p>
      </CardContent>
      <CardFooter>
        <Button asChild variant="primary" size="sm">
          <Link href="/picks">
            비즈-픽 보러가기 <ArrowRight />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
