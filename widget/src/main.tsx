// Widget entrypoint — reads query params, mounts <Widget /> into #root.
import { createRoot } from "react-dom/client";
import { Widget } from "./Widget";
import "./index.css";

const params = new URLSearchParams(window.location.search);
const widgetId = params.get("widget_id");
const hostOrigin = params.get("host_origin") ?? document.referrer ?? "";

if (!widgetId) {
  document.body.innerHTML =
    "<div style='padding:1rem;font-family:sans-serif;color:#b91c1c'>Missing widget_id query param.</div>";
} else {
  const container = document.getElementById("root");
  if (container) {
    createRoot(container).render(<Widget widgetId={widgetId} hostOrigin={hostOrigin} />);
  }
}
