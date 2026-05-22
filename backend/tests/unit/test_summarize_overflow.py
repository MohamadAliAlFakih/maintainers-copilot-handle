"""Tests for the summarize-overflow helper."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.memory.short_term import summarize_overflow


@pytest.mark.asyncio
async def test_summarize_overflow_returns_summary_string():
    """summarize_overflow renders the prompt and returns the LLM's summary."""
    groq = MagicMock()
    groq.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="The user is working on JWT auth."))]
        )
    )

    messages_to_summarize = [
        {"role": "user", "content": "how do I add JWT?"},
        {"role": "assistant", "content": "Use OAuth2PasswordBearer..."},
    ]

    summary = await summarize_overflow(
        groq=groq,
        model="llama-3.1-8b-instant",
        prompts_dir=Path("/tmp/prompts"),
        messages=messages_to_summarize,
        _prompt_text="SUMMARY OF:\n{{ messages }}",
    )
    assert "JWT" in summary
