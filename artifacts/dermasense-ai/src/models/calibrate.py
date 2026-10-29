from __future__ import annotations

import numpy as np
import torch
from torch import nn


def expected_calibration_error(probabilities: np.ndarray, labels: np.ndarray, bins: int = 10) -> float:
    confidences = probabilities.max(axis=1)
    predictions = probabilities.argmax(axis=1)
    correct = predictions == labels
    ece = 0.0
    edges = np.linspace(0.0, 1.0, bins + 1)
    for index in range(bins):
        in_bin = (confidences > edges[index]) & (confidences <= edges[index + 1])
        if in_bin.any():
            ece += float(in_bin.mean()) * abs(float(correct[in_bin].mean()) - float(confidences[in_bin].mean()))
    return ece


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """Fit one scalar temperature on validation logits only."""
    logits_tensor = torch.as_tensor(logits, dtype=torch.float32)
    labels_tensor = torch.as_tensor(labels, dtype=torch.long)
    log_temperature = nn.Parameter(torch.zeros(()))
    optimizer = torch.optim.LBFGS([log_temperature], lr=0.1, max_iter=100)

    def closure():
        optimizer.zero_grad()
        temperature = log_temperature.exp().clamp(0.05, 20.0)
        loss = nn.functional.cross_entropy(logits_tensor / temperature, labels_tensor)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(log_temperature.detach().exp().clamp(0.05, 20.0).item())


def probabilities_from_logits(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    scaled = torch.as_tensor(logits, dtype=torch.float32) / max(float(temperature), 1e-6)
    return torch.softmax(scaled, dim=1).cpu().numpy()
