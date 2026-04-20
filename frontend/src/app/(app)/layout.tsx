"use client";

/**
 * (app) route group — 로그인 + 온보딩 완료 유저 전용 레이아웃.
 *
 * AppGuard 가 다음을 자동 처리:
 *  - 비로그인 → /login 리다이렉트
 *  - 로그인 + 온보딩 미완료 → /onboarding 리다이렉트
 */

import type { ReactNode } from "react";
import { AppShell } from "@/components/layout";
import { AppGuard } from "@/components/auth/AuthGuard";

export default function AppGroupLayout({ children }: { children: ReactNode }) {
  return (
    <AppGuard>
      <AppShell>{children}</AppShell>
    </AppGuard>
  );
}
