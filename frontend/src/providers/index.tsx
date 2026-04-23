"use client";

/**
 * 최상위 Providers 컴포지션.
 *
 * 래핑 순서 (바깥 → 안쪽):
 *  1. QueryProvider  — 서버 상태(React Query) 캐시
 *  2. ToastProvider  — 전역 플로팅 알림 (Portal 기반)
 *
 * 인증 상태는 Zustand 스토어(auth-store)를 직접 사용하므로
 * 별도 Context Provider 불필요.
 */

import type { ReactNode } from "react";
import { useEffect } from "react";
import { QueryProvider } from "./QueryProvider";
import { ToastProvider } from "./ToastProvider";
import { useAuthStore } from "@/stores/auth-store";

function HydrationBridge() {
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const setHasHydrated = useAuthStore((state) => state.setHasHydrated);

  useEffect(() => {
    if (!hasHydrated) {
      setHasHydrated(true);
    }
  }, [hasHydrated, setHasHydrated]);

  return null;
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <ToastProvider>
        <HydrationBridge />
        {children}
      </ToastProvider>
    </QueryProvider>
  );
}

export { QueryProvider, ToastProvider };
