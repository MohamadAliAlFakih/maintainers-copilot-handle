"""Streamlit chat page — streams from /chat/stream and renders incrementally."""
import streamlit as st

from lib.api_client import stream_chat
from lib.session import get_token

st.set_page_config(page_title="Chat — Handle", page_icon="💬", layout="wide")

if not get_token():
    st.warning("Please log in via the main page first.")
    st.stop()

st.title("Chat")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "conversation_id" not in st.session_state:
    st.session_state["conversation_id"] = None

# render existing history
for m in st.session_state["chat_history"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if user_input := st.chat_input("Ask the copilot..."):
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        running_text = ""
        tool_status: list[str] = []

        for event in stream_chat(user_input, st.session_state["conversation_id"]):
            etype = event.get("type")
            if etype == "conversation_id":
                # Stored so the next turn resumes the same Redis short-term context
                st.session_state["conversation_id"] = event["conversation_id"]
            elif etype == "tool_call":
                tool_status.append(f"🔧 calling `{event['name']}`")
                placeholder.markdown("\n".join(tool_status) + "\n\n" + running_text)
            elif etype == "tool_result":
                ok = "✅" if event.get("ok") else "❌"
                tool_status.append(f"{ok} `{event['name']}` returned")
                placeholder.markdown("\n".join(tool_status) + "\n\n" + running_text)
            elif etype == "token":
                running_text += event.get("content", "")
                placeholder.markdown("\n".join(tool_status) + "\n\n" + running_text)
            elif etype == "error":
                placeholder.error(event.get("message", "Unknown error"))
                running_text = ""
            elif etype == "done":
                placeholder.markdown(running_text or "(no response)")

        if running_text:
            st.session_state["chat_history"].append(
                {"role": "assistant", "content": running_text}
            )
