from types import SimpleNamespace

import pytest
from aiogram.enums import ChatAction
from langchain_core.messages import AIMessage, HumanMessage

from apps.bot.app.agent.agent import _user_reset_counters, get_thread_id, reset_user_thread
from apps.bot.app.handlers import message as message_module
from apps.bot.app.services import censor_service, history_service, settings_service
from packages.shared.models.database import DialogueHistory


class _FakeUser:
    id = 183866240
    first_name = "Test"
    last_name = None
    username = "test_user"
    language_code = "ru"


class _FakeChat:
    id = 183866240


class _FakeBot:
    def __init__(self, events=None, fail_chat_action=False):
        self.events = events if events is not None else []
        self.fail_chat_action = fail_chat_action

    async def send_chat_action(self, chat_id, action):
        self.events.append(("typing", chat_id, action))
        if self.fail_chat_action:
            raise RuntimeError("chat action failed")


class _FakeMessage:
    from_user = _FakeUser()
    chat = _FakeChat()

    def __init__(self, bot=None, events=None):
        self.answers = []
        self.events = events if events is not None else []
        self.bot = bot or _FakeBot(self.events)

    async def answer(self, text, **kwargs):
        self.answers.append(text)


class _FakeAgentMessage:
    def __init__(self, content):
        self.content = content


class _FakeAgent:
    tags = []

    def __init__(self, provider):
        self.metadata = {"llm_provider": provider, "llm_model": f"{provider}-model"}
        self.calls = []

    async def ainvoke(self, payload, config):
        self.calls.append({"payload": payload, "config": config})
        return {"messages": [_FakeAgentMessage("draft response")]}


def _record(user_message, assistant_response, thread_id="183866240"):
    return DialogueHistory(
        user_tg_id=183866240,
        thread_id=thread_id,
        trace_id=f"trace-{user_message}",
        user_message=user_message,
        assistant_response=assistant_response,
    )


def test_dialogue_history_to_messages_uses_human_ai_pairs_in_order():
    messages = history_service.dialogue_history_to_messages(
        [_record("q1", "a1"), _record("q2", "a2")]
    )

    assert [type(message) for message in messages] == [
        HumanMessage,
        AIMessage,
        HumanMessage,
        AIMessage,
    ]
    assert [message.content for message in messages] == ["q1", "a1", "q2", "a2"]


@pytest.mark.asyncio
async def test_load_dialogue_history_returns_empty_when_limit_zero(monkeypatch):
    called = False

    def async_session_factory():
        nonlocal called
        called = True

    monkeypatch.setattr(history_service, "async_session_factory", async_session_factory)

    assert await history_service.load_dialogue_history(1, "1", 0) == []
    assert called is False


@pytest.mark.asyncio
async def test_load_dialogue_history_reverses_latest_records_to_chronological(monkeypatch):
    captured = {}

    class Result:
        def scalars(self):
            return self

        def all(self):
            return [_record("new", "new answer"), _record("old", "old answer")]

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def execute(self, statement):
            captured["statement"] = statement
            return Result()

    monkeypatch.setattr(history_service, "async_session_factory", lambda: Session())

    records = await history_service.load_dialogue_history(
        user_tg_id=183866240,
        thread_id="183866240",
        limit=2,
    )

    assert [record.user_message for record in records] == ["old", "new"]
    assert "LIMIT" in str(captured["statement"])


def test_reset_thread_excludes_previous_thread_history():
    _user_reset_counters.clear()

    before = get_thread_id(183866240)
    reset_user_thread(183866240)
    after = get_thread_id(183866240)

    assert before == "183866240"
    assert after == "183866240_1"


@pytest.mark.asyncio
async def test_persistent_reset_avoids_reusing_history_threads_after_process_restart(monkeypatch):
    from apps.bot.app.agent import agent as agent_module
    from packages.shared.models.database import UserConversationState

    _user_reset_counters.clear()
    added = []

    class Result:
        def __init__(self, values):
            self.values = values

        def scalar_one_or_none(self):
            return None

        def scalars(self):
            return self

        def all(self):
            return self.values

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def begin(self):
            return Transaction()

        async def execute(self, statement):
            text = str(statement)
            if "user_conversation_states" in text:
                return Result([])
            return Result(["183866240", "183866240_1"])

        def add(self, item):
            added.append(item)

    monkeypatch.setattr(agent_module, "async_session_factory", lambda: Session())

    thread_id = await agent_module.reset_user_thread_state(183866240)

    assert thread_id == "183866240_2"
    assert len(added) == 1
    assert isinstance(added[0], UserConversationState)
    assert added[0].reset_counter == 2
    assert added[0].current_thread_id == "183866240_2"
    assert _user_reset_counters[183866240] == 2


@pytest.mark.asyncio
async def test_get_current_thread_id_restores_latest_history_thread_when_state_missing(monkeypatch):
    from apps.bot.app.agent import agent as agent_module

    _user_reset_counters.clear()
    added = []

    class Result:
        def scalar_one_or_none(self):
            return "183866240_3"

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, model, key):
            return None

        async def execute(self, statement):
            return Result()

        def add(self, item):
            added.append(item)

        async def commit(self):
            return None

    monkeypatch.setattr(agent_module, "async_session_factory", lambda: Session())

    thread_id = await agent_module.get_current_thread_id(183866240)

    assert thread_id == "183866240_3"
    assert len(added) == 1
    assert added[0].reset_counter == 3
    assert added[0].current_thread_id == "183866240_3"
    assert _user_reset_counters[183866240] == 3


@pytest.mark.parametrize("provider", ["openai", "anthropic", "mistral"])
@pytest.mark.asyncio
async def test_process_user_text_sends_history_through_common_path(monkeypatch, provider):
    fake_agent = _FakeAgent(provider)
    saved = []
    censor_calls = []

    async def assemble_prompt():
        return "system prompt", {}

    async def create_agent(**kwargs):
        return fake_agent

    async def get_llm_history_messages():
        return 20

    async def load_dialogue_history(**kwargs):
        return [_record("previous question", "previous answer")]

    async def apply_censor(**kwargs):
        censor_calls.append(kwargs)
        return "final response"

    async def save_dialogue_turn_best_effort(**kwargs):
        saved.append(kwargs)

    monkeypatch.setattr(message_module, "assemble_prompt", assemble_prompt)
    monkeypatch.setattr(message_module, "create_agent", create_agent)
    monkeypatch.setattr(message_module, "get_llm_history_messages", get_llm_history_messages)
    monkeypatch.setattr(message_module, "load_dialogue_history", load_dialogue_history)
    monkeypatch.setattr(message_module, "apply_censor", apply_censor)
    monkeypatch.setattr(
        message_module,
        "save_dialogue_turn_best_effort",
        save_dialogue_turn_best_effort,
    )
    async def get_current_thread_id(user_id):
        return str(user_id)

    monkeypatch.setattr(message_module, "get_current_thread_id", get_current_thread_id)

    message = _FakeMessage()
    await message_module.process_user_text(message=message, user_text="current question")

    request_messages = fake_agent.calls[0]["payload"]["messages"]
    assert [message.content for message in request_messages] == [
        "previous question",
        "previous answer",
        "current question",
    ]
    assert censor_calls[0]["history_messages"] == request_messages[:-1]
    assert saved == [
        {
            "user_tg_id": 183866240,
            "thread_id": "183866240",
            "trace_id": saved[0]["trace_id"],
            "user_message": "current question",
            "assistant_response": "final response",
            "llm_provider": provider,
            "llm_model": f"{provider}-model",
        }
    ]
    assert message.answers == ["final response"]


@pytest.mark.asyncio
async def test_process_user_text_sends_typing_before_agent_invocation(monkeypatch):
    events = []
    fake_agent = _FakeAgent("openai")

    async def assemble_prompt():
        return "system prompt", {}

    async def create_agent(**kwargs):
        assert events == [("typing", 183866240, ChatAction.TYPING)]
        return fake_agent

    async def get_llm_history_messages():
        return 0

    async def load_dialogue_history(**kwargs):
        return []

    async def apply_censor(**kwargs):
        return kwargs["draft_response"]

    async def save_dialogue_turn_best_effort(**kwargs):
        return None

    monkeypatch.setattr(message_module, "assemble_prompt", assemble_prompt)
    monkeypatch.setattr(message_module, "create_agent", create_agent)
    monkeypatch.setattr(message_module, "get_llm_history_messages", get_llm_history_messages)
    monkeypatch.setattr(message_module, "load_dialogue_history", load_dialogue_history)
    monkeypatch.setattr(message_module, "apply_censor", apply_censor)
    monkeypatch.setattr(
        message_module,
        "save_dialogue_turn_best_effort",
        save_dialogue_turn_best_effort,
    )
    async def get_current_thread_id(user_id):
        return str(user_id)

    monkeypatch.setattr(message_module, "get_current_thread_id", get_current_thread_id)

    message = _FakeMessage(events=events)
    await message_module.process_user_text(message=message, user_text="current question")

    assert events == [("typing", 183866240, ChatAction.TYPING)]
    assert message.answers == ["draft response"]


@pytest.mark.asyncio
async def test_process_user_text_continues_when_typing_activity_fails(monkeypatch):
    fake_agent = _FakeAgent("openai")

    async def assemble_prompt():
        return "system prompt", {}

    async def create_agent(**kwargs):
        return fake_agent

    async def get_llm_history_messages():
        return 0

    async def load_dialogue_history(**kwargs):
        return []

    async def apply_censor(**kwargs):
        return "final response"

    async def save_dialogue_turn_best_effort(**kwargs):
        return None

    monkeypatch.setattr(message_module, "assemble_prompt", assemble_prompt)
    monkeypatch.setattr(message_module, "create_agent", create_agent)
    monkeypatch.setattr(message_module, "get_llm_history_messages", get_llm_history_messages)
    monkeypatch.setattr(message_module, "load_dialogue_history", load_dialogue_history)
    monkeypatch.setattr(message_module, "apply_censor", apply_censor)
    monkeypatch.setattr(
        message_module,
        "save_dialogue_turn_best_effort",
        save_dialogue_turn_best_effort,
    )
    async def get_current_thread_id(user_id):
        return str(user_id)

    monkeypatch.setattr(message_module, "get_current_thread_id", get_current_thread_id)

    events = []
    message = _FakeMessage(
        bot=_FakeBot(events=events, fail_chat_action=True),
        events=events,
    )
    result = await message_module.process_user_text(
        message=message,
        user_text="current question",
    )

    assert result == "final response"
    assert events == [("typing", 183866240, ChatAction.TYPING)]
    assert message.answers == ["final response"]


@pytest.mark.asyncio
async def test_process_user_text_does_not_save_history_when_agent_fails(monkeypatch):
    saved = []

    async def assemble_prompt():
        return "system prompt", {}

    async def get_llm_history_messages():
        return 0

    async def load_dialogue_history(**kwargs):
        return []

    async def create_agent(**kwargs):
        raise RuntimeError("agent failed")

    async def save_dialogue_turn_best_effort(**kwargs):
        saved.append(kwargs)

    async def get_current_thread_id(user_id):
        return str(user_id)

    monkeypatch.setattr(message_module, "assemble_prompt", assemble_prompt)
    monkeypatch.setattr(message_module, "get_llm_history_messages", get_llm_history_messages)
    monkeypatch.setattr(message_module, "load_dialogue_history", load_dialogue_history)
    monkeypatch.setattr(message_module, "create_agent", create_agent)
    monkeypatch.setattr(message_module, "get_current_thread_id", get_current_thread_id)
    monkeypatch.setattr(
        message_module,
        "save_dialogue_turn_best_effort",
        save_dialogue_turn_best_effort,
    )

    message = _FakeMessage()
    await message_module.process_user_text(message=message, user_text="current question")

    assert saved == []
    assert len(message.answers) == 1


@pytest.mark.asyncio
async def test_censor_llm_receives_recent_history(monkeypatch):
    llm_calls = []
    added_runs = []

    class Result:
        def scalar_one_or_none(self):
            return 3

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def execute(self, statement):
            return Result()

        def add(self, item):
            added_runs.append(item)

        async def commit(self):
            return None

    class Llm:
        async def ainvoke(self, messages):
            llm_calls.append(messages)
            return SimpleNamespace(content="reviewed response")

    async def is_censor_enabled():
        return True

    async def get_censor_provider():
        return "mistral"

    async def get_censor_model():
        return "mistral-large-latest"

    async def get_active_censor_prompt():
        return "review prompt"

    monkeypatch.setattr(censor_service, "is_censor_enabled", is_censor_enabled)
    monkeypatch.setattr(censor_service, "get_censor_provider", get_censor_provider)
    monkeypatch.setattr(censor_service, "get_censor_model", get_censor_model)
    monkeypatch.setattr(censor_service, "get_active_censor_prompt", get_active_censor_prompt)
    monkeypatch.setattr(censor_service, "create_llm", lambda **kwargs: Llm())
    monkeypatch.setattr(censor_service, "async_session_factory", lambda: Session())

    history_messages = [HumanMessage(content="old q"), AIMessage(content="old a")]
    result = await censor_service.apply_censor(
        draft_response="draft",
        user_message="current",
        trace_id="trace-1",
        user_tg_id=183866240,
        history_messages=history_messages,
    )

    assert result == "reviewed response"
    assert [message.content for message in llm_calls[0]] == [
        "review prompt",
        "old q",
        "old a",
        "User message: current\n\nDraft response: draft\n\nReturn the final edited response.",
    ]
    assert len(added_runs) == 1


@pytest.mark.asyncio
async def test_get_llm_history_messages_falls_back_for_malformed_values(monkeypatch):
    async def malformed_setting(key, default):
        return "not-an-int"

    monkeypatch.setattr(settings_service, "_get_setting", malformed_setting)

    assert await settings_service.get_llm_history_messages() == 20
