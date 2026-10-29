from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path

import yaml

RULES_PATH = Path(__file__).with_name("rules.yaml")


def _parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as error:
        raise ValueError(f"Time must use 24-hour HH:MM format: {value}") from error


def plan_day(
    wake_time: str = "07:00",
    sleep_time: str = "22:00",
    predicted_class: str | None = None,
    confidence: float | None = None,
    confidence_threshold: float = 0.70,
    rules_path: Path = RULES_PATH,
) -> dict:
    """Create a transparent schedule using only the curated YAML rules."""
    wake = _parse_time(wake_time)
    sleep = _parse_time(sleep_time)
    wake_minutes = wake.hour * 60 + wake.minute
    sleep_minutes = sleep.hour * 60 + sleep.minute
    if sleep_minutes <= wake_minutes:
        sleep_minutes += 24 * 60

    rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    valid_prediction = confidence is not None and confidence >= confidence_threshold and predicted_class is not None
    items = []
    if valid_prediction and predicted_class in rules["urgent_review"]["trigger_classes"]:
        items.append({**rules["urgent_review"], "time": wake_time, "kind": "clinician_review"})
    elif not valid_prediction:
        items.append({**rules["low_confidence"], "time": wake_time, "kind": "clinician_review"})

    slot_minutes = {
        "morning": wake_minutes + 30,
        "before_outdoors": wake_minutes + 60,
        "outdoors": wake_minutes + 180,
        "afternoon": max(wake_minutes + 60, (wake_minutes + sleep_minutes) // 2),
        "evening": sleep_minutes - 60,
        "anytime": wake_minutes + 90,
    }
    for rule in rules["general"]:
        minutes = min(max(slot_minutes[rule["slot"]], wake_minutes), sleep_minutes - 1)
        scheduled = (datetime.combine(datetime.today(), time.min) + timedelta(minutes=minutes)).time()
        items.append({**rule, "time": scheduled.strftime("%H:%M"), "kind": "general"})
    items.sort(key=lambda item: item["time"])
    return {
        "date": datetime.now().date().isoformat(),
        "items": items,
        "disclaimer": rules["disclaimer"],
    }
