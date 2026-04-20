"use client";

/**
 * 데스크탑 사이드바 (lg 이상에서만 고정 노출).
 *
 * 구조
 *  - 상단: 로고
 *  - 중앙: 주요 메뉴(대시보드 · 맞춤 정책 · AI 상담 · 비즈픽 · 마이페이지)
 *  - 하단: 정보 완성도 위젯 자리(추후 추가)
 *
 * 모바일에서는 Header 의 햄버거 메뉴 → Drawer 형태로 동일 컴포넌트를 재사용한다.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Rocket } from "lucide-react";

import { cn } from "@/lib/utils";
import { NAV_ITEMS, isActivePath } from "@/config/navigation";

interface SidebarProps {
  /** Drawer 모드일 때 true — 고정 포지션 대신 전체 너비 노출 */
  variant?: "fixed" | "drawer";
  onNavigate?: () => void;
}

export function Sidebar({ variant = "fixed", onNavigate }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      aria-label="메인 사이드바"
      className={cn(
        "flex flex-col bg-surface border-r border-surface-border",
        variant === "fixed"
          ? "hidden lg:flex lg:fixed lg:inset-y-0 lg:left-0 lg:w-sidebar lg:z-30"
          : "w-full h-full"
      )}
    >
      {/* 로고 영역 */}
      <div className="flex items-center gap-2 h-header px-5 border-b border-surface-border">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600 text-white">
          <Rocket className="h-5 w-5" />
        </div>
        <div className="leading-tight">
          <p className="text-base font-bold text-ink">Biz-Up</p>
          <p className="text-[11px] text-ink-tertiary">사장님 AI 비서</p>
        </div>
      </div>

      {/* 네비게이션 */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const active = isActivePath(pathname, item);
            const Icon = item.icon;
            return (
              <li key={item.key}>
                <Link
                  href={item.href}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary-50 text-primary-700"
                      : "text-ink-secondary hover:bg-surface-muted hover:text-ink"
                  )}
                >
                  <Icon
                    className={cn(
                      "h-5 w-5 shrink-0",
                      active
                        ? "text-primary-600"
                        : "text-ink-tertiary group-hover:text-ink-secondary"
                    )}
                  />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* 하단 상태 영역 (추후 확장) */}
      <div className="border-t border-surface-border p-4">
        <div className="rounded-lg bg-primary-50 p-3">
          <p className="text-xs font-semibold text-primary-700">정보 완성도</p>
          <p className="mt-1 text-lg font-bold text-primary-900">80%</p>
          <div className="mt-2 h-1.5 w-full rounded-full bg-primary-100">
            <div className="h-full w-4/5 rounded-full bg-primary-500" />
          </div>
        </div>
      </div>
    </aside>
  );
}
