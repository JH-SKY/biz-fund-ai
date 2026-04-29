"use client";

import Link from "next/link";
import { ArrowUpRight, FileSearch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { chatService } from "@/lib/services";
import type { AgentRagResult } from "@/types";

interface Props {
  results: AgentRagResult[];
  answer?: string;
  sessionId?: string | null;
  assistantMessageId?: string;
}

export function RagCard({ results, answer, sessionId, assistantMessageId }: Props) {
  const trackPolicyDetail = async (policyId: string) => {
    if (!sessionId || !assistantMessageId) return;

    try {
      await chatService.trackCtaEvent(sessionId, {
        assistant_message_id: assistantMessageId,
        cta_type: "POLICY_DETAIL_PAGE",
        target_path: `/policies/${policyId}`,
        ref_policy_id: policyId,
        metadata: {
          source: "rag_card",
        },
      });
    } catch (error) {
      console.error("[BizMong CTA]", error);
    }
  };

  return (
    <Card className="w-full overflow-hidden border-primary-100">
      <div className="flex items-center gap-2 border-b border-primary-100 bg-primary-50 px-4 py-2.5">
        <FileSearch className="h-4 w-4 text-primary-600" />
        <span className="text-sm font-bold text-primary-800">정책 검색 결과</span>
      </div>

      <CardContent className="space-y-3 p-4">
        {answer ? <p className="text-sm leading-relaxed text-ink">{answer}</p> : null}

        {results.length > 0 ? (
          <div className="space-y-2">
            <p className="text-[11px] font-bold uppercase tracking-wide text-ink-tertiary">참고 정책</p>
            {results.slice(0, 3).map((result, index) => (
              <div
                key={result.policy_id ?? `${result.title ?? "policy"}-${index}`}
                className="rounded-lg border border-surface-border bg-surface-muted p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    {result.title ? <p className="text-xs font-semibold text-ink">{result.title}</p> : null}
                    {result.excerpt || result.content ? (
                      <p className="mt-1 line-clamp-2 text-[11px] text-ink-secondary">
                        {result.excerpt ?? result.content}
                      </p>
                    ) : null}
                  </div>
                  {result.policy_id ? (
                    <Link
                      href={`/policies/${result.policy_id}`}
                      className="shrink-0"
                      onClick={() => void trackPolicyDetail(result.policy_id!)}
                    >
                      <Badge variant="outline" size="sm" className="gap-0.5">
                        상세 <ArrowUpRight className="h-2.5 w-2.5" />
                      </Badge>
                    </Link>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
