import re

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from apps.admin.app.routers import settings as settings_router


def _extract_csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


class _FakeScalarResult:
    def scalar_one_or_none(self):
        return None


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def execute(self, statement):
        return _FakeScalarResult()


@pytest.fixture
def settings_client(monkeypatch):
    state = {"role": "write", "saved": None, "audit": None}

    async def get_llm_provider():
        return "openai"

    async def get_llm_model():
        return "gpt-4.1-mini"

    async def get_censor_provider():
        return "anthropic"

    async def get_censor_model():
        return "claude-3-5-sonnet-latest"

    async def save_llm_settings(**kwargs):
        state["saved"] = kwargs

    async def log_audit_event(**kwargs):
        state["audit"] = kwargs

    def get_current_admin(request):
        return {"tg_id": 12345, "role": state["role"]}

    def require_role(request, min_role):
        role_hierarchy = {"read": 0, "write": 1, "superadmin": 2}
        admin = get_current_admin(request)
        if role_hierarchy[admin["role"]] < role_hierarchy[min_role]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return admin

    monkeypatch.setattr(settings_router, "get_llm_provider", get_llm_provider)
    monkeypatch.setattr(settings_router, "get_llm_model", get_llm_model)
    monkeypatch.setattr(settings_router, "get_censor_provider", get_censor_provider)
    monkeypatch.setattr(settings_router, "get_censor_model", get_censor_model)
    monkeypatch.setattr(settings_router, "save_llm_settings", save_llm_settings)
    monkeypatch.setattr(settings_router, "log_audit_event", log_audit_event)
    monkeypatch.setattr(settings_router, "async_session_factory", lambda: _FakeSession())
    monkeypatch.setattr(settings_router, "get_current_admin", get_current_admin)
    monkeypatch.setattr(settings_router, "require_role", require_role)

    app = FastAPI()
    app.include_router(settings_router.router)

    with TestClient(app, base_url="https://testserver") as client:
        yield client, state


def test_settings_page_renders_csrf_matching_cookie(settings_client):
    client, _state = settings_client

    response = client.get("/admin/settings")

    assert response.status_code == 200
    cookie_token = response.cookies.get("csrf_token")
    form_token = _extract_csrf_token(response.text)
    assert cookie_token
    assert form_token == cookie_token


def test_settings_save_rejects_missing_csrf_form_token(settings_client):
    client, _state = settings_client
    client.get("/admin/settings")

    response = client.post(
        "/admin/settings/save",
        data={
            "llm_provider": "openai",
            "llm_model": "gpt-4.1-mini",
            "censor_provider": "anthropic",
            "censor_model": "claude-3-5-sonnet-latest",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token mismatch"


def test_settings_save_accepts_synchronized_csrf_token(settings_client):
    client, state = settings_client
    get_response = client.get("/admin/settings")
    csrf_token = _extract_csrf_token(get_response.text)

    response = client.post(
        "/admin/settings/save",
        data={
            "csrf_token": csrf_token,
            "llm_provider": "mistral",
            "llm_model": "mistral-large-latest",
            "censor_provider": "openai",
            "censor_model": "gpt-4.1-mini",
        },
    )

    assert response.status_code == 200
    assert "Settings saved successfully" in response.text
    assert state["saved"] == {
        "llm_provider": "mistral",
        "llm_model": "mistral-large-latest",
        "censor_provider": "openai",
        "censor_model": "gpt-4.1-mini",
        "admin_id": None,
    }
    assert state["audit"]["action"] == "settings.updated"


def test_read_role_cannot_save_settings_with_valid_csrf(settings_client):
    client, state = settings_client
    state["role"] = "read"
    get_response = client.get("/admin/settings")
    csrf_token = _extract_csrf_token(get_response.text)

    response = client.post(
        "/admin/settings/save",
        data={
            "csrf_token": csrf_token,
            "llm_provider": "openai",
            "llm_model": "gpt-4.1-mini",
            "censor_provider": "anthropic",
            "censor_model": "claude-3-5-sonnet-latest",
        },
    )

    assert response.status_code == 403
    assert state["saved"] is None
