"""Tests for code-shaped entity matchers."""

import pytest

from app.infra.ner import build_ner_pipeline, extract_entities


@pytest.fixture(scope="module")
def nlp():
    """Loads spaCy + custom matchers once per test module."""
    return build_ner_pipeline()


def test_extracts_version_string(nlp):
    """Version strings like 0.115.4 are extracted as VERSION entities."""
    text = "broke after upgrading to 0.116.0 from 0.115.4"
    ents = extract_entities(nlp, text)
    versions = [e for e in ents if e["type"] == "VERSION"]
    assert any(e["text"] == "0.116.0" for e in versions)
    assert any(e["text"] == "0.115.4" for e in versions)


def test_extracts_issue_reference(nlp):
    """Issue refs like #4520 are extracted as ISSUE_REF entities."""
    text = "see #4520 and #100 for context"
    ents = extract_entities(nlp, text)
    refs = [e for e in ents if e["type"] == "ISSUE_REF"]
    assert any(e["text"] == "#4520" for e in refs)
    assert any(e["text"] == "#100" for e in refs)


def test_extracts_exception_class(nlp):
    """CamelCase 'Error' / 'Exception' names are extracted as EXCEPTION entities."""
    text = "raises TypeError and HTTPException when called"
    ents = extract_entities(nlp, text)
    excs = [e for e in ents if e["type"] == "EXCEPTION"]
    assert any(e["text"] == "TypeError" for e in excs)
    assert any(e["text"] == "HTTPException" for e in excs)


def test_extracts_decorator(nlp):
    """Python decorators @something are extracted as DECORATOR entities."""
    text = "use @app.get to register the route"
    ents = extract_entities(nlp, text)
    decs = [e for e in ents if e["type"] == "DECORATOR"]
    assert any(e["text"] == "@app.get" for e in decs)


def test_extracts_dotted_module_path(nlp):
    """Dotted lowercase paths like 'fastapi.security' are extracted as MODULE entities."""
    text = "import from fastapi.security and pydantic.fields"
    ents = extract_entities(nlp, text)
    mods = [e for e in ents if e["type"] == "MODULE"]
    assert any(e["text"] == "fastapi.security" for e in mods)
    assert any(e["text"] == "pydantic.fields" for e in mods)


def test_empty_text_returns_empty_list(nlp):
    """Empty input returns []."""
    assert extract_entities(nlp, "") == []
