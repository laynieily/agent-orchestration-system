import { useEffect, useState } from "react";

interface EscalationEvent {
  id: string;
  task_id: string;
  reason: string;
  level: string;
  context: Record<string, any>;
  resolution: string | null;
  resolution_notes: string | null;
  created_at: number;
}

export default function Escalations() {
  const [items, setItems] = useState<EscalationEvent[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});

  // Fetch pending escalations
  useEffect(() => {
    fetch("/api/escalations/pending")
      .then((res) => res.json())
      .then((data) => setItems(data));
  }, []);

  function resolve(id: string, action: string, notesValue?: string) {
    fetch(`/api/escalations/${id}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        notes: notesValue ?? null,
      }),
    }).then(() => {
      setItems((prev) => prev.filter((i) => i.id !== id));
    });
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Escalations</h1>

      {items.length === 0 && (
        <p className="text-gray-600">No pending escalations.</p>
      )}

      {items.map((item) => (
        <div
          key={item.id}
          className="bg-white shadow p-4 rounded mb-4 border border-gray-200"
        >
          <h2 className="text-xl font-semibold mb-2">
            Task {item.task_id} — Level {item.level}
          </h2>

          <p className="text-gray-700 mb-2">
            <strong>Reason:</strong> {item.reason}
          </p>

          <pre className="bg-gray-100 p-3 rounded text-sm mb-3 overflow-auto">
            {JSON.stringify(item.context, null, 2)}
          </pre>

          <textarea
            placeholder="Optional notes (required for take_over)"
            className="w-full p-2 border rounded mb-3"
            value={notes[item.id] ?? ""}
            onChange={(e) =>
              setNotes({ ...notes, [item.id]: e.target.value })
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
              onClick={() => resolve(item.id, "abort")}
              className="px-4 py-2 bg-red-600 text-white rounded"
            >
              Abort
            </button>

            <button
              onClick={() =>
                resolve(item.id, "take_over", notes[item.id] ?? "")
              }
              className="px-4 py-2 bg-blue-600 text-white rounded"
            >
              Take Over
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
