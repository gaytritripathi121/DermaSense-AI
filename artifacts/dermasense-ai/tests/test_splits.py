import pandas as pd

from src.data.splits import assert_patient_disjoint, make_patient_splits


def test_patient_grouped_splits_never_share_patients(tmp_path):
    rows = [
        {"patient_id": f"patient-{patient}", "diagnostic": label, "img_id": f"{patient}-{label}"}
        for patient in range(10)
        for label in ("ACK", "BCC", "MEL", "NEV", "SCC", "SEK")
    ]
    splits = make_patient_splits(pd.DataFrame(rows), tmp_path, seed=42)

    assert set(splits) == {"train", "validation", "test"}
    assert_patient_disjoint(splits)
    assert set(splits["train"]["patient_id"]).isdisjoint(splits["test"]["patient_id"])
    assert all((tmp_path / f"{name}.csv").exists() for name in splits)
