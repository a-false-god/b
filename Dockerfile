# Prawko B — Multi-stage Build: React + Vite frontend + FastAPI backend

# Stage 1: Build Frontend SPA with Node.js
FROM node:20-alpine AS frontend-build
WORKDIR /frontend

# Copy frontend dependencies specification
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source and build to app/static/dist
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend Runtime
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ffmpeg: obsługa mediów (faststart / ewentualna dalsza konwersja WMV -> MP4)
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Zależności Python osobno = lepszy cache warstw przy przebudowach
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Kod aplikacji, skrypty, testy oraz narzędzia migracji
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY tools/ ./tools/

# Skopiowanie zbudowanego SPA ze Stage 1 do katalogu statycznego
COPY --from=frontend-build /app/static/dist ./app/static/dist

# Katalogi montowane jako wolumeny w runtime (baza SQLite + media)
RUN mkdir -p /app/data /app/media

EXPOSE 8000

# Jeden worker: BackgroundTasks i sesje żyją w procesie (patrz app/main.py)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
