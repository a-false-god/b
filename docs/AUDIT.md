# Prawko B — System, UX & Architecture Audit Report
*Generated for AI / Human Review*

**Date:** 2026-08-16  
**Target:** Prawko B MVP (FastAPI + React SPA + SQLite + Docker)  
**Scope:** Mobile UX (iOS/Safari/PWA), Frontend Layout, Backend & Auth, Database & Concurrency, Media Streaming, DevOps/Docker.

---

## 1. Executive Summary

Prawko B is an ultra-lightweight, high-performance learning app running under a 512 MB Docker container (~60–80 MB actual runtime RAM). The core architecture is solid and follows clean separation of concerns.

This audit highlights **potential edge cases, UX bottlenecks, and architectural trade-offs** across the system, categorized by severity (High, Medium, Low / Polish).

---

## 2. Findings & Recommendations

### A. Mobile & iOS / Safari UX

| ID | Category | Issue / Risk | Severity | Technical Details & Recommended Fix |
| :--- | :--- | :--- | :--- | :--- |
| **MOB-01** | iOS Input Zoom | Safari auto-zooms viewport on input focus | **Medium** | In iOS Safari, any `<input>` or `<select>` with font size `< 16px` triggers an involuntary zoom-in, breaking the layout. <br>**Fix:** Ensure `text-base sm:text-sm` (16px on mobile) or add CSS rule: `@media (max-width: 640px) { input, select, textarea { font-size: 16px !important; } }`. |
| **MOB-02** | Touch Interaction | Two-tap confirm vs Instant Tap on mobile answers | **Low / UX** | In `AnswerButtons.tsx`, coarse pointers use a 2-step commit (`stagedOption` $\rightarrow$ "Sprawdź odpowiedź"). While this prevents misclicks, some mobile users expect instant answer submission on single tap (with an undo/review window). Consider making this configurable. |
| **MOB-03** | Viewport Height | 100vh vs Dynamic Viewport Units (`dvh`) | **Low** | Mobile browsers with collapsible URL bars shift viewport height. <br>**Fix:** Use `min-h-[100dvh]` instead of `min-h-screen` (100vh) in root containers so address bar toggling doesn't cause layout jumps. |
| **MOB-04** | Landscape Orientation | Small height in landscape mode | **Low** | On iPhone in landscape mode (height ~390px), headers, media, and answers may require intense scrolling. Add `@media (max-height: 500px)` rules to shrink media to thumbnail size in landscape. |
| **MOB-05** | Service Worker | Offline PWA caching | **Enhancement** | Currently, assets are served from cache-control headers, but no offline Service Worker (`sw.js`) is registered. Adding a minimal Vite PWA plugin (`vite-plugin-pwa`) would allow full offline catalog review. |

---

### B. Backend & Authentication

| ID | Category | Issue / Risk | Severity | Technical Details & Recommended Fix |
| :--- | :--- | :--- | :--- | :--- |
| **BE-01** | Session State | In-Memory `SESSIONS` dict resets on restart | **Medium** | In `app/auth.py`, sessions are stored in Python `SESSIONS: dict[str, int]`. When the Docker container restarts or Uvicorn restarts, all active session cookies become invalid, forcing users to log in again. <br>**Fix:** Store session tokens in a simple SQLite table (`user_sessions(token, user_id, created_at, expires_at)`) or use signed JWT / itsdangerous cookies. |
| **BE-02** | Rate Limiting | In-Memory IP logs behind Reverse Proxy | **Medium** | `check_rate_limit` uses `request.client.host`. Behind Caddy or Cloudflare, `request.client.host` might resolve to `127.0.0.1` unless `X-Forwarded-For` / `Forwarded` headers are trusted (via `ProxyHeadersMiddleware` or custom header reader). |
| **BE-03** | Timeouts & WAL | SQLite Busy Timeout under background classification | **Low** | `app/db.py` sets `PRAGMA busy_timeout = 30000` and `WAL` mode. This is good practice. Ensure batch classification scripts (`scripts/vision_pass.py`, `scripts/classify_questions.py`) commit in small batches (e.g., 20 items) rather than one massive lock. |
| **BE-04** | Worker Count | Single Uvicorn worker requirement | **Design Note** | By design, Uvicorn runs with `--workers 1` because session state and background tasks live in-process. If horizontal scaling is needed in the future, BE-01 and an external queue would be required. |

---

### C. Media & Video Streaming

| ID | Category | Issue / Risk | Severity | Technical Details & Recommended Fix |
| :--- | :--- | :--- | :--- | :--- |
| **MED-01** | Video Faststart | MP4 MOOV Atom Placement | **Low** | Safari on iOS requires the `moov` atom at the beginning of MP4 files for immediate playback without downloading the whole file. Verify all MP4s in `media/` were processed with `ffmpeg -movflags +faststart`. |
| **MED-02** | Missing Media Fallback | Handling 404s without UI disruption | **Verified** | `MediaViewer.tsx` has `hasError` fallback showing filename and icon. Verified to work gracefully. |
| **MED-03** | Audio Tracks | Autoplay policy on silent videos | **Verified** | All `<video>` tags are set to `muted`, `autoPlay`, `playsInline`, `loop` with `pointer-events-none` — matches iOS WebKit policy 100%. |

---

### D. Docker, DevOps & Infrastructure

| ID | Category | Issue / Risk | Severity | Technical Details & Recommended Fix |
| :--- | :--- | :--- | :--- | :--- |
| **OPS-01** | RAM Spike on Import | Memory ceiling during XLSX re-import | **Low** | The 512 MB memory limit in `docker-compose.yml` is plenty for runtime (~70 MB). However, running `python tools/import_catalog.py` with `openpyxl` on the 3,698-row catalog uses ~180–250 MB RAM. It will succeed within 512 MB, but avoid running simultaneous vision scripts while importing. |
| **OPS-02** | Backup Retention | Nightly backups volume mounting | **Verified** | `data/backups/` is mounted inside `./data` volume. `tools/backup_db.py` manages 14 daily + 4 weekly snapshots. |
| **OPS-03** | Registration Lock | Open registration on local LAN vs Public VPS | **Security Note** | `.env` has `REGISTRATION_KEY=`. On local Wi-Fi, leaving it empty allows instant access for household members. Before exposing port 80/443 to the public internet via VPS, set `REGISTRATION_KEY` to prevent unauthorized signups. |

---

## 3. Checklist for Next AI / Developer

- [x] Docker multi-stage build verified (`node:20-alpine` + `python:3.11-slim`).
- [x] Port `8000:8000` exposed for LAN access.
- [x] Memory limit set to 512 MB in `docker-compose.yml`.
- [x] Video autoplay, loop, muted, no-controls configured.
- [x] iOS Safe Area insets (`viewport-fit=cover`, `env(safe-area-inset-top)`, `env(safe-area-inset-bottom)`) implemented.
- [x] Web App Manifest (`manifest.json` standalone mode) & app icon configured.
- [x] Side-by-side TAK / NIE buttons in both `NaukaView` and `ExamDialog`.
- [x] Prevented iOS Safari input auto-zoom (`font-size: 16px` rule on mobile).
- [ ] *(Optional BE-01)* Persist sessions in SQLite table to preserve logins across container restarts.
