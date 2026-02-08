from dataclasses import dataclass
import re

from .llm_client import generate_reply
from .schedule_reader import list_trainers, lessons_for_date, parse_day


@dataclass
class AssistantResponse:
    reply: str


def _detect_lang(text: str) -> str:
    s = (text or "").lower()
    pl_chars = set("ąćęłńóśźż")
    return "pl" if any(ch in pl_chars for ch in s) else "en"


def _t(lang: str, key: str) -> str:
    data = {
        "pl": {
            "type_msg": "Napisz wiadomość 🙂",
            "no_trainers": "Nie znaleziono trenerów. Dodaj ich w panelu staff.",
            "trainers_header": "Trenerzy FitPaw:",
            "day_hint": "Podaj dzień: today / tomorrow / YYYY-MM-DD",
            "no_lessons": "Brak zajęć na {d}.",
            "schedule_header": "Grafik na {d}:",
            "tba": "Do ustalenia",
            "gym": "Siłownia",
            "qr": "QR: zeskanuj przy wejściu, aby potwierdzić dostęp. Jeśli nie działa — skontaktuj się z obsługą.",
            "fallback": "Mogę pomóc z grafikiem, trenerami, QR i ogólnymi poradami treningowymi.",
            "trainer_disclaimer": "Dla lepszych efektów i dokładniejszych zaleceń skonsultuj się z naszymi trenerami 💪",
            "llm_rate_limited": "AI jest chwilowo niedostępne (limit). Spróbuj ponownie za chwilę.",
            "llm_not_configured": "AI nie jest skonfigurowane. Skontaktuj się z administratorem.",
            "llm_not_installed": "Brakuje biblioteki AI na serwerze. Skontaktuj się z administratorem.",
            "hello": "Cześć! Zapytaj mnie o grafik, trenerów, QR albo ogólne porady treningowe 🙂",
        },
        "en": {
            "type_msg": "Type a message 🙂",
            "no_trainers": "No trainers found. Please add trainers in the staff panel.",
            "trainers_header": "FitPaw Trainers:",
            "day_hint": "Give a day: today / tomorrow / YYYY-MM-DD",
            "no_lessons": "No lessons found for {d}.",
            "schedule_header": "Lessons for {d}:",
            "tba": "TBA",
            "gym": "Gym",
            "qr": "QR: scan it at the entrance to confirm access. If it fails, contact staff.",
            "fallback": "I can help with schedule, trainers, QR, and general gym tips.",
            "trainer_disclaimer": "For best results and a plan tailored to you, please talk to our trainers 💪",
            "llm_rate_limited": "AI is temporarily unavailable (quota). Please try again in a moment.",
            "llm_not_configured": "AI is not configured. Please contact the admin.",
            "llm_not_installed": "AI library is missing on the server. Please contact the admin.",
            "hello": "Hi! Ask me about schedule, trainers, QR, or general gym tips 🙂",
        },
    }
    return data.get(lang, data["en"])[key]


def _needs_trainer_disclaimer(user_text: str) -> bool:
    s = (user_text or "").lower()
    return any(
        k in s
        for k in [
            "bench", "workout", "gym", "muscle", "bulk", "cut", "diet", "calories", "protein", "weight",
            "chest", "back", "legs", "shoulders", "abs",
            "strength", "hypertrophy", "cardio",
            "ćwic", "cwic", "trening", "dieta", "kalor", "masa", "sił", "sil",
            "klatka", "plecy", "nogi", "barki", "brzuch",
        ]
    )


def _format_trainers(lang: str) -> str:
    trainers = list_trainers()
    if not trainers:
        return _t(lang, "no_trainers")

    blocks = [_t(lang, "trainers_header")]
    for t in trainers:
        name = (t.name or "").strip()
        bio = (t.bio or "").strip()
        if bio:
            blocks.append(f"{name}\n{bio}")
        else:
            blocks.append(name)

    return "\n\n".join(blocks)


def _extract_day_from_text(text: str) -> str:
    """
    Supports:
    - today / tomorrow
    - YYYY-MM-DD
    - YYYY/MM/DD
    - YYYY.MM.DD
    - YYYY MM DD
    - February 14, 2026 / Feb 14 2026
    - 14 February 2026
    - 14 lutego 2026 (PL)
    """
    import re

    s = (text or "").strip().lower()
    if not s:
        return "today"

    if "today" in s:
        return "today"
    if "tomorrow" in s:
        return "tomorrow"

    def iso(y: str, mo: int, d: int) -> str:
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"

    # 1) Direct numeric formats: 2026-02-14 / 2026/02/14 / 2026.02.14
    m = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", s)
    if m:
        return iso(m.group(1), int(m.group(2)), int(m.group(3)))

    # 2) Spaces: 2026 02 14
    m = re.search(r"\b(\d{4})\s+(\d{1,2})\s+(\d{1,2})\b", s)
    if m:
        return iso(m.group(1), int(m.group(2)), int(m.group(3)))

    # 3) Month names (EN + PL)
    month_map = {
        # EN full + short
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,

        # PL (nominative + genitive)
        "styczen": 1, "stycznia": 1,
        "luty": 2, "lutego": 2,
        "marzec": 3, "marca": 3,
        "kwiecien": 4, "kwietnia": 4,
        "maj": 5, "maja": 5,
        "czerwiec": 6, "czerwca": 6,
        "lipiec": 7, "lipca": 7,
        "sierpien": 8, "sierpnia": 8,
        "wrzesien": 9, "wrzesnia": 9,
        "pazdziernik": 10, "pazdziernika": 10,
        "listopad": 11, "listopada": 11,
        "grudzien": 12, "grudnia": 12,
    }

    # normalize Polish diacritics to plain for matching
    # (simple replacements enough for months)
    s_norm = (
        s.replace("ą", "a").replace("ć", "c").replace("ę", "e").replace("ł", "l")
        .replace("ń", "n").replace("ó", "o").replace("ś", "s").replace("ź", "z").replace("ż", "z")
    )

    # Pattern A: February 14, 2026
    m = re.search(r"\b([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?[,]?\s+(\d{4})\b", s_norm)
    if m:
        mon = m.group(1)
        if mon in month_map:
            return iso(m.group(3), month_map[mon], int(m.group(2)))

    # Pattern B: 14 February 2026
    m = re.search(r"\b(\d{1,2})\s+([a-z]+)[,]?\s+(\d{4})\b", s_norm)
    if m:
        mon = m.group(2)
        if mon in month_map:
            return iso(m.group(3), month_map[mon], int(m.group(1)))

    return "today"


def _format_schedule(day_token: str, lang: str) -> str:
    d = parse_day(day_token)
    if not d:
        return _t(lang, "day_hint")

    lessons = lessons_for_date(d)
    if not lessons:
        return _t(lang, "no_lessons").format(d=d.isoformat())

    header = _t(lang, "schedule_header").format(d=d.isoformat())
    lines = [header]

    for l in lessons:
        trainer = l.trainer.name if l.trainer else _t(lang, "tba")
        loc = l.location or _t(lang, "gym")
        lines.append(f"- {l.subject} ({l.start_time}-{l.end_time}) • {trainer} • {loc}")

    return "\n".join(lines)


def _trainers_compact_context() -> str:
    trainers = list_trainers()
    if not trainers:
        return "Trainers in DB: none"

    lines = ["Trainers in DB (use ONLY these names):"]
    for t in trainers[:30]:
        name = (t.name or "").strip()
        bio = (t.bio or "").strip()
        if bio:
            lines.append(f"- {name}: {bio[:220]}")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines)


def _is_list_intent(s: str) -> bool:
    return any(
        k in s
        for k in [
            "list", "show", "all", "names", "who are the trainers", "tell me about the trainers",
            "lista", "pokaż", "pokaz", "wszyscy", "wszystkie", "kim są trenerzy",
        ]
    ) or s.strip() in ("trainer", "trainers", "coach", "coaches", "trener", "trenerzy")


def _is_recommendation_intent(s: str) -> bool:
    return any(
        k in s
        for k in [
            "recommend", "suggest", "which trainer", "best trainer", "who is the best", "pick one", "for me",
            "polecasz", "poleć", "jaki trener", "najlepszy trener", "kogo wybrać", "dla mnie",
            "spine", "back pain", "good back", "strong back", "plecy", "kręgosłup", "kregoslup",
        ]
    )


def handle_message(message: str) -> AssistantResponse:
    msg = (message or "").strip()
    lang = _detect_lang(msg)

    if not msg:
        return AssistantResponse(_t(lang, "type_msg"))

    low = msg.lower().strip()

    if low in ("hi", "hello", "hey", "yo", "cześć", "czesc", "siema", "hej"):
        return AssistantResponse(_t(lang, "hello"))

    if "qr" in low:
        return AssistantResponse(_t(lang, "qr"))

    SCHEDULE_KEYWORDS = [
        "schedule", "lesson", "lessons", "class", "classes",
        "grafik", "zaj", "lekcj", "plan",
        "training day", "training days",
    ]
    if any(k in low for k in SCHEDULE_KEYWORDS):
        day_token = _extract_day_from_text(msg)
        return AssistantResponse(_format_schedule(day_token, lang))

    TRAINER_KEYWORDS = ["trainer", "trainers", "coach", "coaches", "trener", "trenerzy"]
    if any(k in low for k in TRAINER_KEYWORDS):
        if _is_recommendation_intent(low) and not _is_list_intent(low):
            ctx = (
                "FitPaw context:\n"
                "- You can answer about trainers and the lesson schedule.\n"
                "- You must NOT book sessions or modify user data.\n"
                "- Use ONLY trainers listed below (from DB). If DB has no trainers, say so.\n"
                "- If user asks to choose a trainer: pick ONE best match and explain WHY (2-4 bullets).\n"
                "- Reply in the same language as the user (PL or EN).\n\n"
                + _trainers_compact_context()
            )
            llm = generate_reply(msg, context=ctx)
            if llm.ok:
                reply = llm.text
                if _needs_trainer_disclaimer(msg):
                    reply += "\n\n" + _t(lang, "trainer_disclaimer")
                return AssistantResponse(reply)

            if llm.error == "rate_limited":
                return AssistantResponse(_t(lang, "llm_rate_limited"))
            if llm.error == "missing_api_key":
                return AssistantResponse(_t(lang, "llm_not_configured"))
            if llm.error == "google_genai_not_installed":
                return AssistantResponse(_t(lang, "llm_not_installed"))

            return AssistantResponse(_format_trainers(lang))

        return AssistantResponse(_format_trainers(lang))

    ctx = (
        "FitPaw context:\n"
        "- Help with: trainers, lesson schedule, QR, site navigation.\n"
        "- Do not book sessions and do not modify user data.\n"
        "- Reply in the same language as the user (PL or EN).\n\n"
        + _trainers_compact_context()
    )

    llm = generate_reply(msg, context=ctx)
    if llm.ok:
        reply = llm.text
        if _needs_trainer_disclaimer(msg):
            reply += "\n\n" + _t(lang, "trainer_disclaimer")
        return AssistantResponse(reply)

    if llm.error == "rate_limited":
        return AssistantResponse(_t(lang, "llm_rate_limited"))
    if llm.error == "missing_api_key":
        return AssistantResponse(_t(lang, "llm_not_configured"))
    if llm.error == "google_genai_not_installed":
        return AssistantResponse(_t(lang, "llm_not_installed"))

    return AssistantResponse(_t(lang, "fallback"))
