"""Builds the RoBERTa classifier and applies the freeze policy."""
import torch
from transformers import RobertaForSequenceClassification

from scripts._classifier_dataset import ID_TO_LABEL, LABEL_TO_ID


def build_model(
    num_labels: int = 4,
    freeze_through_layer: int = 8,
    pretrained_name: str = "roberta-base",
) -> RobertaForSequenceClassification:
    """Loads roberta-base, swaps in a 4-class head, freezes layers 0..freeze_through_layer."""
    model = RobertaForSequenceClassification.from_pretrained(
        pretrained_name,
        num_labels=num_labels,
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID,
    )

    # Freeze embeddings
    for p in model.roberta.embeddings.parameters():
        p.requires_grad = False

    # Freeze encoder layers up to and including freeze_through_layer
    for i in range(freeze_through_layer + 1):
        for p in model.roberta.encoder.layer[i].parameters():
            p.requires_grad = False

    # Remaining layers + classifier head stay trainable
    return model


def count_trainable_params(model: torch.nn.Module) -> int:
    """Returns the number of parameters with requires_grad=True."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
