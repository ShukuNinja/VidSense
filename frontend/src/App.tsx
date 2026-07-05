import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import NewChatModal from "./components/NewChatModal";
import ChatView from "./components/ChatView";
import { listChats, renameChat, deleteChat } from "./api";
import type { Chat, ChatDetail } from "./types";

export default function App() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    listChats()
      .then(setChats)
      .catch(() => setChats([]));
  }, []);

  function upsertChat(chat: Chat) {
    setChats((prev) => {
      const exists = prev.some((c) => c.id === chat.id);
      if (exists) return prev.map((c) => (c.id === chat.id ? { ...c, ...chat } : c));
      return [chat, ...prev];
    });
  }

  function handleCreated(chat: Chat) {
    upsertChat(chat);
    setActiveId(chat.id);
    setShowModal(false);
  }

  function handleChatChanged(detail: ChatDetail) {
    // Sync sidebar entry (title / status may have changed after ingestion).
    const { messages, ...summary } = detail;
    void messages;
    upsertChat(summary as Chat);
  }

  async function handleRename(id: number, title: string) {
    const updated = await renameChat(id, title);
    upsertChat(updated);
  }

  async function handleDelete(id: number) {
    await deleteChat(id);
    setChats((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  }

  return (
    <div className="app">
      <Sidebar
        chats={chats}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={() => setShowModal(true)}
        onHome={() => setActiveId(null)}
        onRename={handleRename}
        onDelete={handleDelete}
      />

      <main className="main">
        {activeId === null ? (
          <div className="welcome">
            <h1>VidSense</h1>
            <p>Ask questions about any slice of a YouTube video.</p>
            <button onClick={() => setShowModal(true)}>+ New chat</button>
          </div>
        ) : (
          <ChatView
            key={activeId}
            chatId={activeId}
            onBack={() => setActiveId(null)}
            onChatChanged={handleChatChanged}
          />
        )}
      </main>

      {showModal && (
        <NewChatModal
          onCreated={handleCreated}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}
