from __future__ import annotations

import json
from pathlib import Path


VARIANTS = (("fusion", "Image + history"), ("image-only", "Image only"))
METRICS = ("accuracy", "balanced_accuracy", "macro_f1", "ece", "coverage", "accuracy_at_threshold")


def write_ablation_comparison(output_dir: Path) -> Path | None:
    """Write a measured Markdown comparison for variants that have completed evaluation."""
    rows: dict[str, dict] = {}
    for file_stem, label in VARIANTS:
        path = output_dir / f"metrics-{file_stem}.json"
        if not path.exists():
            continue
        metrics = json.loads(path.read_text(encoding="utf-8"))
        measured = metrics.get("test_after_calibration")
        if not isinstance(measured, dict):
            raise ValueError(f"Missing calibrated test metrics in {path}.")
        rows[label] = measured

    if not rows:
        return None
    heading = ["Variant", *METRICS]
    lines = [
        "| " + " | ".join(heading) + " |",
        "| " + " | ".join(["---"] * len(heading)) + " |",
    ]
    for label, measured in rows.items():
        values = [label]
        for metric in METRICS:
            value = measured.get(metric)
            values.append("—" if value is None else f"{float(value):.4f}")
        lines.append("| " + " | ".join(values) + " |")
    path = output_dir / "ablation-comparison.md"
    path.write_text(
        "# Measured held-out ablation results\n\n"
        "Patient-grouped test partition; after temperature scaling. "
        "A dash means the metric was not available for that run.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    return path
