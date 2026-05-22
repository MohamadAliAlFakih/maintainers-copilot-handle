// Applies theme values from the widget config as CSS variables on the root element.
import type { WidgetConfig } from "./types";

export function applyTheme(root: HTMLElement, config: WidgetConfig): void {
  const primary = config.theme.primary_color ?? "#4F46E5";
  root.style.setProperty("--mc-primary", primary);
}

export function positionClass(config: WidgetConfig): string {
  return config.theme.position === "bottom-left"
    ? "mc-bottom-4 mc-left-4"
    : "mc-bottom-4 mc-right-4";
}
