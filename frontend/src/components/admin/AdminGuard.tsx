"use client";

/**
 * AdminGuard — /admin/* 경로 보호.
 *
 * 규칙:
 *  - adminToken 없음 → /admin/login 으로 리다이렉트 (login 페이지 자체는 예외)
 *  - 정상 → children 렌더링
 *
 * 일반 유저용 AppGuard 와 완전히 분리되어 admin-auth-store 만 참조.
 */

import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import { ShieldCheck } from "lucide-react";

import { useAdminAuthStore } from "@/stores/admin-auth-store";

function isExpired(expiresAt?: string | null) {
  if (!expiresAt) return false;
  const expires = new Date(expiresAt).getTime();
  return Number.isFinite(expires) && expires <= Date.now();
}

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
  const expiresAt = useAdminAuthStore((s) => s.admin?.expiresAt ?? null);
  const hasHydrated = useAdminAuthStore((s) => s.hasHydrated);
  const logoutAdmin = useAdminAuthStore((s) => s.logoutAdmin);
  const isAdminExpired = isExpired(expiresAt);

  React.useEffect(() => {
    if (!hasHydrated) return;
    if (isAdminExpired) {
      logoutAdmin();
      router.replace("/admin/login");
      return;
    }
    if (pathname !== "/admin/login" && !isAdminAuthenticated) {
      router.replace("/admin/login");
    }
  }, [hasHydrated, isAdminAuthenticated, isAdminExpired, logoutAdmin, pathname, router]);

  if (!hasHydrated) return <AdminLoadingScreen />;
  if (pathname !== "/admin/login" && (!isAdminAuthenticated || isAdminExpired)) {
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
  const expiresAt = useAdminAuthStore((s) => s.admin?.expiresAt ?? null);
  const hasHydrated = useAdminAuthStore((s) => s.hasHydrated);
  const logoutAdmin = useAdminAuthStore((s) => s.logoutAdmin);
  const isAdminExpired = isExpired(expiresAt);

  React.useEffect(() => {
    if (!hasHydrated) return;
    if (isAdminExpired) {
      logoutAdmin();
      return;
    }
    if (isAdminAuthenticated) {
      router.replace("/admin/dashboard");
    }
  }, [hasHydrated, isAdminAuthenticated, isAdminExpired, logoutAdmin, router]);

  if (!hasHydrated) return <AdminLoadingScreen />;
  if (isAdminAuthenticated && !isAdminExpired) return <AdminLoadingScreen />;
  return <>{children}</>;
}
