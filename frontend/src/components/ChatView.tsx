import { useEffect, useState } from "react";
import { getChat, streamMessage } from "../api";
import type { ChatDetail, Message, StreamEvent } from "../types";
import IngestProgress from "./IngestProgress";
import MessageList from "./MessageList";
import Composer from "./Composer";

interface Props {
  chatId: number;
  onChatChanged: (chat: ChatDetail) => void;
}

export default function ChatView({ chatId, onChatChanged }: Props) {
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

  if (loading) {
    return <div className="chat-view center muted">Loading…</div>;
  }

  if (error && !chat) {
    return <div className="chat-view center error-banner">{error}</div>;
  }

  if (!chat) return null;

  if (chat.status === "failed") {
    return (
      <div className="chat-view center">
        <div className="error-banner">
          <strong>Ingestion failed.</strong>
          <div>{chat.error}</div>
        </div>
      </div>
    );
  }

  if (chat.status !== "ready") {
    return (
      <div className="chat-view">
        <IngestProgress
          chatId={chatId}
          onReady={load}
          onFailed={(msg) => setChat({ ...chat, status: "failed", error: msg })}
        />
      </div>
    );
  }

  return (
    <div className="chat-view">
      <header className="chat-header">
        <span className="chat-header-title">{chat.title}</span>
        {chat.video_title && chat.video_title !== chat.title && (
          <span className="chat-header-sub">{chat.video_title}</span>
        )}
      </header>
      <MessageList messages={messages} />
      {error && <div className="inline-error">{error}</div>}
      <Composer disabled={sending} onSend={handleSend} />
    </div>
  );
}
