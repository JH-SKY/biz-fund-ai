"use client";

/**
 * 상태 트래커 (Application Status Bar).
 *
 * 백엔드 설계 단계
 *  - applications 테이블 / 엔드포인트는 `.cursorrules` §P11 에 '기획 중'으로 표기됨.
 *  - 따라서 현 단계에서는 props 로 최근 신청을 주입받는 구조만 제공하고,
 *    데이터 없으면 "신청 이력이 없습니다" 빈 상태를 렌더한다.
 */

import Link from "next/link";

import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ApplicationItem, ApplicationStatus } from "@/types";

const STAGES: Array<{ key: ApplicationStatus; label: string }> = [
  { key: "INTERESTED", label: "관심 등록" },
  { key: "SUBMITTED", label: "서류 접수" },
  { key: "APPROVED", label: "승인 완료" },
];

interface Props {
  latestApplication?: ApplicationItem | null;
}

export function ApplicationStatusTracker({ latestApplication }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>신청 상태 트래커</CardTitle>
        <CardDescription>
          최근 신청 중인 정책의 진행 단계를 한눈에 볼 수 있어요.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!latestApplication ? (
          <div className="rounded-lg border border-dashed border-surface-border bg-surface-muted p-4">
            <p className="text-sm text-ink-secondary">
              아직 신청 중인 정책이 없어요.
            </p>
            <Button asChild variant="ghost" size="sm" className="mt-1 -ml-2">
              <Link href="/policies">관심 정책 찾아보기 →</Link>
            </Button>
          </div>
        ) : (
          <>
            <div>
              <p className="text-sm text-ink-secondary">최근 신청</p>
              <p className="font-semibold text-ink">
                {latestApplication.policy_title}
              </p>
            </div>
            <StatusProgress status={latestApplication.status} />
          </>
        )}
      </CardContent>
    </Card>
  );
}

function StatusProgress({ status }: { status: ApplicationStatus }) {
  const rejected = status === "REJECTED";
  const currentIdx = rejected
    ? 1 // 서류 접수 후 반려 케이스 기본
    : STAGES.findIndex((s) => s.key === status);

  return (
    <div>
      {rejected && (
        <Badge variant="danger" className="mb-2">
          반려 — 개선 후 재신청 가능
        </Badge>
      )}
      <ol className="flex items-center gap-2">
        {STAGES.map((stage, idx) => {
          const done = idx <= currentIdx;
          const active = idx === currentIdx && !rejected;
          return (
            <li key={stage.key} className="flex flex-1 items-center gap-2">
              <div className="flex w-full flex-col items-center gap-1">
                <div
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-full border-2 text-xs font-bold",
                    done
                      ? "border-primary-600 bg-primary-600 text-white"
                      : "border-surface-border bg-surface text-ink-tertiary",
                    active && "ring-4 ring-primary-100"
                  )}
                >
                  {idx + 1}
                </div>
                <span
                  className={cn(
                    "text-[11px]",
                    done ? "font-semibold text-ink" : "text-ink-tertiary"
                  )}
                >
                  {stage.label}
                </span>
              </div>
              {idx < STAGES.length - 1 && (
                <div
                  className={cn(
                    "h-0.5 flex-1",
                    idx < currentIdx ? "bg-primary-600" : "bg-surface-border"
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
