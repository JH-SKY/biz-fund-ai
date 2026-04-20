/**
 * 공통 유틸리티 — Tailwind 클래스 병합 등.
 */

import clsx, { type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
