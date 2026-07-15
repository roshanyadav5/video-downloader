export default function MetadataSkeleton() {
  return (
    <div className="card animate-pulse rounded-2xl p-5 sm:p-6">
      <div className="flex gap-4">
        <div className="h-24 w-40 shrink-0 rounded-xl bg-surface-2" />
        <div className="flex-1 space-y-3 py-1">
          <div className="h-4 w-3/4 rounded bg-surface-2" />
          <div className="h-3 w-1/3 rounded bg-surface-2" />
          <div className="h-3 w-1/4 rounded bg-surface-2" />
        </div>
      </div>
      <div className="mt-6 space-y-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-14 rounded-xl bg-surface-2" />
        ))}
      </div>
    </div>
  );
}
