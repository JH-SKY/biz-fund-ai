import type { Config } from "tailwindcss";

/**
 * Biz-Up 디자인 시스템 — Tailwind 구성.
 *
 * 컬러 팔레트 설계 철학
 *  - Primary(신뢰의 블루): 금융·정책자금이라는 도메인 특성상 '믿을 수 있다'는 인상을 줘야 하므로
 *    차분하고 선명한 블루(#2563EB)를 기축으로 50~950 톤 스케일 확보.
 *  - Accent(기회의 앰버): CTA·할인·급한 마감 임박을 강조하는 보조 컬러.
 *  - Neutral: 정보 밀도 높은 리스트/카드용 그레이스케일.
 *  - Semantic: success / warning / danger — 상태 뱃지 및 신호등에 사용.
 *  - Traffic light: 기존 매칭 신호등(GREEN/YELLOW/RED)은 별도 의미를 갖도록 유지.
 *
 * CSS 변수 기반(hsl) 설계: shadcn/ui 호환 가능 + 추후 다크모드·테마 전환 대비.
 */
const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: "1rem",
        sm: "1.25rem",
        lg: "2rem",
      },
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        // ── Brand Primary: 신뢰의 블루 ──────────────────────
        primary: {
          50: "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB", // 메인 — 로고·주요 CTA
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#1E3A8A",
          950: "#172554",
          DEFAULT: "#2563EB",
          foreground: "#FFFFFF",
        },
        // ── Accent: 기회의 앰버 (CTA 보조·마감 임박) ───────
        accent: {
          50: "#FFFBEB",
          100: "#FEF3C7",
          200: "#FDE68A",
          300: "#FCD34D",
          400: "#FBBF24",
          500: "#F59E0B",
          600: "#D97706",
          700: "#B45309",
          DEFAULT: "#F59E0B",
          foreground: "#1F2937",
        },
        // ── Semantic ─────────────────────────────────────────
        success: {
          50: "#ECFDF5",
          100: "#D1FAE5",
          500: "#10B981",
          600: "#059669",
          DEFAULT: "#10B981",
          foreground: "#FFFFFF",
        },
        warning: {
          50: "#FFFBEB",
          500: "#F59E0B",
          600: "#D97706",
          DEFAULT: "#F59E0B",
          foreground: "#1F2937",
        },
        danger: {
          50: "#FEF2F2",
          100: "#FEE2E2",
          500: "#EF4444",
          600: "#DC2626",
          DEFAULT: "#EF4444",
          foreground: "#FFFFFF",
        },
        // ── 신호등(매칭 등급) — .cursorrules §3.3 유지 ──────
        traffic: {
          green: "#10B981",
          yellow: "#F59E0B",
          red: "#EF4444",
        },
        // ── 중립 그레이스케일 ───────────────────────────────
        surface: {
          DEFAULT: "#FFFFFF",
          muted: "#F8FAFC", // 섹션 배경
          subtle: "#F1F5F9",
          border: "#E2E8F0",
        },
        ink: {
          DEFAULT: "#0F172A", // 최대 대비 텍스트
          secondary: "#475569",
          tertiary: "#94A3B8",
          disabled: "#CBD5E1",
        },
      },
      fontFamily: {
        sans: [
          "Pretendard Variable",
          "Pretendard",
          "-apple-system",
          "BlinkMacSystemFont",
          "system-ui",
          "Segoe UI",
          "Roboto",
          "Noto Sans KR",
          "sans-serif",
        ],
      },
      fontSize: {
        // [type scale 1.250 - Major Third] + 라인하이트 조정
        // 사장님 친화 UI 원칙: 본문은 16px 이상, 숫자 강조는 큼직하게
        xs: ["0.75rem", { lineHeight: "1rem" }],
        sm: ["0.875rem", { lineHeight: "1.25rem" }],
        base: ["1rem", { lineHeight: "1.5rem" }], // 16/24
        lg: ["1.125rem", { lineHeight: "1.75rem" }],
        xl: ["1.25rem", { lineHeight: "1.75rem" }],
        "2xl": ["1.5rem", { lineHeight: "2rem" }], // 섹션 타이틀
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],
        "4xl": ["2.25rem", { lineHeight: "2.5rem" }], // 점수·금액 강조
        "5xl": ["3rem", { lineHeight: "1.1" }],
        "6xl": ["3.75rem", { lineHeight: "1.05" }], // 랜딩 히어로
      },
      spacing: {
        // 4px 스텝 기본 + 자주 쓰는 레이아웃 전용 키
        header: "4rem", // 64px — GNB 높이
        "header-mobile": "3.5rem", // 56px
        sidebar: "16rem", // 256px — 데스크탑 사이드바
        "sidebar-collapsed": "4.5rem",
        "bottom-tab": "4rem", // 모바일 하단 탭바
      },
      borderRadius: {
        xs: "0.25rem",
        sm: "0.375rem",
        md: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.25rem",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 3px 0 rgb(15 23 42 / 0.06)",
        "card-hover":
          "0 4px 6px -1px rgb(15 23 42 / 0.06), 0 2px 4px -2px rgb(15 23 42 / 0.04)",
        elevated:
          "0 10px 15px -3px rgb(15 23 42 / 0.08), 0 4px 6px -4px rgb(15 23 42 / 0.05)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in-left": {
          from: { transform: "translateX(-100%)" },
          to: { transform: "translateX(0)" },
        },
        // 토스트: 오른쪽에서 슬라이드 인
        "toast-in": {
          from: { opacity: "0", transform: "translateX(calc(100% + 1.5rem))" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        // 토스트: 페이드 아웃 (제거 전)
        "toast-out": {
          from: { opacity: "1", transform: "translateX(0)", maxHeight: "200px" },
          to: { opacity: "0", transform: "translateX(calc(100% + 1.5rem))", maxHeight: "0", marginBottom: "0" },
        },
        // 자동 닫힘 프로그레스 바
        "shrink-width": {
          from: { width: "100%" },
          to: { width: "0%" },
        },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out",
        "slide-in-left": "slide-in-left 220ms cubic-bezier(0.22, 1, 0.36, 1)",
        "toast-in": "toast-in 320ms cubic-bezier(0.22, 1, 0.36, 1)",
        "toast-out": "toast-out 280ms cubic-bezier(0.55, 0, 1, 0.45) forwards",
      },
    },
  },
  plugins: [],
};

export default config;
