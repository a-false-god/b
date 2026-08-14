# Prawko B — Build Brief for the Coding Agent

You are building the MVP of Prawko B, a web app for learning Polish driving-theory exam questions (category B). This file is the authoritative build specification. Follow it literally; do not invent features. When a section conflicts with your intuition, this file wins.

## 0. Assets already provided (do not recreate)
- `data/KATALOG_dla_kandydatów_na_kierowców_072026.xlsx` — Official Ministry question catalog (source of truth)
- `data/questions_full.json` — Parsed catalog, all 3 698 records, 4 languages
- `data/prawko.sqlite` — SQLite with the questions table already imported
- `reference/prawko.html` — Working single-file prototype (2 135 cat-B questions embedded, hotkey tagging, localStorage) — our own code, evolve it into the frontend
- `tools/convert_media.py` — WMV→MP4 media converter (ffmpeg) — already written, do not rewrite

## 1. Product in one paragraph
Learning app for category B. Core loop: browse questions → answer → every answer is logged → error analytics drive reviews. Questions are classified against a global, research-standard taxonomy (section 6). This is not an exam simulator (out of scope).

## 2. Hard constraints
- All application code written from scratch. No code copied from third-party repos. Standard dependencies only (FastAPI, SQLite, ffmpeg, openpyxl).
- Licensing: question texts CC BY-SA 4.0; media CC BY-NC-ND 4.0 → app is non-commercial, closed group / self-hosted. No public media hosting.
- UI language: Polish. Question content: PL default, EN/DE/UA present in data (language switch is post-MVP).
- Keyboard-first (arrows + hotkeys), responsive desktop + mobile, dark/light via prefers-color-scheme.

## 3. Stack
- Backend: FastAPI + SQLite (plain sqlite3 or SQLModel — your choice, no heavy ORM). Session-cookie auth, passwords hashed with argon2 or bcrypt.
- Frontend: vanilla JS/HTML/CSS, served as static files by FastAPI. No JS framework in MVP.
- Media: static directory media/ next to the app (MP4 h264 ≤1024×576 no audio + JPG). Lazy loading; onerror fallback shows the filename.

## 4. Data model
`questions` table already exists in `prawko.sqlite` (columns: id, lp, scope, points, type, correct, media, media_kind, categories, status, q_pl, a_pl, b_pl, c_pl, q_en…, q_de…, q_ua…, pjm_q). id = official question number = stable key. Read-only; re-imports diff by id.

Create the following (migration script `tools/migrate_001.sql`):

```sql
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  login TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS taxonomy_values (
  axis TEXT NOT NULL CHECK (axis IN ('A','B','C')),
  value TEXT NOT NULL,
  definition TEXT NOT NULL,
  PRIMARY KEY (axis, value)
);

CREATE TABLE IF NOT EXISTS question_classification (
  question_id INTEGER NOT NULL REFERENCES questions(id),
  axis TEXT NOT NULL CHECK (axis IN ('A','B','C')),
  value TEXT NOT NULL,
  confidence REAL,
  source TEXT NOT NULL CHECK (source IN ('llm','manual')),
  PRIMARY KEY (question_id, axis, value)
);

CREATE TABLE IF NOT EXISTS answer_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  question_id INTEGER NOT NULL REFERENCES questions(id),
  chosen TEXT NOT NULL,
  is_correct INTEGER NOT NULL,
  time_ms INTEGER NOT NULL,
  session_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_user ON answer_events(user_id, question_id);
CREATE INDEX IF NOT EXISTS idx_events_question ON answer_events(question_id);
```
Seed `taxonomy_values` from section 6. `answer_events` is append-only — never UPDATE or DELETE rows.

## 5. Catalog import (`tools/import_catalog.py`)
Parse the XLSX with openpyxl, sheets `katalog` (status=active) and `W trakcie weryfikacji` (status=pending).
Columns (order): Lp, Numer pytania, Pytanie, Odpowiedź A/B/C, Poprawna odp, Media, Zakres struktury, Liczba punktów, Kategorie, PJM×4, EN×4, DE×4, UA×4.
Normalize scope: uppercase, fix source typos (Specajlistyczny → SPECJALISTYCZNY). type = TN if correct ∈ {T,N} else ABC. categories = split on commas, store JSON array.
Re-import must be a diff by numer: insert new, update changed, never touch question_classification or answer_events.

## 6. Taxonomy and the LLM classifier
Axes (seed data):
- **Axis A** — cognitive demand (Bloom, condensed): `pamiec` (pure recall: numbers, fines, periods, thresholds) / `rozumienie` (understanding a mechanism, e.g. physics of braking) / `zastosowanie` (apply a rule to a situation) / `analiza` (multi-step reasoning).
- **Axis B** — content domain (GDE matrix adapted): `znaki_i_sygnaly` / `pierwszenstwo` / `manewry_i_pozycja` / `predkosc_i_odleglosci` / `technika_pojazdu` / `administracja_i_kary` / `pierwsza_pomoc` / `ekologia`.
- **Axis C** — item quality (multi-label): `podwojne_przeczenie` / `pedanteria` (e.g. "więcej niż 50" vs "50") / `czysta_pamieciowka` / `brak_pulapki`.
Axes D (difficulty) and E (error type) are computed from answer_events — never classified by hand or LLM.

Classifier job (`scripts/classify_questions.py`):
Batch-classify all active cat-B questions (2 135) via the Gemini Flash API (cheap/fast tier). Text-only for now; questions with media get confidence capped at 0.6 until the vision pass exists.
Output per question: `{axis_a, axis_b, axis_c[], confidence 0..1}` → write to question_classification with source='llm'.
Prompt = rubric (axis definitions above) + few-shot examples.
Review queue: confidence < 0.8 OR has media → appears in the UI for one-key accept/override (override writes source='manual').

## 7. API (MVP)
- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`
- `GET /api/questions?scope=P|S&axisA=&axisB=&axisC=&untriaged=1&q=` — filtered list
- `GET /api/questions/{id}` — full record + classification + user's stats
- `POST /api/answers` — body `{question_id, chosen, time_ms, session_id}` → server computes is_correct against questions.correct
- `GET /api/analytics/errors?by=axisA|axisB|axisC|question|option`
- `GET /api/analytics/reason` — slip/lapse/mistake split (see 9.6)
- `GET /api/classification/review` + `POST /api/classification/{question_id}` — review queue

## 8. Frontend views (evolve reference/prawko.html)
- **Nauka** — question card (media, text, answers), filters per axis, hotkeys: arrows navigate, 1–4 accept/override classification suggestion, T/N or A/B/C keys answer. On answer → `POST /api/answers` with measured time_ms.
- **Panel analizy** — tables/charts: hardest questions, errors per axis, confused options, Reason split.
- **Review queue** — low-confidence classifications, one-key decisions.

## 9. Analytics definitions (exact semantics)
- Hardest questions: count of is_correct=0 per question, per user and global.
- Errors per axis: join events → classification; report per A/B/C value.
- Confused options: for ABC questions, count chosen where is_correct=0, grouped by (question, chosen).
- Hesitation: is_correct=1 AND time_ms > 15000 → review candidate.
- Coverage: never-seen vs seen vs mastered (mastered = last 2 answers correct).
- Reason split: slip = wrong AND time_ms < 8000; mistake = wrong AND time_ms ≥ 8000; uncertainty = correct AND time_ms > 15000. Thresholds are constants in one config file.

## 10. Build order
- **M1**: repo skeleton + migration + import → pytest proves 3 698 rows, cat-B = 2 135, zero missing correct.
- **M2**: auth + POST /api/answers + event log test.
- **M3**: Nauka view wired to API (media via media/ with fallback).
- **M4**: classifier script + review queue (dry-run on 50 questions first, human-accepted sample ≥ 85% before full run).
- **M5**: Panel analizy with all six analytics.

## 11. Acceptance criteria
- 100% of answers logged in answer_events.
- Classification suggestion accepted/overridden in ≤ 1 keypress.
- Error ranking available after the first session.
- Catalog re-import loses no classifications or history.

## 12. Out of scope for MVP
Exam simulation mode, commercial/public media hosting, heavy ML (bandits, deep knowledge tracing), native mobile app.
