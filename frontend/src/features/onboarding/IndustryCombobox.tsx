"use client";

/**
 * KSIC 세세분류 검색 콤보 — 선택 시 `code`·`name`을 동시에 상위로 전달합니다.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Search } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  KSIC_DETAILS,
  searchKsicDetails,
  type KsicDetailItem,
} from "@/constants/ksic-detail";

interface IndustryComboboxProps {
  /** 선택된 5자리 KSIC 코드 */
  value: string;
  /** 선택 항목의 표시명 (code + name) */
  onChange: (next: { code: string; name: string }) => void;
  invalid?: boolean;
  placeholder?: string;
  id?: string;
}

export function IndustryCombobox({
  value,
  onChange,
  invalid,
  placeholder = "예: 한식, 제조, IT...",
  id,
}: IndustryComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const results = useMemo<KsicDetailItem[]>(
    () => searchKsicDetails(query),
    [query]
  );

  const labelForValue = useMemo(
    () => (value ? (KSIC_DETAILS.find((i) => i.code === value)?.name ?? "") : ""),
    [value]
  );

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

  const select = (item: KsicDetailItem) => {
    onChange({ code: item.code, name: item.name });
    setQuery("");
    setOpen(false);
    inputRef.current?.blur();
  };

  const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      if (results.length)
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
            open && results[highlight]
              ? `industry-opt-${results[highlight].code}`
              : undefined
          }
          value={open ? query : labelForValue}
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
              검색 결과가 없어요. 다른 키워드로 검색해 주세요.
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
                <span className="text-xs text-ink-tertiary">{item.code}</span>
                <span className="ml-2 font-medium">{item.name}</span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
