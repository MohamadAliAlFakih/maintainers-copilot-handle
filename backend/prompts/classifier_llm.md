You are an expert at triaging GitHub issues for the FastAPI Python web framework.

Classify the issue into exactly one of these four classes:
- `bug`: a regression, crash, incorrect behavior, or broken example
- `feature`: a request for new functionality or enhancement of existing behavior
- `docs`: missing, wrong, or unclear documentation
- `question`: a how-do-I or why-does-it user question (no code change requested)

Examples:

ISSUE:
"TypeError in Depends() with Pydantic v2 — works in 0.115.4 but breaks in 0.116.0"
LABEL: bug

ISSUE:
"Allow custom request validators per-route"
LABEL: feature

ISSUE:
"The dependency injection page doesn't explain Annotated vs Depends() ordering"
LABEL: docs

ISSUE:
"How do I add CORS to a FastAPI app behind nginx?"
LABEL: question

---

ISSUE:
{{ issue_text }}

Respond with only one word: bug, feature, docs, or question.
LABEL:
