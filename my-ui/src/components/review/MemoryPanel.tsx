export interface MemoryEntry {
  task_id: string;
  summary: string;
  success: boolean;
  distance: number;
}

export default function MemoryPanel({ memories }: { memories: MemoryEntry[] }) {
  if (memories.length === 0) {
    return <p className="text-sm text-slate-400">No similar past decisions found yet.</p>;
  }

  return (
    <div className="space-y-2">
      {memories.map((m) => (
        <div
          key={m.task_id}
          className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700"
        >
          <div className="mb-1 flex items-center justify-between gap-2">
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
                m.success
                  ? "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20"
                  : "bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20"
              }`}
            >
              {m.success ? "succeeded" : "failed"}
            </span>
            <span className="truncate font-mono text-xs text-slate-400">{m.task_id}</span>
          </div>
          <p className="line-clamp-3 whitespace-pre-line text-slate-600">{m.summary}</p>
        </div>
      ))}
    </div>
  );
}
