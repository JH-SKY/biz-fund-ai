"use client";

/**
 * IndustryCombobox — 업종 검색형 자동완성 입력 (네이티브 select 대체).
 *
 * 설계
 *  - 검색어 입력 시 INDUSTRIES 에서 이름/동의어 키워드로 필터링
 *  - ↑↓ 방향키, Enter, Esc 키보드 내비게이션
 *  - 결과가 없으면 '기타 / 직접 입력' 힌트 노출 (기획서 §4 예외 대응)
 *
 * 접근성: role="combobox" + aria-expanded + aria-activedescendant
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Search } from "lucide-react";

import { cn } from "@/lib/utils";
import { INDUSTRIES, searchIndustries, type IndustryItem } from "@/constants/industries";

interface IndustryComboboxProps {
  value: string; // 선택된 code
  onChange: (code: string) => void;
  invalid?: boolean;
  placeholder?: string;
  id?: string;
}

export function IndustryCombobox({
  value,
  onChange,
  invalid,
  placeholder = "예: 음식점, 제조, IT...",
  id,
}: IndustryComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const selected = INDUSTRIES.find((i) => i.code === value) ?? null;
  const results = useMemo<IndustryItem[]>(() => searchIndustries(query), [query]);

  // 외부 클릭 시 닫기
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  useEffect(() => {
    setHighlight(0);
  }, [query]);

  const select = (item: IndustryItem) => {
    onChange(item.code);
    setQuery("");
    setOpen(false);
    inputRef.current?.blur();
  };

  const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setHighlight((h) => Math.min(h + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const picked = results[highlight];
      if (picked) select(picked);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <div
        className={cn(
          "flex h-11 items-center gap-2 rounded-lg border bg-surface px-3",
          "transition-colors focus-within:ring-2 focus-within:ring-primary-500 focus-within:ring-offset-2",
          invalid
            ? "border-danger-500 focus-within:ring-danger-500"
            : "border-surface-border focus-within:border-primary-500"
        )}
      >
        <Search className="h-4 w-4 text-ink-tertiary" />
        <input
          id={id}
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          aria-controls="industry-listbox"
          aria-activedescendant={
            open && results[highlight] ? `industry-opt-${results[highlight].code}` : undefined
          }
          value={open ? query : selected?.name ?? ""}
          placeholder={placeholder}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onKeyDown={handleKey}
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-ink-tertiary"
        />
        <button
          type="button"
          aria-label={open ? "업종 목록 닫기" : "업종 목록 열기"}
          onClick={() => {
            setOpen((v) => !v);
            inputRef.current?.focus();
          }}
          className="text-ink-tertiary hover:text-ink-secondary"
        >
          <ChevronDown
            className={cn("h-4 w-4 transition-transform", open && "rotate-180")}
          />
        </button>
      </div>

      {open && (
        <ul
          id="industry-listbox"
          role="listbox"
          className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-surface-border bg-surface py-1 shadow-elevated animate-fade-in"
        >
          {results.length === 0 ? (
            <li className="px-3 py-2 text-sm text-ink-tertiary">
              검색 결과가 없어요. &apos;기타&apos; 또는 직접 입력을 사용해보세요.
            </li>
          ) : (
            results.map((item, idx) => (
              <li
                id={`industry-opt-${item.code}`}
                key={item.code}
                role="option"
                aria-selected={value === item.code}
                onMouseDown={(e) => {
                  e.preventDefault();
                  select(item);
                }}
                onMouseEnter={() => setHighlight(idx)}
                className={cn(
                  "cursor-pointer px-3 py-2 text-sm",
                  idx === highlight
                    ? "bg-primary-50 text-primary-800"
                    : "text-ink hover:bg-surface-muted"
                )}
              >
                <span className="font-medium">{item.name}</span>
                <span className="ml-2 text-xs text-ink-tertiary">
                  {item.keywords.slice(0, 3).join(", ")}
                </span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
