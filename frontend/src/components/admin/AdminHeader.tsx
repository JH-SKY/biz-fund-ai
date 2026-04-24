"use client";

import { usePathname, useRouter } from "next/navigation";
import { LogOut, Menu } from "lucide-react";

import { ADMIN_NAV_ITEMS } from "@/config/admin-navigation";
import { Button } from "@/components/ui/button";
import { useAdminAuthStore } from "@/stores/admin-auth-store";

interface AdminHeaderProps {
  onMenuClick?: () => void;
}

export function AdminHeader({ onMenuClick }: AdminHeaderProps) {
  const pathname = usePathname() ?? "";
  const router = useRouter();
  const admin = useAdminAuthStore((state) => state.admin);
  const logoutAdmin = useAdminAuthStore((state) => state.logoutAdmin);

  const currentItem = ADMIN_NAV_ITEMS.find(
    (item) =>
      pathname === (item.matchPrefix ?? item.href) ||
      pathname.startsWith((item.matchPrefix ?? item.href) + "/")
  );
  const title = currentItem?.label ?? "Admin";

  function handleLogout() {
    logoutAdmin();
    router.replace("/admin/login");
  }

  return (
    <header className="sticky top-0 z-20 flex h-header items-center gap-3 border-b border-surface-border bg-surface/95 px-4 backdrop-blur lg:px-8">
      <Button
        variant="ghost"
        size="icon"
        onClick={onMenuClick}
        className="lg:hidden"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </Button>

      <div className="min-w-0 flex-1">
        <p className="text-xs text-ink-tertiary">Biz-Up Admin</p>
        <h1 className="truncate text-lg font-bold text-ink">{title}</h1>
      </div>

      {admin && (
        <div className="flex items-center gap-3">
          <div className="hidden text-right leading-tight sm:block">
            <p className="text-sm font-semibold text-ink">{admin.name}</p>
            <p className="text-[11px] text-ink-tertiary">
              {admin.role === "SUPER_ADMIN" ? "Super Admin" : "Operator"}
            </p>
          </div>

          <div className="hidden h-9 w-9 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary-700 sm:flex">
            {admin.name.slice(0, 1)}
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleLogout}
            className="gap-2 rounded-full px-3"
            aria-label="Log out"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Log out</span>
          </Button>
        </div>
      )}
    </header>
  );
}
