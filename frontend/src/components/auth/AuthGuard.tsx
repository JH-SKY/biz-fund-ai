"use client";

/**
 * AuthGuard — 클라이언트 사이드 라우트 보호.
 *
 * 사용처 1. (app)/layout.tsx → AppGuard (로그인·온보딩 필요)
 * 사용처 2. (auth)/layout.tsx → PublicGuard (로그인된 유저 진입 차단)
 *
 * 왜 클라이언트 사이드?
 *  - Phase 1: 토큰은 localStorage 에 저장 (SSR 접근 불가).
 *  - Phase 2: httpOnly cookie + Next.js Middleware 로 업그레이드 예정.
 *
 * UX 처리
 *  - hydration 전(=서버 렌더) 에는 children 을 렌더링하지 않아 레이아웃 깜빡임 최소화.
 *  - 리다이렉트 판단 중에는 전체 화면 로딩 스피너를 표시.
 */

import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import { Rocket } from "lucide-react";

import { useAuthStore } from "@/stores/auth-store";

// ── 공통 로딩 스크린 ───────────────────────────────────────────────────
function AuthLoadingScreen() {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-surface">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-600 text-white shadow-elevated">
        <Rocket className="h-7 w-7" />
      </div>
      <div className="flex items-center gap-2 text-sm text-ink-secondary">
        <span
          aria-hidden
          className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-300 border-t-primary-600"
        />
        <span>잠시만 기다려주세요...</span>
      </div>
    </div>
  );
}

// ── AppGuard (로그인 필요 영역 보호) ─────────────────────────────────────
/**
 * (app)/* 경로에 사용.
 * 
 * 규칙:
 *  - 비로그인 → /login 으로 리다이렉트 (현재 경로를 callbackUrl 로 전달)
 *  - 로그인 + 온보딩 미완료 → /onboarding 으로 리다이렉트
 *  - 정상 → children 렌더링
 */
export function AppGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = React.useState(false);

  const isAuthenticated = useAuthStore((s) => Boolean(s.accessToken));
  const isOnboarded = useAuthStore((s) => s.user?.isOnboarded ?? false);

  React.useEffect(() => {
    if (!isAuthenticated) {
      // callbackUrl: 로그인 후 돌아올 경로 (보안상 인코딩)
      const callback = encodeURIComponent(pathname ?? "/dashboard");
      router.replace(`/login?callbackUrl=${callback}`);
      return;
    }
    if (!isOnboarded) {
      router.replace("/onboarding");
      return;
    }
    setReady(true);
  }, [isAuthenticated, isOnboarded, pathname, router]);

  if (!ready) return <AuthLoadingScreen />;
  return <>{children}</>;
}

// ── PublicGuard (인증 영역 진입 차단) ─────────────────────────────────
/**
 * (auth)/* 경로에 사용 (/login, /onboarding).
 *
 * 규칙:
 *  - 로그인 + 온보딩 완료 → /dashboard 로 리다이렉트
 *  - 로그인 + 온보딩 미완료 → /onboarding 은 허용, /login 은 /onboarding 으로 유도
 *  - 비로그인 → 현재 경로 그대로 표시
 */
export function PublicGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = React.useState(false);

  const isAuthenticated = useAuthStore((s) => Boolean(s.accessToken));
  const isOnboarded = useAuthStore((s) => s.user?.isOnboarded ?? false);

  React.useEffect(() => {
    if (isAuthenticated && isOnboarded) {
      router.replace("/dashboard");
      return;
    }
    if (isAuthenticated && !isOnboarded && pathname !== "/onboarding") {
      router.replace("/onboarding");
      return;
    }
    setReady(true);
  }, [isAuthenticated, isOnboarded, pathname, router]);

  if (!ready) return <AuthLoadingScreen />;
  return <>{children}</>;
}
