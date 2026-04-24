"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Rocket } from "lucide-react";

import { PublicGuard } from "@/components/auth/AuthGuard";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";

export default function AuthLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => Boolean(state.accessToken));
  const logout = useAuthStore((state) => state.logout);

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <PublicGuard>
      <div className="flex min-h-dvh flex-col bg-gradient-to-b from-primary-50 to-surface">
        <header className="py-6">
          <div className="mx-auto flex max-w-[var(--content-max)] items-center justify-between gap-3 px-4">
            <Link href="/" className="flex items-center gap-2" aria-label="Go home">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600 text-white">
                <Rocket className="h-5 w-5" />
              </div>
              <span className="text-lg font-bold">Biz-Up</span>
            </Link>

            {isAuthenticated && (
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
            )}
          </div>
        </header>

        <main className="flex flex-1 items-center justify-center px-4 pb-16 pt-4">
          {children}
        </main>
      </div>
    </PublicGuard>
  );
}
