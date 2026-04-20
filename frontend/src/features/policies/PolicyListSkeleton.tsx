/**
 * 리스트 로딩 중 스켈레톤.
 */

export function PolicyListSkeleton({ count = 4 }: { count?: number }) {
  return (
    <ul className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <li
          key={i}
          className="rounded-xl border border-surface-border bg-surface p-5 shadow-card animate-pulse"
        >
          <div className="flex items-center gap-2">
            <div className="h-5 w-16 rounded bg-surface-subtle" />
            <div className="h-5 w-24 rounded bg-surface-subtle" />
          </div>
          <div className="mt-3 h-5 w-3/4 rounded bg-surface-subtle" />
          <div className="mt-4 flex gap-3">
            <div className="h-4 w-20 rounded bg-surface-subtle" />
            <div className="h-4 w-16 rounded bg-surface-subtle" />
            <div className="h-4 w-12 rounded bg-surface-subtle" />
          </div>
        </li>
      ))}
    </ul>
  );
}
