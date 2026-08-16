"""
Main FastAPI Application Entry Point for Prawko B MVP.
Serves API routes, media files, and static frontend assets (SPA with fallback).
"""

import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.db import init_db
from app.api import router as api_router

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDIA_DIR = PROJECT_ROOT / "media"
STATIC_DIR = PROJECT_ROOT / "app" / "static"
DIST_DIR = STATIC_DIR / "dist"

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Prawko B MVP", version="1.0.0")

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000.0
    print(f"[{request.method}] {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)", flush=True)
    return response


# Run DB migrations, session pruning & backup check on startup
@app.on_event("startup")
def startup_db():
    init_db()
    try:
        from app.auth import prune_expired_sessions
        prune_expired_sessions()
    except Exception as e:
        pass
    try:
        from tools.backup_db import check_and_auto_backup
        check_and_auto_backup()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").warning(f"Startup backup check skipped: {e}")

# Include API Router
app.include_router(api_router)

MEDIA_CACHE_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable"}

# Custom media endpoint with .wmv -> .mp4 extension fallback
@app.get("/media/{filename}")
def serve_media_file(filename: str):
    file_path = MEDIA_DIR / filename
    if file_path.exists():
        return FileResponse(file_path, headers=MEDIA_CACHE_HEADERS)
    
    # Fallback: serve .mp4 if .wmv is requested
    if filename.lower().endswith(".wmv"):
        mp4_path = MEDIA_DIR / (Path(filename).stem + ".mp4")
        if mp4_path.exists():
            return FileResponse(mp4_path, media_type="video/mp4", headers=MEDIA_CACHE_HEADERS)
            
    # Fallback: check alternative image extensions
    stem = Path(filename).stem
    for ext in [".jpg", ".png", ".jpeg", ".webp"]:
        img_path = MEDIA_DIR / (stem + ext)
        if img_path.exists():
            return FileResponse(img_path, headers=MEDIA_CACHE_HEADERS)
            
    raise HTTPException(status_code=404, detail="Media file not found")

# Mount static media directory
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# Mount Vite assets directory if dist built
if (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="dist-assets")

# Serve legacy static assets if present
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    dist_index = DIST_DIR / "index.html"
    if dist_index.exists():
        return FileResponse(dist_index)
    ref_file = PROJECT_ROOT / "reference" / "prawko.html"
    if ref_file.exists():
        return FileResponse(ref_file)
    return {"message": "Prawko B MVP API Running"}

# SPA Fallback for client-side routes (e.g., /nauka, /analiza, /review, /exam)
@app.get("/{full_path:path}")
def serve_spa_fallback(full_path: str):
    # Do not catch API, auth, media, or existing mounted routes
    if full_path.startswith(("api/", "auth/", "media/", "static/", "assets/")):
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Check if a static file in dist matches directly (e.g. manifest.json, icon.svg)
    static_file = DIST_DIR / full_path
    if static_file.is_file():
        return FileResponse(static_file)

    dist_index = DIST_DIR / "index.html"
    if dist_index.exists():
        return FileResponse(dist_index)
    ref_file = PROJECT_ROOT / "reference" / "prawko.html"
    if ref_file.exists():
        return FileResponse(ref_file)
    raise HTTPException(status_code=404, detail="Not Found")
