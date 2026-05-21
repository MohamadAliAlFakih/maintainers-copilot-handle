"""Loads version-controlled prompt files; renders Jinja2 templates."""
from functools import lru_cache
from pathlib import Path

from jinja2 import Template


@lru_cache(maxsize=64)
def _load_template(prompts_dir_str: str, name: str) -> str:
    """Reads `prompts_dir/<name>.md` from disk. Cached after first read."""
    path = Path(prompts_dir_str) / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def load_prompt(prompts_dir: Path, name: str) -> str:
    """Returns the raw template text for prompt `<name>.md`."""
    return _load_template(str(prompts_dir), name)


def render_prompt(prompts_dir: Path, name: str, **vars: str) -> str:
    """Loads and renders the prompt with the given Jinja2 variables."""
    text = load_prompt(prompts_dir, name)
    return Template(text).render(**vars)
