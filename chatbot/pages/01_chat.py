"""Streamlit chat page — conversation sidebar, editable title, source chips, trace link."""
import time

import streamlit as st

from lib.api_client import (
    get_conversation_messages,
    list_conversations,
    rename_conversation,
    stream_chat,
)
from lib.session import get_token
from lib.theme import inject_theme, tool_pill

st.set_page_config(page_title="Chat — Handle", page_icon="💬", layout="wide")
inject_theme()

if not get_token():
    st.warning("Please log in via the main page first.")
    st.stop()

# ----- session state -----
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "conversation_id" not in st.session_state:
    st.session_state["conversation_id"] = None
if "conversation_title" not in st.session_state:
    st.session_state["conversation_title"] = ""
if "evidence" not in st.session_state:
    st.session_state["evidence"] = {
        "chunks": [],
        "entities": [],
        "classification": None,
        "sources": [],
    }


def _reset_chat(conversation_id: str | None = None, title: str = "") -> None:
    st.session_state["chat_history"] = []
    st.session_state["conversation_id"] = conversation_id
    st.session_state["conversation_title"] = title
    st.session_state["evidence"] = {
        "chunks": [],
        "entities": [],
        "classification": None,
        "sources": [],
    }


def _load_conversation(convo: dict) -> None:
    """Loads messages from the backend into the chat history."""
    _reset_chat(convo["id"], convo.get("title") or "")
    try:
        msgs = get_conversation_messages(convo["id"])
        st.session_state["chat_history"] = [
            {"role": m["role"], "content": m["content"], "ts": ""} for m in msgs
        ]
    except Exception:  # noqa: BLE001
        pass


# ----- sidebar: conversation list -----
with st.sidebar:
    st.markdown("#### 💬 Conversations")
    if st.button("＋ New chat", use_container_width=True):
        _reset_chat()
        st.rerun()

    try:
        convos = list_conversations()
    except Exception:  # noqa: BLE001
        convos = []

    if not convos:
        st.markdown(
            '<div class="mc-muted" style="margin-top:8px">No past chats yet — '
            "send your first message to start one.</div>",
            unsafe_allow_html=True,
        )
    else:
        for c in convos[:30]:
            label = c.get("title") or f'Chat · {c["created_at"][:16].replace("T", " ")}'
            is_current = c["id"] == st.session_state["conversation_id"]
            btn_label = ("● " if is_current else "  ") + label[:32]
            if st.button(btn_label, key=f'convo_{c["id"]}', use_container_width=True):
                _load_conversation(c)
                st.rerun()

# ----- header row: editable title + new chat -----
header_left, header_right = st.columns([5, 1])
with header_left:
    current_title = st.session_state["conversation_title"] or "Untitled chat"
    new_title = st.text_input(
        "Conversation title",
        value=current_title,
        key="title_input",
        label_visibility="collapsed",
    )
    if (
        new_title
        and new_title != current_title
        and st.session_state["conversation_id"] is not None
    ):
        if rename_conversation(st.session_state["conversation_id"], new_title):
            st.session_state["conversation_title"] = new_title
            st.toast("Title saved")

with header_right:
    if st.button("＋ New", use_container_width=True):
        _reset_chat()
        st.rerun()

# ----- single-column chat layout -----
chat_col = st.container()

# ============================================================
# CHAT COLUMN
# ============================================================
with chat_col:
    chat_container = st.container()
    with chat_container:
        for m in st.session_state["chat_history"]:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                meta_bits = []
                if m.get("ts"):
                    meta_bits.append(m["ts"])
                if m["role"] == "assistant" and m.get("sources"):
                    src_chips = " ".join(
                        f'<span class="mc-badge api">{s.rsplit("/", 1)[-1]}</span>'
                        for s in m["sources"][:5]
                    )
                    st.markdown(src_chips, unsafe_allow_html=True)
                if meta_bits:
                    st.markdown(
                        '<span class="mc-muted">' + " · ".join(meta_bits) + "</span>",
                        unsafe_allow_html=True,
                    )

user_input = st.chat_input("Ask the copilot — paste an issue, ask about pandas, etc.")

if user_input:
    ts_user = time.strftime("%H:%M")
    st.session_state["chat_history"].append(
        {"role": "user", "content": user_input, "ts": ts_user}
    )
    with chat_col:
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)
                st.markdown(
                    f'<span class="mc-muted">{ts_user}</span>', unsafe_allow_html=True
                )

    st.session_state["evidence"] = {
        "chunks": [],
        "entities": [],
        "classification": None,
        "sources": [],
    }

    with chat_col:
        with chat_container:
            with st.chat_message("assistant"):
                tools_box = st.empty()
                content_box = st.empty()
                running_text = ""
                tool_pills_html: list[str] = []
                sources_for_msg: list[str] = []

                for event in stream_chat(user_input, st.session_state["conversation_id"]):
                    etype = event.get("type")
                    if etype == "conversation_id":
                        st.session_state["conversation_id"] = event["conversation_id"]
                    elif etype == "tool_call":
                        name = event["name"]
                        tool_pills_html.append(tool_pill(name, "running"))
                        tools_box.markdown(
                            " ".join(tool_pills_html), unsafe_allow_html=True
                        )
                    elif etype == "tool_result":
                        name = event["name"]
                        ok = event.get("ok", True)
                        state = "ok" if ok else "fail"
                        for i in range(len(tool_pills_html) - 1, -1, -1):
                            if name in tool_pills_html[i] and "running" in tool_pills_html[i]:
                                tool_pills_html[i] = tool_pill(name, state)
                                break
                        tools_box.markdown(
                            " ".join(tool_pills_html), unsafe_allow_html=True
                        )
                        payload = event.get("payload") or {}
                        if not isinstance(payload, dict):
                            continue
                        if name == "rag_search":
                            chunks = payload.get("_chunks_for_snapshot") or []
                            if chunks:
                                st.session_state["evidence"]["chunks"] = chunks
                            srcs = payload.get("sources") or []
                            if srcs:
                                sources_for_msg = srcs
                                st.session_state["evidence"]["sources"] = srcs
                        elif name == "extract_entities":
                            ents = payload.get("entities") or []
                            if ents:
                                st.session_state["evidence"]["entities"] = ents
                        elif name == "classify_issue":
                            st.session_state["evidence"]["classification"] = {
                                "label": payload.get("label"),
                                "confidence": payload.get("confidence", 0.0),
                            }
                    elif etype == "token":
                        running_text += event.get("content", "")
                        content_box.markdown(running_text)
                    elif etype == "error":
                        content_box.error(event.get("message", "Unknown error"))
                        running_text = ""
                    elif etype == "done":
                        content_box.markdown(running_text or "(no response)")

                if running_text:
                    st.session_state["chat_history"].append(
                        {
                            "role": "assistant",
                            "content": running_text,
                            "ts": time.strftime("%H:%M"),
                            "sources": sources_for_msg,
                            "conversation_id": st.session_state["conversation_id"],
                        }
                    )
