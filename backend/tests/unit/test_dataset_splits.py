"""Tests for stratified time-ordered splits."""
import pandas as pd

from scripts._dataset_splits import (
    HeldOutRagSlice,
    SplitConfig,
    build_splits,
)


def _fake_df(n: int) -> pd.DataFrame:
    """Builds n fake rows with balanced classes and monotonically increasing close dates."""
    rows = []
    classes = ["bug", "feature", "docs", "question"]
    for i in range(n):
        rows.append(
            {
                "issue_number": i + 1,
                "title": f"issue {i}",
                "body": f"body {i}",
                "class": classes[i % 4],
                "closed_at": pd.Timestamp("2023-01-01") + pd.Timedelta(days=i),
            }
        )
    return pd.DataFrame(rows)


def test_test_set_is_strictly_more_recent_than_train():
    """Test rows must have closed_at greater than every train row."""
    df = _fake_df(200)
    splits = build_splits(df, SplitConfig(test_frac=0.2, val_frac=0.1, seed=42))
    train_max = splits.train["closed_at"].max()
    test_min = splits.test["closed_at"].min()
    assert test_min > train_max


def test_split_proportions_are_close_to_target():
    """Train/val/test sizes are within +/- 5% of the requested fractions."""
    df = _fake_df(1000)
    splits = build_splits(df, SplitConfig(test_frac=0.2, val_frac=0.1, seed=42))
    total = len(splits.train) + len(splits.val) + len(splits.test)
    assert abs(len(splits.test) / total - 0.2) < 0.05
    assert abs(len(splits.val) / (len(splits.train) + len(splits.val)) - 0.1) < 0.05


def test_all_classes_present_in_each_split():
    """Stratification keeps every class represented in train/val/test."""
    df = _fake_df(400)
    splits = build_splits(df, SplitConfig(test_frac=0.2, val_frac=0.1, seed=42))
    for s in (splits.train, splits.val, splits.test):
        assert set(s["class"]) == {"bug", "feature", "docs", "question"}


def test_held_out_rag_slice_excludes_question_rows_from_splits():
    """The 10% most-recent question rows are removed from the classifier splits."""
    df = _fake_df(400)
    rag = HeldOutRagSlice(question_frac=0.1)
    splits = build_splits(df, SplitConfig(test_frac=0.2, val_frac=0.1, seed=42), rag)
    held = splits.rag_held_out
    assert held is not None
    assert len(held) > 0
    held_ids = set(held["issue_number"])
    for s in (splits.train, splits.val, splits.test):
        assert not (set(s["issue_number"]) & held_ids)


def test_seed_is_deterministic():
    """Two runs with the same seed produce identical splits."""
    df = _fake_df(300)
    a = build_splits(df, SplitConfig(test_frac=0.2, val_frac=0.1, seed=42))
    b = build_splits(df, SplitConfig(test_frac=0.2, val_frac=0.1, seed=42))
    pd.testing.assert_frame_equal(
        a.train.reset_index(drop=True), b.train.reset_index(drop=True)
    )
