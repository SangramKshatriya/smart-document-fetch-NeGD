"""Small routing/security tests for the browser entry point."""
import pytest

flask = pytest.importorskip("flask")

import web_app


def test_health_endpoint_is_public():
    client = web_app.app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_login_is_locked_without_password(monkeypatch):
    monkeypatch.delenv("WEB_APP_PASSWORD", raising=False)
    client = web_app.create_app().test_client()
    response = client.get("/login")
    assert response.status_code == 503
    assert b"WEB_APP_PASSWORD" in response.data


def test_index_requires_login(monkeypatch):
    monkeypatch.setenv("WEB_APP_PASSWORD", "test-password")
    client = web_app.create_app().test_client()
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_with_password_starts_session(monkeypatch):
    monkeypatch.setenv("WEB_APP_PASSWORD", "test-password")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    monkeypatch.setattr(web_app, "start_session", lambda username, display_name: 42)
    monkeypatch.setattr(web_app, "record_login_attempt", lambda **kwargs: 1)
    monkeypatch.setattr(web_app, "log_audit_event", lambda *args, **kwargs: 1)
    client = web_app.create_app().test_client()
    page = client.get("/login")
    import re
    match = re.search(rb'name="_csrf_token" value="([^"]+)"', page.data)
    assert match is not None
    token = match.group(1).decode()
    response = client.post("/login", data={
        "_csrf_token": token, "password": "test-password",
        "display_name": "Test User", "username": "test-user",
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert client.get("/").status_code == 200
