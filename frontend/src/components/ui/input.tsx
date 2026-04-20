/**
 * Input — 텍스트 입력 필드.
 *
 * - 에러 상태(aria-invalid) 시 danger 색상 테두리로 자동 전환
 * - leftIcon / rightIcon 슬롯 지원
 */

import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  invalid?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, leftIcon, rightIcon, invalid, disabled, ...props }, ref) => {
    return (
      <div
        className={cn(
          "flex h-11 items-center gap-2 rounded-lg border bg-surface px-3",
          "transition-colors focus-within:ring-2 focus-within:ring-primary-500 focus-within:ring-offset-2",
          invalid
            ? "border-danger-500 focus-within:ring-danger-500"
            : "border-surface-border focus-within:border-primary-500",
          disabled && "opacity-60 pointer-events-none bg-surface-muted",
          className
        )}
      >
        {leftIcon && <span className="text-ink-tertiary">{leftIcon}</span>}
        <input
          ref={ref}
          aria-invalid={invalid || undefined}
          disabled={disabled}
          className="flex-1 bg-transparent outline-none text-sm text-ink placeholder:text-ink-tertiary disabled:cursor-not-allowed"
          {...props}
        />
        {rightIcon && <span className="text-ink-tertiary">{rightIcon}</span>}
      </div>
    );
  }
);
Input.displayName = "Input";
