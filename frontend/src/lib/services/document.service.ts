/**
 * 서류(documents) 도메인 API.
 *
 * 백엔드 매핑 (backend/src/app/api/v1/business_router.py — documents 섹션)
 *  - GET    /documents                → fetchMyDocuments  ← [대시보드 '등록 서류 현황']
 *  - POST   /documents                → uploadDocument (multipart)
 *  - GET    /documents/{id}           → fetchDocumentDetail
 *  - DELETE /documents/{id}           → deleteDocument
 */

import apiClient from "@/lib/api-client";
import type { DocumentDetail, DocumentListItem } from "@/types";

export interface UploadDocumentPayload {
  file: File;
  documentType: "BIZ_REG" | "VAT_CERT" | "FINANCIAL_STAT" | (string & {});
}

export const documentService = {
  fetchMyDocuments: () => apiClient.get<DocumentListItem[]>("/documents"),

  fetchDocumentDetail: (documentId: string) =>
    apiClient.get<DocumentDetail>(`/documents/${documentId}`),

  uploadDocument: ({ file, documentType }: UploadDocumentPayload) => {
    const form = new FormData();
    form.append("file", file);
    form.append("document_type", documentType);
    return apiClient.post<{ document_id: string; status: string }>(
      "/documents",
      form,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
  },

  deleteDocument: (documentId: string) =>
    apiClient.delete<void>(`/documents/${documentId}`),
};
