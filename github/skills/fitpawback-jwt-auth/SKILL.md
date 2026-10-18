---
name: fitpawback-jwt-auth
description: "JWT authentication implementation in the FitPawBack Django REST Framework backend (SimpleJWT + httponly cookies + custom User model). Use when adding or debugging login, signup, logout, token refresh, or user/me endpoints, or touching accounts/views.py, accounts/serializers.py, accounts/models.py, or accounts/urls.py in the FitPawBack repo."
metadata:
  project_path: /Users/vasyl/PycharmProjects/FitPawBack
  related_skill: fitpawback-django-conventions, fitpaw-api-auth
---

# FitPawBack JWT Authentication

## When to Use This Skill

Use this skill when working on authentication in the `FitPawBack` backend:

- Adding/changing login, signup, logout, or token-refresh behavior
- Debugging 401s, cookie issues, or token expiry
- Adding fields to the user profile / `me` endpoint
- Understanding how this backend's auth is meant to pair with the `fit_paw_ui` frontend (see `fitpaw-api-auth` for the frontend side)

## User Model

`accounts.User` extends `AbstractUser` with:
- `id`: UUID primary key (not the default auto-increment int) — any FK to the user, or code assuming integer PKs, must account for this.
- `img`: optional `ImageField` (avatar) — requires `MEDIA_ROOT`/`MEDIA_URL` configured to actually serve (currently not set, see `fitpawback-django-conventions`).

Always fetch the model via `get_user_model()` / `django.contrib.auth.get_user_model()`, never import a hardcoded `User` from `django.contrib.auth.models`.

## Auth Endpoints (`accounts/urls.py`)

| Method | Path | View | Notes |
|---|---|---|---|
| POST | `/auth/signup/` | `SignupView` | `AllowAny`; also duplicated as a plain `@api_view` function `signup` (dead code — the router-registered `UserViewSet.create` and `SignupView` are the ones actually wired up) |
| POST | `/auth/login/` | `MyTokenObtainPairView` | `AllowAny`; returns tokens **and** sets httponly cookies |
| POST | `/auth/token/refresh/` | `CookieTokenRefreshView` | Reads refresh token from the `refresh` cookie, not the request body |
| GET/POST/PATCH/DELETE | `/auth/users/` , `/auth/users/{id}/` | `UserViewSet` (router) | `create` is `AllowAny`; `PUT/PATCH/DELETE` on user records require `IsAdminUser` |
| GET/PATCH | `/auth/users/me/` | `UserViewSet.me` (`@action`) | Current authenticated user profile |

`/auth/users/me/` is the self-service exception: any authenticated user can
update only their own `email`, `first_name`, and `last_name`. The action always
uses `request.user`; attempts to write identity or privilege fields are ignored
as read-only. This does not grant regular users permission to update another
account through `/auth/users/{id}/`.

## Login / Token Response Shape

`MyTokenObtainPairView` (used by `/auth/login/`) wraps SimpleJWT's
`TokenObtainPairView` with a custom serializer that adds the user profile to
the response body:

```json
{
  "access": "<jwt>",
  "refresh": "<jwt>",
  "user": { "id": "...", "username": "...", "img": null, "first_name": "...", "last_name": "...", "email": "...", "date_joined": "..." }
}
```

**This is the payload the frontend's `loginApi()` reads** (`fit_paw_ui`'s
`authService.ts`), which stores `access` in `localStorage` and attaches it as
a `Bearer` header on future requests (see `fitpaw-api-auth`).

## Dual Token Delivery: Body + httponly Cookies

`MyTokenObtainPairView.post()` does two things with the tokens it issues:

1. Returns `access`/`refresh` in the **JSON body** (used by the frontend to build the `Authorization: Bearer <token>` header on every request — this is the only way JS can access the access token, since it's not exposed via a readable cookie).
2. **Also** sets them as `httponly`, `secure`, `samesite=Lax` cookies named `access` and `refresh` (15 min / 7 day expiry respectively) — these are **not readable by JS by design**. Their only consumer is `CookieTokenRefreshView`.

`CookieTokenRefreshView.post()` ignores any `refresh` value in the request
body and instead reads `request.COOKIES.get("refresh")`. This means:

- The frontend's refresh call must be made with `withCredentials: true` (it is — see `fitpaw-api-auth`'s axios setup) so the `refresh` cookie is actually sent.
- If refresh is failing, first check that the cookie is present and not blocked by `SameSite`/`Secure` settings — e.g. `secure=True` cookies are dropped over plain `http://` in some browsers/environments, which is a common local-dev gotcha since the dev backend runs on `http://127.0.0.1:8000`.
- `CookieTokenRefreshView` returns `401` with `{"detail": "Refresh token not found."}` if the cookie is missing — this is exactly the response the frontend interceptor's refresh-catch branch expects.

**When adding new auth-related endpoints, keep both delivery mechanisms in
sync** — if you change the cookie names/expiry here, nothing on the frontend
needs to change (it never reads these cookies directly), but if you change the
JSON body shape (e.g. renaming `access`), the frontend's `LoginResponse` type
in `authService.ts` must be updated too.

## Signup Flow

`SignupView` (`CreateAPIView` + `UserSignupSerializer`) only creates the user
— it does **not** log the user in or return tokens (unlike the alternate
`signup` function-based view in `views.py`, which does return tokens but is
not the one wired into `urls.py`). If the frontend needs "signup then
immediately logged in" behavior, either:
- Have the frontend call `/auth/signup/` then `/auth/login/`, or
- Switch `accounts/urls.py`'s `signup/` path to the token-returning function view (confirm with the user which behavior is intended before changing).

## Adding a New Protected Endpoint (Any App)

Use `IsAuthenticated` (or a more specific permission) and rely on the
existing JWT auth classes already configured in `settings.py`'s
`REST_FRAMEWORK` dict (SimpleJWT's `JWTAuthentication`) — no per-view JWT
wiring is needed, just set `permission_classes` correctly on the view/ViewSet.
See `fitpawback-django-conventions` for the permission-class AND-vs-OR gotcha
already present in the `schedule` app.

## Debugging Checklist

1. **401 on a request that should be authenticated** → confirm the frontend actually attached `Authorization: Bearer <token>` and that the token hasn't expired (15 min access lifetime).
2. **Refresh not working** → confirm `withCredentials`/cookie is present, `secure=True` isn't blocking the cookie on `http://` in the current environment, and the request actually reaches `/auth/token/refresh/POST` with the `refresh` cookie attached.
3. **User created but frontend not logged in after signup** → expected, see "Signup Flow" above; frontend needs a follow-up login call.
4. **Admin-only actions failing for a "logged in" user** → check whether the endpoint's permission class requires `IsAdminUser`/staff, not just `IsAuthenticated`.
