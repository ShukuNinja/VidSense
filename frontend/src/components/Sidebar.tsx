import type { Chat, ChatStatus } from "../types";

const STATUS_LABEL: Record<ChatStatus, string> = {
  pending: "Queued",
  ingesting: "Processing",
  ready: "Ready",
  failed: "Failed",
};

function StatusDot({ status }: { status: ChatStatus }) {
  return <span className={`dot dot-${status}`} title={STATUS_LABEL[status]} />;
}

interface Props {
  chats: Chat[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  onHome: () => void;
  onRename: (id: number, title: string) => void;
  onDelete: (id: number) => void;
}

export default function Sidebar({
  chats,
  activeId,
  onSelect,
  onNew,
  onHome,
  onRename,
  onDelete,
}: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <button className="brand-btn" onClick={onHome} title="Home">
          VidSense
        </button>
        <button className="new-chat" onClick={onNew}>
          + New
        </button>
      </div>

      <div className="chat-list">
        {chats.length === 0 && <p className="empty-hint">No chats yet.</p>}
        {chats.map((c) => (
          <div
            key={c.id}
            className={`chat-item ${c.id === activeId ? "active" : ""}`}
            onClick={() => onSelect(c.id)}
          >
            <StatusDot status={c.status} />
            <span className="chat-title">{c.title}</span>
            <span className="chat-actions">
              <button
                title="Rename"
                onClick={(e) => {
                  e.stopPropagation();
                  const t = window.prompt("Rename chat", c.title);
                  if (t && t.trim()) onRename(c.id, t.trim());
                }}
              >
                ✎
              </button>
              <button
                title="Delete"
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm("Delete this chat?")) onDelete(c.id);
                }}
              >
                ✕
              </button>
            </span>
          </div>
        ))}
      </div>
    </aside>
  );
}
