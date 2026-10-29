import pandas as pd
import pytest
from PIL import Image

from src.data.dataset import cache_resized_images, verify_dataset


def test_dataset_verifier_reports_missing_pad_files(tmp_path):
    with pytest.raises(FileNotFoundError, match="PAD-UFES-20 files are missing"):
        verify_dataset(tmp_path)


def test_image_cache_keeps_aspect_ratio_and_updates_paths(tmp_path):
    source = tmp_path / "original.png"
    Image.new("RGB", (400, 200), color=(120, 80, 60)).save(source)
    rows = pd.DataFrame([{"img_id": "image-1", "image_path": str(source)}])

    cached = cache_resized_images(rows, tmp_path / "cache", max_side=256)

    assert cached.loc[0, "image_path"] != str(source)
    with Image.open(cached.loc[0, "image_path"]) as image:
        assert image.size == (256, 128)
