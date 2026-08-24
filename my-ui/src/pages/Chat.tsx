import { useEffect, useRef, useState } from "react";
import { SendIcon } from "../components/icons";
import { button, input } from "../lib/styles";

const API_BASE = "http://127.0.0.1:8001"; // TODO: swap for a Vite proxy path if you set one up later

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface TaskStatusResponse {
  thread_id: string;
  status: string;
  final_output: string | null;
  pending_approval_id: string | null;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    if (!inputValue.trim() || sending) return;

    const userMessage: Message = { role: "user", content: inputValue };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setSending(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage.content }),
      });

      const data: TaskStatusResponse = await res.json();

      const assistantMessage: Message = {
        role: "assistant",
        content:
          data.status === "paused"
            ? "This request needs human approval — check the Approvals page."
            : data.final_output ?? "(no output)",
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Chat
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Send a request to the orchestrator.
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-auto rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400">
            No messages yet — send a request to get started.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
                m.role === "user"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-100 text-slate-900"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="mt-4 flex gap-2">
        <input
          className={input}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your request..."
          disabled={sending}
        />
        <button
          type="button"
          onClick={sendMessage}
          disabled={sending || !inputValue.trim()}
          className={button.primary}
        >
          <SendIcon className="h-4 w-4" />
          {sending ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}
