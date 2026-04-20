"use client";

/**
 * 등록 서류 현황 위젯.
 *  - 필수 서류(BIZ_REG / VAT_CERT / FINANCIAL_STAT) 각각 등록 여부 노출
 *  - OCR 상태별 배지 표시 (PENDING/COMPLETED/FAILED)
 *  - [추가 등록하기] 버튼 → /documents
 */

import Link from "next/link";
import { FilePlus2, FileCheck2, Loader2, TriangleAlert } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { DocumentListItem, OcrStatus } from "@/types";

const REQUIRED_DOCS: Array<{ type: string; label: string }> = [
  { type: "BIZ_REG", label: "사업자등록증" },
  { type: "VAT_CERT", label: "부가세증명원" },
  { type: "FINANCIAL_STAT", label: "재무제표" },
];

function OcrBadge({ status }: { status: OcrStatus }) {
  if (status === "COMPLETED")
    return (
      <Badge variant="success" size="sm">
        <FileCheck2 className="h-3 w-3" /> OCR 완료
      </Badge>
    );
  if (status === "FAILED")
    return (
      <Badge variant="danger" size="sm">
        <TriangleAlert className="h-3 w-3" /> OCR 실패
      </Badge>
    );
  return (
    <Badge variant="default" size="sm">
      <Loader2 className="h-3 w-3 animate-spin" /> 분석 중
    </Badge>
  );
}

interface Props {
  documents?: DocumentListItem[];
  isLoading?: boolean;
}

export function DocumentsWidget({ documents, isLoading }: Props) {
  const docMap = new Map<string, DocumentListItem>();
  documents?.forEach((d) => {
    if (!docMap.has(d.doc_type)) docMap.set(d.doc_type, d);
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>등록 서류 현황</CardTitle>
        <CardDescription>
          필수 서류를 미리 등록해 두면 신청 속도가 훨씬 빨라져요.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <ul className="space-y-2">
            {[0, 1, 2].map((i) => (
              <li
                key={i}
                className="h-10 animate-pulse rounded-md bg-surface-subtle"
              />
            ))}
          </ul>
        ) : (
          <ul className="divide-y divide-surface-border">
            {REQUIRED_DOCS.map((req) => {
              const doc = docMap.get(req.type);
              return (
                <li
                  key={req.type}
                  className="flex items-center justify-between gap-2 py-2.5"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-ink">
                      {req.label}
                    </span>
                    <span className="text-[11px] text-ink-tertiary">
                      {req.type}
                    </span>
                  </div>
                  {doc ? (
                    <OcrBadge status={doc.ocr_status} />
                  ) : (
                    <Badge variant="outline" size="sm">
                      미등록
                    </Badge>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
      <CardFooter>
        <Button asChild variant="primary" size="sm">
          <Link href="/documents">
            <FilePlus2 /> 서류 추가 등록하기
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
