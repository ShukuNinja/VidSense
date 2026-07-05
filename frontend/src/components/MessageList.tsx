import { useEffect, useRef } from "react";
import type { Message } from "../types";
import { shortTime } from "../util";

function Bubble({ message }: { message: Message }) {
  const streaming = message.role === "assistant" && message.content === "";
  return (
    <div className={`msg ${message.role}`}>
      <div className="bubble">
        {streaming ? (
          <div className="searching">Searching the transcript…</div>
        ) : (
          <div className="content">{message.content}</div>
        )}
        {message.citations && message.citations.length > 0 && (
          <div className="citations">
            {message.citations.map((c) => (
              <span key={c.region_id} className="cite">
                ⏱ {shortTime(c.start_time)}–{shortTime(c.end_time)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MessageList({ messages }: { messages: Message[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="messages">
      {messages.length === 0 && (
        <p className="empty-hint center">Ask anything about this clip.</p>
      )}
      {messages.map((m) => (
        <Bubble key={m.id} message={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
