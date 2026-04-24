"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { Rocket } from "lucide-react";

import { useAuthStore } from "@/stores/auth-store";
import { useBusinessStore } from "@/stores/business-store";

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

export function AppGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const isAuthenticated = useAuthStore((state) => Boolean(state.accessToken));
  const isOnboarded = useAuthStore((state) => state.user?.isOnboarded ?? false);
  const hasActiveBusiness = useBusinessStore((state) => Boolean(state.activeBizId));
  const canAccessApp = isAuthenticated && (isOnboarded || hasActiveBusiness);

  React.useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    if (!isAuthenticated) {
      const callback = encodeURIComponent(pathname ?? "/dashboard");
      router.replace(`/login?callbackUrl=${callback}`);
      return;
    }

    if (!canAccessApp) {
      router.replace("/onboarding");
      return;
    }
  }, [canAccessApp, hasHydrated, isAuthenticated, pathname, router]);

  if (!hasHydrated) {
    return <AuthLoadingScreen />;
  }

  if (!canAccessApp) {
    return <AuthLoadingScreen />;
  }

  return <>{children}</>;
}

export function PublicGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const isAuthenticated = useAuthStore((state) => Boolean(state.accessToken));
  const isOnboarded = useAuthStore((state) => state.user?.isOnboarded ?? false);
  const hasActiveBusiness = useBusinessStore((state) => Boolean(state.activeBizId));
  const canAccessApp = isAuthenticated && (isOnboarded || hasActiveBusiness);

  React.useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    if (canAccessApp) {
      router.replace("/dashboard");
      return;
    }

    if (isAuthenticated && !isOnboarded && pathname !== "/onboarding") {
      router.replace("/onboarding");
    }
  }, [canAccessApp, hasHydrated, isAuthenticated, isOnboarded, pathname, router]);

  if (!hasHydrated) {
    return <AuthLoadingScreen />;
  }

  if (canAccessApp) {
    return <AuthLoadingScreen />;
  }

  if (isAuthenticated && !isOnboarded && pathname !== "/onboarding") {
    return <AuthLoadingScreen />;
  }

  return <>{children}</>;
}
