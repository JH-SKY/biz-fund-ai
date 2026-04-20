"use client";

/**
 * UploadDialog — 서류 업로드 모달.
 *
 * - 서류 종류 선택 (select)
 * - 파일 drag & drop (+ 클릭 업로드)
 * - 업로드 중 loading 상태
 */

import * as React from "react";
import { Upload, FileText } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";

const DOC_TYPE_OPTIONS = [
  { value: "BIZ_REG", label: "사업자등록증" },
  { value: "VAT_CERT", label: "부가세 과세증명" },
  { value: "FINANCIAL_STAT", label: "재무제표" },
  { value: "OTHER", label: "기타" },
];

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpload: (file: File, documentType: string) => Promise<void>;
  uploading?: boolean;
}

export function UploadDialog({
  open,
  onOpenChange,
  onUpload,
  uploading,
}: UploadDialogProps) {
  const [docType, setDocType] = React.useState("BIZ_REG");
  const [file, setFile] = React.useState<File | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  function reset() {
    setDocType("BIZ_REG");
    setFile(null);
    setDragging(false);
  }

  function handleClose(v: boolean) {
    if (!v) reset();
    onOpenChange(v);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  }

  async function handleSubmit() {
    if (!file) return;
    await onUpload(file, docType);
    reset();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={handleClose}
      title="서류 업로드"
      description="PDF, JPG, PNG 파일을 지원합니다. (최대 20MB)"
      footer={
        <>
          <Button variant="secondary" onClick={() => handleClose(false)}>
            취소
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!file}
            loading={uploading}
          >
            업로드
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label>서류 종류</Label>
          <Select
            options={DOC_TYPE_OPTIONS}
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
          />
        </div>

        {/* Drag & Drop 영역 */}
        <div
          role="button"
          tabIndex={0}
          aria-label="파일 선택 영역"
          className={cn(
            "flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
            dragging
              ? "border-primary-500 bg-primary-50"
              : "border-surface-border hover:border-primary-300 hover:bg-surface-muted"
          )}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            className="sr-only"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) setFile(f);
            }}
          />

          {file ? (
            <>
              <FileText className="h-10 w-10 text-primary-500" />
              <div>
                <p className="text-sm font-semibold text-ink">{file.name}</p>
                <p className="text-xs text-ink-secondary">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <button
                type="button"
                className="text-xs text-primary-600 underline-offset-2 hover:underline"
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
              >
                다른 파일 선택
              </button>
            </>
          ) : (
            <>
              <Upload className="h-10 w-10 text-ink-tertiary" />
              <div>
                <p className="text-sm font-semibold text-ink">
                  파일을 드래그하거나 클릭해서 선택
                </p>
                <p className="text-xs text-ink-secondary">PDF, JPG, PNG</p>
              </div>
            </>
          )}
        </div>
      </div>
    </Dialog>
  );
}
