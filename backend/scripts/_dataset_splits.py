"""Stratified time-ordered splits with optional held-out RAG slice."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SplitConfig:
    """Configuration for the splitter. test_frac/val_frac are fractions of the full dataset."""

    test_frac: float = 0.2
    val_frac: float = 0.1
    seed: int = 42


@dataclass(frozen=True)
class HeldOutRagSlice:
    """Configuration for the question-class held-out slice used by RAG ingestion."""

    question_frac: float = 0.1


@dataclass(frozen=True)
class Splits:
    """Container for train/val/test DataFrames + an optional held-out RAG slice."""

    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame
    rag_held_out: pd.DataFrame | None = None


def _hold_out_recent_questions(df: pd.DataFrame, frac: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Removes the most-recent `frac` of question-class rows and returns (remaining, held_out)."""
    questions = df[df["class"] == "question"].sort_values("closed_at")
    n_hold = max(1, int(len(questions) * frac))
    held = questions.tail(n_hold).copy()
    remaining_idx = df.index.difference(held.index)
    return df.loc[remaining_idx].copy(), held


def _time_then_stratify(
    df: pd.DataFrame, test_frac: float, val_frac: float, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Splits with test as the most-recent slice; train/val stratified-random on the rest."""
    df_sorted = df.sort_values("closed_at").reset_index(drop=True)
    n_test = int(len(df_sorted) * test_frac)
    test = df_sorted.tail(n_test).copy()
    head = df_sorted.head(len(df_sorted) - n_test).copy()

    # stratified train/val on the head
    rng = np.random.default_rng(seed)
    val_rows = []
    for _cls, group in head.groupby("class"):
        group = group.sample(frac=1, random_state=int(rng.integers(0, 2**31 - 1))).reset_index(
            drop=True
        )
        n_val = max(1, int(len(group) * val_frac))
        val_rows.append(group.head(n_val))
    val = pd.concat(val_rows, ignore_index=True)
    train = head.drop(val.index)

    return (
        train.reset_index(drop=True),
        val.reset_index(drop=True),
        test.reset_index(drop=True),
    )


def build_splits(
    df: pd.DataFrame,
    config: SplitConfig,
    rag: HeldOutRagSlice | None = None,
) -> Splits:
    """Produces classifier train/val/test plus an optional RAG held-out slice."""
    df = df.copy()
    held_out = None

    if rag is not None:
        df, held_out = _hold_out_recent_questions(df, rag.question_frac)

    train, val, test = _time_then_stratify(df, config.test_frac, config.val_frac, config.seed)
    return Splits(train=train, val=val, test=test, rag_held_out=held_out)
