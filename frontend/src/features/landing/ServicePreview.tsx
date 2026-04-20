"use client";

/**
 * ServicePreview — 블러 처리된 서비스 미리보기 3종.
 *
 * 스펙 (기획서 §2-③)
 *  - 비즈픽(맞춤정보), 비즈핑(맞춤알림), 비즈몽(AI상담) 맛보기
 *  - 주요 수치를 blur 처리 → 호기심 유발
 *  - 각 카드 클릭 / [상세 분석 시작하기] → /login 이동
 */

import Link from "next/link";
import { ArrowRight, BellRing, MessageSquareHeart, Newspaper } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface PreviewItem {
  key: string;
  title: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  body: React.ReactNode;
}

const ITEMS: PreviewItem[] = [
  {
    key: "pick",
    title: "비즈픽",
    name: "맞춤 정보 피드",
    description: "AI가 가공한 정책 카드 뉴스",
    icon: <Newspaper className="h-5 w-5" />,
    body: (
      <>
        <div className="rounded-lg bg-surface-muted p-3">
          <p className="text-xs text-ink-tertiary">오늘의 픽</p>
          <p className="mt-1 font-semibold text-ink blur-sm select-none">
            소상공인 경영안정자금 — 최대 7천만원
          </p>
        </div>
        <div className="mt-2 flex gap-2">
          <Badge variant="success">신청 가능</Badge>
          <Badge variant="accent">D-30</Badge>
        </div>
      </>
    ),
  },
  {
    key: "ping",
    title: "비즈핑",
    name: "맞춤 알림",
    description: "마감 임박·신규 공고 즉시 알림",
    icon: <BellRing className="h-5 w-5" />,
    body: (
      <>
        <ul className="space-y-2 text-sm">
          <li className="flex items-start gap-2">
            <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-danger-500" />
            <span className="text-ink-secondary blur-sm select-none">
              북마크한 정책의 마감이 3일 남았습니다
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-success-500" />
            <span className="text-ink-secondary blur-sm select-none">
              업력 3년 충족! 새 정책 5개가 열렸어요
            </span>
          </li>
        </ul>
      </>
    ),
  },
  {
    key: "mong",
    title: "비즈몽",
    name: "AI 상담",
    description: "진단·시뮬레이션·RAG 검색",
    icon: <MessageSquareHeart className="h-5 w-5" />,
    body: (
      <>
        <div className="rounded-lg bg-primary-50 p-3 text-sm">
          <p className="font-semibold text-primary-800">🤖 비즈몽</p>
          <p className="mt-1 text-ink-secondary blur-sm select-none">
            사장님 조건 기준 적합도 65점 / 매칭 12건 입니다...
          </p>
        </div>
      </>
    ),
  },
];

export function ServicePreview() {
  return (
    <section className="w-full">
      <div className="mb-6 text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-primary-600">
          What you&apos;ll get
        </p>
        <h2 className="mt-2">로그인하면 열리는 세 가지 도구</h2>
        <p className="mt-2 text-sm text-ink-secondary">
          비즈업의 AI가 사업장 조건을 분석해 아래 정보를 맞춤 제공합니다.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {ITEMS.map((it) => (
          <Link key={it.key} href="/login" className="block">
            <Card interactive className="h-full">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary-50 text-primary-600">
                    {it.icon}
                  </span>
                  <div>
                    <CardTitle className="text-base">{it.title}</CardTitle>
                    <CardDescription className="text-xs">
                      {it.name}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-ink-tertiary mb-3">
                  {it.description}
                </p>
                {it.body}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="mt-8 text-center">
        <Link href="/login">
          <Button variant="primary" size="lg">
            상세 분석 시작하기 <ArrowRight />
          </Button>
        </Link>
      </div>
    </section>
  );
}
