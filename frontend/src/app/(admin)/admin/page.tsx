"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { useAdminAuthStore } from "@/stores/admin-auth-store";

export default function AdminRootPage() {
  const router = useRouter();
  const hasHydrated = useAdminAuthStore((s) => s.hasHydrated);
  const isAdminAuthenticated = useAdminAuthStore((s) => Boolean(s.adminToken));
  const setHasHydrated = useAdminAuthStore((s) => s.setHasHydrated);

  React.useEffect(() => {
    if (!hasHydrated) {
      setHasHydrated(true);
      return;
    }

    router.replace(isAdminAuthenticated ? "/admin/dashboard" : "/admin/login");
  }, [hasHydrated, isAdminAuthenticated, router, setHasHydrated]);

  return null;
}
