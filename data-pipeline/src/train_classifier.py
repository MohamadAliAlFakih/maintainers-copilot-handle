"""Train the RoBERTa issue classifier from data/raw/dataset/ to data/artifacts/classifier/.

Run from the data-pipeline directory:
    uv run python -m src.train_classifier
"""

import argparse
import json
import logging
from pathlib import Path

import mlflow
import pandas as pd
from safetensors.torch import save_file

from src._classifier_card import compute_weights_sha, render_model_card
from src._classifier_dataset import IssueClassificationDataset
from src._classifier_eval import evaluate
from src._classifier_model import build_model, count_trainable_params
from src._classifier_train import TrainConfig, train_classifier

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / "data" / "raw" / "dataset"
DEFAULT_OUT = REPO_ROOT / "data" / "artifacts" / "classifier"
MODEL_NAME = "roberta-issue-cls-v1"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out_dir = args.out / MODEL_NAME
    weights_path = out_dir / "model.safetensors"
    if weights_path.exists() and not args.force:
        log.info("skip: %s exists (use --force to overwrite)", weights_path)
        return

    splits_dir = args.data / "splits"
    train_df = pd.read_parquet(splits_dir / "train.parquet")
    val_df = pd.read_parquet(splits_dir / "val.parquet")
    test_df = pd.read_parquet(splits_dir / "test.parquet")
    manifest = json.loads((args.data / "manifest.json").read_text())
    training_data_hash = manifest["raw_issues_sha256"]
    log.info(
        "data loaded: train=%d val=%d test=%d hash=%s",
        len(train_df), len(val_df), len(test_df), training_data_hash[:12],
    )

    cfg = TrainConfig()
    train_ds = IssueClassificationDataset(train_df, max_seq_len=cfg.max_seq_len)
    val_ds = IssueClassificationDataset(val_df, max_seq_len=cfg.max_seq_len)
    test_ds = IssueClassificationDataset(test_df, max_seq_len=cfg.max_seq_len)

    model = build_model(num_labels=4, freeze_through_layer=8)
    trainable = count_trainable_params(model)
    log.info("model built: %d trainable params", trainable)

    out_dir.mkdir(parents=True, exist_ok=True)
    mlruns_dir = args.out / "_mlruns"
    mlruns_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"file://{mlruns_dir}")
    mlflow.set_experiment("classifier")

    with mlflow.start_run():
        mlflow.log_params(
            {
                "architecture": "roberta-base",
                "learning_rate": cfg.learning_rate,
                "batch_size": cfg.per_device_train_batch_size,
                "epochs": cfg.num_train_epochs,
                "max_seq_len": cfg.max_seq_len,
                "freeze_through_layer": 8,
                "trainable_params": trainable,
                "training_data_hash": training_data_hash,
            }
        )

        model = train_classifier(model, train_ds, val_ds, cfg, out_dir / "_hf")

        log.info("evaluating on test split")
        test_report = evaluate(model, test_ds, batch_size=cfg.per_device_eval_batch_size)
        mlflow.log_metrics(
            {
                "test_macro_f1": test_report.macro_f1,
                "test_accuracy": test_report.accuracy,
                **{f"test_f1_{cls}": v for cls, v in test_report.per_class_f1.items()},
                "test_p50_latency_ms": test_report.p50_latency_ms,
                "test_p95_latency_ms": test_report.p95_latency_ms,
            }
        )
        log.info(
            "test results: macro_f1=%.4f accuracy=%.4f",
            test_report.macro_f1, test_report.accuracy,
        )

        state_dict = model.state_dict()
        clean_state = {k: v.contiguous().cpu() for k, v in state_dict.items()}
        save_file(clean_state, str(weights_path))
        weights_bytes = weights_path.read_bytes()
        weights_sha = compute_weights_sha(weights_bytes)

        card = render_model_card(
            architecture="roberta-base",
            hyperparams={
                "learning_rate": cfg.learning_rate,
                "batch_size": cfg.per_device_train_batch_size,
                "epochs": cfg.num_train_epochs,
                "weight_decay": cfg.weight_decay,
                "max_seq_len": cfg.max_seq_len,
                "freeze_through_layer": 8,
            },
            weights_sha=weights_sha,
            training_data_hash=training_data_hash,
            eval_report=test_report,
        )
        eval_json = json.dumps(
            {
                "accuracy": test_report.accuracy,
                "macro_f1": test_report.macro_f1,
                "per_class_f1": test_report.per_class_f1,
                "confusion_matrix": test_report.confusion_matrix,
                "p50_latency_ms": test_report.p50_latency_ms,
                "p95_latency_ms": test_report.p95_latency_ms,
                "weights_sha256": weights_sha,
                "training_data_hash": training_data_hash,
            },
            indent=2,
        )

        (out_dir / "model_card.md").write_text(card, encoding="utf-8")
        (out_dir / "eval_report.json").write_text(eval_json)
        log.info("wrote %s (sha=%s)", weights_path, weights_sha[:12])


if __name__ == "__main__":
    main()
