import { streamEvents } from "./sse";
import { authHeaders, handleUnauthorized, setToken } from "./session";
import type { Chat, ChatDetail, StreamEvent, User } from "./types";

const BASE = "/api";

async function request(path: string, options: RequestInit = {}): Promise<any> {
  const headers = { ...(options.headers || {}), ...authHeaders() };
  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Session expired. Please sign in again.");
  }
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
  return res.status === 204 ? null : res.json();
}

function jsonPost(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

// ---- auth ----
export async function register(email: string, password: string): Promise<User> {
  const r = await request("/auth/register", jsonPost({ email, password }));
  setToken(r.access_token);
  return r.user;
}

export async function login(email: string, password: string): Promise<User> {
  const r = await request("/auth/login", jsonPost({ email, password }));
  setToken(r.access_token);
  return r.user;
}

export function me(): Promise<User> {
  return request("/auth/me");
}

// ---- chats ----
export function listChats(): Promise<Chat[]> {
  return request("/chats");
}

export function getChat(id: number): Promise<ChatDetail> {
  return request(`/chats/${id}`);
}

export function createChat(body: {
  url: string;
  start_time: string;
  end_time: string;
  title?: string;
}): Promise<Chat> {
  return request("/chats", jsonPost(body));
}

export function renameChat(id: number, title: string): Promise<Chat> {
  return request(`/chats/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export function deleteChat(id: number): Promise<void> {
  return request(`/chats/${id}`, { method: "DELETE" });
}

// ---- streams (auth header injected inside streamEvents) ----
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
