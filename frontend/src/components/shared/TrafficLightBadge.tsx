/**
 * 신호등 배지 (.cursorrules §3.3)
 *
 *  🟢 GREEN  — "신청 가능"
 *  🟡 YELLOW — "조건 부족"
 *  🔴 RED    — "신청 불가"
 *
 * 대소문자 구분 없이 backend Enum("GREEN"|"YELLOW"|"RED") 도 수용하도록
 * 내부에서 toLowerCase 처리한다.
 */

import { cn } from "@/lib/utils";

type Status = "green" | "yellow" | "red" | "GREEN" | "YELLOW" | "RED";

interface Props {
  status: Status;
  label?: string;
  className?: string;
  showDot?: boolean;
}

const STATUS_META: Record<
  "green" | "yellow" | "red",
  { bg: string; text: string; dot: string; defaultLabel: string }
> = {
  green: {
    bg: "bg-success-50",
    text: "text-success-600",
    dot: "bg-traffic-green",
    defaultLabel: "신청 가능",
  },
  yellow: {
    bg: "bg-warning-50",
    text: "text-warning-600",
    dot: "bg-traffic-yellow",
    defaultLabel: "조건 부족",
  },
  red: {
    bg: "bg-danger-50",
    text: "text-danger-600",
    dot: "bg-traffic-red",
    defaultLabel: "신청 불가",
  },
};

export function TrafficLightBadge({
  status,
  label,
  className,
  showDot = true,
}: Props) {
  const key = status.toLowerCase() as "green" | "yellow" | "red";
  const meta = STATUS_META[key] ?? STATUS_META.green;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-semibold",
        meta.bg,
        meta.text,
        className
      )}
    >
      {showDot && (
        <span
          aria-hidden
          className={cn("h-2 w-2 rounded-full", meta.dot)}
        />
      )}
      {label ?? meta.defaultLabel}
    </span>
  );
}
