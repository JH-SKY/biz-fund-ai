"use client";

/**
 * Button — shadcn/ui 레시피에 Biz-Up 톤을 입힌 범용 버튼.
 *
 * variants
 *  - primary:   메인 CTA (신청하기, 진단 시작 등) — 브랜드 블루
 *  - secondary: 보조 액션 — 중립 톤 아웃라인
 *  - ghost:     배경 없는 텍스트 액션
 *  - outline:   테두리만 있는 보조 액션
 *  - destructive: 삭제·취소
 *  - accent:    앰버 — 마감임박·핫딜 강조
 *  - link:      텍스트 링크 스타일
 * sizes: sm / md / lg / icon
 *
 * asChild(slot 패턴)
 *  - Radix Slot 에 외부 의존 없이 React.cloneElement 로 대체 구현.
 *  - 자식 요소(Link, a, button 등) 에 variant 클래스를 병합하여 내려준다.
 *  - loading/leftIcon 같은 버튼 전용 꾸미기는 asChild 일 때 자식의 children 을 감싸 처리한다.
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap",
    "rounded-lg font-semibold transition-colors",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2",
    "disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg]:shrink-0",
  ].join(" "),
  {
    variants: {
      variant: {
        primary:
          "bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 shadow-sm",
        secondary:
          "bg-surface border border-surface-border text-ink hover:bg-surface-muted",
        outline:
          "border border-primary-600 text-primary-700 hover:bg-primary-50",
        ghost: "text-ink hover:bg-surface-muted",
        destructive:
          "bg-danger-600 text-white hover:bg-danger-700 shadow-sm",
        accent:
          "bg-accent-500 text-ink hover:bg-accent-600 hover:text-white shadow-sm",
        link: "text-primary-600 underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3 text-sm [&_svg]:size-4",
        md: "h-10 px-4 text-sm [&_svg]:size-4",
        lg: "h-12 px-6 text-base [&_svg]:size-5",
        icon: "h-10 w-10 [&_svg]:size-5",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      loading,
      disabled,
      asChild,
      children,
      ...props
    },
    ref
  ) => {
    const merged = cn(buttonVariants({ variant, size }), className);

    const innerContent = (
      <>
        {loading && (
          <span
            aria-hidden
            className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
        )}
        {children}
      </>
    );

    // asChild: 첫 번째 자식 엘리먼트(예: <Link>, <a>) 에 스타일을 병합해 반환
    if (asChild && React.isValidElement(children)) {
      const child = children as React.ReactElement<{ className?: string }>;
      return React.cloneElement(child, {
        className: cn(merged, child.props.className),
      });
    }

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={merged}
        {...props}
      >
        {innerContent}
      </button>
    );
  }
);
Button.displayName = "Button";

export { buttonVariants };
