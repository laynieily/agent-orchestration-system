import { useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  async function sendMessage() {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: input }),
    });

    const data = await res.json();

    const assistantMessage: Message = {
      role: "assistant",
      content: data.reply,
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setInput("");
  }

  return (
    <div className="flex flex-col h-full">
      <h1 className="text-2xl font-bold mb-4">Chat</h1>

      <div className="flex-1 overflow-auto bg-white p-4 rounded shadow">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`mb-3 p-3 rounded ${
              m.role === "user"
                ? "bg-blue-100 text-blue-900"
                : "bg-gray-100 text-gray-900"
            }`}
          >
            {m.content}
          </div>
        ))}
      </div>

      <div className="mt-4 flex gap-2">
        <input
          className="flex-1 p-2 border rounded"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your request..."
        />
        <button
          onClick={sendMessage}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          Send
        </button>
      </div>
    </div>
  );
}
