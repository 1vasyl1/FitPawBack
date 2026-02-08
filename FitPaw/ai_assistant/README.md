# FitPaw AI Assistant (ai_assistant)

A lightweight assistant for the FitPaw Gym backend.
It answers questions about:
- trainers (from DB),
- lesson schedule (from DB),
- QR instructions,
- basic site navigation + general gym tips.

The assistant supports **PL/EN** and uses a **hybrid LLM setup**:
- **Primary:** Gemini (Google)
- **Fallback:** Ollama (local) when Gemini is rate-limited (429/quota)

> This README documents the **first working version** of the assistant.

---

## Features (current MVP)

✅ PL / EN responses (auto-detection)  
✅ Trainers list from database  
✅ Trainers recommendation (uses DB data inside LLM prompt)  
✅ Schedule lookup from database (supports multiple date formats)  
✅ QR quick help  
✅ Demo chat UI page (`/assistant/demo/`)

---

## Requirements

### Backend / Python
- Python 3.11+ recommended
- Django + DRF
- PostgreSQL (as used in the main FitPaw backend)

### LLM Providers
You can run:
- **Gemini only**
- **Ollama only**
- **Gemini + Ollama fallback** (recommended)

---

## Libraries used

Core:
- `django`
- `djangorestframework`
- `python-dotenv`

LLM / HTTP:
- `google-genai` (Gemini client)
- `requests` (Ollama HTTP calls)

API docs (project-level):
- `drf-yasg`

---

## Setup

### 1) Install Python dependencies
Activate your venv and install:

```bash
pip install -r requirements.txt
```

If you don’t have them in requirements yet, the minimum for this module is:
```bash
pip install requests python-dotenv google-genai
```

---

## Gemini setup (optional)

Add to your `.env`:

```env
GEMINI_API_KEY=YOUR_KEY
GEMINI_MODEL=gemini-1.5-flash
```

---

## Ollama setup (recommended)

### 1) Install Ollama (Windows)
Download and install Ollama for Windows.

Verify:
```bash
ollama --version
```

### 2) Pull a model
For 16GB RAM, a safe MVP choice is **qwen2.5:7b**:

```bash
ollama pull qwen2.5:7b
```

Check models:
```bash
ollama list
```

### 3) Make sure Ollama server is running
Usually Ollama runs as a service in the background.
Test quickly:

```bash
curl http://127.0.0.1:11434/api/tags
```

If needed:
```bash
ollama serve
```

---

## Hybrid LLM config (Gemini primary + Ollama fallback)

Add to your `.env`:

```env
LLM_PRIMARY=gemini
LLM_ENABLE_FALLBACK=1

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=60
```

### Ollama-only mode
```env
LLM_PRIMARY=ollama
LLM_ENABLE_FALLBACK=0

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
```

---

## Run the project (local)

From backend root:

```bash
python manage.py runserver
```

Useful URLs:
- Demo UI: `http://127.0.0.1:8000/assistant/demo/`
- API endpoint: `POST http://127.0.0.1:8000/api/assistant/chat/`
- Swagger: `http://127.0.0.1:8000/swagger/`

---

## How to use (current commands)

### Trainers
- `trainers`
- `show trainers`
- `tell me about the trainers`
- `which trainer is best for back/spine?` (recommendation mode)

### Schedule
Supported date formats:
- `schedule today`
- `schedule tomorrow`
- `schedule 2026-02-14`
- `schedule 2026/02/14`
- `schedule 2026 02 14`
- natural language: `lesson schedule on February 14, 2026`

### QR
- `qr`

---

## Implementation notes

- Trainers and lessons are fetched from DB (Django models).
- For recommendations, the assistant injects a compact list of DB trainers into the LLM prompt.
- If Gemini returns rate limit / quota (429), the assistant switches to Ollama automatically (if enabled).

---

## First change (v1)

This is the **first working iteration** of the `ai_assistant` module:
- hybrid LLM (Gemini + Ollama fallback),
- DB-aware trainers + schedule,
- demo UI for local testing.

---

## Next steps / TODO

There is still a lot to improve, but first we focus on backend quality:

- better intent detection (less false positives)
- stricter prompt rules (avoid hallucinating trainers/schedule)
- conversation memory (short history) for better chat flow
- improve schedule parsing + timezone support
- add tests for date parsing and intent routing
- improve UI: typing indicator, better formatting, shorter answers
