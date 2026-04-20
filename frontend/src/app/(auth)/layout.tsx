"use client";

/**
 * (auth) route group layout — 로그인·온보딩 공통 쉘.
 *
 * PublicGuard 가 다음을 처리:
 *  - 이미 로그인 + 온보딩 완료 → /dashboard 리다이렉트
 *  - 로그인 + 온보딩 미완료 → /onboarding 으로 유도 (/login 접근 시)
 */

import type { ReactNode } from "react";
import Link from "next/link";
import { Rocket } from "lucide-react";
import { PublicGuard } from "@/components/auth/AuthGuard";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <PublicGuard>
      <div className="min-h-dvh bg-gradient-to-b from-primary-50 to-surface flex flex-col">
        <header className="py-6">
          <div className="mx-auto flex max-w-[var(--content-max)] items-center justify-center px-4">
            <Link
              href="/"
              className="flex items-center gap-2"
              aria-label="Biz-Up 홈"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600 text-white">
                <Rocket className="h-5 w-5" />
              </div>
              <span className="text-lg font-bold">Biz-Up</span>
            </Link>
          </div>
        </header>

        <main className="flex-1 flex items-center justify-center px-4 pb-16 pt-4">
          {children}
        </main>
      </div>
    </PublicGuard>
  );
}
