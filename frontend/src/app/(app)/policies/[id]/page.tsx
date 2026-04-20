"use client";

/**
 * [P07] /policies/[id] — 정책 상세 페이지.
 *
 * 레이아웃 (desktop 1024+)
 *   ┌──────────────────────────────────────────────────┐
 *   │ (breadcrumb · back)                              │
 *   │ [Hero: AI 맞춤 브리핑]                           │
 *   │ [핵심 정보 Table]            [우측: 액션 사이드] │
 *   │ [공고 원문]                                       │
 *   └──────────────────────────────────────────────────┘
 *
 * - 적합도(match_level / score) 는 /policies/recommend 캐시에서 보조로 찾음.
 *   (Detail API 에 match 필드가 없으므로 cross-referencing)
 * - 인증/온보딩 가드는 (app) 레이아웃 레벨에서 추후 연결.
 */

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Calendar, Eye } from "lucide-react";
import { useMemo } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PolicyActionBar } from "@/features/policies/PolicyActionBar";
import { PolicyDetailHero } from "@/features/policies/PolicyDetailHero";
import { PolicyInfoTable } from "@/features/policies/PolicyInfoTable";
import {
  useBookmarkToggle,
  usePolicyDetail,
  useRecommendedPolicies,
} from "@/hooks/usePolicies";

function formatDate(iso?: string | null): string {
  if (!iso) return "-";
  if (iso.startsWith("9999")) return "상시접수";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

function formatDday(iso?: string | null): { label: string; closed: boolean } {
  if (!iso) return { label: "-", closed: false };
  if (iso.startsWith("9999")) return { label: "상시접수", closed: false };
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(iso);
  if (Number.isNaN(target.getTime())) return { label: iso, closed: false };
  const diff = Math.ceil(
    (target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
  );
  if (diff < 0) return { label: "마감", closed: true };
  if (diff === 0) return { label: "D-Day", closed: false };
  return { label: `D-${diff}`, closed: false };
}

export default function PolicyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const policyId = params?.id;

  const { data: detail, isLoading, isError } = usePolicyDetail(policyId);
  const { data: recommend } = useRecommendedPolicies();
  const bookmarkMutation = useBookmarkToggle();

  // 적합도 보조 데이터 — recommend 캐시에서 match 찾기
  const matchInfo = useMemo(() => {
    if (!recommend?.items || !policyId) return null;
    return recommend.items.find((i) => i.policy_id === policyId) ?? null;
  }, [recommend, policyId]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-24 animate-pulse rounded bg-surface-subtle" />
        <div className="h-56 animate-pulse rounded-2xl bg-surface-subtle" />
        <div className="h-40 animate-pulse rounded-xl bg-surface-subtle" />
      </div>
    );
  }

  if (isError || !detail) {
    return (
      <div className="rounded-xl border border-danger-200 bg-danger-50 p-6 text-sm text-danger-800">
        정책 정보를 불러오지 못했습니다.
        <div className="mt-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push("/policies")}
          >
            목록으로 돌아가기
          </Button>
        </div>
      </div>
    );
  }

  const dday = formatDday(detail.closed_at);

  return (
    <div className="space-y-5 pb-4">
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.back()}
          aria-label="목록으로 돌아가기"
        >
          <ArrowLeft />
          <span>목록으로</span>
        </Button>
        <Link
          href="/policies/matching"
          className="text-xs font-semibold text-primary-700 hover:underline"
        >
          맞춤 정책 더 보기 →
        </Link>
      </div>

      <PolicyDetailHero
        title={detail.title}
        content={detail.content}
        matchLevel={matchInfo?.match_level ?? null}
        matchScore={matchInfo?.match_score ?? null}
        reason={matchInfo?.reason ?? null}
        hasBusinessProfile={!!matchInfo}
      />

      <PolicyInfoTable
        rows={[
          {
            label: "시행 기관",
            value: <span className="font-semibold">{detail.agency_name}</span>,
          },
          {
            label: "카테고리",
            value: detail.category ? (
              <Badge variant="outline" size="sm">
                {detail.category}
              </Badge>
            ) : (
              "-"
            ),
          },
          {
            label: "지원 금액",
            value: (
              <span className="numeric font-semibold text-primary-700">
                {detail.support_amount ?? "공고문 참조"}
              </span>
            ),
          },
          {
            label: "접수 기간",
            value: (
              <span className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-primary-500" />
                <span className="numeric">{formatDate(detail.closed_at)}</span>
                <Badge
                  variant={dday.closed ? "outline" : "accent"}
                  size="sm"
                  className="ml-1"
                >
                  {dday.label}
                </Badge>
              </span>
            ),
          },
          {
            label: "필수 서류",
            value:
              detail.required_documents.length > 0 ? (
                <ul className="flex flex-wrap gap-1.5">
                  {detail.required_documents.map((doc) => (
                    <li key={doc}>
                      <Badge variant="outline" size="sm">
                        {doc}
                      </Badge>
                    </li>
                  ))}
                </ul>
              ) : (
                "-"
              ),
          },
          {
            label: "조회수",
            value: (
              <span className="numeric flex items-center gap-1.5 text-ink-secondary">
                <Eye className="h-4 w-4" />
                {detail.view_count.toLocaleString()}
              </span>
            ),
          },
        ]}
      />

      <Card>
        <CardContent className="py-5">
          <h2 className="mb-2 text-sm font-bold text-ink">공고 원문 / 요약</h2>
          <p className="whitespace-pre-line text-sm leading-relaxed text-ink-secondary">
            {detail.content}
          </p>
        </CardContent>
      </Card>

      <PolicyActionBar
        policyId={detail.policy_id}
        isBookmarked={detail.is_bookmarked}
        onBookmarkToggle={() => bookmarkMutation.mutate(detail.policy_id)}
        applyUrl={detail.apply_url}
        isClosed={dday.closed}
      />
    </div>
  );
}
