/**
 * Badge — 상태·태그·카운트 표시용 배지.
 *
 * variants
 *  - default:    중립 회색 태그
 *  - primary:    브랜드 블루 태그
 *  - success:    신호등 GREEN — "신청 가능" 등
 *  - warning:    신호등 YELLOW — "조건 부족"
 *  - danger:     신호등 RED — "신청 불가"
 *  - accent:     앰버 — "마감임박", "NEW"
 *  - outline:    테두리만
 *
 * 신호등 매핑 헬퍼
 *  mapMatchLevelToBadgeVariant(level) → variant
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import type { MatchLevel } from "@/types";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "bg-surface-subtle text-ink-secondary",
        primary: "bg-primary-50 text-primary-700",
        success: "bg-success-50 text-success-600",
        warning: "bg-warning-50 text-warning-600",
        danger: "bg-danger-50 text-danger-600",
        accent: "bg-accent-50 text-accent-600",
        outline: "border border-surface-border text-ink-secondary",
      },
      size: {
        sm: "px-1.5 py-0 text-[11px]",
        md: "px-2 py-0.5 text-xs",
        lg: "px-2.5 py-1 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(badgeVariants({ variant, size }), className)}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge";

/** 매칭 신호등(GREEN/YELLOW/RED) → Badge variant 매핑 */
export function mapMatchLevelToBadgeVariant(
  level: MatchLevel
): NonNullable<VariantProps<typeof badgeVariants>["variant"]> {
  switch (level) {
    case "GREEN":
      return "success";
    case "YELLOW":
      return "warning";
    case "RED":
      return "danger";
    default:
      return "default";
  }
}

export { badgeVariants };
