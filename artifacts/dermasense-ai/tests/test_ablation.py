import json

from src.models.ablation import write_ablation_comparison


def test_ablation_comparison_only_uses_measured_runs(tmp_path):
    (tmp_path / "metrics-fusion.json").write_text(
        json.dumps({"test_after_calibration": {"accuracy": 0.82, "macro_f1": 0.78}}),
        encoding="utf-8",
    )

    comparison = write_ablation_comparison(tmp_path)

    assert comparison is not None
    text = comparison.read_text(encoding="utf-8")
    assert "| Image + history | 0.8200 | — | 0.7800 |" in text
    assert "Image only" not in text
