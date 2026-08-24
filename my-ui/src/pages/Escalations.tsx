import { useEffect, useState } from "react";
import { RefreshIcon } from "../components/icons";
import { button, card, emptyState } from "../lib/styles";

const API_BASE = "http://127.0.0.1:8001";

interface ApprovalDetail {
  id: string;
  task_id: string;
  level: string;
  reason: string;
  created_at: number;
  context: Record<string, any>;
  resolution: string | null;
  resolution_notes: string;
  resolved_at: number | null;
}

const RESOLUTION_OPTIONS = [
  { label: "All", value: "" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
  { label: "Accepted", value: "accept" },
  { label: "Took Over", value: "take_over" },
  { label: "Aborted", value: "abort" },
];

export default function Escalations() {
  const [items, setItems] = useState<ApprovalDetail[]>([]);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    fetchHistory();
  }, [filter]);

  function fetchHistory() {
    const url = filter
      ? `${API_BASE}/approvals/history?resolution=${filter}`
      : `${API_BASE}/approvals/history`;

    fetch(url)
      .then((res) => res.json())
      .then((data: ApprovalDetail[]) => setItems(data))
      .catch((err) => console.error("failed to load escalation history", err));
  }

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Escalation History
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Past decisions on escalated plans and subtasks.
          </p>
        </div>
        <button type="button" onClick={fetchHistory} className={button.secondary}>
          <RefreshIcon className="h-4 w-4" />
          Refresh
        </button>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {RESOLUTION_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => setFilter(opt.value)}
            className={filter === opt.value ? button.primary : button.secondary}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {items.length === 0 && (
        <div className={emptyState}>No resolved escalations yet.</div>
      )}

      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.id} className={card}>
            <div className="mb-3 flex items-center justify-between gap-4">
              <h2 className="text-lg font-semibold text-slate-900">
                Task {item.task_id}
              </h2>
              <div className="flex gap-2">
                <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 ring-1 ring-inset ring-slate-500/15">
                  {item.level}
                </span>
                <span className="shrink-0 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-600/20">
                  {item.resolution}
                </span>
              </div>
            </div>

            <p className="mb-2 text-sm text-slate-700">
              <span className="font-medium text-slate-900">Reason: </span>
              {item.reason}
            </p>

            {item.resolution_notes && (
              <p className="mb-3 text-sm text-slate-700">
                <span className="font-medium text-slate-900">Notes: </span>
                {item.resolution_notes}
              </p>
            )}

            <p className="mb-3 text-xs text-slate-500">
              Resolved{" "}
              {item.resolved_at
                ? new Date(item.resolved_at * 1000).toLocaleString()
                : "—"}
            </p>

            <pre className="overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
              {JSON.stringify(item.context, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}