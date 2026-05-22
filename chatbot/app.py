"""Streamlit entrypoint — login screen + redirects to pages."""
import streamlit as st

from lib.api_client import fetch_me, login, register
from lib.session import (
    clear_session,
    get_token,
    get_user,
    set_user,
)

st.set_page_config(
    page_title="Handle — Maintainer's Copilot",
    page_icon="🤖",
    layout="wide",
)


def _ensure_user_loaded() -> bool:
    """Loads /users/me if we have a token but no cached user. Returns True if logged in."""
    if not get_token():
        return False
    if get_user() is None:
        u = fetch_me()
        if u is None:
            return False
        set_user(u)
    return True


def _render_login_form() -> None:
    """Shows the login + register tabs."""
    st.title("Handle — Maintainer's Copilot")
    st.write("Log in to continue.")
    tab_login, tab_register = st.tabs(["Log in", "Register"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
            if submitted:
                ok, msg = login(email, password)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with tab_register:
        with st.form("register_form"):
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password (>= 8 chars)", type="password", key="reg_pw")
            submitted = st.form_submit_button("Create account")
            if submitted:
                ok, msg = register(email, password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)


def _render_landing() -> None:
    """Shows the post-login landing page with navigation hints."""
    u = get_user()
    st.title(f"Welcome, {u['email']}")
    st.write(f"Role: **{u['role']}**")
    st.write("Use the sidebar to open Chat, Memory inspector, or (admin) Widget admin.")

    if st.button("Log out"):
        clear_session()
        st.rerun()


if _ensure_user_loaded():
    _render_landing()
else:
    _render_login_form()
