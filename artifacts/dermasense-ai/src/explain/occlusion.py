from __future__ import annotations

import numpy as np
import torch
from matplotlib import colormaps
from torch import nn


def occlusion_sensitivity(
    model: nn.Module,
    image: torch.Tensor,
    metadata: torch.Tensor,
    class_index: int,
    patch_size: int = 32,
    stride: int = 16,
) -> np.ndarray:
    """Return a normalized heatmap showing score changes under image occlusion."""
    model.eval()
    _, _, height, width = image.shape
    heatmap = np.zeros((height, width), dtype=np.float32)
    counts = np.zeros_like(heatmap)
    with torch.inference_mode():
        baseline = float(torch.softmax(model(image, metadata), dim=1)[0, class_index])
        for top in range(0, height, stride):
            for left in range(0, width, stride):
                bottom, right = min(top + patch_size, height), min(left + patch_size, width)
                occluded = image.clone()
                occluded[:, :, top:bottom, left:right] = 0
                score = float(torch.softmax(model(occluded, metadata), dim=1)[0, class_index])
                heatmap[top:bottom, left:right] += baseline - score
                counts[top:bottom, left:right] += 1
    heatmap /= np.maximum(counts, 1)
    scale = float(np.abs(heatmap).max())
    return heatmap / scale if scale > 0 else heatmap


def colorize_occlusion(heatmap: np.ndarray) -> np.ndarray:
    normalized = np.clip((heatmap + 1.0) / 2.0, 0.0, 1.0)
    return (colormaps["coolwarm"](normalized)[..., :3] * 255).astype(np.uint8)
