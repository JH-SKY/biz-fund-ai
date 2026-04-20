"use client";

/**
 * 대시보드 최상단 환영 섹션.
 *  - 사장님 호명 (사업장 이름 우선, 없으면 '사장님')
 *  - 온보딩 미완료(bizId 없음) 시 온보딩 유도 문구 노출
 */

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { BusinessInfo } from "@/types";

interface Props {
  business?: BusinessInfo | null;
  isLoading?: boolean;
  isOnboarded: boolean;
}

export function WelcomeHeader({ business, isLoading, isOnboarded }: Props) {
  const displayName = business?.biz_name ?? "사장님";

  if (isLoading) {
    return (
      <section className="space-y-2">
        <div className="h-4 w-24 animate-pulse rounded bg-surface-subtle" />
        <div className="h-8 w-56 animate-pulse rounded bg-surface-subtle" />
      </section>
    );
  }

  if (!isOnboarded) {
    return (
      <section className="flex flex-col gap-3 rounded-xl border border-accent-200 bg-accent-50/70 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-accent-700">
            온보딩이 필요해요
          </p>
          <h1 className="mt-1 text-xl sm:text-2xl">
            사업자번호만 입력하면 3초 만에 맞춤 정책을 찾아드려요
          </h1>
          <p className="mt-1 text-sm text-ink-secondary">
            사업장 등록을 마쳐야 비즈몽 AI 상담과 맞춤 진단을 받을 수 있습니다.
          </p>
        </div>
        <Button asChild variant="accent" size="lg">
          <Link href="/auth/onboarding">
            시작하기 <ArrowRight />
          </Link>
        </Button>
      </section>
    );
  }

  return (
    <section>
      <p className="text-sm text-ink-tertiary">안녕하세요</p>
      <h1 className="text-2xl sm:text-3xl">
        <span className="text-primary-700">{displayName}</span> 사장님 👋
      </h1>
      <p className="mt-1 text-sm text-ink-secondary">
        오늘도 사장님의 사업을 응원합니다. 아래는 오늘의 핵심 브리핑이에요.
      </p>
    </section>
  );
}
