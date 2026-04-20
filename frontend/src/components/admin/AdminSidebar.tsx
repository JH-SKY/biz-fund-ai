"use client";

/**
 * 관리자 센터 좌측 사이드바 (다크 톤).
 *
 * 디자인
 *  - 배경: primary-950(#172554) → 일반 서비스(흰색)와 완전히 구분
 *  - 섹션 헤더: 대문자 + 저채도 컬러
 *  - 활성 메뉴: primary-500 배경 + 흰 글씨
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck, LogOut } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  ADMIN_NAV_SECTIONS,
  isActiveAdminPath,
} from "@/config/admin-navigation";
import { useAdminAuthStore } from "@/stores/admin-auth-store";

interface AdminSidebarProps {
  variant?: "fixed" | "drawer";
  onNavigate?: () => void;
}

export function AdminSidebar({
  variant = "fixed",
  onNavigate,
}: AdminSidebarProps) {
  const pathname = usePathname();
  const admin = useAdminAuthStore((s) => s.admin);
  const logoutAdmin = useAdminAuthStore((s) => s.logoutAdmin);

  return (
    <aside
      aria-label="관리자 사이드바"
      className={cn(
        "flex flex-col bg-primary-950 text-white/90",
        variant === "fixed"
          ? "hidden lg:flex lg:fixed lg:inset-y-0 lg:left-0 lg:w-sidebar lg:z-30"
          : "w-full h-full"
      )}
    >
      <div className="flex items-center gap-3 h-header px-5 border-b border-white/10">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600">
          <ShieldCheck className="h-5 w-5" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-bold text-white">Biz-Up Admin</p>
          <p className="text-[11px] text-white/60">통합 관리 센터</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="flex flex-col gap-5">
          {ADMIN_NAV_SECTIONS.map((section) => (
            <li key={section.section}>
              <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/40">
                {section.section}
              </p>
              <ul className="flex flex-col gap-1">
                {section.items.map((item) => {
                  const active = isActiveAdminPath(pathname ?? "", item);
                  const Icon = item.icon;
                  return (
                    <li key={item.key}>
                      <Link
                        href={item.href}
                        onClick={onNavigate}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                          active
                            ? "bg-primary-600 text-white shadow-sm"
                            : "text-white/70 hover:bg-white/5 hover:text-white"
                        )}
                      >
                        <Icon
                          className={cn(
                            "h-4.5 w-4.5 shrink-0",
                            active ? "text-white" : "text-white/60"
                          )}
                        />
                        <span>{item.label}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-white/10 p-4 space-y-3">
        {admin && (
          <div className="rounded-lg bg-white/5 p-3">
            <p className="text-xs text-white/60">로그인</p>
            <p className="mt-0.5 text-sm font-semibold text-white truncate">
              {admin.name}
            </p>
            <p className="text-[11px] text-primary-300">
              {admin.role === "SUPER_ADMIN" ? "최고 관리자" : "운영 담당자"}
            </p>
          </div>
        )}
        <button
          type="button"
          onClick={() => {
            logoutAdmin();
            if (typeof window !== "undefined") {
              window.location.href = "/admin/login";
            }
          }}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm font-medium text-white/80 transition-colors hover:bg-white/5 hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          로그아웃
        </button>
      </div>
    </aside>
  );
}
