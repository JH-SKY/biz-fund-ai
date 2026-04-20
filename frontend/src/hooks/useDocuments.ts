"use client";

/**
 * 서류 보관함 React Query 훅 모음.
 *
 *  useDocumentList()   → 서류 목록
 *  useUploadDocument() → 파일 업로드 mutation
 *  useDeleteDocument() → 삭제 mutation
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentService } from "@/lib/services";
import type { UploadDocumentPayload } from "@/lib/services/document.service";
import { useBusinessStore } from "@/stores/business-store";

export const DOCUMENT_KEYS = {
  list: (bizId: string | null) => ["documents", "list", bizId] as const,
};

export function useDocumentList() {
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useQuery({
    queryKey: DOCUMENT_KEYS.list(bizId),
    queryFn: () => documentService.fetchMyDocuments(),
    enabled: Boolean(bizId),
    staleTime: 30_000,
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useMutation({
    mutationFn: (payload: UploadDocumentPayload) =>
      documentService.uploadDocument(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: DOCUMENT_KEYS.list(bizId) });
    },
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  const bizId = useBusinessStore((s) => s.activeBizId);
  return useMutation({
    mutationFn: (documentId: string) =>
      documentService.deleteDocument(documentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: DOCUMENT_KEYS.list(bizId) });
    },
  });
}
