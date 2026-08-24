import { useState } from "react";
import { SendIcon } from "../icons";
import { input as inputStyle } from "../../lib/styles";

interface AskMessage {
  role: "user" | "assistant";
  content: string;
}

export default function AskPanel({
  apiBase,
  approvalId,
}: {
  apiBase: string;
  approvalId: string;
}) {
  const [messages, setMessages] = useState<AskMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);

  function ask() {
    const q = question.trim();
    if (!q || asking) return;

    const nextMessages: AskMessage[] = [...messages, { role: "user", content: q }];
    setMessages(nextMessages);
    setQuestion("");
    setAsking(true);

    fetch(`${apiBase}/approvals/${approvalId}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, history: messages }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`ask failed (${res.status})`);
        return res.json();
      })
      .then((data: { answer: string }) => {
        setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
      })
      .catch((err) => {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `(couldn't get an answer: ${err.message})` },
        ]);
      })
      .finally(() => setAsking(false));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      ask();
    }
  }

  return (
    <div>
      {messages.length > 0 && (
        <div className="mb-3 max-h-56 space-y-2 overflow-auto rounded-lg border border-slate-200 bg-white p-3">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] whitespace-pre-wrap rounded-xl px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-100 text-slate-900"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {asking && <p className="text-xs text-slate-400">Thinking…</p>}
        </div>
      )}
      <div className="flex gap-2">
        <input
          className={inputStyle}
          placeholder="Ask the agent a clarifying question before deciding…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={asking}
        />
        <button
          type="button"
          onClick={ask}
          disabled={asking || !question.trim()}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <SendIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
