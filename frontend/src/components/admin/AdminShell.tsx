"use client";

/**
 * AdminShell — 관리자 센터 공통 레이아웃.
 *
 * 구조
 *  ┌──────────────────────────────────────┐
 *  │  Header (sticky)                     │
 *  ├─────────┬────────────────────────────┤
 *  │ Sidebar │  <main>                    │
 *  │ (lg+)   │  (surface-muted 배경)      │
 *  └─────────┴────────────────────────────┘
 *
 * - 로그인 페이지는 shell 없이 AdminPublicGuard 만 적용한다.
 * - BizmongWidget, BottomTabBar 등 일반 서비스 컴포넌트는 포함하지 않는다.
 */

import * as React from "react";
import { AdminSidebar } from "./AdminSidebar";
import { AdminHeader } from "./AdminHeader";

export function AdminShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  return (
    <div className="min-h-dvh bg-surface-muted">
      <AdminSidebar variant="fixed" />

      {/* 모바일 Drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            aria-hidden
            className="absolute inset-0 bg-ink/60"
            onClick={() => setDrawerOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-64 animate-slide-in-left">
            <AdminSidebar
              variant="drawer"
              onNavigate={() => setDrawerOpen(false)}
            />
          </div>
        </div>
      )}

      <div className="lg:pl-sidebar flex min-h-dvh flex-col">
        <AdminHeader onMenuClick={() => setDrawerOpen(true)} />

        <main
          id="admin-main-content"
          className="flex-1 px-4 py-6 lg:px-8 lg:py-8"
        >
          <div className="mx-auto w-full max-w-[1400px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
