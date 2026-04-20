import * as React from "react";
import { cn } from "@/lib/utils";

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
}

export const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
  ({ className, children, required, ...props }, ref) => (
    <label
      ref={ref}
      className={cn("text-sm font-semibold text-ink", className)}
      {...props}
    >
      {children}
      {required && <span className="ml-0.5 text-danger-500">*</span>}
    </label>
  )
);
Label.displayName = "Label";

export interface FieldHintProps extends React.HTMLAttributes<HTMLParagraphElement> {
  tone?: "default" | "error" | "success";
}

export const FieldHint = React.forwardRef<HTMLParagraphElement, FieldHintProps>(
  ({ className, tone = "default", ...props }, ref) => (
    <p
      ref={ref}
      className={cn(
        "text-xs mt-1.5",
        tone === "error" && "text-danger-600",
        tone === "success" && "text-success-600",
        tone === "default" && "text-ink-tertiary",
        className
      )}
      {...props}
    />
  )
);
FieldHint.displayName = "FieldHint";
