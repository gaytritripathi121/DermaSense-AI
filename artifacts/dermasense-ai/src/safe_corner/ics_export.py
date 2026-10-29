from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def create_weekly_calendar(items: list[dict], start_date: date | None = None) -> str:
    """Create a standards-shaped calendar file with weekly reminder events."""
    start = start_date or date.today()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DermaSense AI//Safe Corner//EN",
        "CALSCALE:GREGORIAN",
    ]
    for index, item in enumerate(items):
        event_day = start + timedelta(days=index)
        time_value = str(item.get("time", "09:00"))
        try:
            parsed_time = datetime.strptime(time_value, "%H:%M").time()
        except ValueError:
            parsed_time = datetime.strptime("09:00", "%H:%M").time()
        begins = datetime.combine(event_day, parsed_time).strftime("%Y%m%dT%H%M%S")
        ends = (datetime.combine(event_day, parsed_time) + timedelta(minutes=15)).strftime("%Y%m%dT%H%M%S")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{_escape(str(item.get('rule_id', 'routine')))}-{index}@dermasense.local",
                f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{begins}",
                f"DTEND:{ends}",
                f"SUMMARY:{_escape(str(item.get('title', 'Skin wellness reminder')))}",
                f"DESCRIPTION:{_escape(str(item.get('guidance', '')))}",
                "RRULE:FREQ=WEEKLY;COUNT=4",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
