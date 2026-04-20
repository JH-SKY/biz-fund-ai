"use client";

/**
 * ToastProvider — 전역 토스트 상태 관리 + Portal 렌더링.
 *
 * 위치 전략
 *  - 데스크탑(lg+): 우하단 고정 (right-6 bottom-6)
 *  - 모바일: 하단 탭바(bottom-tab = 4rem) 위에 중앙 정렬
 *    → bottom: calc(theme(spacing.bottom-tab) + 0.75rem)
 *
 * 스택: 최신 토스트가 제일 위 (아래가 먼저 표시됨, flex-col-reverse)
 * 최대 동시 노출: 4개 (오래된 것 자동 제거)
 */

import * as React from "react";
import { createPortal } from "react-dom";
import { ToastItem, type ToastData, type ToastVariant } from "@/components/ui/toast";

// ── 타입 ──────────────────────────────────────────────────────────────
interface ToastOptions {
  message?: string;
  duration?: number;
}

interface ToastContextValue {
  /** 토스트 추가 — shorthand helpers 아래 참고 */
  push: (variant: ToastVariant, title: string, opts?: ToastOptions) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

let _idCounter = 0;
const MAX_TOASTS = 4;

// ── Provider ───────────────────────────────────────────────────────────
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastData[]>([]);
  const [mounted, setMounted] = React.useState(false);

  // Portal 은 클라이언트에서만 가능
  React.useEffect(() => setMounted(true), []);

  const push = React.useCallback(
    (variant: ToastVariant, title: string, opts?: ToastOptions) => {
      const id = `toast-${++_idCounter}`;
      setToasts((prev) => {
        const next = [
          ...prev,
          { id, variant, title, message: opts?.message, duration: opts?.duration },
        ];
        // 최대 초과 시 오래된 것부터 제거
        return next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next;
      });
    },
    []
  );

  const remove = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      {mounted &&
        createPortal(
          <div
            aria-label="알림 목록"
            className={[
              // 공통
              "pointer-events-none fixed z-[9999] flex w-full flex-col gap-2 px-4",
              // 모바일: 하단 탭바 위 중앙 정렬
              "bottom-[calc(theme(spacing.bottom-tab)+0.75rem)] left-0 items-center",
              // 데스크탑: 우하단 정렬
              "lg:bottom-6 lg:left-auto lg:right-6 lg:w-auto lg:items-end lg:px-0",
            ].join(" ")}
          >
            {[...toasts].reverse().map((t) => (
              <div key={t.id} className="pointer-events-auto w-full lg:w-auto">
                <ToastItem toast={t} onClose={remove} />
              </div>
            ))}
          </div>,
          document.body
        )}
    </ToastContext.Provider>
  );
}

// ── 훅 ────────────────────────────────────────────────────────────────
export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within <ToastProvider>");
  }

  return {
    /**
     * 직접 호출:
     *   toast.success('저장됐어요')
     *   toast.error('오류', { message: '네트워크 오류' })
     */
    success: (title: string, opts?: ToastOptions) =>
      ctx.push("success", title, opts),
    error: (title: string, opts?: ToastOptions) =>
      ctx.push("error", title, opts),
    warning: (title: string, opts?: ToastOptions) =>
      ctx.push("warning", title, opts),
    info: (title: string, opts?: ToastOptions) =>
      ctx.push("info", title, opts),
  };
}
