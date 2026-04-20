"use client";

/**
 * 관리자 센터 상단 헤더.
 *
 * 구성
 *  - 좌측: 모바일 햄버거 메뉴(향후) + 페이지 타이틀
 *  - 우측: 관리자 이름 · 역할 · 로그아웃 버튼
 */

import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAdminAuthStore } from "@/stores/admin-auth-store";
import { ADMIN_NAV_ITEMS } from "@/config/admin-navigation";

interface AdminHeaderProps {
  onMenuClick?: () => void;
}

export function AdminHeader({ onMenuClick }: AdminHeaderProps) {
  const pathname = usePathname() ?? "";
  const admin = useAdminAuthStore((s) => s.admin);

  const currentItem = ADMIN_NAV_ITEMS.find(
    (item) =>
      pathname === (item.matchPrefix ?? item.href) ||
      pathname.startsWith((item.matchPrefix ?? item.href) + "/")
  );
  const title = currentItem?.label ?? "관리자 센터";

  return (
    <header className="sticky top-0 z-20 flex h-header items-center gap-3 border-b border-surface-border bg-surface/95 px-4 backdrop-blur lg:px-8">
      <Button
        variant="ghost"
        size="icon"
        onClick={onMenuClick}
        className="lg:hidden"
        aria-label="메뉴 열기"
      >
        <Menu className="h-5 w-5" />
      </Button>

      <div className="min-w-0 flex-1">
        <p className="text-xs text-ink-tertiary">Biz-Up Admin</p>
        <h1 className="truncate text-lg font-bold text-ink">{title}</h1>
      </div>

      {admin && (
        <div className="hidden items-center gap-3 sm:flex">
          <div className="text-right leading-tight">
            <p className="text-sm font-semibold text-ink">{admin.name}</p>
            <p className="text-[11px] text-ink-tertiary">
              {admin.role === "SUPER_ADMIN" ? "최고 관리자" : "운영 담당자"}
            </p>
          </div>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary-700">
            {admin.name.slice(0, 1)}
          </div>
        </div>
      )}
    </header>
  );
}
