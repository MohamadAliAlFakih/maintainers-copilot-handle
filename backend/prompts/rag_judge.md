You are evaluating a RAG-generated answer for the FastAPI documentation assistant.

Score the candidate answer on TWO dimensions, each on a 1-5 integer scale:

- **faithfulness**: how well-grounded the answer is in the retrieved context. 5 = every claim is supported by the context; 1 = answer is mostly hallucinated.
- **answer_relevancy**: how directly the answer addresses the question. 5 = exactly what was asked; 1 = off-topic.

The ideal answer is provided as a reference for what a correct answer looks like; you do NOT need to match it exactly. Judge the candidate on its own merits.

Respond in this exact format, nothing else:

```
faithfulness: <1-5>
answer_relevancy: <1-5>
```

---

QUESTION:
{{ question }}

IDEAL ANSWER (reference):
{{ ideal_answer }}

RETRIEVED CONTEXT (what the candidate had access to):
{{ context }}

CANDIDATE ANSWER:
{{ candidate_answer }}

SCORES:
