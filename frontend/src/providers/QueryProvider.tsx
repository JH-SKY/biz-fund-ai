"use client";

/**
 * TanStack Query QueryClientProvider.
 *
 * Next.js App Router 권장 패턴:
 *  - `useState` 로 QueryClient 를 컴포넌트 인스턴스 내부에 고정하여
 *    SSR → CSR 전환 시 클라이언트 간 상태 공유를 방지한다.
 *  - staleTime = 1분: 과도한 refetch 억제 (정책 데이터는 자주 변하지 않음)
 *  - retry = 1:     네트워크 일시 오류만 한 번 재시도
 *  - refetchOnWindowFocus = false: UX 상 깜빡임 방지 (사장님 친화 UI 원칙)
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState, type ReactNode } from "react";

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1분
            gcTime: 5 * 60 * 1000, // 5분
            retry: 1,
            refetchOnWindowFocus: false,
          },
          mutations: {
            retry: 0,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-right" />
      )}
    </QueryClientProvider>
  );
}
