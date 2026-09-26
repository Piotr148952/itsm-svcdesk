# ai-generated: 100% - Codex implemented Warsaw business-time arithmetic from the receipted specification.
from datetime import datetime, time, timedelta, timezone
import re
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")
TARGETS = {"P1": (15, 240), "P2": (60, 480), "P3": (240, 1440), "P4": (480, 4320)}
RFC3339 = re.compile(r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})\Z")


def parse_instant(value: str) -> datetime:
    if not RFC3339.fullmatch(value):
        raise ValueError("Expected an RFC3339 instant with timezone offset")
    return datetime.fromisoformat(value.upper().replace("Z", "+00:00")).astimezone(timezone.utc)


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def business_open(value: datetime) -> bool:
    local = value.astimezone(WARSAW)
    return local.weekday() < 5 and time(8) <= local.time() < time(16)


def add_business_minutes(value: datetime, minutes: int) -> datetime:
    local = value.astimezone(WARSAW)
    remaining = timedelta(minutes=minutes)
    while True:
        opening = datetime.combine(local.date(), time(8), WARSAW)
        closing = datetime.combine(local.date(), time(16), WARSAW)
        if local.weekday() >= 5 or local >= closing:
            local = datetime.combine(local.date() + timedelta(days=1), time(8), WARSAW)
            continue
        local = max(local, opening)
        available = closing - local
        if remaining <= available:
            return (local + remaining).astimezone(timezone.utc)
        remaining -= available
        local = datetime.combine(local.date() + timedelta(days=1), time(8), WARSAW)


def deadlines(created: datetime, priority: str) -> dict:
    ack, resolve = TARGETS[priority]
    def due(minutes: int) -> str:
        instant = (created + timedelta(minutes=minutes) if priority == "P1"
                   else add_business_minutes(created, minutes))
        return stamp(instant)
    return {"ack_due_at": due(ack), "resolve_due_at": due(resolve)}
