"use client";

/**
 * RagCard — 정책 RAG 검색 결과 카드.
 * .cursorrules §7-4
 *  - 답변 텍스트
 *  - 참조 정책 목록
 */

import Link from "next/link";
import { ArrowUpRight, FileSearch } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AgentRagResult } from "@/types";

interface Props {
  results: AgentRagResult[];
  answer?: string;
}

export function RagCard({ results, answer }: Props) {
  return (
    <Card className="w-full overflow-hidden border-primary-100">
      <div className="flex items-center gap-2 bg-primary-50 px-4 py-2.5 border-b border-primary-100">
        <FileSearch className="h-4 w-4 text-primary-600" />
        <span className="text-sm font-bold text-primary-800">정책 검색 결과</span>
      </div>

      <CardContent className="p-4 space-y-3">
        {/* 답변 */}
        {answer && (
          <p className="text-sm leading-relaxed text-ink">{answer}</p>
        )}

        {/* 참조 정책 */}
        {results && results.length > 0 && (
          <div className="space-y-2">
            <p className="text-[11px] font-bold uppercase tracking-wide text-ink-tertiary">
              참조 정책
            </p>
            {results.slice(0, 3).map((r, i) => (
              <div
                key={r.policy_id ?? i}
                className="rounded-lg border border-surface-border bg-surface-muted p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    {r.title && (
                      <p className="text-xs font-semibold text-ink">{r.title}</p>
                    )}
                    {(r.content || r.excerpt) && (
                      <p className="mt-1 line-clamp-2 text-[11px] text-ink-secondary">
                        {r.excerpt ?? r.content}
                      </p>
                    )}
                  </div>
                  {r.policy_id && (
                    <Link
                      href={`/policies/${r.policy_id}`}
                      className="shrink-0"
                    >
                      <Badge variant="outline" size="sm" className="gap-0.5">
                        상세 <ArrowUpRight className="h-2.5 w-2.5" />
                      </Badge>
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
