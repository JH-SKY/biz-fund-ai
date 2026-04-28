"use client";

import { useEffect, useRef } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const BIZMONG_QUICK_REPLIES = [
  "정책자금에서 자주 나오는 용어를 쉽게 설명해줘",
  "우리 사업장 상황에서 먼저 챙길 리스크가 뭘까?",
  "이 공고가 무슨 뜻인지 쉽게 풀어줘",
  "정밀진단을 왜 받아야 하는지 알려줘",
];

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
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

  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 144)}px`;
  }, [value]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !isLoading && value.trim()) {
      event.preventDefault();
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
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
          placeholder={
            isLoading
              ? "비즈몽이 답변을 정리하고 있습니다..."
              : "정책자금, 공고 해석, 사업장 고민을 편하게 물어보세요. (Shift+Enter 줄바꿈)"
          }
          aria-label="메시지 입력"
          className={cn(
            "min-h-[44px] max-h-36 flex-1 resize-none rounded-xl border border-surface-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition-colors",
            "placeholder:text-ink-tertiary focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
            "disabled:cursor-not-allowed disabled:bg-surface-muted"
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
        비즈몽은 상담과 해석을 돕는 비서입니다. 최종 신청 전에는 공식 공고를 다시 확인해 주세요.
      </p>
    </div>
  );
}
