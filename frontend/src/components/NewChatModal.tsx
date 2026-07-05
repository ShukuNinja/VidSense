import { useEffect, useState } from "react";
import { createChat } from "../api";
import { isYouTubeUrl, isValidRange, isTimestamp } from "../util";
import type { Chat } from "../types";

interface Props {
  onCreated: (chat: Chat) => void;
  onClose: () => void;
}

export default function NewChatModal({ onCreated, onClose }: Props) {
  const [url, setUrl] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function validate(): string | null {
    if (!isYouTubeUrl(url)) return "Enter a valid YouTube URL.";
    if (!isTimestamp(start)) return "Start time must be HH:MM:SS.";
    if (!isTimestamp(end)) return "End time must be HH:MM:SS.";
    if (!isValidRange(start, end)) return "Start time must be before end time.";
    return null;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const chat = await createChat({ url, start_time: start, end_time: end });
      onCreated(chat);
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>New chat from a clip</h2>
        <p className="modal-sub">
          Pick a YouTube video and the time range you want to learn about.
        </p>
        <form onSubmit={submit}>
          <label>
            YouTube URL
            <input
              type="text"
              value={url}
              placeholder="https://youtu.be/…"
              onChange={(e) => setUrl(e.target.value)}
              autoFocus
            />
          </label>
          <div className="row">
            <label>
              Start (HH:MM:SS)
              <input
                type="text"
                value={start}
                placeholder="00:10:00"
                onChange={(e) => setStart(e.target.value)}
              />
            </label>
            <label>
              End (HH:MM:SS)
              <input
                type="text"
                value={end}
                placeholder="00:10:45"
                onChange={(e) => setEnd(e.target.value)}
              />
            </label>
          </div>

          {error && <p className="form-error">{error}</p>}

          <div className="modal-actions">
            <button type="button" className="ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" disabled={submitting}>
              {submitting ? "Creating…" : "Create chat"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
