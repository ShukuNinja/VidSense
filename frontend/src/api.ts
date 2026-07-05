import { streamEvents } from "./sse";
import type { Chat, ChatDetail, StreamEvent } from "./types";

const BASE = "/api";

async function jsonOrThrow(res: Response) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // keep statusText
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function listChats(): Promise<Chat[]> {
  return jsonOrThrow(await fetch(`${BASE}/chats`));
}

export async function getChat(id: number): Promise<ChatDetail> {
  return jsonOrThrow(await fetch(`${BASE}/chats/${id}`));
}

export async function createChat(body: {
  url: string;
  start_time: string;
  end_time: string;
  title?: string;
}): Promise<Chat> {
  return jsonOrThrow(
    await fetch(`${BASE}/chats`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function renameChat(id: number, title: string): Promise<Chat> {
  return jsonOrThrow(
    await fetch(`${BASE}/chats/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }),
  );
}

export async function deleteChat(id: number): Promise<void> {
  await jsonOrThrow(await fetch(`${BASE}/chats/${id}`, { method: "DELETE" }));
}

export function streamIngest(
  id: number,
  onEvent: (data: any) => void,
  signal: AbortSignal,
): Promise<void> {
  return streamEvents(
    `${BASE}/chats/${id}/ingest/stream`,
    { method: "GET", signal },
    onEvent,
  );
}

export function streamMessage(
  id: number,
  content: string,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  return streamEvents(
    `${BASE}/chats/${id}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
      signal,
    },
    onEvent,
  );
}
