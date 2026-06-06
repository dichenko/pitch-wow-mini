import pytest

from apps.bot.app.handlers import message as message_module


class _FakeUser:
    id = 183866240
    first_name = "Test"
    last_name = None
    username = "test_user"
    language_code = "ru"


class _FakeMessage:
    from_user = _FakeUser()
    text = None

    def __init__(self):
        self.answers = []

    async def answer(self, text):
        self.answers.append(text)


class _FakeAgent:
    metadata = {}
    tags = []

    def __init__(self):
        self.calls = []

    async def ainvoke(self, payload, config):
        self.calls.append({"payload": payload, "config": config})
        return {"messages": [_FakeAgentMessage("agent response")]}


class _FakeAgentMessage:
    def __init__(self, content):
        self.content = content


@pytest.mark.asyncio
async def test_process_user_text_uses_explicit_text_for_voice_messages(monkeypatch):
    fake_agent = _FakeAgent()

    async def assemble_prompt():
        return "system prompt", {}

    async def create_agent(**kwargs):
        return fake_agent

    async def apply_censor(**kwargs):
        return kwargs["draft_response"]

    async def get_llm_history_messages():
        return 0

    async def load_dialogue_history(**kwargs):
        return []

    async def save_dialogue_turn_best_effort(**kwargs):
        return None

    monkeypatch.setattr(message_module, "assemble_prompt", assemble_prompt)
    monkeypatch.setattr(message_module, "create_agent", create_agent)
    monkeypatch.setattr(message_module, "apply_censor", apply_censor)
    monkeypatch.setattr(message_module, "get_thread_id", lambda user_id: f"{user_id}")
    monkeypatch.setattr(message_module, "get_llm_history_messages", get_llm_history_messages)
    monkeypatch.setattr(message_module, "load_dialogue_history", load_dialogue_history)
    monkeypatch.setattr(
        message_module,
        "save_dialogue_turn_best_effort",
        save_dialogue_turn_best_effort,
    )

    message = _FakeMessage()
    await message_module.process_user_text(message=message, user_text="transcribed voice")

    assert fake_agent.calls[0]["payload"]["messages"][0].content == "transcribed voice"
    assert message.answers == ["agent response"]
