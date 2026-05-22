// Chat panel content - message list + input + streaming.
import { useEffect, useRef, useState } from "react";
import { streamChat } from "./api";
import type { ChatMessage, SseEvent } from "./types";

interface Props {
  greeting: string;
  token: string | null;
}

export function ChatPanel({ greeting, token }: Props): JSX.Element {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: greeting },
  ]);
  const [input, setInput] = useState("");
  const [conversationId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [toolStatus, setToolStatus] = useState<string[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, toolStatus]);

  function autoGrow(el: HTMLTextAreaElement | null): void {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(120, el.scrollHeight) + "px";
  }

  async function handleSend(): Promise<void> {
    if (!input.trim() || streaming) return;
    const userMsg: ChatMessage = { role: "user", content: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    if (inputRef.current) inputRef.current.style.height = "auto";
    setStreaming(true);
    setToolStatus([]);

    let assistant = "";
    try {
      for await (const ev of streamChat(userMsg.content, token, conversationId)) {
        handleEvent(ev);
      }
    } catch (e) {
      const err = e instanceof Error ? e.message : String(e);
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${err}` }]);
    } finally {
      setStreaming(false);
    }

    function handleEvent(ev: SseEvent): void {
      if (ev.type === "tool_call" && ev.name) {
        setToolStatus((s) => [...s, `${ev.name}`]);
      } else if (ev.type === "tool_result" && ev.name) {
        setToolStatus((s) => s.map((x) => (x === ev.name ? `${ev.name} ${ev.ok ? "✓" : "✗"}` : x)));
      } else if (ev.type === "token" && ev.content) {
        assistant += ev.content;
        setMessages((m) => {
          const last = m[m.length - 1];
          if (last && last.role === "assistant" && m.length > 1 && last.content !== greeting) {
            return [...m.slice(0, -1), { ...last, content: assistant }];
          }
          return [...m, { role: "assistant", content: assistant }];
        });
      } else if (ev.type === "error" && ev.message) {
        setMessages((m) => [...m, { role: "assistant", content: `Error: ${ev.message}` }]);
      }
    }
  }

  return (
    <div className="mc-flex mc-flex-col mc-h-full mc-bg-white">
      <div className="mc-flex-1 mc-overflow-y-auto mc-px-4 mc-py-5 mc-space-y-4">
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="mc-flex mc-justify-end">
              <div
                className="mc-px-4 mc-py-2.5 mc-rounded-2xl mc-text-sm mc-text-white mc-max-w-[80%] mc-whitespace-pre-wrap mc-shadow-sm"
                style={{ backgroundColor: "var(--mc-primary)" }}
              >
                {m.content}
              </div>
            </div>
          ) : (
            <div key={i} className="mc-flex mc-justify-start">
              <div className="mc-px-4 mc-py-2.5 mc-rounded-2xl mc-bg-gray-100 mc-text-sm mc-text-gray-800 mc-max-w-[85%] mc-whitespace-pre-wrap">
                {m.content}
              </div>
            </div>
          )
        )}
        {streaming && (
          <div className="mc-flex mc-justify-start">
            <div className="mc-px-4 mc-py-3 mc-rounded-2xl mc-bg-gray-100 mc-flex mc-gap-1">
              <span className="mc-w-2 mc-h-2 mc-rounded-full mc-bg-gray-400 mc-animate-pulse" />
              <span
                className="mc-w-2 mc-h-2 mc-rounded-full mc-bg-gray-400 mc-animate-pulse"
                style={{ animationDelay: "120ms" }}
              />
              <span
                className="mc-w-2 mc-h-2 mc-rounded-full mc-bg-gray-400 mc-animate-pulse"
                style={{ animationDelay: "240ms" }}
              />
            </div>
          </div>
        )}
        {toolStatus.length > 0 && (
          <div className="mc-flex mc-flex-wrap mc-gap-1.5 mc-text-xs">
            {toolStatus.map((s, i) => (
              <span
                key={i}
                className="mc-inline-flex mc-items-center mc-px-2 mc-py-0.5 mc-rounded-full mc-bg-gray-50 mc-text-gray-600 mc-border mc-border-gray-200"
              >
                {s}
              </span>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>
      <div className="mc-border-t mc-border-gray-100 mc-px-3 mc-py-3">
        <div
          className="mc-flex mc-items-end mc-gap-2 mc-bg-gray-50 mc-rounded-2xl mc-border mc-border-gray-200 mc-px-3 mc-py-2 focus-within:mc-border-gray-400 mc-transition-colors"
        >
          <textarea
            ref={inputRef}
            rows={1}
            className="mc-flex-1 mc-bg-transparent mc-outline-none mc-resize-none mc-text-sm mc-text-gray-900 placeholder:mc-text-gray-400 mc-leading-5"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              autoGrow(e.currentTarget);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Message Handle..."
            disabled={streaming}
          />
          <button
            onClick={handleSend}
            disabled={streaming || !input.trim()}
            className="mc-flex mc-items-center mc-justify-center mc-w-8 mc-h-8 mc-rounded-full mc-text-white mc-transition-opacity disabled:mc-opacity-30"
            style={{ backgroundColor: "var(--mc-primary)" }}
            aria-label="Send"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </div>
        <div className="mc-text-[10px] mc-text-gray-400 mc-mt-1.5 mc-text-center">
          Handle may produce inaccurate info — verify against the docs.
        </div>
      </div>
    </div>
  );
}