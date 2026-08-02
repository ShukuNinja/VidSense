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
    } catch {}

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

export interface AuthRegisterResponse {
  message: string;
  email: string;
  requires_verification: boolean;
  user: User;
}

export interface AuthVerifyResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export interface AuthResendResponse {
  message: string;
  email: string;
  requires_verification: boolean;
}

export async function register(email: string, password: string): Promise<AuthRegisterResponse> {
  return request("/auth/register", jsonPost({ email, password }));
}

export async function verifyOtp(
  email: string,
  otpCode: string
): Promise<AuthVerifyResponse> {
  return request(
    "/auth/verify-otp",
    jsonPost({
      email,
      otp_code: otpCode,
    })
  );
}

export async function resendOtp(email: string): Promise<AuthResendResponse> {
  return request("/auth/resend-otp", jsonPost({ email }));
}

export async function login(email: string, password: string): Promise<User> {
  const payload = await request("/auth/login", jsonPost({ email, password })) as AuthVerifyResponse;

  setToken(payload.access_token);

  return payload.user;
}

export function finishVerification(
  payload: AuthVerifyResponse
): User {
  setToken(payload.access_token);
  return payload.user;
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

export function streamIngest(
  id: number,
  onEvent: (data: any) => void,
  signal: AbortSignal
): Promise<void> {
  return streamEvents(
    `${BASE}/chats/${id}/ingest/stream`,
    { method: "GET", signal },
    onEvent
  );
}

export function streamMessage(
  id: number,
  content: string,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal
): Promise<void> {
  return streamEvents(
    `${BASE}/chats/${id}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
      signal,
    },
    onEvent
  );
}