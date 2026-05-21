"""Cohen's kappa for judge-human agreement on 1-5 integer scores."""

from sklearn.metrics import cohen_kappa_score


def compute_kappa(human_scores: list[int], judge_scores: list[int]) -> float:
    """Returns Cohen's kappa. 0 for empty input."""
    if not human_scores or not judge_scores:
        return 0.0
    if len(human_scores) != len(judge_scores):
        raise ValueError("score lists must be the same length")
    return float(cohen_kappa_score(human_scores, judge_scores))
