"use client";

import type { ReactNode } from "react";

import { QueryProvider } from "./QueryProvider";
import { ToastProvider } from "./ToastProvider";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <ToastProvider>{children}</ToastProvider>
    </QueryProvider>
  );
}

export { QueryProvider, ToastProvider };
