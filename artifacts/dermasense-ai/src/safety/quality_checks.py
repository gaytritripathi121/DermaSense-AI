from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import laplace


def inspect_image(
    image_path: str | Path,
    minimum_dimension: int = 800,
    minimum_laplacian_variance: float = 10.0,
    minimum_brightness: float = 40.0,
    maximum_brightness: float = 220.0,
) -> dict:
    with Image.open(image_path) as source:
        rgb = source.convert("RGB")
        width, height = rgb.size
        grayscale = np.asarray(rgb.convert("L"), dtype=np.float32)
    mean_brightness = float(grayscale.mean())
    blur_score = float(laplace(grayscale).var())
    flags = {
        "resolution_ok": width >= minimum_dimension and height >= minimum_dimension,
        "brightness_ok": minimum_brightness <= mean_brightness <= maximum_brightness,
        "sharpness_ok": blur_score >= minimum_laplacian_variance,
    }
    return {
        "width": width,
        "height": height,
        "mean_brightness": mean_brightness,
        "laplacian_variance": blur_score,
        "flags": flags,
        "usable": all(flags.values()),
        "message": (
            "Image quality checks passed. They do not assess whether the image shows a lesion."
            if all(flags.values())
            else "Use a clearer, well-lit image with at least the minimum resolution. "
            "These technical checks do not determine whether a spot is concerning."
        ),
    }
