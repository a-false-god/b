"""
Tests for Phase 1: Registration Key gating on /auth/register (Task P6).
"""

import os
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import reset_rate_limits

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_env_and_rate_limits():
    orig_key = os.environ.get("REGISTRATION_KEY")
    reset_rate_limits()
    yield
    if orig_key is not None:
        os.environ["REGISTRATION_KEY"] = orig_key
    else:
        os.environ.pop("REGISTRATION_KEY", None)
    reset_rate_limits()


def test_registration_when_key_is_set():
    os.environ["REGISTRATION_KEY"] = "secret_prawko_key_2026"

    test_login_fail1 = f"user_nokey_{uuid.uuid4().hex[:6]}"
    # 1. Attempt without key -> 403 Forbidden
    res1 = client.post("/auth/register", json={"login": test_login_fail1, "password": "password123"})
    assert res1.status_code == 403
    assert res1.json().get("detail") == "Rejestracja wymaga klucza"

    # 2. Attempt with wrong key -> 403 Forbidden
    test_login_fail2 = f"user_wrongkey_{uuid.uuid4().hex[:6]}"
    res2 = client.post("/auth/register", json={
        "login": test_login_fail2,
        "password": "password123",
        "registration_key": "wrong_key_xyz"
    })
    assert res2.status_code == 403
    assert res2.json().get("detail") == "Rejestracja wymaga klucza"

    # 3. Attempt with correct key in body -> 200 OK
    test_login_ok1 = f"user_ok1_{uuid.uuid4().hex[:6]}"
    res3 = client.post("/auth/register", json={
        "login": test_login_ok1,
        "password": "password123",
        "registration_key": "secret_prawko_key_2026"
    })
    assert res3.status_code == 200
    assert res3.json().get("login") == test_login_ok1

    # 4. Attempt with correct key in X-Registration-Key header -> 200 OK
    test_login_ok2 = f"user_ok2_{uuid.uuid4().hex[:6]}"
    res4 = client.post(
        "/auth/register",
        json={"login": test_login_ok2, "password": "password123"},
        headers={"X-Registration-Key": "secret_prawko_key_2026"}
    )
    assert res4.status_code == 200
    assert res4.json().get("login") == test_login_ok2


def test_registration_when_key_is_unset():
    os.environ.pop("REGISTRATION_KEY", None)

    # Open registration without key -> 200 OK
    test_login = f"user_open_{uuid.uuid4().hex[:6]}"
    res = client.post("/auth/register", json={"login": test_login, "password": "password123"})
    assert res.status_code == 200
    assert res.json().get("login") == test_login
