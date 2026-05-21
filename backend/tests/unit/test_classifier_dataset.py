"""Tests for the classifier dataset wrapper."""
import pandas as pd

from scripts._classifier_dataset import LABEL_TO_ID, IssueClassificationDataset


def _fake_df() -> pd.DataFrame:
    """Tiny 4-row DataFrame, one per class."""
    return pd.DataFrame(
        {
            "title": ["t1", "t2", "t3", "t4"],
            "body": ["b1", "b2", "b3", "b4"],
            "class": ["bug", "feature", "docs", "question"],
        }
    )


def test_label_to_id_has_4_classes():
    """LABEL_TO_ID maps exactly the 4 expected labels to integers."""
    assert set(LABEL_TO_ID.keys()) == {"bug", "feature", "docs", "question"}
    assert set(LABEL_TO_ID.values()) == {0, 1, 2, 3}


def test_dataset_returns_correct_items():
    """__getitem__ returns a dict with input_ids, attention_mask, and labels."""
    df = _fake_df()
    ds = IssueClassificationDataset(df, tokenizer_name="roberta-base", max_seq_len=32)
    item = ds[0]
    assert "input_ids" in item
    assert "attention_mask" in item
    assert "labels" in item
    assert item["labels"].item() == LABEL_TO_ID["bug"]


def test_dataset_length():
    """__len__ matches the underlying DataFrame."""
    df = _fake_df()
    ds = IssueClassificationDataset(df, tokenizer_name="roberta-base", max_seq_len=32)
    assert len(ds) == 4
