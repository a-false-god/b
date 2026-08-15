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

---

## Wdrożenie produkcyjne (Oracle Cloud Always Free ARM64 — Task P6)

Architektura produkcyjna:
- **Serwer**: Oracle Cloud A1.Flex ARM64 (Ubuntu 24.04 LTS, region domowy Frankfurt).
- **Ingress & TLS**: Caddy 2 reverse proxy z automatycznymi certyfikatami Let's Encrypt (`https://prawko.lqdb.pl`).
- **Aplikacja**: FastAPI backend + React SPA serwowane w Dockerze (izolowane na `127.0.0.1:8000`).
- **Kopie zapasowe**: Automatyczny nightly cron rclone o `04:00` synchronizujący `data/backups/`.

### 1. Wymagania wstępne i DNS
Upewnij się, że rekord DNS `A` dla `prawko.lqdb.pl` wskazuje na publiczny adres IP VPS przed uruchomieniem Caddy.
W OCI Security List otwórz porty Ingress: TCP 22 (SSH), TCP 80 (HTTP) oraz TCP 443 (HTTPS).

### 2. Konfiguracja na serwerze VPS
```bash
# Klonowanie repozytorium
git clone https://github.com/a-false-god/b.git ~/b
cd ~/b

# Utworzenie pliku .env z kluczem rejestracji
cp .env.example .env # lub wygeneruj:
echo "REGISTRATION_KEY=$(openssl rand -hex 16)" >> .env
echo "TZ=Europe/Warsaw" >> .env
```

### 3. Synchronizacja mediów i bazy danych
Z maszyny lokalnej prześlij pliki mediów (~2 GB) oraz bazę SQLite:
```bash
rsync -avz --progress ./media/ ubuntu@<VPS_IP>:~/b/media/
rsync -avz --progress ./data/prawko.sqlite ubuntu@<VPS_IP>:~/b/data/prawko.sqlite
```

### 4. Uruchomienie Docker Compose
```bash
docker compose up -d --build
```
Weryfikacja lokalna:
```bash
curl -s http://localhost:8000/healthz
# Oczekiwana odpowiedź: {"status":"ok","db_ok":true,"questions_count":3698}
```

### 5. Utwardzenie systemu (Hardening)
```bash
# Firewall UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Blokada logowania hasłem po SSH (zachowanie kluczy)
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null || true
sudo systemctl restart ssh || sudo systemctl restart sshd

# Automatyczne aktualizacje bezpieczeństwa
sudo apt update && sudo apt install -y unattended-upgrades
sudo systemctl enable --now unattended-upgrades
```

### 6. Harmonogram kopii zapasowych (Rclone Cron)
Skonfiguruj zdalny magazyn w rclone (`rclone config`), dodaj `BACKUP_REMOTE=twoj_remote` do `~/.bashrc` / `~/b/.env` i dodaj zadanie do crontaba:
```bash
crontab -e
# Dodaj wpis:
0 4 * * * /home/ubuntu/b/ops/rclone-backup.sh >> /var/log/rclone-backup.log 2>&1
```

