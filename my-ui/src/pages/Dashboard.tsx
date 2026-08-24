import { useEffect, useState } from "react";
import { useTaskEvents } from "../hooks/useTaskEvents";
import { ChevronDownIcon, RefreshIcon } from "../components/icons";
import Markdown from "../components/Markdown";
import { button, card, emptyState, statusBadgeClass } from "../lib/styles";

const API_BASE = "http://127.0.0.1:8001";

interface TaskHistoryItem {
  thread_id: string;
  status: string;
  final_output: string | null;
  writer_output: string | null;
  pending_approval_id: string | null;
  request: string;
}

type ExpandedView = "full" | "writer" | null;

export default function Dashboard() {
  const [history, setHistory] = useState<TaskHistoryItem[]>([]);
  const [expanded, setExpanded] = useState<Record<string, ExpandedView>>({});

  useEffect(() => {
    fetchHistory();
  }, []);

  useTaskEvents(() => fetchHistory());

  function fetchHistory() {
    fetch(`${API_BASE}/tasks`)
      .then((res) => res.json())
      .then((data: TaskHistoryItem[]) => setHistory([...data].reverse()))
      .catch((err) => console.error("failed to load task history", err));
  }

  function toggleView(threadId: string, view: ExpandedView) {
    setExpanded((prev) => ({ ...prev, [threadId]: prev[threadId] === view ? null : view }));
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Recent task requests and their status.
          </p>
        </div>
        <button type="button" onClick={fetchHistory} className={button.secondary}>
          <RefreshIcon className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {history.length === 0 && (
        <div className={emptyState}>No requests sent yet — try the Chat page.</div>
      )}

      <div className="space-y-3">
        {history.map((item) => {
          const view = expanded[item.thread_id] ?? null;

          return (
            <div key={item.thread_id} className={card}>
              <div className="mb-2 flex items-start justify-between gap-4">
                <p className="font-medium text-slate-900">{item.request}</p>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${statusBadgeClass(
                    item.status
                  )}`}
                >
                  {item.status}
                </span>
              </div>
              <p className="font-mono text-xs text-slate-400">{item.thread_id}</p>

              {item.final_output && view === null && (
                <p className="mt-2 line-clamp-3 text-sm text-slate-600">
                  {item.final_output}
                </p>
              )}

              {(item.final_output || item.writer_output) && (
                <div className="mt-2 flex flex-wrap items-center gap-4">
                  {item.final_output && (
                    <button
                      type="button"
                      onClick={() => toggleView(item.thread_id, "full")}
                      className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-500"
                    >
                      <ChevronDownIcon
                        className={`h-4 w-4 transition-transform ${view === "full" ? "rotate-180" : ""}`}
                      />
                      {view === "full" ? "Hide full result" : "View full result"}
                    </button>
                  )}
                  {item.writer_output && (
                    <button
                      type="button"
                      onClick={() => toggleView(item.thread_id, "writer")}
                      className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-500"
                    >
                      <ChevronDownIcon
                        className={`h-4 w-4 transition-transform ${view === "writer" ? "rotate-180" : ""}`}
                      />
                      {view === "writer" ? "Hide writer's answer" : "View writer's answer"}
                    </button>
                  )}
                </div>
              )}

              {view === "full" && item.final_output && (
                <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <Markdown>{item.final_output}</Markdown>
                </div>
              )}

              {view === "writer" && item.writer_output && (
                <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <Markdown>{item.writer_output}</Markdown>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
