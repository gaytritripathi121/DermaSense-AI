from __future__ import annotations

import numpy as np

from src.data.dataset import CLASS_NAMES


def screen_probabilities(
    probabilities: np.ndarray,
    quality_ok: bool,
    confidence_threshold: float = 0.70,
    minimum_max_probability: float = 0.35,
    maximum_normalized_entropy: float = 0.90,
) -> dict:
    values = np.asarray(probabilities, dtype=np.float64).reshape(-1)
    if len(values) != len(CLASS_NAMES) or not np.isfinite(values).all():
        raise ValueError("Expected one finite probability for each of the six supported classes.")
    if (values < 0).any() or not np.isclose(values.sum(), 1.0, atol=1e-3):
        raise ValueError("Model probabilities must be non-negative and sum to 1.")
    if not quality_ok:
        return {
            "status": "image_quality_warning",
            "accepted": False,
            "top_three": [],
            "warning": "Image quality checks failed. No screening result should be interpreted.",
        }

    order = np.argsort(values)[::-1]
    confidence = float(values[order[0]])
    entropy = float(-(values * np.log(np.clip(values, 1e-12, 1.0))).sum())
    normalized_entropy = entropy / np.log(len(CLASS_NAMES))
    if confidence < minimum_max_probability or normalized_entropy > maximum_normalized_entropy:
        return {
            "status": "out_of_distribution_warning",
            "accepted": False,
            "top_three": [],
            "warning": "The image may be outside the model's supported inputs. Use a clearer photo and consult a clinician.",
        }

    top_three = [
        {"class_code": CLASS_NAMES[index], "probability": float(values[index])}
        for index in order[:3]
    ]
    if confidence < confidence_threshold:
        return {
            "status": "low_confidence",
            "accepted": False,
            "top_three": top_three,
            "warning": "Low confidence: the model is not sure. This result is unreliable. Please consult a dermatologist.",
        }
    return {
        "status": "screening_support",
        "accepted": True,
        "top_three": top_three,
        "warning": "This is screening support only. Consult a clinician to confirm any concern.",
    }
