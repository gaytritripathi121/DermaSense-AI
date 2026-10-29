import numpy as np
import pytest

from src.safety.confidence_filter import screen_probabilities


def test_low_confidence_is_never_accepted():
    result = screen_probabilities(
        np.array([0.44, 0.2, 0.12, 0.1, 0.08, 0.06]),
        quality_ok=True,
    )
    assert result["status"] == "low_confidence"
    assert result["accepted"] is False
    assert len(result["top_three"]) == 3
    assert "unreliable" in result["warning"].lower()


def test_bad_image_quality_blocks_class_suggestions():
    result = screen_probabilities(np.array([0.9, 0.02, 0.02, 0.02, 0.02, 0.02]), quality_ok=False)
    assert result["status"] == "image_quality_warning"
    assert result["top_three"] == []


def test_probabilities_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1"):
        screen_probabilities(np.array([0.5] * 6), quality_ok=True)
