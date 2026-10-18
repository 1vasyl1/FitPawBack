---
name: fitpawback-ai-assistant
description: "The ai_assistant module in the FitPawBack Django backend: a hybrid Gemini + Ollama LLM-powered gym chat assistant. Use when working on chatbot/assistant features, LLM integration, Ollama fallback configuration, or intent detection, or touching FitPaw/ai_assistant/** in the FitPawBack repo."
metadata:
  project_path: /Users/vasyl/PycharmProjects/FitPawBack
  related_skill: fitpawback-django-conventions
---

# FitPawBack AI Assistant (Gemini + Ollama)

## When to Use This Skill

Use this skill when working on the `ai_assistant` Django app — the FitPaw gym
chatbot that answers questions about trainers, the lesson schedule, QR
check-in, and general gym tips, in Polish or English. Relevant when:

- Adding new intents/commands to the assistant
- Configuring or debugging the Gemini/Ollama LLM providers
- Changing the DB-aware context (trainers/schedule) fed to the LLM
- Working with local Ollama models specifically

## Architecture

```
ai_assistant/
  views.py                    # AssistantChatView (POST /api/assistant/chat/), demo() view
  urls.py                     # api/assistant/chat/, assistant/demo/
  serializers.py               # ChatRequestSerializer (validates {"message": str})
  services/
    llm_client.py               # generate_reply(): hybrid Gemini-primary/Ollama-fallback caller
    assistant_service.py        # handle_message(): rule-based intent routing + PL/EN i18n
    schedule_reader.py           # DB helpers: list_trainers(), lessons_for_date(), parse_day()
  templates/ai_assistant/demo.html  # standalone demo chat UI
```

This is **not** a pure LLM chatbot — it's a rule-based router
(`assistant_service.handle_message`) that only calls the LLM for open-ended
questions and trainer recommendations; simple intents (greeting, QR, trainer
list, schedule lookup) are answered directly from the database without an LLM
call, which keeps it fast/cheap and avoids hallucinated trainers or lesson
times for factual lookups.

## Request Flow

1. `POST /api/assistant/chat/` with `{"message": "<user text>"}`.
2. `handle_message()` detects language (PL if Polish diacritics present, else EN) and checks, in order: greeting → QR keyword → schedule keywords → trainer keywords → fallback to LLM with general FitPaw context.
3. For trainer **recommendation** intent specifically, it builds a compact DB-backed context (`_trainers_compact_context()`) listing only real trainers from the database and instructs the LLM to pick ONE and justify it — this prevents the LLM from inventing trainers that don't exist.
4. LLM calls go through `llm_client.generate_reply()`.

## Hybrid LLM Client (`llm_client.py`)

Controlled by Django settings (in the gitignored `settings.py`, loaded via
`python-dotenv`/`.env`):

| Setting | Purpose | Default in code |
|---|---|---|
| `LLM_PRIMARY` | `"gemini"` or `"ollama"` | `"gemini"` |
| `LLM_ENABLE_FALLBACK` | whether to fall back to the other provider | `True` |
| `GEMINI_API_KEY` | Gemini API key | — (required for Gemini) |
| `GEMINI_MODEL` | Gemini model name | `"gemini-1.5-flash"` |
| `OLLAMA_BASE_URL` | local Ollama server URL | `"http://127.0.0.1:11434"` |
| `OLLAMA_MODEL` | Ollama model tag | `"llama3.1:8b"` (README recommends `qwen2.5:7b` for 16GB RAM) |
| `OLLAMA_TIMEOUT_SECONDS` | request timeout | `60` |

Fallback logic in `generate_reply()`:
- If `LLM_PRIMARY="ollama"`: try Ollama first; on failure, fall back to Gemini if `LLM_ENABLE_FALLBACK` is true.
- If `LLM_PRIMARY="gemini"` (default): try Gemini first; **only** fall back to Ollama if the Gemini failure is specifically rate-limiting (`_is_rate_limited` matches `resource_exhausted`, `quota`, `rate limit`, `429`, or `too many requests` in the error string) — other Gemini errors (e.g. bad API key, library missing) do **not** trigger the Ollama fallback and are surfaced as-is.

When adding a new provider or changing fallback rules, preserve this
distinction (any-failure fallback for Ollama-primary vs. rate-limit-only
fallback for Gemini-primary) unless the user explicitly wants to change it.

## Working with Ollama Locally

1. Install Ollama and pull a model: `ollama pull qwen2.5:7b` (or another model matching your RAM — 7B models need ~16GB RAM comfortably).
2. Confirm the server is up: `curl http://127.0.0.1:11434/api/tags` (Ollama usually runs as a background service; use `ollama serve` if not).
3. Set `.env`: `LLM_PRIMARY=ollama`, `LLM_ENABLE_FALLBACK=0`, `OLLAMA_BASE_URL=http://127.0.0.1:11434`, `OLLAMA_MODEL=qwen2.5:7b` to run Ollama-only (useful for offline dev or avoiding Gemini quota during testing).
4. `_ollama_generate()` calls `POST {base_url}/api/generate` with `{"model", "prompt", "stream": false}` and reads `response.json()["response"]` — if you change the Ollama call shape (e.g. to streaming or the `/api/chat` endpoint), update both the request and this parsing logic together.

## Adding a New Intent

To add a new rule-based intent to `assistant_service.handle_message()`:

1. Add a keyword list (PL + EN) similar to `SCHEDULE_KEYWORDS`/`TRAINER_KEYWORDS`.
2. Add an `if any(k in low for k in YOUR_KEYWORDS): return AssistantResponse(...)` branch **before** the final LLM fallback block, in priority order (earlier checks win).
3. Add PL/EN strings for any new user-facing text to the `_t()` dictionary in both `"pl"` and `"en"` sections — never hardcode a single-language string inline.
4. If the intent needs DB data, add a helper to `schedule_reader.py` rather than querying models directly inside `assistant_service.py`.

## Known Limitations (per the module's own README TODO)

- Intent detection is keyword-based and can produce false positives/negatives — no ML classifier.
- No conversation memory (each message is handled independently, no chat history).
- Schedule parsing/timezones aren't fully hardened.
- No automated tests yet for date parsing or intent routing — add these under `ai_assistant/tests.py` when extending this module, since there's currently no coverage to catch regressions.

## Safety Rules Baked into Prompts

Every LLM prompt built by `_build_prompt()`/the trainer-recommendation context
explicitly instructs the model: do not book sessions, do not modify user
data, and (implicitly) don't invent trainers not in the DB-supplied list.
Preserve these constraints in any prompt changes — they're the main guardrail
against the assistant taking actions or hallucinating gym staff.
