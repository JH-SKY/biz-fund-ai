/**
 * KSIC 세세분류 샘플 (온보딩 검색).
 * 운영 시 정부/통계 표준 데이터로 확장·동기화하면 됩니다.
 */

export interface KsicDetailItem {
  /** 5자리 KSIC 코드 */
  code: string;
  /** 공식 산업명 */
  name: string;
  /** 검색 키워드 */
  keywords: string[];
}

export const KSIC_DETAILS: KsicDetailItem[] = [
  {
    code: "56111",
    name: "한식 일반 음식점업",
    keywords: ["한식", "음식점", "식당", "밥집", "한식당"],
  },
  {
    code: "56112",
    name: "중식 음식점업",
    keywords: ["중식", "중국집", "짜장면"],
  },
  {
    code: "56211",
    name: "커피 전문점",
    keywords: ["카페", "커피", "스타벅스", "베이커리"],
  },
  {
    code: "47112",
    name: "슈퍼마켓",
    keywords: ["슈퍼", "마트", "편의점", "소매"],
  },
  {
    code: "62010",
    name: "컴퓨터 프로그래밍 서비스업",
    keywords: ["IT", "소프트웨어", "개발", "SI", "프로그래밍"],
  },
  {
    code: "63120",
    name: "데이터베이스 및 온라인 정보 제공업",
    keywords: ["데이터", "SaaS", "클라우드", "인프라"],
  },
  {
    code: "70111",
    name: "부동산 임대업(주거용)",
    keywords: ["임대", "건물", "상가", "부동산"],
  },
];

export function searchKsicDetails(query: string): KsicDetailItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return KSIC_DETAILS;
  return KSIC_DETAILS.filter(
    (i) =>
      i.name.toLowerCase().includes(q) ||
      i.code.includes(q) ||
      i.keywords.some((kw) => kw.toLowerCase().includes(q))
  );
}
