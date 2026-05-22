"""GitHub-label -> 4-class mapping for the pandas-dev/pandas dataset.

Matching is case-insensitive and tolerant of pandas' label naming (e.g.
"Bug", "Enhancement", "Docs", "Usage Question"). Substrings like "Question"
inside compound labels are matched too.
"""

from dataclasses import dataclass

# Each entry: (lowercase substring, target class). Order does not matter for
# unambiguous matches; conflicts (e.g. both "bug" and "enhancement" labels on the
# same issue) cause the row to be dropped.
_LABEL_PATTERNS: list[tuple[str, str]] = [
    ("bug", "bug"),
    ("regression", "bug"),
    ("enhancement", "feature"),
    ("feature", "feature"),
    ("performance", "feature"),
    ("api", "feature"),
    ("docs", "docs"),
    ("documentation", "docs"),
    ("question", "question"),
    ("discussion", "question"),
    ("usage", "question"),
    ("needs info", "question"),
]


@dataclass(frozen=True)
class LabelMappingResult:
    """Result of mapping a set of GitHub labels onto one of the 4 classes."""

    label: str | None
    conflict: bool = False
    dropped: bool = False


def _label_class(label: str) -> str | None:
    """Returns the class for one GitHub label, or None if it doesn't match."""
    lowered = label.lower().strip()
    for pattern, cls in _LABEL_PATTERNS:
        if pattern in lowered:
            return cls
    return None


def map_labels_to_class(labels: list[str]) -> LabelMappingResult:
    """Picks a single class from a list of GitHub labels, or marks the row as dropped."""
    mapped: set[str] = set()
    for raw in labels:
        cls = _label_class(raw)
        if cls is not None:
            mapped.add(cls)
    if not mapped:
        return LabelMappingResult(label=None, dropped=True)
    if len(mapped) > 1:
        return LabelMappingResult(label=None, conflict=True, dropped=True)
    return LabelMappingResult(label=mapped.pop())
