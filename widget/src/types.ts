// Shared types for the widget.
export interface WidgetConfig {
  widget_id: string;
  theme: { primary_color?: string; position?: "bottom-right" | "bottom-left" };
  greeting: string;
  enabled_tools: string[];
}

export type SseEventType = "tool_call" | "tool_result" | "token" | "error" | "done";

export interface SseEvent {
  type: SseEventType;
  name?: string;
  ok?: boolean;
  content?: string;
  message?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
