"""Memory inspector — user sees own facts; admin can also view any user."""
import httpx
import streamlit as st

from lib.api_client import API_URL, _auth_headers, delete_my_memory, list_my_memory
from lib.session import get_token, is_admin

st.set_page_config(page_title="Memory — Handle", page_icon="🧠", layout="wide")

if not get_token():
    st.warning("Please log in first.")
    st.stop()

st.title("Memory inspector")

# --- own memory ---
st.subheader("Your saved facts")

try:
    facts = list_my_memory()
except Exception as e:
    st.error(f"Could not load facts: {e}")
    st.stop()

if not facts:
    st.info("You have no saved facts yet. Tell the chatbot something about yourself to start.")
else:
    for f in facts:
        col1, col2 = st.columns([10, 1])
        with col1:
            st.markdown(f"- _{f['created_at']}_ — {f['fact_text']}")
        with col2:
            if st.button("🗑️", key=f"del_{f['id']}"):
                if delete_my_memory(f["id"]):
                    st.success("Deleted")
                    st.rerun()
                else:
                    st.error("Delete failed")

# --- admin view of any user ---
if is_admin():
    st.divider()
    st.subheader("Admin: view another user's memory")
    target_uid = st.text_input("User UUID")
    if target_uid and st.button("Load"):
        try:
            r = httpx.get(
                f"{API_URL}/memory/admin/{target_uid}",
                headers=_auth_headers(),
                timeout=15.0,
            )
            r.raise_for_status()
            for f in r.json():
                st.markdown(f"- _{f['created_at']}_ — {f['fact_text']}")
        except Exception as e:
            st.error(f"{e}")
