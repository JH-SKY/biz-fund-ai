"use client";

import * as React from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DocumentCard, DocumentCardSkeleton } from "@/features/documents/DocumentCard";
import { UploadDialog } from "@/features/documents/UploadDialog";
import { useDocumentList, useUploadDocument, useDeleteDocument } from "@/hooks/useDocuments";

export default function DocumentsPage() {
  const { data: docs, isLoading } = useDocumentList();
  const upload = useUploadDocument();
  const remove = useDeleteDocument();

  const [uploadOpen, setUploadOpen] = React.useState(false);

  async function handleUpload(file: File, documentType: string) {
    await upload.mutateAsync({ file, documentType });
    setUploadOpen(false);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">서류 보관함</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            사업장 관련 서류를 업로드하면 OCR로 자동 분석됩니다.
          </p>
        </div>
        <Button onClick={() => setUploadOpen(true)} className="gap-2 shrink-0">
          <Plus className="h-4 w-4" />
          서류 업로드
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <DocumentCardSkeleton key={i} />
          ))}
        </div>
      ) : !docs || docs.length === 0 ? (
        <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-surface-border bg-surface px-6 py-20 text-center">
          <p className="text-4xl">📁</p>
          <div className="space-y-1">
            <p className="text-base font-semibold text-ink">
              등록된 서류가 없습니다
            </p>
            <p className="text-sm text-ink-secondary">
              사업자등록증, 재무제표 등을 업로드해보세요.
            </p>
          </div>
          <Button variant="outline" onClick={() => setUploadOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            첫 서류 업로드
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {docs.map((doc) => (
            <DocumentCard
              key={doc.document_id}
              doc={doc}
              onDelete={() => remove.mutate(doc.document_id)}
              deleteDisabled={remove.isPending}
            />
          ))}
        </div>
      )}

      <UploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onUpload={handleUpload}
        uploading={upload.isPending}
      />
    </div>
  );
}
