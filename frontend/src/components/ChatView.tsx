import { useEffect, useState } from "react";
import { getChat, streamMessage } from "../api";
import type { ChatDetail, Message, StreamEvent } from "../types";
import IngestProgress from "./IngestProgress";
import MessageList from "./MessageList";
import Composer from "./Composer";

interface Props {
  chatId: number;
  onBack: () => void;
  onChatChanged: (chat: ChatDetail) => void;
}

export default function ChatView({ chatId, onBack, onChatChanged }: Props) {
  const [chat, setChat] = useState<ChatDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    getChat(chatId)
      .then((c) => {
        setChat(c);
        setMessages(c.messages);
        setLoading(false);
        onChatChanged(c);
      })
      .catch((e) => {
        setError(String(e instanceof Error ? e.message : e));
        setLoading(false);
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatId]);

  async function handleSend(text: string) {
    if (sending) return;
    setSending(true);
    setError(null);

    const userId = -Date.now();
    const assistantId = userId - 1;
    const now = new Date().toISOString();
    setMessages((m) => [
      ...m,
      { id: userId, role: "user", content: text, is_followup: null, citations: null, created_at: now },
      { id: assistantId, role: "assistant", content: "", is_followup: null, citations: null, created_at: now },
    ]);

    const ctrl = new AbortController();
    try {
      await streamMessage(
        chatId,
        text,
        (ev: StreamEvent) => {
          if (ev.type === "token") {
            setMessages((m) =>
              m.map((x) =>
                x.id === assistantId ? { ...x, content: x.content + ev.text } : x,
              ),
            );
          } else if (ev.type === "done") {
            setMessages((m) =>
              m.map((x) =>
                x.id === assistantId
                  ? { ...x, content: ev.answer, citations: ev.citations, is_followup: ev.is_followup }
                  : x,
              ),
            );
          } else if (ev.type === "error") {
            setError(ev.message);
            setMessages((m) => m.filter((x) => x.id !== assistantId));
          }
        },
        ctrl.signal,
      );
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
      setMessages((m) => m.filter((x) => x.id !== assistantId));
    } finally {
      setSending(false);
    }
  }

  let body;
  if (loading) {
    body = <div className="center muted">Loading…</div>;
  } else if (error && !chat) {
    body = (
      <div className="center">
        <div className="error-banner">{error}</div>
      </div>
    );
  } else if (!chat) {
    body = null;
  } else if (chat.status === "failed") {
    body = (
      <div className="center">
        <div className="error-banner">
          <strong>Ingestion failed.</strong>
          <div>{chat.error}</div>
        </div>
      </div>
    );
  } else if (chat.status !== "ready") {
    body = (
      <IngestProgress
        chatId={chatId}
        onReady={load}
        onFailed={(msg) => setChat({ ...chat, status: "failed", error: msg })}
      />
    );
  } else {
    body = (
      <>
        <MessageList messages={messages} />
        {error && <div className="inline-error">{error}</div>}
        <Composer disabled={sending} onSend={handleSend} />
      </>
    );
  }

  return (
    <div className="chat-view">
      <header className="chat-topbar">
        <button className="back-btn" onClick={onBack} title="Back to home">
          ← Back
        </button>
        {chat && (
          <div className="topbar-titles">
            <span className="chat-header-title">{chat.title}</span>
            <span className="chat-header-sub">
              {chat.video_title && chat.video_title !== chat.title
                ? `${chat.video_title} · `
                : ""}
              clip {chat.start_time}–{chat.end_time}
            </span>
          </div>
        )}
      </header>
      <div className="chat-content">{body}</div>
    </div>
  );
}
