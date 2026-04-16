"""
Schedule normalization helpers.

This keeps schedule parsing separate from persistence and worker runtime.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


def cron_from_preset(preset: str, timezone: str = "UTC") -> str:
    """Generate a cron expression from a supported preset."""
    presets = {
        "every_minute": "* * * * *",
        "every_5_min": "*/5 * * * *",
        "every_15_min": "*/15 * * * *",
        "every_30_min": "*/30 * * * *",
        "hourly": "0 * * * *",
        "daily": "0 0 * * *",
        "weekly": "0 0 * * 1",
        "monthly": "0 0 1 * *",
    }
    return presets.get(preset, "0 * * * *")


def normalize_schedule_config(config: dict | None) -> dict:
    """Normalize user/LLM-friendly schedule config to runtime cron config."""
    config = dict(config or {})

    if config.get("cron"):
        return config

    interval_minutes = config.get("interval_minutes")
    if isinstance(interval_minutes, int) and interval_minutes > 0:
        if interval_minutes == 1:
            config["cron"] = "* * * * *"
        elif interval_minutes < 60 and 60 % interval_minutes == 0:
            config["cron"] = f"*/{interval_minutes} * * * *"
        elif interval_minutes % 60 == 0 and interval_minutes < 24 * 60:
            config["cron"] = f"0 */{interval_minutes // 60} * * *"
        elif interval_minutes == 24 * 60:
            config["cron"] = "0 0 * * *"

    schedule_preset = config.get("schedule_preset")
    if not config.get("cron") and isinstance(schedule_preset, str):
        config["cron"] = cron_from_preset(schedule_preset, config.get("timezone", "UTC"))

    return config


def next_run_from_cron(cron: str) -> Optional[datetime]:
    """
    Calculate the next run for the small cron subset emitted by this app.

    Supported shapes:
    - * * * * *
    - */N * * * *
    - M * * * *
    - M H * * *
    - M H * * D
    - M H D * *
    """
    parts = cron.strip().split()
    if len(parts) != 5:
        return None

    minute, hour, day_of_month, month, day_of_week = parts
    now = datetime.now().replace(second=0, microsecond=0)

    if minute == "*" and hour == "*" and day_of_month == "*" and month == "*" and day_of_week == "*":
        return now + timedelta(minutes=1)

    if minute.startswith("*/") and hour == "*" and day_of_month == "*" and month == "*" and day_of_week == "*":
        step = int(minute[2:] or "1")
        if step <= 0:
            return None
        candidate = now + timedelta(minutes=1)
        remainder = candidate.minute % step
        if remainder:
            candidate += timedelta(minutes=step - remainder)
        return candidate.replace(second=0, microsecond=0)

    def parse_int(token: str) -> Optional[int]:
        return None if token == "*" else int(token)

    minute_value = parse_int(minute)
    hour_value = parse_int(hour)
    day_value = parse_int(day_of_month)
    month_value = parse_int(month)
    weekday_value = parse_int(day_of_week)

    for day_offset in range(0, 370):
        base_date = now.date() + timedelta(days=day_offset)

        if month_value is not None and base_date.month != month_value:
            continue
        if day_value is not None and base_date.day != day_value:
            continue
        if weekday_value is not None and ((base_date.weekday() + 1) % 7) != weekday_value:
            continue

        candidate_hours = [hour_value] if hour_value is not None else list(range(24))
        candidate_minute = minute_value if minute_value is not None else 0

        for candidate_hour in candidate_hours:
            candidate = datetime.combine(base_date, datetime.min.time()).replace(
                hour=candidate_hour,
                minute=candidate_minute,
            )
            if candidate > now:
                return candidate

    return now + timedelta(minutes=1)
