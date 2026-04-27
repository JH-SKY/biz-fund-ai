"use client";

import { useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export const POST_DIAGNOSIS_QUICK_REPLIES = [
  "시뮬레이션해보기",
  "매칭 정책 목록 보기",
  "서류 준비 도와줘",
  "다른 조건으로 재진단",
];

interface ChatInputProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  isLoading,
  disabled,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // textarea 높이 자동 조절 (최대 6줄)
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 144) + "px";
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !isLoading && value.trim()) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="border-t border-surface-border bg-surface px-4 py-3 safe-pb">
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
          placeholder={
            isLoading
              ? "비즈몽이 분석 중입니다..."
              : "비즈몽에게 무엇이든 물어보세요 (Shift+Enter: 줄바꿈)"
          }
          aria-label="메시지 입력"
          className={cn(
            "flex-1 resize-none rounded-xl border border-surface-border bg-surface",
            "px-4 py-2.5 text-sm text-ink outline-none",
            "placeholder:text-ink-tertiary",
            "focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
            "disabled:cursor-not-allowed disabled:bg-surface-muted",
            "max-h-36 min-h-[44px] transition-colors"
          )}
        />
        <Button
          variant="primary"
          size="icon"
          onClick={onSend}
          disabled={disabled || isLoading || !value.trim()}
          aria-label="메시지 전송"
          loading={isLoading}
          className="shrink-0"
        >
          {!isLoading && <Send />}
        </Button>
      </div>

      <p className="mt-1.5 text-center text-[11px] text-ink-tertiary">
        AI 응답은 참고용이며, 실제 신청 전 공식 공고를 반드시 확인하세요.
      </p>
    </div>
  );
}
