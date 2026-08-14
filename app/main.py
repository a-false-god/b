"""
Main FastAPI Application Entry Point for Prawko B MVP.
Serves API routes, media files, and static frontend assets (SPA with fallback).
"""

from pathlib import Path
from fastapi import FastAPI, HTTPException
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

# Run DB migrations on startup
@app.on_event("startup")
def startup_db():
    init_db()

# Include API Router
app.include_router(api_router)

# Custom media endpoint with .wmv -> .mp4 extension fallback
@app.get("/media/{filename}")
def serve_media_file(filename: str):
    file_path = MEDIA_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)
    
    # Fallback: serve .mp4 if .wmv is requested
    if filename.lower().endswith(".wmv"):
        mp4_path = MEDIA_DIR / (Path(filename).stem + ".mp4")
        if mp4_path.exists():
            return FileResponse(mp4_path, media_type="video/mp4")
            
    # Fallback: check alternative image extensions
    stem = Path(filename).stem
    for ext in [".jpg", ".png", ".jpeg"]:
        img_path = MEDIA_DIR / (stem + ext)
        if img_path.exists():
            return FileResponse(img_path)
            
    raise HTTPException(status_code=404, detail="Media file not found")

# Mount static media directory
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# Mount Vite assets directory if dist built
if (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="dist-assets")

# Serve legacy static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    dist_index = DIST_DIR / "index.html"
    if dist_index.exists():
        return FileResponse(dist_index)
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    ref_file = PROJECT_ROOT / "reference" / "prawko.html"
    if ref_file.exists():
        return FileResponse(ref_file)
    return {"message": "Prawko B MVP API Running"}

# SPA Fallback for client-side routes (e.g., /nauka, /analiza, /review)
@app.get("/{full_path:path}")
def serve_spa_fallback(full_path: str):
    # Do not catch API, auth, media, or existing mounted routes
    if full_path.startswith(("api/", "auth/", "media/", "static/", "assets/")):
        raise HTTPException(status_code=404, detail="Not Found")
    
    dist_index = DIST_DIR / "index.html"
    if dist_index.exists():
        return FileResponse(dist_index)
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Not Found")
