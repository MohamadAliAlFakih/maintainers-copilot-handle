// Backend API client — read config + stream chat.
import type { SseEvent, WidgetConfig } from "./types";

// The iframe is loaded by the backend (Plan 5b), so same-origin requests work.
function apiBase(): string {
  return window.location.origin;
}

export async function fetchConfig(widgetId: string): Promise<WidgetConfig> {
  const r = await fetch(`${apiBase()}/widgets/${widgetId}/config`);
  if (!r.ok) {
    throw new Error(`config fetch failed: ${r.status}`);
  }
  return r.json();
}

export async function* streamChat(
  message: string,
  token: string | null,
  conversationId: string | null
): AsyncGenerator<SseEvent> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const body = JSON.stringify({
    message,
    ...(conversationId ? { conversation_id: conversationId } : {}),
  });

  const r = await fetch(`${apiBase()}/chat/stream`, {
    method: "POST",
    headers,
    body,
  });

  if (!r.ok || !r.body) {
    yield { type: "error", message: `HTTP ${r.status}` };
    return;
  }

  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    while (buffer.includes("\n\n")) {
      const idx = buffer.indexOf("\n\n");
      const eventBlock = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      if (eventBlock.startsWith("data: ")) {
        try {
          yield JSON.parse(eventBlock.slice(6));
        } catch {
          // ignore malformed event blocks
        }
      }
    }
  }
}
