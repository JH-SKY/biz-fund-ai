"use client";

/**
 * AdminGuard — /admin/* 경로 보호.
 *
 * 규칙:
 *  - adminToken 없음 → /admin/login 으로 리다이렉트 (login 페이지 자체는 예외)
 *  - 정상 → children 렌더링
 *
 * 일반 유저용 AppGuard 와 완전히 분리되어 admin-auth-store 만 참조.
 *
 * 안전장치:
 *  - onRehydrateStorage 가 state=undefined 로 호출되거나 스토리지 예외가 발생해
 *    hasHydrated 가 영원히 false 로 남는 경우를 대비해 HYDRATION_TIMEOUT_MS 후
 *    강제로 hasHydrated=true 로 전환한다.
 */

import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import { ShieldCheck } from "lucide-react";

import { useAdminAuthStore } from "@/stores/admin-auth-store";

/** hydration 이 이 시간 안에 완료되지 않으면 강제로 완료 처리 (ms) */
const HYDRATION_TIMEOUT_MS = 3_000;

function AdminLoadingScreen() {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-ink">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-600 text-white shadow-elevated">
        <ShieldCheck className="h-7 w-7" />
      </div>
      <div className="flex items-center gap-2 text-sm text-white/70">
        <span
          aria-hidden
          className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white"
        />
        <span>관리자 세션을 확인하는 중...</span>
      </div>
    </div>
  );
}

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const isAdminAuthenticated = useAdminAuthStore((s) =>
    Boolean(s.adminToken)
  );
  const hasHydrated = useAdminAuthStore((s) => s.hasHydrated);
  const setHasHydrated = useAdminAuthStore((s) => s.setHasHydrated);

  // 안전장치: persist hydration 이 차단된 경우 무한 로딩 방지
  React.useEffect(() => {
    if (hasHydrated) return;
    const timer = setTimeout(() => {
      if (!useAdminAuthStore.getState().hasHydrated) {
        setHasHydrated(true);
      }
    }, HYDRATION_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [hasHydrated, setHasHydrated]);

  React.useEffect(() => {
    if (!hasHydrated) return;
    if (pathname !== "/admin/login" && !isAdminAuthenticated) {
      router.replace("/admin/login");
    }
  }, [hasHydrated, isAdminAuthenticated, pathname, router]);

  if (!hasHydrated) return <AdminLoadingScreen />;
  if (pathname !== "/admin/login" && !isAdminAuthenticated) {
    return <AdminLoadingScreen />;
  }
  return <>{children}</>;
}

/** /admin/login 에서 사용 — 이미 로그인된 경우 대시보드로 이동 */
export function AdminPublicGuard({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();

  const isAdminAuthenticated = useAdminAuthStore((s) =>
    Boolean(s.adminToken)
  );
  const hasHydrated = useAdminAuthStore((s) => s.hasHydrated);
  const setHasHydrated = useAdminAuthStore((s) => s.setHasHydrated);

  // 안전장치: persist hydration 이 차단된 경우 무한 로딩 방지
  React.useEffect(() => {
    if (hasHydrated) return;
    const timer = setTimeout(() => {
      if (!useAdminAuthStore.getState().hasHydrated) {
        setHasHydrated(true);
      }
    }, HYDRATION_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [hasHydrated, setHasHydrated]);

  React.useEffect(() => {
    if (!hasHydrated) return;
    if (isAdminAuthenticated) {
      router.replace("/admin/dashboard");
    }
  }, [hasHydrated, isAdminAuthenticated, router]);

  if (!hasHydrated) return <AdminLoadingScreen />;
  if (isAdminAuthenticated) return <AdminLoadingScreen />;
  return <>{children}</>;
}
