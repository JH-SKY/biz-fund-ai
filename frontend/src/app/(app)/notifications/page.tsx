"use client";

import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  NotificationItem,
  NotificationItemSkeleton,
} from "@/features/notifications/NotificationItem";
import {
  useNotificationList,
  useMarkAsRead,
  useMarkAllRead,
} from "@/hooks/useNotifications";

export default function NotificationsPage() {
  const { data: notifications, isLoading } = useNotificationList();
  const markAsRead = useMarkAsRead();
  const markAllRead = useMarkAllRead();

  const unreadCount =
    notifications?.filter((n) => !n.is_read).length ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">알림</h1>
          {unreadCount > 0 && (
            <p className="mt-0.5 text-sm text-ink-secondary">
              읽지 않은 알림{" "}
              <span className="font-bold text-primary-600">{unreadCount}개</span>
            </p>
          )}
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

      <div className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-card">
        {isLoading ? (
          <div className="divide-y divide-surface-border">
            {Array.from({ length: 5 }).map((_, i) => (
              <NotificationItemSkeleton key={i} />
            ))}
          </div>
        ) : !notifications || notifications.length === 0 ? (
          <div className="flex flex-col items-center gap-3 px-6 py-20 text-center">
            <Bell className="h-12 w-12 text-ink-tertiary" />
            <p className="text-base font-semibold text-ink">알림이 없습니다</p>
            <p className="text-sm text-ink-secondary">
              정책 마감, 매칭 결과 등 중요한 소식을 이곳에서 알려드려요.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-surface-border">
            {notifications.map((item) => (
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
    </div>
  );
}
