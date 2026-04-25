"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck } from "lucide-react";

import { useAdminAuthStore } from "@/stores/admin-auth-store";

function isExpired(expiresAt?: string | null) {
  if (!expiresAt) return false;
  const expires = new Date(expiresAt).getTime();
  return Number.isFinite(expires) && expires <= Date.now();
}

export default function AdminRootPage() {
  const router = useRouter();
  const hasHydrated = useAdminAuthStore((s) => s.hasHydrated);
  const isAdminAuthenticated = useAdminAuthStore((s) => Boolean(s.adminToken));
  const expiresAt = useAdminAuthStore((s) => s.admin?.expiresAt ?? null);
  const logoutAdmin = useAdminAuthStore((s) => s.logoutAdmin);
  const isAdminExpired = isExpired(expiresAt);

  React.useEffect(() => {
    if (!hasHydrated) return;
    if (isAdminExpired) {
      logoutAdmin();
      router.replace("/admin/login");
      return;
    }

    router.replace(isAdminAuthenticated ? "/admin/dashboard" : "/admin/login");
  }, [hasHydrated, isAdminAuthenticated, isAdminExpired, logoutAdmin, router]);

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
        <span>관리자 페이지로 이동하는 중...</span>
      </div>
    </div>
  );
}
