from __future__ import annotations

import hashlib

import numpy as np
import torch
from lime.lime_image import LimeImageExplainer
from PIL import Image
from skimage.color import gray2rgb
from skimage.segmentation import mark_boundaries, slic
from torch import nn
from torchvision import transforms

_EXPLANATION_CACHE: dict[str, tuple[np.ndarray, str]] = {}


def lime_explanation(
    model: nn.Module,
    image: np.ndarray,
    metadata: torch.Tensor,
    class_index: int,
    num_samples: int = 400,
) -> tuple[np.ndarray, str]:
    """Explain a model score with SLIC superpixels while holding history fixed."""
    if not 300 <= num_samples <= 500:
        raise ValueError("LIME num_samples must be between 300 and 500.")
    image = np.asarray(image)
    if np.issubdtype(image.dtype, np.floating) and image.size and image.max() <= 1.0:
        image = image * 255.0
    if image.ndim == 2:
        image = gray2rgb(image)
    if image.ndim != 3 or image.shape[-1] not in {3, 4}:
        raise ValueError("LIME expects an RGB, RGBA, or grayscale image.")
    image = np.asarray(image, dtype=np.uint8)
    if image.shape[-1] == 4:
        image = image[..., :3]
    metadata_bytes = metadata.detach().cpu().contiguous().numpy().tobytes()
    model_versions = tuple(getattr(parameter, "_version", 0) for parameter in model.parameters())
    cache_key = hashlib.sha256(
        str((id(model), model_versions, class_index, num_samples)).encode("utf-8")
        + image.tobytes()
        + metadata_bytes
    ).hexdigest()
    if cache_key in _EXPLANATION_CACHE:
        cached_visual, caption = _EXPLANATION_CACHE[cache_key]
        return cached_visual.copy(), caption
    image_size = 224
    model_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )

    def predict_batch(images: np.ndarray) -> np.ndarray:
        tensors = torch.stack(
            [model_transform(Image.fromarray(candidate.astype(np.uint8))) for candidate in images]
        )
        fixed_history = metadata.expand(len(tensors), -1)
        with torch.inference_mode():
            return torch.softmax(model(tensors.cpu(), fixed_history.cpu()), dim=1).cpu().numpy()

    explainer = LimeImageExplainer()
    explanation = explainer.explain_instance(
        image,
        predict_batch,
        labels=(class_index,),
        hide_color=0,
        num_samples=num_samples,
        segmentation_fn=lambda source: slic(source, n_segments=60, compactness=10, start_label=1),
        progress_bar=True,
    )
    segments = explanation.segments
    weights = dict(explanation.local_exp[class_index])
    mask = np.zeros(segments.shape, dtype=np.float32)
    for segment_id, weight in weights.items():
        mask[segments == segment_id] = weight
    visual = mark_boundaries(image.astype(np.float32) / 255.0, segments, color=(1.0, 0.8, 0.2))
    positive, negative = mask > 0, mask < 0
    visual[positive] = visual[positive] * 0.58 + np.array([0.12, 0.72, 0.38]) * 0.42
    visual[negative] = visual[negative] * 0.58 + np.array([0.86, 0.28, 0.24]) * 0.42
    caption = (
        "Highlighted regions show image areas that influenced this model output. "
        "The explanation describes model behavior, not clinical proof."
    )
    visual = (np.clip(visual, 0.0, 1.0) * 255).astype(np.uint8)
    if len(_EXPLANATION_CACHE) >= 64:
        _EXPLANATION_CACHE.pop(next(iter(_EXPLANATION_CACHE)))
    _EXPLANATION_CACHE[cache_key] = (visual.copy(), caption)
    return visual, caption
