"""Streamlit session-state helpers for auth and user info."""
import streamlit as st

ACCESS_TOKEN_KEY = "access_token"
USER_KEY = "user"


def get_token() -> str | None:
    """Returns the stored JWT or None."""
    return st.session_state.get(ACCESS_TOKEN_KEY)


def set_token(token: str) -> None:
    """Saves the JWT in session state."""
    st.session_state[ACCESS_TOKEN_KEY] = token


def clear_session() -> None:
    """Logs the user out by clearing session state."""
    for key in (ACCESS_TOKEN_KEY, USER_KEY):
        if key in st.session_state:
            del st.session_state[key]


def get_user() -> dict | None:
    """Returns the cached current-user dict or None."""
    return st.session_state.get(USER_KEY)


def set_user(user: dict) -> None:
    """Saves the user dict in session state."""
    st.session_state[USER_KEY] = user


def is_admin() -> bool:
    """True iff the cached user has role=admin."""
    u = get_user()
    return bool(u and u.get("role") == "admin")
