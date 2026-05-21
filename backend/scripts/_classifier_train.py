"""Training loop using HF Trainer with macro-F1 early stopping."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score
from transformers import (
    EarlyStoppingCallback,
    RobertaForSequenceClassification,
    Trainer,
    TrainingArguments,
)

from scripts._classifier_dataset import IssueClassificationDataset


@dataclass
class TrainConfig:
    """Hyperparameters surfaced in the model card."""

    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    per_device_train_batch_size: int = 16
    per_device_eval_batch_size: int = 32
    num_train_epochs: int = 3
    max_seq_len: int = 256
    seed: int = 42


def _compute_macro_f1(eval_pred) -> dict[str, float]:  # type: ignore[no-untyped-def]
    """HF callback signature — returns macro-F1 for early stopping."""
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {"macro_f1": f1_score(labels, preds, average="macro")}


def train_classifier(
    model: RobertaForSequenceClassification,
    train_ds: IssueClassificationDataset,
    val_ds: IssueClassificationDataset,
    config: TrainConfig,
    output_dir: Path,
) -> RobertaForSequenceClassification:
    """Trains the model with early stopping on val macro-F1. Returns the best model."""
    args = TrainingArguments(
        output_dir=str(output_dir),
        learning_rate=config.learning_rate,
        per_device_train_batch_size=config.per_device_train_batch_size,
        per_device_eval_batch_size=config.per_device_eval_batch_size,
        num_train_epochs=config.num_train_epochs,
        weight_decay=config.weight_decay,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        seed=config.seed,
        report_to=[],
        logging_dir=str(output_dir / "logs"),
        save_total_limit=2,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=_compute_macro_f1,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=1)],
    )
    trainer.train()
    return trainer.model  # type: ignore[return-value]
