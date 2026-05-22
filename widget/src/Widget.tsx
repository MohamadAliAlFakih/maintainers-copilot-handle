// Top-level widget — bubble + panel + postMessage glue.
import { useEffect, useState } from "react";
import { ChatPanel } from "./ChatPanel";
import { fetchConfig } from "./api";
import { onHostMessage, sendToHost } from "./postMessage";
import { applyTheme, positionClass } from "./theme";
import type { WidgetConfig } from "./types";

interface Props {
  widgetId: string;
  hostOrigin: string;
}

export function Widget({ widgetId, hostOrigin }: Props): JSX.Element | null {
  const [config, setConfig] = useState<WidgetConfig | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchConfig(widgetId)
      .then(setConfig)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [widgetId]);

  useEffect(() => {
    if (!config) return;
    const root = document.getElementById("root");
    if (root) applyTheme(root, config);
    sendToHost({ type: "ready" }, hostOrigin);
  }, [config, hostOrigin]);

  useEffect(() => {
    const off = onHostMessage(hostOrigin, (msg) => {
      if (msg.type === "auth") setToken(msg.token);
    });
    return off;
  }, [hostOrigin]);

  useEffect(() => {
    const height = open ? 680 : 80;
    sendToHost({ type: "resize", height }, hostOrigin);
  }, [open, hostOrigin]);

  if (error) {
    return (
      <div className="mc-fixed mc-bottom-4 mc-right-4 mc-bg-red-50 mc-p-3 mc-rounded mc-text-sm">
        Widget error: {error}
      </div>
    );
  }
  if (!config) return null;

  return (
    <div className={`mc-fixed mc-z-50 ${positionClass(config)}`}>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="mc-w-14 mc-h-14 mc-rounded-full mc-shadow-lg mc-text-white mc-text-2xl"
          style={{ backgroundColor: "var(--mc-primary)" }}
          aria-label="Open chat"
        >
          💬
        </button>
      )}
      {open && (
        <div
          className="mc-w-[380px] mc-h-[600px] mc-bg-white mc-rounded-xl mc-shadow-xl mc-flex mc-flex-col mc-overflow-hidden"
          style={{ border: "1px solid #e5e7eb" }}
        >
          <header
            className="mc-flex mc-items-center mc-justify-between mc-px-3 mc-py-2 mc-text-white"
            style={{ backgroundColor: "var(--mc-primary)" }}
          >
            <span className="mc-font-medium">Handle</span>
            <button
              onClick={() => setOpen(false)}
              className="mc-text-white"
              aria-label="Close chat"
            >
              ×
            </button>
          </header>
          <div className="mc-flex-1 mc-min-h-0">
            <ChatPanel greeting={config.greeting} token={token} />
          </div>
        </div>
      )}
    </div>
  );
}
