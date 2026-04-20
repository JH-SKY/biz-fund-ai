/**
 * Select — 네이티브 select 요소에 Biz-Up 스타일을 입힌 래퍼.
 *
 * 이유: 접근성(키보드·스크린리더) 무료 + 모바일에서 OS 네이티브 휠 피커 자동 사용.
 * 복잡한 커스텀 드롭다운이 필요할 때만 별도 Combobox 를 추가한다.
 */

import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SelectOption {
  label: string;
  value: string;
}

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  placeholder?: string;
  invalid?: boolean;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    { className, options, placeholder, invalid, disabled, value, ...props },
    ref
  ) => {
    return (
      <div
        className={cn(
          "relative flex h-11 items-center rounded-lg border bg-surface",
          "focus-within:ring-2 focus-within:ring-primary-500 focus-within:ring-offset-2",
          invalid
            ? "border-danger-500 focus-within:ring-danger-500"
            : "border-surface-border focus-within:border-primary-500",
          disabled && "opacity-60 pointer-events-none bg-surface-muted",
          className
        )}
      >
        <select
          ref={ref}
          disabled={disabled}
          value={value ?? ""}
          aria-invalid={invalid || undefined}
          className={cn(
            "w-full appearance-none bg-transparent pl-3 pr-9 text-sm text-ink outline-none",
            "disabled:cursor-not-allowed",
            // 빈 문자열이면 placeholder 톤
            !value && "text-ink-tertiary"
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} className="text-ink">
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 h-4 w-4 text-ink-tertiary" />
      </div>
    );
  }
);
Select.displayName = "Select";
