"use client";

/**
 * GNB (Global Navigation Bar) — 상단 고정 헤더.
 *
 * 데스크탑 (lg+)
 *  - 사이드바 옆으로 붙어 페이지 내용 상단만 차지
 *  - 우측: 알림 · 프로필
 *
 * 모바일 (<lg)
 *  - 좌측 햄버거 버튼 → 사이드바 Drawer 토글
 *  - 가운데 로고
 *  - 우측 알림
 */

import Link from "next/link";
import { Bell, Menu, Rocket, UserCircle2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Sidebar } from "./Sidebar";

export function Header() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  // 경로 변경 시 자동 닫힘 + 바디 스크롤 락
  useEffect(() => {
    if (drawerOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [drawerOpen]);

  return (
    <>
      <header
        className={cn(
          "sticky top-0 z-40 h-header-mobile lg:h-header",
          "border-b border-surface-border bg-surface/90 backdrop-blur",
          "flex items-center justify-between px-4 lg:px-6",
          // 데스크탑에서는 사이드바 너비만큼 왼쪽으로 밀어 정렬
          "lg:pl-[calc(theme(spacing.sidebar)+1.5rem)]"
        )}
      >
        <div className="flex items-center gap-3">
          {/* 모바일 햄버거 */}
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="메뉴 열기"
            className="lg:hidden inline-flex h-10 w-10 items-center justify-center rounded-lg hover:bg-surface-muted"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* 모바일 로고 */}
          <Link
            href="/dashboard"
            className="lg:hidden flex items-center gap-2"
            aria-label="Biz-Up 홈"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-600 text-white">
              <Rocket className="h-4 w-4" />
            </div>
            <span className="text-base font-bold text-ink">Biz-Up</span>
          </Link>

          {/* 데스크탑 브레드크럼 자리 (추후 확장) */}
          <div className="hidden lg:block text-sm text-ink-tertiary">
            환영합니다, 사장님 👋
          </div>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            aria-label="알림"
            className="relative"
          >
            <Bell className="h-5 w-5" />
            {/* 미확인 알림 뱃지 */}
            <span
              aria-hidden
              className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger-500"
            />
          </Button>
          <Button variant="ghost" size="icon" aria-label="프로필">
            <UserCircle2 className="h-6 w-6" />
          </Button>
        </div>
      </header>

      {/* 모바일 Drawer */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-50 lg:hidden"
          role="dialog"
          aria-modal="true"
        >
          {/* 오버레이 */}
          <div
            className="absolute inset-0 bg-ink/40 animate-fade-in"
            onClick={() => setDrawerOpen(false)}
            aria-hidden
          />
          {/* Drawer 패널 */}
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] bg-surface shadow-elevated animate-slide-in-left">
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              aria-label="메뉴 닫기"
              className="absolute right-2 top-3 inline-flex h-10 w-10 items-center justify-center rounded-lg hover:bg-surface-muted"
            >
              <X className="h-5 w-5" />
            </button>
            <Sidebar
              variant="drawer"
              onNavigate={() => setDrawerOpen(false)}
            />
          </div>
        </div>
      )}
    </>
  );
}
