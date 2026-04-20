"use client";

/**
 * DocumentCard — 업로드된 서류 카드.
 *
 * OCR 상태 배지 (PENDING·COMPLETED·FAILED) + 삭제 버튼.
 */

import * as React from "react";
import { FileText, Trash2, Download } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { BadgeProps } from "@/components/ui/badge";
import type { OcrStatus, DocumentListItem } from "@/types";
import { cn } from "@/lib/utils";

const OCR_BADGE: Record<
  OcrStatus,
  { label: string; variant: BadgeProps["variant"] }
> = {
  PENDING: { label: "처리중", variant: "warning" },
  COMPLETED: { label: "완료", variant: "success" },
  FAILED: { label: "실패", variant: "danger" },
};

const DOC_TYPE_LABELS: Record<string, string> = {
  BIZ_REG: "사업자등록증",
  VAT_CERT: "부가세 과세증명",
  FINANCIAL_STAT: "재무제표",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

interface DocumentCardProps {
  doc: DocumentListItem;
  onDelete: () => void;
  deleteDisabled?: boolean;
}

export function DocumentCard({ doc, onDelete, deleteDisabled }: DocumentCardProps) {
  const ocrMeta = OCR_BADGE[doc.ocr_status] ?? {
    label: doc.ocr_status,
    variant: "default" as const,
  };
  const typeLabel = DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type;

  return (
    <article className="flex items-center gap-4 rounded-xl border border-surface-border bg-surface p-4 shadow-card">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-primary-600">
        <FileText className="h-5 w-5" />
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-ink">{typeLabel}</p>
        <p className="text-xs text-ink-secondary">{formatDate(doc.created_at)}</p>
      </div>

      <Badge variant={ocrMeta.variant} size="sm">
        {ocrMeta.label}
      </Badge>

      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label="다운로드"
          className={cn(
            "rounded p-1.5 text-ink-tertiary transition-colors hover:bg-surface-muted hover:text-ink",
            doc.ocr_status !== "COMPLETED" && "pointer-events-none opacity-40"
          )}
        >
          <Download className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={onDelete}
          disabled={deleteDisabled}
          aria-label="삭제"
          className="rounded p-1.5 text-ink-tertiary transition-colors hover:bg-danger-50 hover:text-danger-500 disabled:pointer-events-none disabled:opacity-50"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </article>
  );
}

export function DocumentCardSkeleton() {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-surface-border bg-surface p-4 shadow-card">
      <div className="h-11 w-11 animate-pulse rounded-lg bg-surface-subtle" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-36 animate-pulse rounded bg-surface-subtle" />
        <div className="h-3 w-24 animate-pulse rounded bg-surface-subtle" />
      </div>
      <div className="h-5 w-12 animate-pulse rounded bg-surface-subtle" />
    </div>
  );
}
