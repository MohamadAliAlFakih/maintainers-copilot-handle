"""PyTorch Dataset that tokenizes issue title+body for RoBERTa classification."""

from typing import Any

import pandas as pd
import torch
from torch.utils.data import Dataset
from transformers import AutoTokenizer

LABEL_TO_ID: dict[str, int] = {
    "bug": 0,
    "feature": 1,
    "docs": 2,
    "question": 3,
}

ID_TO_LABEL: dict[int, str] = {v: k for k, v in LABEL_TO_ID.items()}


class IssueClassificationDataset(Dataset):
    """Wraps a DataFrame of issues into a tokenized dataset for HF Trainer."""

    def __init__(
        self,
        df: pd.DataFrame,
        tokenizer_name: str = "roberta-base",
        max_seq_len: int = 256,
    ) -> None:
        self._df = df.reset_index(drop=True)
        self._tok = AutoTokenizer.from_pretrained(tokenizer_name)
        self._max_seq_len = max_seq_len

    def __len__(self) -> int:
        """Number of rows in the underlying DataFrame."""
        return len(self._df)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        """Tokenizes one row's title+body and returns input_ids/attention_mask/labels."""
        row = self._df.iloc[idx]
        text = f"{row['title']}\n\n{row['body']}"
        enc: dict[str, Any] = self._tok(
            text,
            truncation=True,
            max_length=self._max_seq_len,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(LABEL_TO_ID[row["class"]], dtype=torch.long),
        }
