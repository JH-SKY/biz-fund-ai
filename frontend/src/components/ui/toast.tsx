"use client";

/**
 * Toast — 전역 플로팅 알림 아이템.
 *
 * 디자인 원칙 (Biz-Up 신뢰감 우선)
 *  - 좌측 컬러 라인으로 타입을 즉각 인지  
 *  - 아이콘 + 제목 + 선택적 메시지
 *  - 우하단(데스크톱) / 하단 탭바 위(모바일) 에 쌓임
 *  - 자동 닫힘 타이머를 하단 프로그레스바로 시각화
 *  - 닫기(×) 버튼으로 즉시 해제 가능
 */

import * as React from "react";
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from "lucide-react";
import { cn } from "@/lib/utils";

// ── 타입 정의 ──────────────────────────────────────────────────────────
export type ToastVariant = "success" | "error" | "warning" | "info";

export interface ToastData {
  id: string;
  variant: ToastVariant;
  title: string;
  message?: string;
  /** ms 단위 자동 닫힘 시간 (0 = 영구) */
  duration?: number;
}

// ── 변종별 메타 ────────────────────────────────────────────────────────
const META: Record<
  ToastVariant,
  {
    icon: React.ElementType;
    bar: string;
    border: string;
    iconBg: string;
    iconColor: string;
  }
> = {
  success: {
    icon: CheckCircle2,
    bar: "bg-success-500",
    border: "border-l-success-500",
    iconBg: "bg-success-50",
    iconColor: "text-success-600",
  },
  error: {
    icon: AlertCircle,
    bar: "bg-danger-500",
    border: "border-l-danger-500",
    iconBg: "bg-danger-50",
    iconColor: "text-danger-600",
  },
  warning: {
    icon: AlertTriangle,
    bar: "bg-accent-500",
    border: "border-l-accent-500",
    iconBg: "bg-accent-50",
    iconColor: "text-accent-700",
  },
  info: {
    icon: Info,
    bar: "bg-primary-500",
    border: "border-l-primary-500",
    iconBg: "bg-primary-50",
    iconColor: "text-primary-700",
  },
};

// ── ToastItem ──────────────────────────────────────────────────────────
interface ToastItemProps {
  toast: ToastData;
  onClose: (id: string) => void;
}

export function ToastItem({ toast, onClose }: ToastItemProps) {
  const [exiting, setExiting] = React.useState(false);
  const meta = META[toast.variant];
  const Icon = meta.icon;
  const duration = toast.duration ?? 4500;

  const handleClose = React.useCallback(() => {
    setExiting(true);
    // 아웃 애니메이션 후 실제 제거
    setTimeout(() => onClose(toast.id), 260);
  }, [toast.id, onClose]);

  // 자동 닫힘 타이머
  React.useEffect(() => {
    if (duration === 0) return;
    const t = setTimeout(handleClose, duration);
    return () => clearTimeout(t);
  }, [duration, handleClose]);

  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      className={cn(
        // 베이스
        "relative w-full max-w-sm overflow-hidden rounded-xl border border-surface-border",
        "bg-white shadow-elevated",
        // 좌측 컬러 라인
        "border-l-4",
        meta.border,
        // 애니메이션
        exiting ? "animate-toast-out" : "animate-toast-in"
      )}
    >
      <div className="flex items-start gap-3 p-4">
        {/* 아이콘 */}
        <div
          className={cn(
            "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
            meta.iconBg
          )}
        >
          <Icon className={cn("h-4 w-4", meta.iconColor)} />
        </div>

        {/* 텍스트 */}
        <div className="flex-1 min-w-0 pt-0.5">
          <p className="text-sm font-semibold text-ink leading-tight">{toast.title}</p>
          {toast.message && (
            <p className="mt-0.5 text-xs leading-relaxed text-ink-secondary">
              {toast.message}
            </p>
          )}
        </div>

        {/* 닫기 버튼 */}
        <button
          type="button"
          onClick={handleClose}
          aria-label="알림 닫기"
          className={cn(
            "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md",
            "text-ink-tertiary transition-colors hover:bg-surface-subtle hover:text-ink"
          )}
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* 자동 닫힘 프로그레스 바 */}
      {duration > 0 && (
        <div
          className={cn("h-0.5 w-full origin-left", meta.bar)}
          style={{
            animation: `shrink-width ${duration}ms linear forwards`,
          }}
        />
      )}
    </div>
  );
}
