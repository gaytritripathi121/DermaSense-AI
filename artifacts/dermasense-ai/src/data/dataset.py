from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from PIL import Image

CLASS_NAMES = ("ACK", "BCC", "MEL", "NEV", "SCC", "SEK")
IMAGE_PARTS = ("imgs_part_1", "imgs_part_2", "imgs_part_3")
REQUIRED_COLUMNS = ("patient_id", "img_id", "diagnostic")


def _image_key(value: object) -> str:
    return Path(str(value).strip()).stem.casefold()


def verify_dataset(dataset_root: Path = Path("data/raw")) -> pd.DataFrame:
    """Read PAD-UFES-20 metadata and attach only images that exist locally."""
    metadata_path = dataset_root / "metadata.csv"
    missing = [str(path) for path in [metadata_path, *(dataset_root / part for part in IMAGE_PARTS)] if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "PAD-UFES-20 files are missing. Expected metadata.csv and all image "
            f"folders under {dataset_root.resolve()}. Missing: {', '.join(missing)}"
        )

    frame = pd.read_csv(metadata_path, low_memory=False)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValueError(
            f"{metadata_path} is missing required columns: {', '.join(missing_columns)}"
        )

    image_by_key: dict[str, Path] = {}
    for part in IMAGE_PARTS:
        for image_path in sorted((dataset_root / part).rglob("*")):
            if image_path.is_file() and image_path.suffix.casefold() in {".jpg", ".jpeg", ".png"}:
                image_by_key.setdefault(_image_key(image_path.name), image_path)

    frame["diagnostic"] = frame["diagnostic"].astype("string").str.strip().str.upper()
    frame["image_path"] = frame["img_id"].map(
        lambda image_id: str(image_by_key.get(_image_key(image_id), "")) if pd.notna(image_id) else ""
    )
    usable = frame["image_path"].ne("") & frame["patient_id"].notna() & frame["diagnostic"].isin(CLASS_NAMES)
    dropped = int((~usable).sum())
    frame = frame.loc[usable].copy().reset_index(drop=True)
    if frame.empty:
        raise ValueError("No usable labeled rows with patient IDs and matching image files were found.")

    print(f"Metadata rows: {len(pd.read_csv(metadata_path, usecols=['img_id']))}")
    print(f"Usable labeled images: {len(frame)}")
    print(f"Rows excluded for missing images, patient IDs, or unsupported labels: {dropped}")
    print(f"Distinct patients: {frame['patient_id'].nunique()}")
    print("Class counts:")
    print(frame["diagnostic"].value_counts().reindex(CLASS_NAMES, fill_value=0).to_string())
    return frame


class LesionDataset:
    def __init__(
        self,
        frame: pd.DataFrame,
        metadata_values,
        transform=None,
    ) -> None:
        import torch

        self.frame = frame.reset_index(drop=True)
        self.metadata_values = torch.as_tensor(metadata_values, dtype=torch.float32)
        self.transform = transform
        self.class_to_index = {name: index for index, name in enumerate(CLASS_NAMES)}
        if len(self.frame) != len(self.metadata_values):
            raise ValueError("Metadata feature rows must match the image rows.")

    def __len__(self) -> int:
        return len(self.frame)

    def __getitem__(self, index: int):
        import torch

        row = self.frame.iloc[index]
        with Image.open(row["image_path"]) as source:
            image = source.convert("RGB")
        if self.transform:
            image = self.transform(image)
        label = self.class_to_index[str(row["diagnostic"])]
        return image, self.metadata_values[index], torch.tensor(label, dtype=torch.long)


def cache_resized_images(
    frame: pd.DataFrame,
    cache_dir: Path,
    max_side: int = 256,
) -> pd.DataFrame:
    """Cache decoded, aspect-preserving thumbnails to avoid repeated disk decoding."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    result = frame.copy().reset_index(drop=True)
    cached_paths = []
    for _, row in result.iterrows():
        key = hashlib.sha256(f"{row['img_id']}:{row['image_path']}".encode("utf-8")).hexdigest()[:20]
        cached = cache_dir / f"{key}.jpg"
        if not cached.exists():
            with Image.open(row["image_path"]) as source:
                image = source.convert("RGB")
                image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                image.save(cached, format="JPEG", quality=92, optimize=True)
        cached_paths.append(str(cached))
    result["image_path"] = cached_paths
    return result


def main() -> None:
    try:
        verify_dataset()
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
