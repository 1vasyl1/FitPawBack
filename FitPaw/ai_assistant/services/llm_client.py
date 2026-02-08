from dataclasses import dataclass
from typing import Optional

from django.conf import settings

import requests

try:
    from google import genai
except Exception:
    genai = None


@dataclass
class LLMResult:
    ok: bool
    text: str
    error: Optional[str] = None


def _is_rate_limited(err: str) -> bool:
    s = (err or "").lower()
    return (
        "resource_exhausted" in s
        or "quota" in s
        or "rate limit" in s
        or "429" in s
        or "too many requests" in s
    )


def _build_prompt(user_message: str, context: str = "") -> str:
    return (
        "You are FitPaw Gym Assistant.\n"
        "Rules:\n"
        "- Help with FitPaw site navigation, trainers, lesson schedule, QR.\n"
        "- You must NOT book sessions, modify user data, or access private info.\n"
        "- For gym advice: give general tips; for personalized plans recommend FitPaw trainers.\n"
        "- Reply in the same language as the user (PL or EN).\n\n"
        f"{context}\n\n"
        f"User: {user_message}\n"
        "Assistant:"
    )


def _gemini_generate(prompt: str) -> LLMResult:
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash") or "gemini-1.5-flash"

    if not api_key:
        return LLMResult(ok=False, text="", error="missing_api_key")

    if genai is None:
        return LLMResult(ok=False, text="", error="google_genai_not_installed")

    try:
        client = genai.Client(api_key=api_key)  # LLM
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        text = (getattr(resp, "text", "") or "").strip()
        if not text:
            return LLMResult(ok=False, text="", error="empty_response")
        return LLMResult(ok=True, text=text)

    except Exception as e:
        err = str(e)
        if _is_rate_limited(err):
            return LLMResult(ok=False, text="", error="rate_limited")
        return LLMResult(ok=False, text="", error="llm_failed")


def _ollama_generate(prompt: str) -> LLMResult:
    base_url = getattr(settings, "OLLAMA_BASE_URL", "") or "http://127.0.0.1:11434"
    model_name = getattr(settings, "OLLAMA_MODEL", "") or "llama3.1:8b"
    timeout_s = int(getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 60) or 60)

    try:
        r = requests.post(
            f"{base_url.rstrip('/')}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
            },
            timeout=timeout_s,
        )
        if r.status_code != 200:
            return LLMResult(ok=False, text="", error="ollama_failed")

        data = r.json() if r.content else {}
        text = (data.get("response") or "").strip()
        if not text:
            return LLMResult(ok=False, text="", error="empty_response")

        return LLMResult(ok=True, text=text)

    except Exception:
        return LLMResult(ok=False, text="", error="ollama_failed")


def generate_reply(user_message: str, context: str = "") -> LLMResult:
    prompt = _build_prompt(user_message, context=context)

    primary = getattr(settings, "LLM_PRIMARY", "gemini") or "gemini"
    enable_fallback = bool(getattr(settings, "LLM_ENABLE_FALLBACK", True))

    if primary == "ollama":
        res = _ollama_generate(prompt)
        if res.ok:
            return res
        if enable_fallback:
            return _gemini_generate(prompt)
        return res

    res = _gemini_generate(prompt)
    if res.ok:
        return res

    if enable_fallback and res.error == "rate_limited":
        return _ollama_generate(prompt)

    return res
