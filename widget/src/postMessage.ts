// Two-way postMessage between the iframe and the host page.
// All messages are scoped by event.origin matching the configured host_origin.

export interface InitMessage {
  type: "init";
  widget_id: string;
  host_origin: string;
}

export interface AuthMessage {
  type: "auth";
  token: string;
}

export interface ThemeOverrideMessage {
  type: "theme_override";
  primary_color?: string;
  position?: "bottom-right" | "bottom-left";
}

export type IncomingMessage = InitMessage | AuthMessage | ThemeOverrideMessage;

export interface ResizeMessage {
  type: "resize";
  height: number;
}

export interface ReadyMessage {
  type: "ready";
}

export type OutgoingMessage = ResizeMessage | ReadyMessage;

export function sendToHost(msg: OutgoingMessage, hostOrigin: string): void {
  if (!window.parent || window.parent === window) return;
  window.parent.postMessage(msg, hostOrigin);
}

export function onHostMessage(
  expectedOrigin: string,
  handler: (msg: IncomingMessage) => void
): () => void {
  function listener(event: MessageEvent): void {
    if (event.origin !== expectedOrigin) return;
    const data = event.data as IncomingMessage | undefined;
    if (!data || typeof data !== "object" || !("type" in data)) return;
    handler(data);
  }
  window.addEventListener("message", listener);
  return () => window.removeEventListener("message", listener);
}
