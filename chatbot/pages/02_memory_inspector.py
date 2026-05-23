"""Memory inspector — dark themed, card layout."""
import httpx
import streamlit as st

from lib.api_client import API_URL, _auth_headers, delete_my_memory, list_my_memory
from lib.session import get_token, is_admin
from lib.theme import badge, inject_theme

st.set_page_config(page_title="Memory — Handle", page_icon="🧠", layout="wide")
inject_theme()

if not get_token():
    st.warning("Please log in first.")
    st.stop()

st.markdown("### 🧠 Memory inspector")
st.markdown(
    '<div class="mc-muted">Facts the copilot saved when you said '
    "&quot;remember that…&quot;.</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr/>", unsafe_allow_html=True)

# ----- own memory -----
try:
    facts = list_my_memory()
except Exception as e:
    st.error(f"Could not load facts: {e}")
    st.stop()

if not facts:
    st.markdown(
        '<div class="mc-card"><div class="mc-card-title">No saved facts yet</div>'
        '<div class="mc-card-meta">Tell the chatbot something durable about yourself '
        "(e.g. &quot;I work mostly with Polars&quot;) and it will appear here.</div></div>",
        unsafe_allow_html=True,
    )
else:
    for f in facts:
        col_main, col_del = st.columns([12, 1])
        with col_main:
            st.markdown(
                f'<div class="mc-card">'
                f'<div class="mc-card-meta">{f["created_at"]} {badge("MEMORY", "memory")}</div>'
                f'<div>{f["fact_text"]}</div>'
                "</div>",
                unsafe_allow_html=True,
            )
        with col_del:
            if st.button("🗑️", key=f"del_{f['id']}", help="Delete this fact"):
                if delete_my_memory(f["id"]):
                    st.toast("Deleted")
                    st.rerun()
                else:
                    st.error("Delete failed")

# ----- admin view -----
if is_admin():
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("#### 🔑 Admin: view another user's memory")
    target_uid = st.text_input("User UUID", placeholder="e.g. 4f8e5c20-…")
    if target_uid and st.button("Load", type="secondary"):
        try:
            r = httpx.get(
                f"{API_URL}/memory/admin/{target_uid}",
                headers=_auth_headers(),
                timeout=15.0,
            )
            r.raise_for_status()
            rows = r.json()
            if not rows:
                st.info("No facts for that user.")
            for f in rows:
                st.markdown(
                    f'<div class="mc-card">'
                    f'<div class="mc-card-meta">{f["created_at"]}</div>'
                    f'<div>{f["fact_text"]}</div></div>',
                    unsafe_allow_html=True,
                )
        except Exception as e:  # noqa: BLE001
            st.error(f"{e}")
