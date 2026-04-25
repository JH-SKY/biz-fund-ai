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

  // onOpenChange 를 ref 로 보관한다.
  // useEffect 의존성에서 제외해야 타이핑 시마다 effect 가 재실행되어
  // X 닫기 버튼으로 포커스가 빼앗기는 현상을 막을 수 있다.
  const onOpenChangeRef = React.useRef(onOpenChange);
  React.useEffect(() => {
    onOpenChangeRef.current = onOpenChange;
  });

  React.useEffect(() => setMounted(true), []);

  React.useEffect(() => {
    if (!open) return;

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChangeRef.current(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";

    // 초기 포커스: 닫기 버튼을 건너뛰고 첫 번째 입력 요소로 이동.
    // X 버튼에 초기 포커스가 가면 타이핑 전 탭 이동이 필요하고,
    // 이전 버그 재발 시 입력 도중 포커스가 닫기 버튼으로 돌아갈 수 있다.
    const firstInput = panelRef.current?.querySelector<HTMLElement>(
      'input:not([type="hidden"]), select, textarea'
    );
    const firstFocusable = panelRef.current?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    (firstInput ?? firstFocusable)?.focus();

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]); // onOpenChange 는 ref 로 관리하므로 의존성 제외

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
        onClick={() => dismissOnOverlayClick && onOpenChangeRef.current(false)}
      />
      <div
        ref={panelRef}
        className={cn(
          "relative z-10 flex w-full max-h-[calc(100dvh-1rem)] flex-col sm:w-[min(32rem,calc(100vw-2rem))]",
          "bg-surface rounded-t-2xl sm:rounded-2xl shadow-elevated",
          "animate-fade-in",
          className
        )}
      >
        <button
          type="button"
          onClick={() => onOpenChangeRef.current(false)}
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

        <div className="min-h-0 overflow-y-auto px-6 py-4">{children}</div>

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
