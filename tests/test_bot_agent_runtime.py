import pytest

from apps.bot.app.agent import agent as agent_module
from apps.bot.app import healthcheck


class _FakeAgent:
    pass


@pytest.mark.asyncio
async def test_create_agent_uses_langgraph_state_modifier(monkeypatch):
    calls = {}

    async def get_llm_provider():
        return "openai"

    async def get_llm_model():
        return "gpt-4.1-mini"

    def create_llm(**kwargs):
        calls["llm"] = kwargs
        return object()

    def create_react_agent(model, tools, **kwargs):
        calls["agent"] = {"model": model, "tools": tools, "kwargs": kwargs}
        return _FakeAgent()

    monkeypatch.setattr(agent_module, "get_llm_provider", get_llm_provider)
    monkeypatch.setattr(agent_module, "get_llm_model", get_llm_model)
    monkeypatch.setattr(agent_module, "create_llm", create_llm)
    monkeypatch.setattr(agent_module, "get_all_tools", lambda: [])
    monkeypatch.setattr(agent_module, "create_react_agent", create_react_agent)

    created = await agent_module.create_agent(
        system_prompt="assembled system prompt",
        trace_id="trace-123",
        prompt_meta={
            "system_prompt_version": 1,
            "tools_instruction_version": 2,
            "assembled_prompt_hash": "abc123",
        },
    )

    assert isinstance(created, _FakeAgent)
    assert calls["llm"] == {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "temperature": 0.7,
    }
    assert "prompt" not in calls["agent"]["kwargs"]
    assert calls["agent"]["kwargs"]["state_modifier"] == "assembled system prompt"
    assert "checkpointer" not in calls["agent"]["kwargs"]


def test_polling_healthcheck_checks_bot_main_process(monkeypatch):
    monkeypatch.setenv("BOT_MODE", "polling")
    monkeypatch.setattr(healthcheck, "_main_process_is_bot", lambda: True)

    assert healthcheck.main() == 0


def test_polling_healthcheck_fails_when_main_process_is_not_bot(monkeypatch):
    monkeypatch.setenv("BOT_MODE", "polling")
    monkeypatch.setattr(healthcheck, "_main_process_is_bot", lambda: False)

    assert healthcheck.main() == 1


def test_webhook_healthcheck_uses_http_health_endpoint(monkeypatch):
    calls = {}

    class Response:
        def read(self):
            return b'{"status":"OK"}'

    def urlopen(url, timeout):
        calls["url"] = url
        calls["timeout"] = timeout
        return Response()

    monkeypatch.setenv("BOT_MODE", "webhook")
    monkeypatch.setattr(healthcheck.urllib.request, "urlopen", urlopen)

    assert healthcheck.main() == 0
    assert calls == {"url": "http://localhost:8000/health", "timeout": 5}


def test_webhook_healthcheck_fails_on_http_error(monkeypatch):
    def urlopen(url, timeout):
        raise OSError("connection refused")

    monkeypatch.setenv("BOT_MODE", "webhook")
    monkeypatch.setattr(healthcheck.urllib.request, "urlopen", urlopen)

    assert healthcheck.main() == 1
