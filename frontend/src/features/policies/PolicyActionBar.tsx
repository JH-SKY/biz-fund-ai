"use client";

/**
 * 정책 상세 하단 실행 버튼 영역 (Sticky on mobile).
 * - 찜하기(북마크 토글)
 * - 비즈몽과 서류 준비하기 → /chat?mode=document&policyId=...
 * - 공식 사이트 이동 (외부 링크)
 */

import Link from "next/link";
import { Bookmark, ExternalLink, MessageSquareHeart } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  policyId: string;
  isBookmarked: boolean;
  onBookmarkToggle: () => void;
  applyUrl: string | null | undefined;
  isClosed: boolean;
}

export function PolicyActionBar({
  policyId,
  isBookmarked,
  onBookmarkToggle,
  applyUrl,
  isClosed,
}: Props) {
  return (
    <div
      className={cn(
        // 모바일: 하단 탭바(bottom-tab) 바로 위에 sticky; 데스크톱: 일반 카드
        "sticky left-0 right-0 z-30 -mx-4 border-t border-surface-border bg-surface/95 px-4 py-3 backdrop-blur-sm",
        "bottom-[theme(spacing.bottom-tab)] lg:bottom-0",
        "sm:static sm:mx-0 sm:rounded-xl sm:border sm:px-5 sm:py-4 sm:shadow-card",
        "safe-pb"
      )}
    >
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          onClick={onBookmarkToggle}
          aria-label={isBookmarked ? "관심 정책 해제" : "관심 정책 저장"}
        >
          <Bookmark
            className={cn(isBookmarked && "fill-primary-600 text-primary-600")}
          />
          <span className="hidden sm:inline">
            {isBookmarked ? "저장됨" : "찜하기"}
          </span>
        </Button>

        <Button asChild variant="outline" className="flex-1 sm:flex-initial">
          <Link
            href={`/chat?mode=document&policyId=${encodeURIComponent(policyId)}`}
          >
            <MessageSquareHeart />
            <span>비즈몽과 서류 준비</span>
          </Link>
        </Button>

        {applyUrl && !isClosed ? (
          <Button asChild variant="primary" className="flex-1 sm:flex-initial">
            <a href={applyUrl} target="_blank" rel="noopener noreferrer">
              <span>신청 사이트 이동</span>
              <ExternalLink />
            </a>
          </Button>
        ) : (
          <Button variant="primary" className="flex-1 sm:flex-initial" disabled>
            {isClosed ? "마감된 공고" : "링크 준비 중"}
          </Button>
        )}
      </div>
    </div>
  );
}
