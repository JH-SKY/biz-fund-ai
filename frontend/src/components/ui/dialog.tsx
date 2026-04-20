"use client";

/**
 * 경량 Dialog(Modal) — 외부 패키지 없이 구현.
 *
 * 접근성
 *  - role="dialog" + aria-modal + aria-labelledby
 *  - Esc 키 / 오버레이 클릭 / 닫기 버튼으로 닫기
 *  - body scroll lock
 *  - open 시 초기 포커스는 내부 첫 포커스 가능 요소로 이동(간이 구현)
 */

import * as React from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  /** 오버레이 클릭으로 닫히지 않게 하려면 false */
  dismissOnOverlayClick?: boolean;
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  className,
  dismissOnOverlayClick = true,
}: DialogProps) {
  const [mounted, setMounted] = React.useState(false);
  const panelRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => setMounted(true), []);

  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";

    // 초기 포커스: 내부 첫 포커스 가능 요소
    const el = panelRef.current?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    el?.focus();

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onOpenChange]);

  if (!mounted || !open) return null;

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "dialog-title" : undefined}
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
    >
      <div
        aria-hidden
        className="absolute inset-0 bg-ink/50 animate-fade-in"
        onClick={() => dismissOnOverlayClick && onOpenChange(false)}
      />
      <div
        ref={panelRef}
        className={cn(
          "relative z-10 w-full sm:w-[min(32rem,calc(100vw-2rem))]",
          "bg-surface rounded-t-2xl sm:rounded-2xl shadow-elevated",
          "animate-fade-in",
          className
        )}
      >
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          aria-label="닫기"
          className="absolute right-3 top-3 inline-flex h-9 w-9 items-center justify-center rounded-lg text-ink-tertiary hover:bg-surface-muted"
        >
          <X className="h-5 w-5" />
        </button>

        {(title || description) && (
          <div className="px-6 pt-6 pb-2">
            {title && (
              <h2
                id="dialog-title"
                className="text-lg font-bold text-ink pr-8"
              >
                {title}
              </h2>
            )}
            {description && (
              <p className="mt-1 text-sm text-ink-secondary">{description}</p>
            )}
          </div>
        )}

        <div className="px-6 py-4">{children}</div>

        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-surface-border px-6 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}
