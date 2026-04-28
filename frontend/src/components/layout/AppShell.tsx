"use client";

/**
 * AppShell — 로그인 후 공통 레이아웃.
 *
 * 반응형 구조
 *  ┌────────────────────────────────────────────────┐
 *  │ Header (sticky, lg: 사이드바 너비만큼 들여쓰기) │
 *  ├─────────┬──────────────────────────────────────┤
 *  │ Sidebar │  <main> — 페이지 본문                │
 *  │ (lg+)   │                                      │
 *  ├─────────┴──────────────────────────────────────┤
 *  │ Footer (lg+)                                   │
 *  └────────────────────────────────────────────────┘
 *  모바일: Sidebar 숨김 → Header 의 햄버거 Drawer + 하단 BottomTabBar
 */

import type { ReactNode } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { BottomTabBar } from "./BottomTabBar";
import { Footer } from "./Footer";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-surface-muted">
      <Sidebar variant="fixed" />

      <div className="lg:pl-sidebar flex min-h-dvh flex-col">
        <Header />

        <main
          className="flex-1 px-4 pb-[calc(theme(spacing.bottom-tab)+1rem)] pt-4 lg:px-8 lg:pb-10 lg:pt-6"
          id="main-content"
        >
          <div className="mx-auto w-full max-w-[var(--content-max)]">
            {children}
          </div>
        </main>

        <Footer />
      </div>

      <BottomTabBar />
    </div>
  );
}
