from datetime import date

from src.safe_corner.ics_export import create_weekly_calendar


def test_calendar_export_contains_weekly_reminders_and_escapes_text():
    calendar = create_weekly_calendar(
        [{"time": "09:15", "rule_id": "UV-01", "title": "Shade, please", "guidance": "Use shade; if outdoors, reapply."}],
        start_date=date(2026, 1, 5),
    )
    assert "BEGIN:VCALENDAR" in calendar
    assert "RRULE:FREQ=WEEKLY;COUNT=4" in calendar
    assert "DESCRIPTION:Use shade\\; if outdoors\\, reapply." in calendar
    assert calendar.endswith("END:VCALENDAR\r\n")
