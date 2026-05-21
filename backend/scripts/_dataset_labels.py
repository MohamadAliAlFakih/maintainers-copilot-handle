"""GitHub-label -> 4-class mapping for the pandas-dev/pandas dataset."""

from dataclasses import dataclass

# Mapping defined in DECISIONS.md and reflected here.
_LABEL_TO_CLASS: dict[str, str] = {
    "bug": "bug",
    "feature": "feature",
    "enhancement": "feature",
    "docs": "docs",
    "documentation": "docs",
    "question": "question",
    "discussion": "question",
    "answered": "question",
}


@dataclass(frozen=True)
class LabelMappingResult:
    """Result of mapping a set of GitHub labels onto one of the 4 classes."""

    label: str | None
    conflict: bool = False
    dropped: bool = False


def map_labels_to_class(labels: list[str]) -> LabelMappingResult:
    """Picks a single class from a list of GitHub labels, or marks the row as dropped."""
    mapped = {_LABEL_TO_CLASS[label] for label in labels if label in _LABEL_TO_CLASS}

    if not mapped:
        return LabelMappingResult(label=None, dropped=True)

    if len(mapped) > 1:
        return LabelMappingResult(label=None, conflict=True, dropped=True)

    return LabelMappingResult(label=mapped.pop())
