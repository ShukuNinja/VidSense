// Consume a Server-Sent Events stream from a fetch response. EventSource only
// supports GET, so we read the ReadableStream ourselves — which also lets us
// stream POST responses (the message endpoint).
import { authHeaders, handleUnauthorized } from "./session";

export async function streamEvents(
  url: string,
  init: RequestInit,
  onEvent: (data: any) => void,
): Promise<void> {
  const headers = { ...(init.headers || {}), ...authHeaders() };
  const res = await fetch(url, { ...init, headers });

  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Session expired. Please sign in again.");
  }

  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      const line = frame.split("\n").find((l) => l.startsWith("data: "));
      if (line) {
        onEvent(JSON.parse(line.slice(6)));
      }
    }
  }
}
