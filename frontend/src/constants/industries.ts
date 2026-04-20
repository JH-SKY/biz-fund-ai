/**
 * 한국표준산업분류(KSIC) 대분류 — 랜딩·온보딩에서 사용.
 *
 * 참고: 온보딩에서는 검색형 UI(중분류까지)로 확장할 수 있도록,
 * 이 배열을 베이스로 별도 중분류 테이블을 추가 매핑 가능.
 */

import type { SelectOption } from "@/components/ui/select";

export interface IndustryItem {
  code: string; // KSIC 대분류 코드 (A~U)
  name: string;
  keywords: string[]; // 검색용 동의어
}

export const INDUSTRIES: IndustryItem[] = [
  { code: "A", name: "농업·임업·어업", keywords: ["농업", "임업", "어업", "농장", "축산"] },
  { code: "C", name: "제조업", keywords: ["제조", "생산", "공장", "가공"] },
  { code: "F", name: "건설업", keywords: ["건설", "시공", "토목", "건축"] },
  { code: "G", name: "도매·소매업", keywords: ["소매", "도매", "판매", "유통", "상점"] },
  { code: "H", name: "운수·창고업", keywords: ["운수", "물류", "창고", "배송", "택배"] },
  { code: "I", name: "숙박·음식점업", keywords: ["숙박", "음식점", "식당", "카페", "호텔", "펜션"] },
  { code: "J", name: "정보통신업", keywords: ["IT", "소프트웨어", "통신", "정보", "콘텐츠"] },
  { code: "K", name: "금융·보험업", keywords: ["금융", "보험", "은행", "투자"] },
  { code: "L", name: "부동산업", keywords: ["부동산", "임대", "중개"] },
  { code: "M", name: "전문·과학·기술 서비스업", keywords: ["연구", "기술", "컨설팅", "광고", "디자인"] },
  { code: "N", name: "사업시설관리·사업지원 서비스업", keywords: ["청소", "경비", "인력", "사무지원"] },
  { code: "P", name: "교육 서비스업", keywords: ["교육", "학원", "강의", "컴퓨터학원", "과외"] },
  { code: "Q", name: "보건업·사회복지 서비스업", keywords: ["의료", "병원", "보건", "복지", "요양"] },
  { code: "R", name: "예술·스포츠·여가 서비스업", keywords: ["예술", "스포츠", "헬스장", "공연", "레저"] },
  { code: "S", name: "협회·단체·수리·기타 개인 서비스업", keywords: ["미용실", "세탁", "수리", "협회"] },
];

export const INDUSTRY_OPTIONS: SelectOption[] = INDUSTRIES.map((i) => ({
  value: i.code,
  label: i.name,
}));

export function getIndustryLabel(code: string): string {
  return INDUSTRIES.find((i) => i.code === code)?.name ?? code;
}

/** 업종 검색(온보딩 자동완성용) */
export function searchIndustries(query: string): IndustryItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return INDUSTRIES;
  return INDUSTRIES.filter(
    (i) =>
      i.name.toLowerCase().includes(q) ||
      i.keywords.some((kw) => kw.toLowerCase().includes(q)) ||
      i.code.toLowerCase() === q
  );
}
