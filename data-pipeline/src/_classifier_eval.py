"""Eval helpers — macro-F1, per-class F1, confusion matrix, latency."""

import time
from dataclasses import dataclass

import numpy as np
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from torch.utils.data import DataLoader

from src._classifier_dataset import ID_TO_LABEL, IssueClassificationDataset


@dataclass
class EvalReport:
    accuracy: float
    macro_f1: float
    per_class_f1: dict[str, float]
    confusion_matrix: list[list[int]]
    p50_latency_ms: float
    p95_latency_ms: float


def evaluate(
    model: torch.nn.Module,
    ds: IssueClassificationDataset,
    batch_size: int = 32,
    device: str = "cpu",
) -> EvalReport:
    model.eval().to(device)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False)

    all_preds: list[int] = []
    all_labels: list[int] = []
    per_call_latencies_ms: list[float] = []

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"]
            t0 = time.perf_counter()
            logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
            elapsed_ms = (time.perf_counter() - t0) * 1000
            per_call_latencies_ms.extend([elapsed_ms / len(labels)] * len(labels))

            preds = torch.argmax(logits, dim=-1).cpu().numpy()
            all_preds.extend(preds.tolist())
            all_labels.extend(labels.tolist())

    macro = f1_score(all_labels, all_preds, average="macro")
    per_class_f1_arr = f1_score(all_labels, all_preds, average=None)
    per_class = {ID_TO_LABEL[i]: float(per_class_f1_arr[i]) for i in range(len(per_class_f1_arr))}
    cm = confusion_matrix(all_labels, all_preds).tolist()
    acc = accuracy_score(all_labels, all_preds)

    return EvalReport(
        accuracy=float(acc),
        macro_f1=float(macro),
        per_class_f1=per_class,
        confusion_matrix=cm,
        p50_latency_ms=float(np.percentile(per_call_latencies_ms, 50)),
        p95_latency_ms=float(np.percentile(per_call_latencies_ms, 95)),
    )
