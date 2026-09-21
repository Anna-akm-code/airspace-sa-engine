"""Position freshness visibility; mirrors the existing detector's age threshold."""

from .models import Aircraft


def position_age(aircraft: Aircraft, now: int) -> int | None:
    return None if aircraft.time_position is None else now - aircraft.time_position


def position_freshness(aircraft: Aircraft, now: int, max_age_s: int = 60) -> str:
    age = position_age(aircraft, now)
    if age is None:
        return 'missing_time'
    return 'stale' if age > max_age_s else 'fresh'
