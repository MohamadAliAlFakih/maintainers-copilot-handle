"""NER pipeline: spaCy en_core_web_sm + regex matchers for code-shaped entities."""

import re
from typing import Any

import spacy
from spacy.language import Language

# Regex patterns for code-shaped entities not covered well by general NER
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Version like 0.115.4 or 1.2.3
    ("VERSION", re.compile(r"\b\d+\.\d+(?:\.\d+)?(?:[ab]\d+)?\b")),
    # Issue/PR ref like #4520
    ("ISSUE_REF", re.compile(r"#\d{1,6}\b")),
    # CamelCase Error/Exception class names (must end in Error or Exception)
    ("EXCEPTION", re.compile(r"\b[A-Z][a-zA-Z0-9]*(?:Error|Exception)\b")),
    # Decorator @something or @app.get
    ("DECORATOR", re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*")),
    # Lowercase dotted module path: fastapi.security, pydantic.fields
    ("MODULE", re.compile(r"\b[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+\b")),
]


def build_ner_pipeline() -> Language:
    """Loads spaCy and disables components we don't need (parser, tagger) for speed."""
    nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
    return nlp


def _regex_entities(text: str) -> list[dict[str, Any]]:
    """Runs the custom regex matchers; returns a list of entity dicts."""
    out = []
    for ent_type, pat in _PATTERNS:
        for m in pat.finditer(text):
            out.append({"text": m.group(0), "type": ent_type, "start": m.start(), "end": m.end()})
    return out


def _spacy_entities(nlp: Language, text: str) -> list[dict[str, Any]]:
    """Runs spaCy NER; returns PERSON/ORG/etc. as a list of dicts."""
    doc = nlp(text)
    return [
        {"text": ent.text, "type": ent.label_, "start": ent.start_char, "end": ent.end_char}
        for ent in doc.ents
    ]


def _dedupe(ents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drops overlapping entities, preferring the more specific (custom-regex) match."""
    ents = sorted(
        ents,
        key=lambda e: (-(e["end"] - e["start"]), e["type"] in {"CARDINAL", "DATE"}),
    )
    kept: list[dict[str, Any]] = []
    for e in ents:
        if any(e["start"] < k["end"] and e["end"] > k["start"] for k in kept):
            continue
        kept.append(e)
    return sorted(kept, key=lambda e: e["start"])


def extract_entities(nlp: Language, text: str) -> list[dict[str, Any]]:
    """Runs spaCy + regex matchers, deduplicates overlaps, returns sorted list."""
    if not text:
        return []
    ents = _spacy_entities(nlp, text) + _regex_entities(text)
    return _dedupe(ents)
