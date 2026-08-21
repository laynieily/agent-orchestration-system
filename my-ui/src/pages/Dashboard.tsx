import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTaskEvents } from "../hooks/useTaskEvents";

const API_BASE = "http://127.0.0.1:8000";

interface TaskHistoryItem {
  thread_id: string;
  status: string;
  final_output: string | null;
  pending_approval_id: string | null;
  request: string;
}

export default function Dashboard() {
  const [history, setHistory] = useState<TaskHistoryItem[]>([]);

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

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <div className="flex gap-4 mb-8">
        <Link to="/chat" className="px-4 py-2 bg-blue-600 text-white rounded">
          Chat
        </Link>
        <Link to="/approvals" className="px-4 py-2 bg-blue-600 text-white rounded">
          Approvals
        </Link>
        <Link to="/escalations" className="px-4 py-2 bg-blue-600 text-white rounded">
          Escalations
        </Link>
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Request History</h2>
        <button onClick={fetchHistory} className="px-3 py-1 bg-gray-200 rounded text-sm">
          Refresh
        </button>
      </div>

      {history.length === 0 && <p className="text-gray-600">No requests sent yet.</p>}

      <div className="space-y-3">
        {history.map((item) => (
          <div key={item.thread_id} className="bg-white shadow p-4 rounded border border-gray-200">
            <div className="flex justify-between items-start mb-2">
              <p className="font-medium text-gray-800">{item.request}</p>
              <span
                className={
                  "text-xs px-2 py-1 rounded font-semibold " +
                  (item.status === "done"
                    ? "bg-green-100 text-green-700"
                    : item.status === "paused"
                    ? "bg-yellow-100 text-yellow-700"
                    : item.status === "aborted" || item.status === "plan_rejected"
                    ? "bg-red-100 text-red-700"
                    : "bg-gray-100 text-gray-700")
                }
              >
                {item.status}
              </span>
            </div>
            <p className="text-xs text-gray-500">thread: {item.thread_id}</p>
            {item.final_output && (
              <p className="text-sm text-gray-600 mt-2 line-clamp-3">{item.final_output}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}