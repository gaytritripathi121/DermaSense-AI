from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from joblib import load
from PIL import Image
from torchvision import transforms

from src.models.calibrate import probabilities_from_logits
from src.models.fusion_model import FusionClassifier
from src.safety.confidence_filter import screen_probabilities
from src.safety.quality_checks import inspect_image


def predict(
    image_path: str | Path,
    history: dict,
    checkpoint_path: str | Path = "outputs/checkpoint-fusion.pt",
    preprocessor_path: str | Path = "outputs/preprocessor.joblib",
    confidence_threshold: float = 0.70,
) -> dict:
    """Run local research inference; this function is not wired to the web app."""
    checkpoint_path = Path(checkpoint_path)
    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"No trained checkpoint found at {checkpoint_path}. Train and evaluate the model first."
        )
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    preprocessor_bundle = load(preprocessor_path)
    processor = preprocessor_bundle["processor"]
    feature_columns = preprocessor_bundle["feature_columns"]
    frame = pd.DataFrame([history]).reindex(columns=feature_columns)
    for column in frame.columns:
        if column not in history or history[column] in (None, ""):
            frame.loc[0, column] = np.nan if column in {"age", "diameter_1", "diameter_2"} else "UNK"
    for column in {"age", "diameter_1", "diameter_2"} & set(frame.columns):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.replace(r"^\s*$", np.nan, regex=True)
    metadata = torch.as_tensor(processor.transform(frame), dtype=torch.float32)

    image_size = int(checkpoint["image_size"])
    transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )
    with Image.open(image_path) as source:
        image = transform(source.convert("RGB")).unsqueeze(0)
    quality = inspect_image(image_path)
    model = FusionClassifier(
        metadata_dim=int(checkpoint["metadata_dim"]),
        num_classes=len(checkpoint["class_names"]),
        image_only=bool(checkpoint["image_only"]),
        pretrained=False,
    ).cpu()
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    with torch.inference_mode():
        logits = model(image, metadata).numpy()
    probabilities = probabilities_from_logits(logits, float(checkpoint["temperature"]))[0]
    return {
        "quality": quality,
        "screening": screen_probabilities(
            probabilities,
            quality_ok=quality["usable"],
            confidence_threshold=confidence_threshold,
        ),
        "disclaimer": "Research screening support only, not a diagnosis or a substitute for professional care.",
    }
