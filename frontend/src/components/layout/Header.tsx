"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, LogOut, Menu, Rocket, UserCircle2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  NotificationItem,
  NotificationItemSkeleton,
} from "@/features/notifications/NotificationItem";
import {
  useMarkAllRead,
  useMarkAsRead,
  useNotificationList,
} from "@/hooks/useNotifications";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";
import { Sidebar } from "./Sidebar";

export function Header() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const router = useRouter();
  const logout = useAuthStore((state) => state.logout);
  const notificationLayerRef = useRef<HTMLDivElement | null>(null);

  const { data: notifications, isLoading } = useNotificationList();
  const markAsRead = useMarkAsRead();
  const markAllRead = useMarkAllRead();

  const unreadCount =
    notifications?.filter((notification) => !notification.is_read).length ?? 0;
  const previewItems = notifications?.slice(0, 5) ?? [];

  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";

    return () => {
      document.body.style.overflow = "";
    };
  }, [drawerOpen]);

  useEffect(() => {
    if (!notificationOpen) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      if (
        notificationLayerRef.current &&
        !notificationLayerRef.current.contains(event.target as Node)
      ) {
        setNotificationOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setNotificationOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [notificationOpen]);

  function handleLogout() {
    logout();
    setDrawerOpen(false);
    setNotificationOpen(false);
    router.replace("/login");
  }

  return (
    <>
      <header
        className={cn(
          "sticky top-0 z-40 h-header-mobile lg:h-header",
          "border-b border-surface-border bg-surface/90 backdrop-blur",
          "flex items-center justify-between px-4 lg:px-6",
          "lg:pl-[calc(theme(spacing.sidebar)+1.5rem)]"
        )}
      >
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="메뉴 열기"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg hover:bg-surface-muted lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          <Link
            href="/dashboard"
            className="flex items-center gap-2 lg:hidden"
            aria-label="대시보드로 이동"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-600 text-white">
              <Rocket className="h-4 w-4" />
            </div>
            <span className="text-base font-bold text-ink">Biz-Up</span>
          </Link>

          <div className="hidden text-sm text-ink-tertiary lg:block">
            오늘도 놓치지 않게 챙겨드릴게요
          </div>
        </div>

        <div className="flex items-center gap-1">
          <div className="relative" ref={notificationLayerRef}>
            <Button
              variant="ghost"
              size="icon"
              aria-label="알림 열기"
              aria-expanded={notificationOpen}
              aria-haspopup="dialog"
              className="relative"
              onClick={() => setNotificationOpen((open) => !open)}
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span
                  aria-hidden
                  className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger-500"
                />
              )}
            </Button>

            {notificationOpen && (
              <div className="absolute right-0 top-[calc(100%+0.5rem)] z-50 w-[min(92vw,24rem)] overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-elevated">
                <div className="flex items-center justify-between border-b border-surface-border px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-ink">알림</p>
                    <p className="text-xs text-ink-tertiary">
                      {unreadCount > 0
                        ? `읽지 않은 알림 ${unreadCount}개`
                        : "새 알림이 없습니다"}
                    </p>
                  </div>

                  {unreadCount > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => markAllRead.mutate()}
                      loading={markAllRead.isPending}
                    >
                      모두 읽음
                    </Button>
                  )}
                </div>

                <div className="max-h-[24rem] overflow-y-auto">
                  {isLoading ? (
                    <div className="divide-y divide-surface-border">
                      {Array.from({ length: 4 }).map((_, index) => (
                        <NotificationItemSkeleton key={index} />
                      ))}
                    </div>
                  ) : previewItems.length === 0 ? (
                    <div className="px-4 py-10 text-center">
                      <p className="text-sm font-semibold text-ink">
                        표시할 알림이 없습니다
                      </p>
                      <p className="mt-1 text-xs text-ink-tertiary">
                        새로운 소식이 오면 여기에서 바로 확인할 수 있어요.
                      </p>
                    </div>
                  ) : (
                    <ul className="divide-y divide-surface-border">
                      {previewItems.map((item) => (
                        <li key={item.noti_id}>
                          <NotificationItem
                            item={item}
                            onRead={() => markAsRead.mutate(item.noti_id)}
                          />
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="border-t border-surface-border p-2">
                  <Button
                    asChild
                    variant="ghost"
                    className="w-full justify-center"
                  >
                    <Link
                      href="/notifications"
                      onClick={() => setNotificationOpen(false)}
                    >
                      알림 전체 보기
                    </Link>
                  </Button>
                </div>
              </div>
            )}
          </div>

          <Button asChild variant="ghost" size="icon" aria-label="프로필">
            <Link href="/profile">
              <UserCircle2 className="h-6 w-6" />
            </Link>
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleLogout}
            className="gap-2 rounded-full px-3"
            aria-label="로그아웃"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">로그아웃</span>
          </Button>
        </div>
      </header>

      {drawerOpen && (
        <div
          className="fixed inset-0 z-50 lg:hidden"
          role="dialog"
          aria-modal="true"
        >
          <div
            className="absolute inset-0 animate-fade-in bg-ink/40"
            onClick={() => setDrawerOpen(false)}
            aria-hidden
          />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] animate-slide-in-left bg-surface shadow-elevated">
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              aria-label="메뉴 닫기"
              className="absolute right-2 top-3 inline-flex h-10 w-10 items-center justify-center rounded-lg hover:bg-surface-muted"
            >
              <X className="h-5 w-5" />
            </button>
            <Sidebar
              variant="drawer"
              onNavigate={() => setDrawerOpen(false)}
            />
          </div>
        </div>
      )}
    </>
  );
}
