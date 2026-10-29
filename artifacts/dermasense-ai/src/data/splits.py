from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold


def assert_patient_disjoint(splits: dict[str, pd.DataFrame]) -> None:
    names = list(splits)
    for left_index, left_name in enumerate(names):
        left = set(splits[left_name]["patient_id"].dropna().astype(str))
        for right_name in names[left_index + 1 :]:
            right = set(splits[right_name]["patient_id"].dropna().astype(str))
            overlap = left & right
            if overlap:
                raise ValueError(
                    f"Patient leakage between {left_name} and {right_name}: "
                    f"{len(overlap)} patient IDs overlap."
                )


def make_patient_splits(
    frame: pd.DataFrame,
    output_dir: Path = Path("data/processed/splits"),
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """Use two folds for validation/test and keep patients disjoint."""
    required = {"patient_id", "diagnostic"}
    if not required.issubset(frame.columns):
        raise ValueError("Patient-grouped splitting requires patient_id and diagnostic columns.")
    if frame["patient_id"].isna().any():
        raise ValueError("Rows with missing patient_id must be removed before splitting.")
    if frame["patient_id"].nunique() < 5:
        raise ValueError("At least five distinct patients are required for five-fold splitting.")

    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    folds = [valid_index for _, valid_index in splitter.split(frame, frame["diagnostic"], frame["patient_id"])]
    test_indices = folds[0]
    validation_indices = folds[1]
    held_out = set(test_indices) | set(validation_indices)
    train_indices = [index for index in range(len(frame)) if index not in held_out]
    splits = {
        "train": frame.iloc[train_indices].copy().reset_index(drop=True),
        "validation": frame.iloc[validation_indices].copy().reset_index(drop=True),
        "test": frame.iloc[test_indices].copy().reset_index(drop=True),
    }
    assert_patient_disjoint(splits)

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, split in splits.items():
        split.to_csv(output_dir / f"{name}.csv", index=False)
    return splits
