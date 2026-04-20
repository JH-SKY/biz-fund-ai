"use client";

/**
 * HeroCounter — 정책자금 총예산 카운트업 애니메이션.
 *
 * 스펙
 *  - 2초 동안 0 → target 까지 증가 (requestAnimationFrame + easeOutCubic)
 *  - 3자리 콤마 자동 삽입 (ko-KR locale)
 *  - reduced-motion 사용자에게는 즉시 최종값 표시 (접근성)
 *  - 모바일: 가독성을 위해 '26조 4,500억 원' 같은 축약 병기
 */

import { useEffect, useRef, useState } from "react";

interface HeroCounterProps {
  target: number; // 원 단위
  durationMs?: number;
  label?: string;
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

function formatShort(won: number): string {
  const jo = Math.floor(won / 1_0000_0000_0000);
  const eok = Math.floor((won % 1_0000_0000_0000) / 1_0000_0000);
  const manEok = Math.floor(eok / 10_000);
  const restEok = eok - manEok * 10_000;
  const parts: string[] = [];
  if (jo > 0) parts.push(`${jo}조`);
  if (restEok > 0) parts.push(`${restEok.toLocaleString("ko-KR")}억`);
  return parts.join(" ") || "0원";
}

export function HeroCounter({
  target,
  durationMs = 2000,
  label = "2026년 사장님들을 기다리는 정책 자금 총액",
}: HeroCounterProps) {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (prefersReducedMotion) {
      setValue(target);
      return;
    }

    const start = performance.now();
    const step = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / durationMs, 1);
      setValue(Math.round(target * easeOutCubic(progress)));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step);
      }
    };
    rafRef.current = requestAnimationFrame(step);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [target, durationMs]);

  return (
    <div className="flex flex-col items-center gap-3 text-center">
      <p className="text-sm font-medium text-primary-700 sm:text-base">
        {label}
      </p>
      <p
        className="numeric bg-gradient-to-r from-primary-700 to-primary-500 bg-clip-text text-transparent font-bold tracking-tight text-3xl sm:text-5xl lg:text-6xl break-keep"
        aria-live="polite"
      >
        ₩ {value.toLocaleString("ko-KR")}
      </p>
      <p className="text-base sm:text-lg font-semibold text-ink-secondary">
        약 <span className="text-primary-700">{formatShort(target)}</span>{" "}
        규모
      </p>
    </div>
  );
}
