"use client";

/**
 * 비즈몽 AI 응답 대기 중 로딩 버블.
 * .cursorrules §P07: 단계별 텍스트를 2초 간격으로 순환 표시.
 */

import { useEffect, useState } from "react";
import { Bot } from "lucide-react";

const STEPS = [
  "비즈몽이 사업장 정보를 확인하고 있습니다...",
  "현재 접수 중인 정책 200개를 검토 중입니다...",
  "AI가 맞춤 채점을 진행 중입니다...",
];

export function AgentLoadingBubble() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      setStep((prev) => (prev + 1) % STEPS.length);
    }, 2000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex items-start gap-3">
      {/* 아바타 — 박동 애니메이션 */}
      <div className="flex h-8 w-8 shrink-0 animate-pulse items-center justify-center rounded-full bg-primary-600 text-white shadow-sm">
        <Bot className="h-4 w-4" />
      </div>

      <div className="rounded-2xl rounded-tl-sm border border-primary-100 bg-primary-50 px-4 py-3 shadow-card">
        {/* 타이핑 점 */}
        <div className="mb-2 flex items-center gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-primary-500"
              style={{ animationDelay: `${i * 180}ms` }}
            />
          ))}
        </div>

        {/* 진행 단계 텍스트 */}
        <p className="text-xs font-medium text-primary-700">{STEPS[step]}</p>

        {/* 진행 바 */}
        <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-primary-100">
          <div
            className="h-full rounded-full bg-primary-500 transition-all duration-[2000ms] ease-linear"
            style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
