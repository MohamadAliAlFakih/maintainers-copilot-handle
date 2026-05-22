"""Tests for the model builder + freeze policy."""

from scripts.classifier._classifier_model import build_model, count_trainable_params


def test_build_model_returns_classifier_with_4_labels():
    """build_model returns a RobertaForSequenceClassification with 4 output labels."""
    model = build_model(num_labels=4, freeze_through_layer=8)
    assert model.config.num_labels == 4


def test_freeze_through_layer_8_freezes_lower_layers():
    """Layers 0-8 are frozen; 9-11 + classifier head remain trainable."""
    model = build_model(num_labels=4, freeze_through_layer=8)

    for p in model.roberta.embeddings.parameters():
        assert p.requires_grad is False

    for i in range(9):
        for p in model.roberta.encoder.layer[i].parameters():
            assert p.requires_grad is False

    for i in range(9, 12):
        any_trainable = any(p.requires_grad for p in model.roberta.encoder.layer[i].parameters())
        assert any_trainable

    for p in model.classifier.parameters():
        assert p.requires_grad is True


def test_count_trainable_params_is_a_fraction_of_total():
    """Trainable param count is meaningfully less than total when frozen."""
    model = build_model(num_labels=4, freeze_through_layer=8)
    total = sum(p.numel() for p in model.parameters())
    trainable = count_trainable_params(model)
    assert 0 < trainable < total
    assert trainable / total < 0.30
