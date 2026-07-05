import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import NewChatModal from "./components/NewChatModal";
import ChatView from "./components/ChatView";
import Auth from "./components/Auth";
import { listChats, renameChat, deleteChat, me } from "./api";
import { getToken, clearToken, setUnauthorizedHandler } from "./session";
import type { Chat, ChatDetail, User } from "./types";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [showModal, setShowModal] = useState(false);

  // Restore session on load; log out on any 401.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setChats([]);
      setActiveId(null);
    });
    if (getToken()) {
      me()
        .then(setUser)
        .catch(() => {
          clearToken();
          setUser(null);
        })
        .finally(() => setChecking(false));
    } else {
      setChecking(false);
    }
  }, []);

  // Load this user's chats once authenticated.
  useEffect(() => {
    if (user) listChats().then(setChats).catch(() => setChats([]));
  }, [user]);

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
    const { messages, ...summary } = detail;
    void messages;
    upsertChat(summary as Chat);
  }

  async function handleRename(id: number, title: string) {
    upsertChat(await renameChat(id, title));
  }

  async function handleDelete(id: number) {
    await deleteChat(id);
    setChats((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  }

  function handleLogout() {
    clearToken();
    setUser(null);
    setChats([]);
    setActiveId(null);
  }

  if (checking) {
    return <div className="app center muted">Loading…</div>;
  }

  if (!user) {
    return <Auth onAuthed={setUser} />;
  }

  return (
    <div className="app">
      <Sidebar
        chats={chats}
        activeId={activeId}
        userEmail={user.email}
        onSelect={setActiveId}
        onNew={() => setShowModal(true)}
        onHome={() => setActiveId(null)}
        onRename={handleRename}
        onDelete={handleDelete}
        onLogout={handleLogout}
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
