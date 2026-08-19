import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000"; // TODO: swap for a Vite proxy path if you set one up later

interface ApprovalSummary {
  id: string;
  task_id: string;
  level: "approve_plan" | "approve_action" | "notify" | "take_over";
  reason: string;
  created_at: number;
}

interface ApprovalDetail extends ApprovalSummary {
  context: Record<string, any>;
  resolution: string | null;
  resolution_notes: string | null;
}

export default function Approvals() {
  const [items, setItems] = useState<ApprovalSummary[]>([]);
  const [details, setDetails] = useState<Record<string, ApprovalDetail>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [outputs, setOutputs] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch(`${API_BASE}/approvals`)
      .then((res) => res.json())
      .then((data: ApprovalSummary[]) => {
        setItems(data);
        data.forEach((item) => fetchDetail(item.id));
      });
  }, []);

  function fetchDetail(id: string) {
    fetch(`${API_BASE}/approvals/${id}`)
      .then((res) => res.json())
      .then((data: ApprovalDetail) =>
        setDetails((prev) => ({ ...prev, [id]: data }))
      );
  }

  function resolve(id: string, decision: string, output?: string) {
    fetch(`${API_BASE}/approvals/${id}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision,
        notes: notes[id] ?? "",
        output: output ?? null,
      }),
    }).then(() => {
      setItems((prev) => prev.filter((i) => i.id !== id));
    });
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Approval Queue</h1>

      {items.length === 0 && (
        <p className="text-gray-600">No pending approvals.</p>
      )}

      {items.map((item) => {
        const detail = details[item.id];
        const isPlanLevel = item.level === "approve_plan";

        return (
          <div
            key={item.id}
            className="bg-white shadow p-4 rounded mb-4 border border-gray-200"
          >
            <h2 className="text-xl font-semibold mb-2">Task {item.task_id}</h2>

            <p className="text-gray-700 mb-2">
              <strong>Reason:</strong> {item.reason}
            </p>

            <pre className="bg-gray-100 p-3 rounded text-sm mb-3 overflow-auto">
              {detail ? JSON.stringify(detail.context, null, 2) : "Loading context..."}
            </pre>

            <textarea
              placeholder="Optional notes"
              className="w-full p-2 border rounded mb-3"
              value={notes[item.id] ?? ""}
              onChange={(e) => setNotes({ ...notes, [item.id]: e.target.value })}
            />

            {isPlanLevel ? (
              <div className="flex gap-3">
                <button
                  onClick={() => resolve(item.id, "approved")}
                  className="px-4 py-2 bg-green-600 text-white rounded"
                >
                  Approve
                </button>
                <button
                  onClick={() => resolve(item.id, "rejected")}
                  className="px-4 py-2 bg-red-600 text-white rounded"
                >
                  Reject
                </button>
              </div>
            ) : (
              <div>
                <textarea
                  placeholder="Output to use if taking over"
                  className="w-full p-2 border rounded mb-3"
                  value={outputs[item.id] ?? ""}
                  onChange={(e) =>
                    setOutputs({ ...outputs, [item.id]: e.target.value })
                  }
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => resolve(item.id, "accept")}
                    className="px-4 py-2 bg-green-600 text-white rounded"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => resolve(item.id, "take_over", outputs[item.id] ?? "")}
                    className="px-4 py-2 bg-blue-600 text-white rounded"
                  >
                    Take Over
                  </button>
                  <button
                    onClick={() => resolve(item.id, "abort")}
                    className="px-4 py-2 bg-red-600 text-white rounded"
                  >
                    Abort
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}