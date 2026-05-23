"""HTTP client utilities for talking to the backend API from Streamlit."""
import json
from typing import Any, Iterator

import httpx

from lib.session import clear_session, get_token, set_token

API_URL = "http://api:8000"


def _auth_headers() -> dict[str, str]:
    """Builds the Authorization header if a token is present."""
    tok = get_token()
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def login(email: str, password: str) -> tuple[bool, str]:
    """POST /auth/jwt/login. Returns (success, message)."""
    try:
        r = httpx.post(
            f"{API_URL}/auth/jwt/login",
            data={"username": email, "password": password},
            timeout=15.0,
        )
        if r.status_code == 200:
            set_token(r.json()["access_token"])
            return True, "Logged in"
        if r.status_code == 400:
            return False, "Invalid credentials"
        return False, f"Login failed: {r.status_code}"
    except httpx.HTTPError as e:
        return False, f"Network error: {e}"


def register(email: str, password: str) -> tuple[bool, str]:
    """POST /auth/register."""
    try:
        r = httpx.post(
            f"{API_URL}/auth/register",
            json={"email": email, "password": password},
            timeout=15.0,
        )
        if r.status_code in (200, 201):
            return True, "Registered. Please log in."
        return False, f"Registration failed: {r.status_code} {r.text[:200]}"
    except httpx.HTTPError as e:
        return False, f"Network error: {e}"


def fetch_me() -> dict | None:
    """GET /users/me. Returns user dict or None on 401."""
    r = httpx.get(f"{API_URL}/users/me", headers=_auth_headers(), timeout=15.0)
    if r.status_code == 401:
        clear_session()
        return None
    r.raise_for_status()
    return r.json()


def list_my_memory() -> list[dict]:
    """GET /memory/me — returns the user's facts."""
    r = httpx.get(f"{API_URL}/memory/me", headers=_auth_headers(), timeout=15.0)
    r.raise_for_status()
    return r.json()


def delete_my_memory(fact_id: str) -> bool:
    """DELETE /memory/me/{id}."""
    r = httpx.delete(
        f"{API_URL}/memory/me/{fact_id}", headers=_auth_headers(), timeout=15.0
    )
    return r.status_code == 204


def list_widgets() -> list[dict]:
    """GET /admin/widgets (admin only)."""
    r = httpx.get(f"{API_URL}/admin/widgets/", headers=_auth_headers(), timeout=15.0)
    r.raise_for_status()
    return r.json()


def create_widget(payload: dict) -> dict:
    """POST /admin/widgets."""
    r = httpx.post(
        f"{API_URL}/admin/widgets/", json=payload, headers=_auth_headers(), timeout=15.0
    )
    r.raise_for_status()
    return r.json()


def update_widget(widget_id: str, payload: dict) -> dict:
    """PATCH /admin/widgets/{id}."""
    r = httpx.patch(
        f"{API_URL}/admin/widgets/{widget_id}",
        json=payload,
        headers=_auth_headers(),
        timeout=15.0,
    )
    r.raise_for_status()
    return r.json()


def list_conversations() -> list[dict]:
    """GET /conversations/me — returns the user's conversations (most recent first)."""
    r = httpx.get(f"{API_URL}/conversations/me", headers=_auth_headers(), timeout=15.0)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()


def get_conversation_messages(conversation_id: str) -> list[dict]:
    """GET /conversations/{id}/messages — returns the messages for replay on resume."""
    r = httpx.get(
        f"{API_URL}/conversations/{conversation_id}/messages",
        headers=_auth_headers(), timeout=15.0,
    )
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()


def rename_conversation(conversation_id: str, title: str) -> bool:
    """PATCH /conversations/{id}/title."""
    r = httpx.patch(
        f"{API_URL}/conversations/{conversation_id}/title",
        json={"title": title},
        headers=_auth_headers(),
        timeout=15.0,
    )
    return r.status_code == 200


def get_snapshot(conversation_id: str, turn_index: int = 0) -> list[dict] | None:
    """GET /conversations/{id}/snapshots/{turn} — returns retrieved chunks for one turn."""
    r = httpx.get(
        f"{API_URL}/conversations/{conversation_id}/snapshots/{turn_index}",
        headers=_auth_headers(), timeout=15.0,
    )
    if r.status_code in (404, 204):
        return None
    r.raise_for_status()
    return r.json()


def get_eval_reports() -> dict:
    """GET /admin/evals/latest — returns the latest classification + RAG reports."""
    r = httpx.get(f"{API_URL}/admin/evals/latest", headers=_auth_headers(), timeout=30.0)
    if r.status_code == 404:
        return {}
    r.raise_for_status()
    return r.json()


def list_audit_log(limit: int = 100) -> list[dict]:
    """GET /admin/audit_log — returns recent audit entries."""
    r = httpx.get(
        f"{API_URL}/admin/audit_log",
        params={"limit": limit},
        headers=_auth_headers(), timeout=15.0,
    )
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()


def stream_chat(message: str, conversation_id: str | None = None) -> Iterator[dict[str, Any]]:
    """POST /chat/stream and yield SSE events as parsed dicts."""
    payload: dict[str, Any] = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id

    headers = {**_auth_headers(), "Accept": "text/event-stream"}
    with httpx.stream(
        "POST",
        f"{API_URL}/chat/stream",
        json=payload,
        headers=headers,
        timeout=httpx.Timeout(60.0, read=120.0),
    ) as response:
        if response.status_code != 200:
            yield {"type": "error", "message": f"HTTP {response.status_code}"}
            return

        buffer = ""
        for chunk in response.iter_text():
            buffer += chunk
            while "\n\n" in buffer:
                event, buffer = buffer.split("\n\n", 1)
                if event.startswith("data: "):
                    try:
                        yield json.loads(event[len("data: ") :])
                    except json.JSONDecodeError:
                        continue
