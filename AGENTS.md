# Prawko B — Architecture & Agent Working Agreements

This document defines the authoritative architecture, data model, and strict working agreements for all coding agents interacting with the **Prawko B** codebase.

---

## 1. Core Working Agreements for AI Agents

1. **Pytest Green Before Claiming Done**:
   * Every code change or task must conclude with a 100% green test suite run (`pytest -v`).
   * No task may be marked complete if any test or assertion fails.

2. **Test-Count Discipline**:
   * The headline test count must reconcile exactly with the test suite breakdown (zero silent omissions, zero test drift).
   * All added capabilities must be accompanied by targeted regression tests.

3. **Database Migrations (`tools/migrate_NNN.sql`)**:
   * All schema changes must be codified in sequential `tools/migrate_NNN.sql` files and hooked into `app/db.py:init_db()`.
   * Migrations **must be strictly idempotent** (safe to run multiple times without throwing errors or duplicating data; guard `ALTER TABLE ADD COLUMN` via `PRAGMA table_info`).

4. **Visual Regression & Baseline Protocol**:
   * Visual regression tests (`tests/e2e/test_visual_regression.py`) run across desktop and mobile surfaces in both dark and light modes.
   * **HARD RULE:** Never run `UPDATE_BASELINE=1` or regenerate visual regression baselines automatically. Any baseline update requires prior live-app visual review and explicit user approval.

5. **Design Tokens & UI Aesthetics (Ritual v2)**:
   * The app follows the **Ritual Design System**. All colors, typography, elevations, borders, and dark/light mode themes must use predefined CSS tokens.
   * Do not introduce arbitrary Tailwind color classes (e.g. `bg-red-500`, `text-blue-400`) or raw hex codes in components.

6. **Scope Lock**:
   * Scope is locked to Polish driving-theory examination for Category B (2,135 active questions).
   * UI language is strictly Polish.
   * Do not invent unapproved features or modes.

7. **Dependency Discipline**:
   * No new backend (Python) or frontend (npm) dependencies may be added without explicit approval from the project owner.

---

## 2. Product Overview

Prawko B is an adaptive, research-grounded web application for mastering the official Polish category B driving license theory exam.

### Core Pillars:
- **Intelligent Session Composer**: Prioritizes spaced review candidates and recently incorrect questions (~60%) combined with point-prioritized new questions (~40%), interleaved across Axis B content domains.
- **Rasch Mastery Model ($\theta$)**: Calibrated proficiency tracking with decay across domains.
- **Official Exam Simulation**: 32 questions (20 basic + 12 specialized), 74 maximum points, pass threshold at 68 points, timed at 25 minutes.
- **Dual-Pass AI Explanations**: Pre-computed statutory explanations with verified legal citations (`Art. / Dz.U.`) and visual context validation (multimodal Gemini 2.5 Flash).
- **Error & Reason Analytics**: Automatic classification into slips, mistakes, and hesitation.

---

## 3. Technology Stack & Architecture

- **Backend**: FastAPI (Python 3.13), plain SQLite with WAL mode and performance pragmas (`synchronous=NORMAL`, `cache_size=-8000`, `temp_store=MEMORY`, `mmap_size=33554432`). Session cookie authentication with hashed passwords.
- **Frontend**: React + TypeScript + Vite + TailwindCSS (Ritual Design System).
- **Font Subsets**: Inter `@fontsource/inter` strictly configured for Latin + Latin-Ext subsets to ensure full Polish diacritics support (`ąćęłńóśźż`).
- **Media**: Static directory `media/` served with `Cache-Control: public, max-age=31536000, immutable` for success responses. Media is **never** committed to Git.
- **Deployment**: Docker multi-stage build, optimized for 1 GB RAM VPS instances (Oracle Cloud E2.1.Micro) with Caddy reverse proxy and automated daily encrypted backups.

---

## 4. Data Model Summary

* `questions`: Official catalog (3,698 total questions, 2,135 Category B active records).
* `users`: User accounts with bcrypt password hashes.
* `user_sessions`: Persistent session management.
* `question_classification`: Multi-axis taxonomy (`A: cognitive`, `B: domain`, `C: item quality`).
* `answer_events`: Append-only interaction log with `mode` column (`nauka` vs `sprawdzian`).
* `exam_checks`: Graded exam simulation results.
* `question_stats` & `user_skill`: Rasch $\theta$ difficulty and user ability tracking.
* `question_explanations`: Cached statutory explanations.

---

## 5. Licensing & Legal Constraints

- Application code is licensed under the **MIT License**.
- Official question texts are CC BY-SA 4.0. Media files are CC BY-NC-ND 4.0.
- Media assets are self-hosted in private deployments and **must not be distributed publicly**.
