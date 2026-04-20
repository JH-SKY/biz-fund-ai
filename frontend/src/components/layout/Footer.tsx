/**
 * Footer — 데스크탑에서만 노출. 모바일은 하단 탭바가 역할을 대신.
 */

export function Footer() {
  return (
    <footer className="hidden lg:block border-t border-surface-border bg-surface-muted py-6">
      <div className="mx-auto max-w-[var(--content-max)] px-6 text-xs text-ink-tertiary flex items-center justify-between">
        <div>© {new Date().getFullYear()} Biz-Up. 사장님을 위한 AI 정책자금 비서.</div>
        <div className="flex items-center gap-4">
          <a href="#" className="hover:text-ink-secondary">
            이용약관
          </a>
          <a href="#" className="hover:text-ink-secondary">
            개인정보처리방침
          </a>
          <a href="#" className="hover:text-ink-secondary">
            고객센터
          </a>
        </div>
      </div>
    </footer>
  );
}
