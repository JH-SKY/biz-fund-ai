"use client";

/**
 * Tabs — 상태 관리를 외부에서 제어하는 경량 탭 UI.
 * (라이브러리 의존성 없이 구현)
 *
 * 접근성
 *  - role="tablist" / role="tab" / aria-selected / aria-controls
 *  - 좌우 방향키 이동은 기본 네이티브 포커스 이동에 맡김(추후 필요 시 확장)
 */

import * as React from "react";
import { cn } from "@/lib/utils";

export interface TabItem {
  value: string;
  label: React.ReactNode;
  count?: number;
}

interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  items: TabItem[];
  className?: string;
  size?: "sm" | "md";
  variant?: "pill" | "underline";
}

export function Tabs({
  value,
  onValueChange,
  items,
  className,
  size = "md",
  variant = "pill",
}: TabsProps) {
  return (
    <div
      role="tablist"
      className={cn(
        "flex w-full items-center overflow-x-auto",
        variant === "pill" ? "gap-2" : "gap-0 border-b border-surface-border",
        className
      )}
    >
      {items.map((item) => {
        const selected = item.value === value;
        return (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onValueChange(item.value)}
            className={cn(
              "inline-flex items-center gap-1.5 whitespace-nowrap font-semibold transition-colors",
              size === "sm" ? "text-xs" : "text-sm",
              variant === "pill"
                ? [
                    "rounded-full px-3.5 py-1.5 border",
                    selected
                      ? "bg-primary-600 border-primary-600 text-white"
                      : "bg-surface border-surface-border text-ink-secondary hover:border-primary-200 hover:text-ink",
                  ]
                : [
                    "px-4 py-3 border-b-2 -mb-px",
                    selected
                      ? "border-primary-600 text-primary-700"
                      : "border-transparent text-ink-tertiary hover:text-ink-secondary",
                  ]
            )}
          >
            <span>{item.label}</span>
            {typeof item.count === "number" && (
              <span
                className={cn(
                  "rounded-full px-1.5 text-[11px] numeric",
                  selected && variant === "pill"
                    ? "bg-white/20 text-white"
                    : "bg-surface-subtle text-ink-secondary"
                )}
              >
                {item.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
