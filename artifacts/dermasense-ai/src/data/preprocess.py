from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

IDENTIFIER_OR_LEAKAGE_COLUMNS = {
    "patient_id",
    "lesion_id",
    "img_id",
    "image_path",
    "diagnostic",
    "biopsed",
}
NUMERIC_CANDIDATES = {"age", "diameter_1", "diameter_2"}


def create_preprocessor(train_frame: pd.DataFrame):
    feature_columns = [
        column for column in train_frame.columns
        if column not in IDENTIFIER_OR_LEAKAGE_COLUMNS
    ]
    numeric_columns = [column for column in feature_columns if column in NUMERIC_CANDIDATES]
    categorical_columns = [column for column in feature_columns if column not in numeric_columns]

    numeric_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="constant", fill_value="UNK", keep_empty_features=True)),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    processor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_columns),
            ("categorical", categorical_pipeline, categorical_columns),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return processor, feature_columns


def clean_features(frame: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    result = frame.reindex(columns=feature_columns).copy()
    result = result.replace(r"^\s*$", np.nan, regex=True)
    for column in NUMERIC_CANDIDATES.intersection(result.columns):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    for column in result.select_dtypes(include=["object", "string"]).columns:
        result[column] = result[column].replace({"UNK": np.nan, "unknown": np.nan, "Unknown": np.nan})
    return result


def fit_transform_metadata(
    train_frame: pd.DataFrame,
    other_frames: dict[str, pd.DataFrame],
    output_path: Path = Path("outputs/preprocessor.joblib"),
):
    """Fit imputation/scaling/encoding on train rows only."""
    processor, feature_columns = create_preprocessor(train_frame)
    train_values = processor.fit_transform(clean_features(train_frame, feature_columns)).astype(np.float32)
    transformed = {
        name: processor.transform(clean_features(frame, feature_columns)).astype(np.float32)
        for name, frame in other_frames.items()
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dump({"processor": processor, "feature_columns": feature_columns}, output_path)
    return train_values, transformed
