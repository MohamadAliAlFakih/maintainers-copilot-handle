// Chat panel content — message list + input + streaming.
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

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, toolStatus]);

  async function handleSend(): Promise<void> {
    if (!input.trim() || streaming) return;
    const userMsg: ChatMessage = { role: "user", content: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");
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
        setToolStatus((s) => [...s, `🔧 ${ev.name}`]);
      } else if (ev.type === "tool_result" && ev.name) {
        setToolStatus((s) => [...s, `${ev.ok ? "✅" : "❌"} ${ev.name}`]);
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
    <div className="mc-flex mc-flex-col mc-h-full">
      <div className="mc-flex-1 mc-overflow-y-auto mc-p-3 mc-space-y-2">
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "mc-ml-auto mc-bg-gray-100 mc-rounded-lg mc-p-2 mc-max-w-[85%]"
                : "mc-mr-auto mc-bg-blue-50 mc-rounded-lg mc-p-2 mc-max-w-[85%]"
            }
          >
            {m.content}
          </div>
        ))}
        {toolStatus.length > 0 && (
          <div className="mc-text-xs mc-text-gray-500 mc-italic">{toolStatus.join(" · ")}</div>
        )}
        <div ref={endRef} />
      </div>
      <div className="mc-p-2 mc-border-t mc-flex mc-gap-2">
        <input
          className="mc-flex-1 mc-border mc-rounded mc-px-2 mc-py-1 mc-text-sm"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask the copilot..."
          disabled={streaming}
        />
        <button
          className="mc-px-3 mc-py-1 mc-rounded mc-text-white mc-text-sm"
          style={{ backgroundColor: "var(--mc-primary)" }}
          onClick={handleSend}
          disabled={streaming || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
