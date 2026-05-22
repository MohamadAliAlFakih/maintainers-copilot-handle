"""Widget admin — admin-only widget CRUD + embed snippet generator."""
import streamlit as st

from lib.api_client import create_widget, list_widgets, update_widget
from lib.session import get_token, is_admin

st.set_page_config(page_title="Widget admin — Handle", page_icon="🧩", layout="wide")

if not get_token():
    st.warning("Please log in first.")
    st.stop()

if not is_admin():
    st.error("Admin role required.")
    st.stop()

st.title("Widget admin")

# --- create new ---
with st.expander("Create new widget"):
    with st.form("create_widget"):
        name = st.text_input("Name")
        origins = st.text_input(
            "Allowed origins (comma-separated)", value="http://localhost:9000"
        )
        greeting = st.text_input("Greeting", value="How can I help?")
        primary_color = st.color_picker("Primary color", value="#4F46E5")
        position = st.selectbox("Position", ["bottom-right", "bottom-left"])
        submitted = st.form_submit_button("Create")
        if submitted:
            payload = {
                "name": name,
                "allowed_origins": [o.strip() for o in origins.split(",") if o.strip()],
                "theme": {"primary_color": primary_color, "position": position},
                "greeting": greeting,
                "enabled_tools": [
                    "classify_issue",
                    "extract_entities",
                    "summarize_thread",
                    "rag_search",
                ],
            }
            try:
                w = create_widget(payload)
                st.success(f"Created widget {w['widget_id']}")
                st.rerun()
            except Exception as e:
                st.error(f"{e}")

# --- list + edit ---
st.subheader("Existing widgets")

try:
    widgets = list_widgets()
except Exception as e:
    st.error(f"{e}")
    st.stop()

for w in widgets:
    with st.expander(f"{w['name']} — `{w['widget_id']}`"):
        st.write(f"**Created:** {w['created_at']}")
        st.write(f"**Allowed origins:** {', '.join(w['allowed_origins']) or '(none)'}")
        st.write(f"**Greeting:** {w['greeting']}")
        st.write(f"**Theme:** {w['theme']}")

        snippet = (
            f'<script src="http://localhost:8000/widget.js" '
            f'data-widget-id="{w["widget_id"]}" async></script>'
        )
        st.code(snippet, language="html")
        st.caption("Copy this snippet into your host page.")

        with st.form(f"edit_{w['widget_id']}"):
            new_origins = st.text_input(
                "Allowed origins",
                value=",".join(w["allowed_origins"]),
                key=f"orig_{w['widget_id']}",
            )
            new_greeting = st.text_input(
                "Greeting", value=w["greeting"], key=f"greet_{w['widget_id']}"
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
                        },
                    )
                    st.success("Updated")
                    st.rerun()
                except Exception as e:
                    st.error(f"{e}")
