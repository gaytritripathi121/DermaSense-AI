from __future__ import annotations

import numpy as np
import torch
from torch import nn


def local_feature_sensitivity(
    model: nn.Module,
    image: torch.Tensor,
    metadata: torch.Tensor,
    feature_names: list[str],
) -> list[dict]:
    """Estimate local score changes by zeroing one encoded feature at a time."""
    model.eval()
    with torch.inference_mode():
        baseline = torch.softmax(model(image, metadata), dim=1)[0]
        predicted_class = int(baseline.argmax())
        baseline_score = float(baseline[predicted_class])
        results = []
        for index, name in enumerate(feature_names):
            perturbed = metadata.clone()
            perturbed[:, index] = 0.0
            score = float(torch.softmax(model(image, perturbed), dim=1)[0, predicted_class])
            results.append(
                {
                    "feature": name,
                    "score_change": score - baseline_score,
                    "note": "Local model sensitivity, not causal or clinical evidence.",
                }
            )
    return sorted(results, key=lambda item: abs(item["score_change"]), reverse=True)
