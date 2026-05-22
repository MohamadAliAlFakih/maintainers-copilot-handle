"""End-to-end classifier training: pull splits, train, eval, push weights + card to MinIO.

Run inside the backend container:
    docker compose exec api uv run python /app/scripts/train_classifier.py
"""

import io
import json
import sys
from pathlib import Path

import mlflow
import pandas as pd
from safetensors.torch import save_file

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402
from scripts.classifier._classifier_card import compute_weights_sha, render_model_card  # noqa: E402
from scripts.classifier._classifier_dataset import IssueClassificationDataset  # noqa: E402
from scripts.classifier._classifier_eval import evaluate  # noqa: E402
from scripts.classifier._classifier_model import build_model, count_trainable_params  # noqa: E402
from scripts.classifier._classifier_train import TrainConfig, train_classifier  # noqa: E402

log = get_logger(__name__)

MODEL_NAME = "roberta-issue-cls-v1"


def _load_parquet_from_minio(client, bucket: str, key: str) -> pd.DataFrame:
    """Pulls a parquet object from MinIO into a DataFrame."""
    resp = client.get_object(bucket, key)
    try:
        return pd.read_parquet(io.BytesIO(resp.read()))
    finally:
        resp.close()
        resp.release_conn()


def _load_manifest(client) -> dict:
    """Loads the dataset manifest produced by Plan 1a."""
    resp = client.get_object("dataset", "manifest.json")
    try:
        return json.loads(resp.read())
    finally:
        resp.close()
        resp.release_conn()


def _upload(client, bucket: str, key: str, data: bytes) -> None:
    """Uploads bytes to MinIO under bucket/key."""
    client.put_object(bucket, key, io.BytesIO(data), length=len(data))


def main() -> None:
    """Orchestrates the full training run."""
    configure_logging()
    settings = get_settings()
    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )

    log.info("classifier.train.begin")

    train_df = _load_parquet_from_minio(minio_client, "dataset", "splits/train.parquet")
    val_df = _load_parquet_from_minio(minio_client, "dataset", "splits/val.parquet")
    test_df = _load_parquet_from_minio(minio_client, "dataset", "splits/test.parquet")
    manifest = _load_manifest(minio_client)
    training_data_hash = manifest["raw_issues_sha256"]
    log.info(
        "classifier.train.data_loaded",
        n_train=len(train_df),
        n_val=len(val_df),
        n_test=len(test_df),
        training_data_hash=training_data_hash[:12],
    )

    cfg = TrainConfig()
    train_ds = IssueClassificationDataset(train_df, max_seq_len=cfg.max_seq_len)
    val_ds = IssueClassificationDataset(val_df, max_seq_len=cfg.max_seq_len)
    test_ds = IssueClassificationDataset(test_df, max_seq_len=cfg.max_seq_len)

    model = build_model(num_labels=4, freeze_through_layer=8)
    trainable = count_trainable_params(model)
    log.info("classifier.train.model_built", trainable_params=trainable)

    output_dir = Path("/data/mlflow")
    output_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"file://{output_dir / 'mlruns'}")
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

        model = train_classifier(model, train_ds, val_ds, cfg, output_dir)

        log.info("classifier.eval.test")
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
            "classifier.train.test_results",
            macro_f1=test_report.macro_f1,
            accuracy=test_report.accuracy,
        )

        state_dict = model.state_dict()
        clean_state = {k: v.contiguous().cpu() for k, v in state_dict.items()}
        weights_path = output_dir / "model.safetensors"
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
        ).encode("utf-8")

        # ---- upload to MinIO ----
        prefix = f"classifier/{MODEL_NAME}"
        _upload(minio_client, "models", f"{prefix}/model.safetensors", weights_bytes)
        _upload(minio_client, "models", f"{prefix}/model_card.md", card.encode("utf-8"))
        _upload(minio_client, "models", f"{prefix}/eval_report.json", eval_json)

        # ---- also persist to host-mounted volume so artifacts survive `compose down -v` ----
        host_dir = Path("/data/classifier_artifacts") / MODEL_NAME
        host_dir.mkdir(parents=True, exist_ok=True)
        (host_dir / "model.safetensors").write_bytes(weights_bytes)
        (host_dir / "model_card.md").write_text(card, encoding="utf-8")
        (host_dir / "eval_report.json").write_bytes(eval_json)

        log.info(
            "classifier.train.done",
            weights_sha=weights_sha[:12],
            host_path=str(host_dir),
        )


if __name__ == "__main__":
    main()
