import type { Metadata, Viewport } from "next";
import { Providers } from "@/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Biz-Up | 사장님을 위한 AI 정책자금 비서",
  description:
    "비즈몽 AI가 사업장 조건에 딱 맞는 정책자금을 찾아드립니다. 진단·시뮬레이션·맞춤 추천까지 한 번에.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#ffffff",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
