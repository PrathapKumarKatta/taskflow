from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.services import auth
from app.services.auth import rate_limit_login


async def test_shared_database_login_limit(factory, monkeypatch):
    monkeypatch.setattr(auth.time, "time", lambda: 6000)
    ip = str(uuid4())
    for _ in range(get_settings().login_limit):
        async with factory() as db:
            await rate_limit_login(db, ip)
    async with factory() as db:
        with pytest.raises(HTTPException) as exc:
            await rate_limit_login(db, ip)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


async def test_rate_limit_resets_in_next_window(factory, monkeypatch):
    ip = str(uuid4())
    window = get_settings().login_window_seconds
    monkeypatch.setattr(auth.time, "time", lambda: window * 100)
    async with factory() as db:
        for _ in range(get_settings().login_limit):
            await rate_limit_login(db, ip)
        with pytest.raises(HTTPException):
            await rate_limit_login(db, ip)
        monkeypatch.setattr(auth.time, "time", lambda: window * 101)
        await rate_limit_login(db, ip)


async def test_failed_logins_still_consume_limit(client, monkeypatch):
    monkeypatch.setattr(auth.time, "time", lambda: 6000)
    monkeypatch.setattr(auth, "rate_limit_login", rate_limit_login)
    credentials = {"email": "missing@example.com", "password": "invalid-password"}
    for _ in range(get_settings().login_limit):
        response = await client.post("/api/v1/auth/login", json=credentials)
        assert response.status_code == 401
    response = await client.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 429
    assert "Retry-After" in response.headers
