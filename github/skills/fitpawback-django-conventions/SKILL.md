---
name: fitpawback-django-conventions
description: "Project conventions for the FitPawBack repository (Django 5.1 + Django REST Framework backend for the FitPaw app, github.com/1vasyl1/FitPawBack, local path /Users/vasyl/PycharmProjects/FitPawBack). Use when adding a Django app, model, serializer, view, ViewSet, or URL route, or when the user mentions FitPaw backend, FitPawBack, or this Django project. Covers app layout, ViewSet/permission patterns, settings, Swagger docs, admin, and Docker."
metadata:
  project_path: /Users/vasyl/PycharmProjects/FitPawBack
  github_repo: 1vasyl1/FitPawBack
  stack: Django 5.1.5, Django REST Framework 3.16, PostgreSQL, SimpleJWT, drf-yasg
  related_skill: fitpawback-jwt-auth, fitpawback-ai-assistant, fitpaw-ui-conventions
---

# FitPawBack Django Conventions

## When to Use This Skill

Use this skill whenever working inside the `FitPawBack` repository — the
Django REST Framework backend that the `fit_paw_ui` React frontend calls.
Trigger it when:

- Adding a new Django app, model, serializer, ViewSet, or URL route
- Reviewing/refactoring backend code
- Debugging permissions, routing, or admin panel issues
- Explaining how this specific backend is structured

For JWT/auth-cookie specifics see `fitpawback-jwt-auth`. For the LLM chat
assistant module see `fitpawback-ai-assistant`. For the frontend counterpart
see `fitpaw-ui-conventions` / `fitpaw-api-auth` / `fitpaw-stripe-checkout`.

## Tech Stack

- Python 3.11/3.12, Django 5.1.5, Django REST Framework 3.16
- PostgreSQL (psycopg2) — expected DB name `FitPawDB`, user `postgres` locally
- Auth: `djangorestframework-simplejwt` (see `fitpawback-jwt-auth`)
- API docs: `drf-yasg` → Swagger UI at `/swagger/`, Redoc at `/redoc/`
- Admin: stock Django admin at `/admin/` **plus** a separate staff-only admin site (`django-unfold` themed) at `/staff-panel/`
- `django-cors-headers` — `CORS_ALLOWED_ORIGINS` currently only allows `http://localhost:3000` (the Vite dev server)
- `pillow` for `ImageField` (avatars, trainer photos)
- `google-genai` + `requests` + `python-dotenv` for the AI assistant (see `fitpawback-ai-assistant`)
- Containerized via `Dockerfile` (Python 3.11 base, runs `manage.py runserver 0.0.0.0:8000`)
- CI: JetBrains Qodana (`.github/workflows/qodana_code_quality.yml`)

## Repository Layout

```
FitPaw/                     # Django project root (settings.py is gitignored — not in the repo)
  FitPaw/
    urls.py                 # root URLconf — includes every app below
    settings.py              # NOT in git; must be created locally (see below)
    wsgi.py / asgi.py
  accounts/                  # custom User model + JWT auth endpoints (see fitpawback-jwt-auth)
  membership/                # per-user Stripe membership state and /api/membership/me/
  payments/                  # Stripe plans, embedded checkout, status, and webhook
  schedule/                  # Trainer + Lessons models/views, staff_panel.py (Unfold admin site)
  api/                       # general API app; currently a placeholder
  ai_assistant/               # hybrid Gemini/Ollama chat assistant (see fitpawback-ai-assistant)
  manage.py
requirements.txt
Dockerfile
qodana.yaml
```

Root URL routing (`FitPaw/FitPaw/urls.py`):

```python
urlpatterns = [
    path('', lambda request: redirect('schema-swagger-ui', permanent=False)),
    path('admin/', admin.site.urls),
    path('staff-panel/', staff_admin.urls),
    path('api/', include('api.urls')),
    path('auth/', include('accounts.urls')),
    path('schedule', include('schedule.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/membership/', include('membership.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path("", include("ai_assistant.urls")),
]
```

New apps get their own `path('<prefix>/', include('<app>.urls'))` line here.

## Important: `settings.py` and `docker-compose.yml` Are Gitignored

Both `FitPaw/FitPaw/settings.py` and `docker-compose.yml` are excluded from
git (`.gitignore`). They exist locally but are never pushed. When cloning
fresh or reviewing "why is X missing", check locally first — don't assume the
GitHub repo is incomplete. Known settings mentioned in the README:

- `SECRET_KEY` and DB credentials must be changed before any real deployment
- `CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]` — add new frontend origins here
- `MEDIA_ROOT` / `MEDIA_URL` are **not** currently configured, needed for the `ImageField`s on `User.img` and `Trainer.img` to actually serve files
- AI assistant settings (`GEMINI_API_KEY`, `LLM_PRIMARY`, `OLLAMA_*`, etc.) — see `fitpawback-ai-assistant`

## App-by-App Summary

### `accounts` — custom user + auth
- Custom `User(AbstractUser)` model with a UUID primary key and an `img` field. Always reference `accounts.User` (via `get_user_model()`), never assume Django's default `User`.
- See `fitpawback-jwt-auth` for the full login/signup/refresh flow.

### `schedule` — trainers & lessons
- `Trainer` (name, bio, img) and `Lessons` (date, start_time, end_time, subject, location, FK to `Trainer` with `on_delete=SET_NULL`) models.
- `TrainerViewSet` / `LessonsViewSet` are plain `ModelViewSet`s registered on a `DefaultRouter` in `schedule/urls.py`.
- `staff_panel.py` defines a second, staff-only Django admin site (`StaffAdminSite`, django-unfold themed) mounted at `/staff-panel/`, separate from `/admin/`. Register any new staff-manageable models on **both** `admin.py` (for `/admin/`) and `staff_panel.py`'s `staff_admin` (for `/staff-panel/`) if staff should manage them there.

**Permission gotcha to watch for:** `TrainerViewSet`/`LessonsViewSet` set
`permission_classes = [IsAuthenticatedOrReadOnly, IsAdminUser]`. DRF combines
multiple permission classes with **AND**, not OR — so despite the README
saying "POST: Tak" (yes, any logged-in user), this actually requires the user
to be **both** authenticated-or-safe-method **and** an admin/staff user to
write. If a non-admin logged-in user reports "403 on POST /schedule/trainers/"
that's this AND-combination, not a bug in their request — confirm with the
user whether admin-only writes are actually intended before "fixing" it.
(Also note: the stray module-level `permission_classes = [...]` line above
each ViewSet in `schedule/views.py` has no effect — only the **class
attribute** `permission_classes` inside the ViewSet body is used by DRF.)

### `api` — general API app
- Currently a placeholder with no domain models or views. Keep domain-specific endpoints in their dedicated Django apps rather than adding payments or membership logic here.

### `payments` and `membership` — Stripe subscriptions
- `payments` owns plan listing, authenticated embedded Checkout Session creation, session-status verification, and the Stripe-only webhook.
- `membership` owns the one-to-one membership record per user and the authenticated `GET /api/membership/me/` endpoint.
- Verified Stripe webhook events are the source of truth for ongoing membership state. Do not make frontend redirects or ordinary status reads mutate membership state.
- Stripe secret and price configuration stays in backend settings/environment; never expose the secret key to the frontend.
- Keep the API paths and contracts documented in the root `README.md` when changing these apps.

### `ai_assistant` — hybrid LLM chat assistant
- See the dedicated `fitpawback-ai-assistant` skill.

## Adding a New App/Feature — Checklist

1. `python manage.py startapp <name>` (run from `FitPaw/` where `manage.py` lives).
2. Add it to `INSTALLED_APPS` in `settings.py` (local, gitignored file).
3. Define models in `models.py`, serializers in `serializers.py`, views/ViewSets in `views.py`.
4. Register ViewSets on a `DefaultRouter` in the app's `urls.py`, following the `schedule`/`accounts` pattern.
5. Wire the app's URLs into `FitPaw/FitPaw/urls.py` with `path('<prefix>/', include('<app>.urls'))`.
6. Run `python manage.py makemigrations <app> && python manage.py migrate`.
7. If the model should be admin-manageable, register it in both `admin.py` and (if staff-facing) `staff_panel.py`.
8. Update `README.md`'s endpoint table to keep documentation in sync.
9. Run `python manage.py test` before considering the change done.

## Docker

`Dockerfile` builds a plain `python:3.11` image, installs `requirements.txt`,
and runs `manage.py runserver 0.0.0.0:8000` — this is a dev-style container
(Django's dev server), not a production WSGI/ASGI setup (no gunicorn/uvicorn
yet). `docker-compose.yml` exists locally (gitignored) for wiring up Postgres
alongside it — check that file locally rather than assuming compose config
from the Dockerfile alone.
