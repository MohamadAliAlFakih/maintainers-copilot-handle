"""Loads classifier weights from MinIO, verifies SHA against the model card."""

import hashlib
import re
from dataclasses import dataclass

from minio import Minio
from safetensors.torch import load
from transformers import AutoTokenizer, RobertaForSequenceClassification

from app.infra.logging_setup import get_logger
from app.infra.minio import fetch_object_bytes

log = get_logger(__name__)

LABEL_TO_ID = {"bug": 0, "feature": 1, "docs": 2, "question": 3}
ID_TO_LABEL = {v: k for k, v in LABEL_TO_ID.items()}


class WeightsShaMismatch(Exception):
    """Raised when weights bytes don't hash to the value in the model card."""


@dataclass(frozen=True)
class LoadedClassifier:
    """The loaded model + tokenizer ready for inference."""

    model: RobertaForSequenceClassification
    tokenizer: AutoTokenizer
    weights_sha: str


def extract_weights_sha_from_card(card_text: str) -> str:
    """Pulls the weights_sha256 value out of the model card markdown."""
    m = re.search(r"weights_sha256:\*\*\s*`([a-f0-9]+)`", card_text)
    if not m:
        raise ValueError("weights_sha256 not found in model card")
    return m.group(1)


def verify_weights_sha(weights_bytes: bytes, expected_sha: str) -> None:
    """Raises WeightsShaMismatch if the computed SHA doesn't match expected."""
    actual = hashlib.sha256(weights_bytes).hexdigest()
    if actual != expected_sha:
        raise WeightsShaMismatch(
            f"weights SHA mismatch. expected={expected_sha[:8]}... actual={actual[:8]}..."
        )


def load_classifier_from_minio(client: Minio, model_key_prefix: str) -> LoadedClassifier:
    """Pulls weights + card from MinIO, verifies SHA, loads into a RoBERTa model."""
    log.info("classifier.load.begin", model_key_prefix=model_key_prefix)

    card_bytes = fetch_object_bytes(client, "models", f"{model_key_prefix}/model_card.md")
    card = card_bytes.decode("utf-8")
    expected_sha = extract_weights_sha_from_card(card)

    weights_bytes = fetch_object_bytes(client, "models", f"{model_key_prefix}/model.safetensors")
    verify_weights_sha(weights_bytes, expected_sha)

    model = RobertaForSequenceClassification.from_pretrained(
        "roberta-base",
        num_labels=4,
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID,
    )
    state = load(weights_bytes)
    model.load_state_dict(state)
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained("roberta-base")

    log.info("classifier.load.done", weights_sha=expected_sha[:12])
    return LoadedClassifier(model=model, tokenizer=tokenizer, weights_sha=expected_sha)
