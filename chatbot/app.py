"""Streamlit entrypoint — dark login + auth-gated navigation."""
import streamlit as st

from lib.api_client import fetch_me, login, register
from lib.session import (
    clear_session,
    get_token,
    get_user,
    is_admin,
    set_user,
)
from lib.theme import inject_theme

st.set_page_config(
    page_title="Handle — Maintainer's Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="auto",
)
inject_theme()


def _ensure_user_loaded() -> bool:
    """Loads /users/me if we have a token but no cached user."""
    if not get_token():
        return False
    if get_user() is None:
        u = fetch_me()
        if u is None:
            return False
        set_user(u)
    return True


# ---------------------------------------------------------------------------
# Login (rendered as a Streamlit "page" so st.navigation owns the routing)
# ---------------------------------------------------------------------------


def login_page() -> None:
    """Centered login + register tabs. No wrapper div — uses st.columns for centering."""
    # Center with three columns; middle column holds the card.
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("## 🤖 Handle")
        st.markdown(
            '<div class="mc-muted">Maintainer\'s Copilot — sign in to continue.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br/>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Log in", "Register"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", use_container_width=True)
                if submitted:
                    ok, msg = login(email, password)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_register:
            with st.form("register_form"):
                email = st.text_input(
                    "Email", key="reg_email", placeholder="you@example.com"
                )
                password = st.text_input(
                    "Password (≥ 8 chars)", type="password", key="reg_pw"
                )
                submitted = st.form_submit_button(
                    "Create account", use_container_width=True
                )
                if submitted:
                    ok, msg = register(email, password)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)


def home_page() -> None:
    """Post-login landing — quick links + logout."""
    u = get_user()
    st.markdown(f"## Welcome, {u['email']}")
    st.markdown(
        f'<span class="mc-badge memory">{u["role"].upper()}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("<br/><br/>", unsafe_allow_html=True)

    cards = [
        ("💬 Chat", "Talk to the copilot — classify issues, ask pandas questions, get summaries."),
        ("🧠 Memory", "Inspect facts the copilot has saved about you, delete what you don't want."),
        ("🔧 Widget admin", "Admins: create + edit embeddable widgets, manage allowed origins."),
    ]
    cols = st.columns(len(cards))
    for col, (title, desc) in zip(cols, cards, strict=True):
        with col:
            st.markdown(
                f'<div class="mc-card"><div class="mc-card-title">{title}</div>'
                f'<div class="mc-card-meta">{desc}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br/>", unsafe_allow_html=True)
    if st.button("Log out", type="secondary"):
        clear_session()
        st.rerun()


# ---------------------------------------------------------------------------
# Routing: st.navigation builds the sidebar from these page definitions only,
# so unauthenticated users see only "Sign in" — pages/*.py files don't leak.
# ---------------------------------------------------------------------------

if _ensure_user_loaded():
    pages: list = [
        st.Page(home_page, title="Home", icon="🏠", default=True),
        st.Page("pages/01_chat.py", title="Chat", icon="💬"),
        st.Page("pages/02_memory_inspector.py", title="Memory", icon="🧠"),
    ]
    if is_admin():
        pages.append(st.Page("pages/03_widget_admin.py", title="Widget admin", icon="🔧"))
    nav = st.navigation(pages)
    nav.run()
else:
    # Single-page nav so the sidebar shows nothing else.
    nav = st.navigation([st.Page(login_page, title="Sign in", icon="🔐", default=True)])
    nav.run()
