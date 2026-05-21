"""Tests for the prompt loader."""

from pathlib import Path

import pytest

from app.infra.prompts import load_prompt, render_prompt


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    """Creates a tmp prompts dir with a fake prompt."""
    p = tmp_path / "prompts"
    p.mkdir()
    (p / "greeting.md").write_text("Hello, {{ name }}!")
    return p


def test_load_prompt_reads_file(prompts_dir: Path):
    """load_prompt returns the raw template text."""
    from app.infra.prompts import _load_template

    _load_template.cache_clear()
    text = load_prompt(prompts_dir, "greeting")
    assert text == "Hello, {{ name }}!"


def test_load_prompt_cached_same_object(prompts_dir: Path):
    """Repeated load_prompt calls return the same string (cached)."""
    from app.infra.prompts import _load_template

    _load_template.cache_clear()
    a = load_prompt(prompts_dir, "greeting")
    b = load_prompt(prompts_dir, "greeting")
    assert a == b


def test_render_prompt_substitutes_variables(prompts_dir: Path):
    """render_prompt fills in jinja vars."""
    from app.infra.prompts import _load_template

    _load_template.cache_clear()
    out = render_prompt(prompts_dir, "greeting", name="Alice")
    assert out == "Hello, Alice!"


def test_load_prompt_missing_file_raises(prompts_dir: Path):
    """Missing prompt file raises FileNotFoundError."""
    from app.infra.prompts import _load_template

    _load_template.cache_clear()
    with pytest.raises(FileNotFoundError):
        load_prompt(prompts_dir, "nonexistent")
