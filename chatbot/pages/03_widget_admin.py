"""Widget admin — dark themed, card-based widget CRUD + embed snippet."""
import streamlit as st

from lib.api_client import create_widget, list_widgets, update_widget
from lib.session import get_token, is_admin
from lib.theme import badge, inject_theme

st.set_page_config(page_title="Widget admin — Handle", page_icon="🔧", layout="wide")
inject_theme()

if not get_token():
    st.warning("Please log in first.")
    st.stop()

if not is_admin():
    st.error("Admin role required.")
    st.stop()

st.markdown("### 🔧 Widget admin")
st.markdown(
    '<div class="mc-muted">Create + configure embeddable widgets. '
    "Each widget has its own allowed-origin list, theme, and greeting.</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr/>", unsafe_allow_html=True)

ALL_TOOLS = ["classify_issue", "extract_entities", "summarize_thread", "rag_search"]

# ----- create new -----
with st.expander("＋ Create new widget"):
    with st.form("create_widget"):
        name = st.text_input("Name", placeholder="My website widget")
        origins = st.text_input(
            "Allowed origins (comma-separated)",
            value="http://localhost:9000,http://localhost:8080",
        )
        greeting = st.text_input("Greeting", value="Hi! Ask me anything about pandas.")
        col_a, col_b = st.columns(2)
        with col_a:
            primary_color = st.color_picker("Primary color", value="#2F81F7")
        with col_b:
            position = st.selectbox("Position", ["bottom-right", "bottom-left"])
        tools_selected = st.multiselect(
            "Enabled tools",
            ALL_TOOLS,
            default=ALL_TOOLS,
        )
        if st.form_submit_button("Create widget"):
            try:
                w = create_widget(
                    {
                        "name": name,
                        "allowed_origins": [o.strip() for o in origins.split(",") if o.strip()],
                        "theme": {"primary_color": primary_color, "position": position},
                        "greeting": greeting,
                        "enabled_tools": tools_selected,
                    }
                )
                st.success(f"Created widget `{w['widget_id']}`")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"{e}")

st.markdown("#### Existing widgets")

try:
    widgets = list_widgets()
except Exception as e:  # noqa: BLE001
    st.error(f"{e}")
    st.stop()

if not widgets:
    st.markdown(
        '<div class="mc-card"><div class="mc-card-title">No widgets yet</div>'
        '<div class="mc-card-meta">Create one above to get an embed snippet.</div></div>',
        unsafe_allow_html=True,
    )

for w in widgets:
    origins_badges = " ".join(badge(o, "memory") for o in w["allowed_origins"]) or '<span class="mc-muted">(none)</span>'
    tools_badges = " ".join(badge(t, "api") for t in w.get("enabled_tools", []))
    st.markdown(
        f'<div class="mc-card">'
        f'<div class="mc-card-title">{w["name"]} '
        f'<span class="mc-mono mc-muted">· {w["widget_id"]}</span></div>'
        f'<div class="mc-card-meta">Created {w["created_at"]}</div>'
        f'<div style="margin:6px 0">Origins: {origins_badges}</div>'
        f'<div style="margin:6px 0">Tools: {tools_badges}</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    snippet = (
        f'<script src="http://localhost:8000/widget.js" '
        f'data-widget-id="{w["widget_id"]}" async></script>'
    )
    st.code(snippet, language="html")
    st.caption("Paste this into your host page's HTML — the loader handles the rest.")

    with st.expander(f"Edit `{w['widget_id']}`"):
        with st.form(f"edit_{w['widget_id']}"):
            new_origins = st.text_input(
                "Allowed origins",
                value=",".join(w["allowed_origins"]),
                key=f"orig_{w['widget_id']}",
            )
            new_greeting = st.text_input(
                "Greeting", value=w["greeting"], key=f"greet_{w['widget_id']}"
            )
            new_color = st.color_picker(
                "Primary color",
                value=w.get("theme", {}).get("primary_color", "#2F81F7"),
                key=f"color_{w['widget_id']}",
            )
            new_tools = st.multiselect(
                "Enabled tools",
                ALL_TOOLS,
                default=w.get("enabled_tools", ALL_TOOLS),
                key=f"tools_{w['widget_id']}",
            )
            if st.form_submit_button("Update"):
                try:
                    update_widget(
                        w["widget_id"],
                        {
                            "allowed_origins": [
                                o.strip() for o in new_origins.split(",") if o.strip()
                            ],
                            "greeting": new_greeting,
                            "theme": {
                                **w.get("theme", {}),
                                "primary_color": new_color,
                            },
                            "enabled_tools": new_tools,
                        },
                    )
                    st.toast("Updated")
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f"{e}")
