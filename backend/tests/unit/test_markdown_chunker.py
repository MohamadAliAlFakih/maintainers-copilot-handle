"""Tests for the structure-aware markdown chunker."""

from app.services.rag.chunker import chunk_markdown

SAMPLE = """# Security

Top-level intro.

## OAuth2

OAuth2 paragraph.

```python
from fastapi import Depends

@app.get("/")
def handler(token: str = Depends(oauth2_scheme)):
    return token
```

### JWT

Sub-section about JWT.

More text here.

## Cookies

Cookie auth section.
"""


def test_chunks_split_on_h1_h2_h3():
    """Each header in the sample starts a new chunk."""
    chunks = chunk_markdown(SAMPLE, source_path="docs/security.md")
    headers_per_chunk = [c.section_headers for c in chunks]
    assert any("Security" in h for h in headers_per_chunk)
    assert any("OAuth2" in h for h in headers_per_chunk)
    assert any("Cookies" in h for h in headers_per_chunk)


def test_code_block_kept_intact():
    """Code fences are not split across chunks."""
    chunks = chunk_markdown(SAMPLE, source_path="docs/security.md")
    code_chunks = [c for c in chunks if "@app.get" in c.text]
    assert len(code_chunks) == 1
    text = code_chunks[0].text
    assert text.count("```") == 2


def test_chunk_metadata_includes_section_headers_and_path():
    """Each chunk records its header chain and source path."""
    chunks = chunk_markdown(SAMPLE, source_path="docs/security.md")
    for c in chunks:
        assert c.source_path == "docs/security.md"
        assert c.source_type == "doc"
        assert isinstance(c.section_headers, list)
        assert c.chunk_id


def test_chunk_ids_are_deterministic():
    """Running twice produces identical chunk_ids."""
    a = chunk_markdown(SAMPLE, source_path="docs/security.md")
    b = chunk_markdown(SAMPLE, source_path="docs/security.md")
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]


def test_tiny_section_merged_into_sibling():
    """A section under 100 tokens is folded into the next sibling under the same parent."""
    small = """# Top

## Tiny

short

## NotTiny

This section has a lot more content and definitely exceeds one hundred tokens
""" + ("blah " * 100)
    chunks = chunk_markdown(small, source_path="docs/x.md")
    standalone_tiny = [
        c
        for c in chunks
        if c.section_headers and c.section_headers[-1] == "Tiny" and "blah" not in c.text
    ]
    assert len(standalone_tiny) == 0
