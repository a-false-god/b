"""
Pytest suite for Milestone M3 of Prawko B MVP.

Acceptance criteria for M3:
- Nauka view & static files served cleanly.
- GET /api/questions filtering supports scope & axis.
- Media route provides fallback handling.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app

client = TestClient(app)


def test_static_and_root_routes():
    res = client.get("/")
    assert res.status_code == 200
    assert "root" in res.text or "Prawko B" in res.text

    # SPA client routes return 200 HTML
    nauka_res = client.get("/nauka")
    assert nauka_res.status_code == 200
    assert "root" in nauka_res.text or "Prawko B" in nauka_res.text


def test_questions_api_filtering():
    # Filter basic scope
    res = client.get("/api/questions?category=B&scope=PODSTAWOWY")
    assert res.status_code == 200
    questions = res.json()
    assert isinstance(questions, list)
    assert len(questions) > 0
    for q in questions:
        assert q["scope"] == "PODSTAWOWY"

    # Filter specialist scope
    res_spec = client.get("/api/questions?category=B&scope=SPECJALISTYCZNY")
    assert res_spec.status_code == 200
    spec_qs = res_spec.json()
    for q in spec_qs:
        assert q["scope"] == "SPECJALISTYCZNY"


def test_media_fallback_route():
    # Non-existent media should return 404 cleanly
    res = client.get("/media/non_existent_file.mp4")
    assert res.status_code == 404


def test_media_wmv_fallback():
    media_dir = PROJECT_ROOT / "media"
    dummy_mp4 = media_dir / "test_sample_video.mp4"
    try:
        dummy_mp4.write_bytes(b"dummy mp4 video bytes")
        # Requesting .wmv should return the .mp4 file
        res = client.get("/media/test_sample_video.wmv")
        assert res.status_code == 200
        assert res.content == b"dummy mp4 video bytes"
        assert res.headers.get("cache-control") == "public, max-age=31536000, immutable"
    finally:
        if dummy_mp4.exists():
            dummy_mp4.unlink()


def test_media_cache_control_headers():
    media_dir = PROJECT_ROOT / "media"
    dummy_img = media_dir / "test_cache_check.jpg"
    try:
        dummy_img.write_bytes(b"dummy image bytes")
        res = client.get("/media/test_cache_check.jpg")
        assert res.status_code == 200
        assert res.headers.get("cache-control") == "public, max-age=31536000, immutable"

        # 404 must not have immutable cache control
        res_404 = client.get("/media/missing_never_exists.jpg")
        assert res_404.status_code == 404
        assert res_404.headers.get("cache-control") != "public, max-age=31536000, immutable"
    finally:
        if dummy_img.exists():
            dummy_img.unlink()


