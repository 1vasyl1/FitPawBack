# FitPaw API

FitPaw to backend aplikacji wspierajacej zarzadzanie treningami i trenerami dla wlascicieli zwierzat. Projekt bazuje na Django i Django REST Framework, udostepnia JWT do uwierzytelniania oraz dokumentacje Swagger/Redoc do szybkiego poznania dostepnych zasobow.

## Najwazniejsze funkcje
- Rejestracja uzytkownikow i logowanie z wykorzystaniem JWT (SimpleJWT)
- Modele kont z awatarem oraz podstawowymi danymi profilowymi
- Moduly trenerow oraz zajec z harmonogramem opartym na REST API
- Panel administracyjny Django (z motywem Unfold) oraz interaktywna dokumentacja API
- Konfigurowalne uprawnienia: odczyt publiczny, modyfikacje po zalogowaniu lub z konta administratora

## Stos technologiczny
- Python 3.12 (rekomendowana wersja)
- Django 5.1.5
- Django REST Framework 3.16
- PostgreSQL 14+ (psycopg2)
- JWT (djangorestframework-simplejwt)
- drf-yasg (Swagger/Redoc)
- django-cors-headers, pillow (obsluga plikow graficznych)

## Wymagania wstepne
- Zainstalowany Python 3.12 lub zgodna wersja z Django 5.1
- Dzialajaca instancja bazy PostgreSQL
- Narzedzia wirtualnego srodowiska (venv, virtualenv itp.)
- Opcjonalnie: narzedzia typu make, docker (jesli planujesz dalsza automatyzacje)

## Konfiguracja srodowiska developerskiego
1. Sklonuj repozytorium i przejdz do katalogu projektu:
   ```bash
   git clone <adres_repozytorium>
   cd FitPawBack
   ```
2. Utworz i aktywuj wirtualne srodowisko:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```
3. Zainstaluj zaleznosci (plik znajduje sie w katalogu `FitPaw/`):
   ```bash
   pip install -r FitPaw/requirements.txt
   ```
4. Skonfiguruj dostep do bazy danych. Domyslne ustawienia (`FitPaw/FitPaw/settings.py`) zakladaja lokalna baze `FitPawDB` na uzytkowniku `postgres`. Dostosuj je do swojego srodowiska lub przenies dane do zmiennych srodowiskowych (np. przez `export`/`set`).
5. Wykonaj migracje i (opcjonalnie) zaladuj dane startowe:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
6. Uruchom serwer developerski:
   ```bash
   python manage.py runserver
   ```

Serwer jest domyslnie dostepny pod adresem `http://127.0.0.1:8000/`. Karta glowna przekierowuje do interfejsu Swagger.

## Dokumentacja API
- Swagger UI: `http://127.0.0.1:8000/swagger/`
- Redoc: `http://127.0.0.1:8000/redoc/`

Do testowania endpointow wymagajacych autoryzacji dodaj naglowek `Authorization: Bearer <token>` (token access generowany przez SimpleJWT).

## Najwazniejsze endpointy
| Metoda | Sciezka | Opis | Autoryzacja |
|--------|---------|------|-------------|
| POST | `/auth/signup/` | Rejestracja nowego uzytkownika | Nie |
| POST | `/auth/login/` | Uzyskanie pary tokenow (refresh + access) | Nie |
| POST | `/auth/token/refresh/` | Odnowienie access tokena | Nie (wymaga refresh tokena) |
| GET | `/auth/users/` | Lista uzytkownikow | Tak (admin) |
| GET | `/auth/users/{id}/` | Szczegoly uzytkownika | Tak |
| POST | `/auth/users/` | Dodanie uzytkownika | Nie |
| GET | `/auth/users/me/` | Zalogowany uzytkownik | Tak |
| PATCH | `/auth/users/me/` | Aktualizacja profilu zalogowanego uzytkownika | Tak |
| GET/POST | `/schedule/trainers/` | Lista i tworzenie trenerow | GET: Nie, POST: Tak |
| GET/PATCH/DELETE | `/schedule/trainers/{id}/` | Operacje na trenerze | Tak |
| GET/POST | `/schedule/lessons/` | Lista i tworzenie zajec | GET: Nie, POST: Tak |
| GET/PATCH/DELETE | `/schedule/lessons/{id}/` | Operacje na zajeciach | Tak |
| GET | `/admin/` | Panel administracyjny Django | Tak (konto staff) |

> Uwaga: router REST Framework domyslnie dodaje znak `/` na koncu sciezek. Jezeli zmieniasz `APPEND_SLASH` w ustawieniach, dostosuj powyzsze adresy.

## Testy
Aby uruchomic testy jednostkowe i integracyjne projektu:
```bash
python manage.py test
```

## Przydatne wskazowki
- Projekt korzysta z modelu uzytkownika `accounts.User`; wszelkie migracje i logika powinny odwoluwac sie wlasnie do niego.
- Pola `ImageField` wymagaja skonfigurowania `MEDIA_ROOT` oraz `MEDIA_URL` (obecnie nie ma ich w ustawieniach); podczas pracy lokalnej mozesz dodac je w `settings.py`.
- Zmien klucz `SECRET_KEY` oraz dane bazy przed wdrozeniem na produkcje. Rozwaz uzycie zmiennych srodowiskowych lub menedzera sekretow.
- `CORS_ALLOWED_ORIGINS` jest ustawione na `http://localhost:3000`. Dodaj kolejne domeny frontendu wedlug potrzeb.

## Dalszy rozwoj
- Dodanie walidacji kolizji terminow w modelu zajec
- Rozszerzenie API o rezerwacje zajec przez uzytkownikow
- Integracja z CI (lint, testy) i narzedzia do konteneryzacji (Docker)
- Rozbudowa pokrycia testowego dla widokow, serializerow oraz uprawnien
