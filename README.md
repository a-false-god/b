# Prawko B — Aplikacja do nauki pytań egzaminacyjnych kat. B

[![CI](https://github.com/a-false-god/b/actions/workflows/ci.yml/badge.svg)](https://github.com/a-false-god/b/actions/workflows/ci.yml)

Prawko B to nowoczesna, responsywna aplikacja internetowa wspierająca przygotowanie do państwowego egzaminu teoretycznego na prawo jazdy kategorii B (zgodna z oficjalnym katalogiem pytań Ministerstwa Infrastruktury).

---

## Szybki start

### Wymagania
- Python 3.11+
- Node.js 20+

### Uruchomienie lokalne
```bash
# 1. Backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. Frontend (development)
cd frontend
npm.cmd install
npm.cmd run dev
```

Aplikacja dostępna pod adresem: `http://localhost:8000` (lub `http://localhost:5173` w trybie Vite dev).

---

## Baza danych i kopie zapasowe (Task S1)

Kopie zapasowe bazy SQLite tworzone są za pomocą SQLite Online Backup API do katalogu `data/backups/`.

### Ręczne wykonanie kopii zapasowej
```bash
python tools/backup_db.py
```

### Polityka retencji
- **14 migawek dziennych**: najnowszy snapshot z każdego z ostatnich 14 dni kalendarzowych.
- **4 migawki tygodniowe**: po 1 snapshot na tydzień dla 4 poprzedzających tygodni.
- Starsze migawki są automatycznie usuwane przy tworzeniu nowej kopii.
- Przy starcie aplikacji FastAPI (`app/main.py`) sprawdza wiek najnowszego snapshotu i w razie potrzeby tworzy nową kopię (w sposób nieblokujący).

### Przywracanie bazy (Restore Drill)
Przed przywróceniem narzędzie automatycznie weryfikuje integralność bazy (`PRAGMA integrity_check`).
```bash
python tools/backup_db.py --restore data/backups/prawko_YYYYMMDD_HHMMSS.sqlite
```

---

## Bezpieczeństwo i Kontrola Dostępu (Task S4)
- **Ograniczanie częstotliwości żądań (Rate Limiting)**: Maksymalnie 5 prób uwierzytelnienia na minutę na adres IP (`429 Too Many Requests`).
- **Ochrona przed enumeracją kont**: Identyczny czas odpowiedzi (poprzez stałoczasową weryfikację hasła atrapą) oraz identyczny komunikat błędu dla nieistniejącego użytkownika i błędnego hasła.
- **Rotacja sesji i ciasteczka**: Pliki cookie sesji posiadają atrybuty `HttpOnly`, `SameSite=Lax`, `Max-Age=30 dni` oraz nowy token generowany przy każdym logowaniu z unieważnieniem starej sesji.
- **CORS**: Ścisła polityka same-origin (brak zezwoleń dla domen obcych).

---

## Obserwowalność i Niezawodność (Task S6)
- **Health Check**: `GET /healthz` zwraca status serwisu, łączność z bazą danych oraz liczbę pytań (`{"status": "ok", "db_ok": true, "questions_count": 3698}`).
- **Middleware logujący**: Wypisuje metodę HTTP, ścieżkę, kod statusu oraz czas wykonania w ms do stdout.
- **React ErrorBoundary**: Chroni interfejs użytkownika przed awariami komponentów, prezentując stonowany widok awaryjny Ritual z możliwością odświeżenia stanu.

---

## Testy i weryfikacja

### Pełny zestaw testów (jednostkowe, integracyjne, właściwościowe Hypothesis, bezpieczeństwo)
```bash
pytest -v
```

### Pominięcie testów przeglądarkowych Playwright w środowiskach bez GUI (CI / kontenery)
```bash
SKIP_PLAYWRIGHT_TESTS=1 pytest
```

### Aktualizacja baseline dla testów regresji wizualnej (Playwright)
```bash
pytest tests/e2e/test_visual_regression.py --update-baseline
```

---

## Metryki katalogu pytań (Task S7)

Wyjaśnienie i weryfikacja liczb katalogowych:
```bash
python tools/clarify_metrics.py
```

- **3 698**: Wszystkie rekordy w oficjalnym katalogu pytań.
- **2 135**: Aktywne pytania kategorii B.
- **1 941**: Odwołania do mediów dla wszystkich pytań kat. B (w tym w trakcie weryfikacji).
- **1 789**: Odwołania do mediów w aktywnej puli kat. B (oraz unikalne pliki mediów dla wszystkich rekordów).
- **1 566**: Unikalne pliki mediów w aktywnej puli kat. B.
