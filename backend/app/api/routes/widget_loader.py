"""Widget loader (/widget.js) and embed HTML wrapper (/widget/{id}/embed)."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import db_session_dep
from app.domain.exceptions import NotFoundError
from app.repositories.widgets import get_widget_by_widget_id

router = APIRouter()


LOADER_JS = r"""
// Handle widget loader. Host pastes:
//   <script src="<api-host>/widget.js" data-widget-id="wgt_xxx" async></script>
(function () {
  var current = document.currentScript;
  if (!current) {
    var scripts = document.querySelectorAll("script[data-widget-id]");
    current = scripts[scripts.length - 1];
  }
  if (!current) return;

  var widgetId = current.getAttribute("data-widget-id");
  if (!widgetId) return;

  var apiBase = new URL(current.src).origin;
  var hostOrigin = window.location.origin;

  var iframe = document.createElement("iframe");
  iframe.src =
    apiBase +
    "/widget/" +
    encodeURIComponent(widgetId) +
    "/embed?host_origin=" +
    encodeURIComponent(hostOrigin);
  iframe.style.position = "fixed";
  iframe.style.bottom = "0";
  iframe.style.right = "0";
  iframe.style.width = "420px";
  iframe.style.height = "80px";
  iframe.style.border = "0";
  iframe.style.zIndex = "2147483646";
  iframe.style.background = "transparent";
  iframe.style.colorScheme = "normal";
  iframe.setAttribute("title", "Handle chat widget");
  iframe.setAttribute("allow", "clipboard-write");

  document.body.appendChild(iframe);

  window.addEventListener("message", function (event) {
    if (event.source !== iframe.contentWindow) return;
    if (event.origin !== apiBase) return;
    if (!event.data || typeof event.data !== "object") return;
    if (event.data.type === "resize" && typeof event.data.height === "number") {
      iframe.style.height = Math.min(720, Math.max(80, event.data.height)) + "px";
    }
  });

  iframe.addEventListener("load", function () {
    iframe.contentWindow.postMessage(
      { type: "init", widget_id: widgetId, host_origin: hostOrigin },
      apiBase
    );
  });
})();
"""


@router.get("/widget.js", response_class=PlainTextResponse)
async def widget_loader() -> PlainTextResponse:
    """Returns the loader script with sensible cache headers."""
    return PlainTextResponse(
        LOADER_JS,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=300",
        },
    )


@router.get("/widget/{widget_id}/embed", response_class=HTMLResponse)
async def widget_embed(
    widget_id: str,
    request: Request,
    session: AsyncSession = Depends(db_session_dep),
) -> HTMLResponse:
    """Serves the iframe-content HTML with Content-Security-Policy frame-ancestors set
    from the widget's allowed_origins list.
    """
    widget = await get_widget_by_widget_id(session, widget_id)
    if widget is None:
        raise NotFoundError("widget not found")

    if widget.allowed_origins:
        frame_ancestors = " ".join(widget.allowed_origins)
    else:
        frame_ancestors = "'none'"

    host_origin = request.query_params.get("host_origin") or ""
    bundle_url = (
        f"http://localhost:8080/?widget_id={widget_id}&host_origin={host_origin}"
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="frame-ancestors {frame_ancestors}">
  <title>Handle widget</title>
  <style>html,body{{margin:0;background:transparent}}</style>
</head>
<body>
  <iframe src="{bundle_url}" style="border:0;width:100%;height:100vh;background:transparent;" title="Handle"></iframe>
</body>
</html>
"""

    return HTMLResponse(
        html,
        headers={
            "Content-Security-Policy": f"frame-ancestors {frame_ancestors}",
            "Cache-Control": "no-store",
        },
    )
