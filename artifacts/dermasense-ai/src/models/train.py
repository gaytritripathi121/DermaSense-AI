from __future__ import annotations

import argparse
import copy
import json
import random
from pathlib import Path

import numpy as np
import torch
import yaml
from sklearn.metrics import f1_score
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader
from torchvision import transforms

from src.data.dataset import CLASS_NAMES, LesionDataset, cache_resized_images, verify_dataset
from src.data.preprocess import fit_transform_metadata
from src.models.ablation import write_ablation_comparison
from src.data.splits import make_patient_splits
from src.models.calibrate import fit_temperature, probabilities_from_logits
from src.models.evaluate import build_metrics, save_evaluation_plots, save_metrics
from src.models.fusion_model import FusionClassifier


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def _predict(model: nn.Module, loader: DataLoader) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    logits_list, labels_list = [], []
    with torch.inference_mode():
        for images, metadata, labels in loader:
            logits_list.append(model(images.cpu(), metadata.cpu()).cpu().numpy())
            labels_list.append(labels.cpu().numpy())
    return np.concatenate(logits_list), np.concatenate(labels_list)


def _train_epoch(model, loader, optimizer, criterion) -> float:
    model.train()
    if not any(parameter.requires_grad for parameter in model.image_backbone.parameters()):
        model.image_backbone.eval()
    total_loss, total_rows = 0.0, 0
    for images, metadata, labels in loader:
        images, metadata, labels = images.cpu(), metadata.cpu(), labels.cpu()
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(images, metadata), labels)
        loss.backward()
        optimizer.step()
        total_loss += float(loss.detach()) * len(labels)
        total_rows += len(labels)
    return total_loss / max(total_rows, 1)


def _config() -> dict:
    path = Path("config.yaml")
    if not path.exists():
        raise FileNotFoundError("Run training from artifacts/dermasense-ai, where config.yaml is located.")
    with path.open(encoding="utf-8") as source:
        return yaml.safe_load(source)


def train(image_only: bool = False, stage_one_epochs: int | None = None, stage_two_epochs: int | None = None) -> Path:
    config = _config()
    seed = int(config["seed"])
    seed_everything(seed)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))

    dataset_root = Path(config["dataset_root"])
    frame = verify_dataset(dataset_root)
    splits = make_patient_splits(frame, Path(config["processed_root"]) / "splits", seed)
    if config.get("cache_images", True):
        cache_root = Path(config["processed_root"]) / "image_cache"
        for split_name in splits:
            splits[split_name] = cache_resized_images(
                splits[split_name],
                cache_root,
                max_side=int(config["image_size"]) + 32,
            )
    train_values, other_values = fit_transform_metadata(
        splits["train"],
        {"validation": splits["validation"], "test": splits["test"]},
        Path(config["output_root"]) / ("preprocessor-image-only.joblib" if image_only else "preprocessor.joblib"),
    )
    image_size = int(config["image_size"])
    train_transform = transforms.Compose(
        [
            transforms.RandomResizedCrop(image_size, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(30),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15, hue=0.03),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )
    evaluation_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )
    train_data = LesionDataset(splits["train"], train_values, train_transform)
    validation_data = LesionDataset(splits["validation"], other_values["validation"], evaluation_transform)
    test_data = LesionDataset(splits["test"], other_values["test"], evaluation_transform)
    batch_size = int(config["batch_size"])
    workers = int(config["num_workers"])
    train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, num_workers=workers)
    validation_loader = DataLoader(validation_data, batch_size=batch_size, shuffle=False, num_workers=workers)
    test_loader = DataLoader(test_data, batch_size=batch_size, shuffle=False, num_workers=workers)

    counts = splits["train"]["diagnostic"].value_counts()
    class_weights = torch.tensor(
        [len(splits["train"]) / (len(CLASS_NAMES) * max(int(counts.get(name, 0)), 1)) for name in CLASS_NAMES],
        dtype=torch.float32,
    )
    model = FusionClassifier(
        metadata_dim=train_values.shape[1],
        num_classes=len(CLASS_NAMES),
        image_only=image_only,
        pretrained=True,
    ).cpu()
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    output_dir = Path(config["output_root"])
    output_dir.mkdir(parents=True, exist_ok=True)
    run_name = "image-only" if image_only else "fusion"
    log_path = output_dir / f"training-{run_name}.log"
    log_path.write_text(
        f"Run started; seed={seed}; image_only={image_only}; device=cpu\n",
        encoding="utf-8",
    )

    def log(message: str) -> None:
        print(message)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")

    best_state = copy.deepcopy(model.state_dict())
    best_macro_f1 = -1.0
    patience = int(config["early_stopping_patience"])

    stages = [
        ("frozen", False, int(stage_one_epochs or config["stage_one_epochs"]), 1e-3),
        ("fine-tune", True, int(stage_two_epochs or config["stage_two_epochs"]), float(config["learning_rate"])),
    ]
    for stage_name, unfreeze, epochs, learning_rate in stages:
        if stage_name == "fine-tune":
            model.load_state_dict(best_state)
        model.set_backbone_trainable(unfreeze, last_blocks=3)
        optimizer = AdamW(
            (parameter for parameter in model.parameters() if parameter.requires_grad),
            lr=learning_rate,
            weight_decay=float(config["weight_decay"]),
        )
        scheduler = CosineAnnealingLR(optimizer, T_max=max(epochs, 1))
        stage_best, stale_epochs = -1.0, 0
        for epoch in range(epochs):
            train_loss = _train_epoch(model, train_loader, optimizer, criterion)
            validation_logits, validation_labels = _predict(model, validation_loader)
            validation_f1 = float(
                f1_score(
                    validation_labels,
                    validation_logits.argmax(axis=1),
                    average="macro",
                    labels=list(range(len(CLASS_NAMES))),
                    zero_division=0,
                )
            )
            log(
                f"{stage_name} epoch {epoch + 1}/{epochs}: "
                f"train_loss={train_loss:.4f} validation_macro_f1={validation_f1:.4f}"
            )
            if validation_f1 > stage_best:
                stage_best = validation_f1
                stale_epochs = 0
                stage_state = copy.deepcopy(model.state_dict())
            else:
                stale_epochs += 1
            if validation_f1 > best_macro_f1:
                best_macro_f1 = validation_f1
                best_state = copy.deepcopy(model.state_dict())
            scheduler.step()
            if stale_epochs >= patience:
                break
        if stage_best < 0:
            raise RuntimeError(f"No validation epochs completed for stage {stage_name}.")
        # Carry the best checkpoint from this stage into fine-tuning.
        model.load_state_dict(stage_state)

    model.load_state_dict(best_state)
    validation_logits, validation_labels = _predict(model, validation_loader)
    temperature = fit_temperature(validation_logits, validation_labels)
    test_logits, test_labels = _predict(model, test_loader)
    raw_test_probabilities = probabilities_from_logits(test_logits)
    calibrated_probabilities = probabilities_from_logits(test_logits, temperature)
    metrics = {
        "model_version": "0.1.0-research",
        "dataset": "PAD-UFES-20",
        "split_method": "StratifiedGroupKFold(5), with distinct folds for validation and test",
        "seed": seed,
        "image_only": image_only,
        "class_names": list(CLASS_NAMES),
        "best_validation_macro_f1": best_macro_f1,
        "temperature": temperature,
        "test_before_calibration": build_metrics(
            test_labels, raw_test_probabilities, float(config["confidence_threshold"])
        ),
        "test_after_calibration": build_metrics(
            test_labels, calibrated_probabilities, float(config["confidence_threshold"])
        ),
    }
    metrics_path = output_dir / f"metrics-{run_name}.json"
    save_metrics(metrics, metrics_path)
    save_evaluation_plots(
        test_labels,
        calibrated_probabilities,
        output_dir / "plots",
        run_name,
        before_calibration=raw_test_probabilities,
    )
    ablation_path = write_ablation_comparison(output_dir)
    checkpoint_path = output_dir / f"checkpoint-{run_name}.pt"
    torch.save(
        {
            "model_state_dict": best_state,
            "metadata_dim": int(train_values.shape[1]),
            "class_names": list(CLASS_NAMES),
            "image_only": image_only,
            "temperature": temperature,
            "image_size": image_size,
            "seed": seed,
            "metrics_path": str(metrics_path),
        },
        checkpoint_path,
    )
    log(f"Saved checkpoint: {checkpoint_path}")
    log(f"Saved measured test metrics: {metrics_path}")
    if ablation_path:
        log(f"Saved measured ablation comparison: {ablation_path}")
    return checkpoint_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the PAD-UFES-20 model using CPU only.")
    parser.add_argument("--image-only", action="store_true", help="Train the image-only ablation.")
    parser.add_argument("--stage-one-epochs", type=int, default=None)
    parser.add_argument("--stage-two-epochs", type=int, default=None)
    args = parser.parse_args()
    train(args.image_only, args.stage_one_epochs, args.stage_two_epochs)


if __name__ == "__main__":
    main()
