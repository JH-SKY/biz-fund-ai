"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

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

  return null;
}
