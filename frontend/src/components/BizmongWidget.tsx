"use client";

/**
 * BizmongWidget — 모든 (app) 페이지 우하단 고정 플로팅 버튼.
 *
 * 기능
 *  - /chat 페이지에서는 자동 숨김 (이미 채팅 화면이므로 불필요)
 *  - 클릭 시 /chat 으로 이동
 *  - 미니 툴팁으로 "비즈몽에게 물어보기" 안내
 *
 * 위치
 *  - 데스크탑: bottom-6 right-6
 *  - 모바일: 하단 탭바(4rem) 위 + 0.75rem 여백
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot } from "lucide-react";
import { cn } from "@/lib/utils";

export function BizmongWidget() {
  const pathname = usePathname();

  // /chat 페이지에서는 숨김
  if (pathname?.startsWith("/chat")) return null;

  return (
    <div
      className={cn(
        "fixed z-40 transition-transform hover:scale-105",
        // 모바일: 하단 탭바 바로 위
        "bottom-[calc(theme(spacing.bottom-tab)+0.75rem)] right-4",
        // 데스크탑: 우하단
        "lg:bottom-6 lg:right-6"
      )}
    >
      <Link
        href="/chat"
        aria-label="비즈몽 AI 상담 시작"
        className={cn(
          "group flex h-14 w-14 items-center justify-center rounded-full",
          "bg-primary-600 text-white shadow-elevated",
          "hover:bg-primary-700 active:bg-primary-800",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        )}
      >
        <Bot className="h-6 w-6" />
        {/* 툴팁 */}
        <span
          className={cn(
            "pointer-events-none absolute right-16 top-1/2 -translate-y-1/2",
            "whitespace-nowrap rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-white shadow-elevated",
            "opacity-0 transition-opacity group-hover:opacity-100",
            "after:absolute after:left-full after:top-1/2 after:-translate-y-1/2",
            "after:border-4 after:border-transparent after:border-l-ink after:content-['']"
          )}
        >
          비즈몽에게 물어보기
        </span>
      </Link>
    </div>
  );
}
