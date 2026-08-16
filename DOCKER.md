# Prawko B — Docker na localhost

## Wymagania
- Docker Desktop (na Windows: z włączonym WSL2).

## Układ katalogów w repo
```text
prawko/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── app/
├── scripts/
├── tests/
├── tools/
├── data/       # prawko.sqlite — wolumen (trwałość bazy)
└── media/      # MP4/JPG — wolumen read-only
```

## Start
```bash
docker compose up -d --build
```
Aplikacja: <http://localhost:8000>

## Codzienne operacje
```bash
docker compose logs -f prawko                          # logi
docker compose exec prawko python -m pytest tests/ -q  # testy w kontenerze
docker compose down                                     # stop
docker compose up -d                                   # start bez przebudowy
```

## Uwagi
- `requirements.txt` musi istnieć w katalogu głównym repo. Minimalny zestaw do zweryfikowania z importami: `fastapi`, `uvicorn[standard]`, `argon2-cffi`, `openpyxl`, `pytest`, `httpx`, `pydantic`, `python-multipart`.
- Baza jest automatycznie inicjalizowana przy starcie (`app/main.py`), więc pierwszy start działa też z pustym `data/`.
- Media są montowane jako read-only (`:ro`). Jeśli chcesz odpalać `convert_media.py` w kontenerze, usuń `:ro` z wolumenu `./media`.
- Baza i media są celowo wykluczone z obrazu (`.dockerignore`) — trafiają do kontenera wyłącznie przez wolumeny.
- Jeden worker Uvicorn: sesje i BackgroundTasks żyją w procesie — nie zwiększać `--workers`.

## Dostęp z telefonu / sieci lokalnej (LAN)
1. Sprawdź lokalny adres IP komputera w sieci Wi-Fi/LAN (w terminalu: `ipconfig` -> `IPv4 Address`, np. `192.168.1.150`).
2. Upewnij się, że telefon jest połączony z tą samą siecią Wi-Fi.
3. W przeglądarce w telefonie (Safari / Chrome) otwórz: `http://<IP_KOMPUTERA>:8000` (np. `http://192.168.1.150:8000`).
4. (Opcjonalnie) Dodaj do ekranu głównego telefonu (*Add to Home Screen*) jako aplikację PWA.
5. Jeśli strona się nie ładuje, upewnij się, że Windows Firewall zezwala na ruch przychodzący na porcie 8000:
   ```powershell
   New-NetFirewallRule -DisplayName "Prawko B Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```

## Smoke Test
1. Otwórz <http://localhost:8000> w przeglądarce.
2. Zarejestruj się / zaloguj (`/auth/register`, `/auth/login`).
3. Rozpocznij sesję nauki z pytaniem zawierającym wideo/zdjęcie.
4. Udziel odpowiedzi (klawisze `T`/`N` lub `A`/`B`/`C` lub dotknij na telefonie).
5. Zweryfikuj, że odpowiedź została zapisana w tabeli `answer_events`.

