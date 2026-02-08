from datetime import date, timedelta
from typing import Optional, List
import re

from schedule.models import Trainer, Lessons


def list_trainers(limit: int = 50) -> List[Trainer]:
    return list(Trainer.objects.all().order_by("name")[:limit])


def lessons_for_date(d: date) -> List[Lessons]:
    return list(Lessons.objects.select_related("trainer").filter(date=d).order_by("start_time"))


def parse_day(text: str) -> Optional[date]:
    s = (text or "").strip().lower()
    if not s:
        return None

    if s == "today":
        return date.today()
    if s == "tomorrow":
        return date.today() + timedelta(days=1)

    # normalize: allow YYYY/MM/DD or YYYY.MM.DD
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except ValueError:
            return None

    # normal iso
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None
