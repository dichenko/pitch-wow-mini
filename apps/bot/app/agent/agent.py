"""LangChain agent definition with tool calling."""

import logging
import os

from langgraph.prebuilt import create_react_agent
from sqlalchemy import select

from apps.bot.app.agent.tools import get_all_tools
from apps.bot.app.config import get_settings
from apps.bot.app.db.session import async_session_factory
from apps.bot.app.services.llm_factory import create_llm
from apps.bot.app.services.settings_service import get_llm_model, get_llm_provider
from packages.shared.models.database import DialogueHistory, UserConversationState

logger = logging.getLogger(__name__)
settings = get_settings()

# Track per-user thread reset counters.
_user_reset_counters: dict[int, int] = {}


def get_thread_id(user_tg_id: int) -> str:
    """Get the current thread ID for a user."""
    counter = _user_reset_counters.get(user_tg_id, 0)
    if counter == 0:
        return str(user_tg_id)
    return f"{user_tg_id}_{counter}"


def reset_user_thread(user_tg_id: int) -> None:
    """Increment the thread counter for a user, starting a fresh conversation."""
    current = _user_reset_counters.get(user_tg_id, 0)
    _user_reset_counters[user_tg_id] = current + 1
    logger.info(f"User {user_tg_id} conversation reset (counter={current + 1})")


async def get_current_thread_id(user_tg_id: int) -> str:
    """Get the persisted current thread ID for a user."""
    async with async_session_factory() as session:
        state = await session.get(UserConversationState, user_tg_id)
        if state:
            _sync_memory_counter(user_tg_id, state.reset_counter)
            return state.current_thread_id

        current_thread_id, counter = await _latest_thread_from_history(session, user_tg_id)
        if current_thread_id is None:
            counter = _user_reset_counters.get(user_tg_id, 0)
            current_thread_id = _thread_id_from_counter(user_tg_id, counter)

        session.add(
            UserConversationState(
                user_tg_id=user_tg_id,
                reset_counter=counter,
                current_thread_id=current_thread_id,
            )
        )
        await session.commit()
        _sync_memory_counter(user_tg_id, counter)
        return current_thread_id


async def reset_user_thread_state(user_tg_id: int) -> str:
    """Persistently reset the user's conversation and return the new thread ID."""
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(UserConversationState)
                .where(UserConversationState.user_tg_id == user_tg_id)
                .with_for_update()
            )
            state = result.scalar_one_or_none()

            if state:
                next_counter = state.reset_counter + 1
            else:
                next_counter = await _next_counter_from_history(session, user_tg_id)
                state = UserConversationState(user_tg_id=user_tg_id)
                session.add(state)

            thread_id = _thread_id_from_counter(user_tg_id, next_counter)
            state.reset_counter = next_counter
            state.current_thread_id = thread_id
            _sync_memory_counter(user_tg_id, next_counter)

    logger.info("User %s conversation reset (thread_id=%s)", user_tg_id, thread_id)
    return thread_id


async def _next_counter_from_history(session, user_tg_id: int) -> int:
    result = await session.execute(
        select(DialogueHistory.thread_id).where(DialogueHistory.user_tg_id == user_tg_id)
    )
    max_counter = 0
    user_prefix = f"{user_tg_id}_"
    for thread_id in result.scalars().all():
        if thread_id == str(user_tg_id):
            max_counter = max(max_counter, 0)
        elif thread_id.startswith(user_prefix):
            suffix = thread_id[len(user_prefix):]
            if suffix.isdigit():
                max_counter = max(max_counter, int(suffix))
    return max_counter + 1


async def _latest_thread_from_history(session, user_tg_id: int) -> tuple[str | None, int]:
    result = await session.execute(
        select(DialogueHistory.thread_id)
        .where(DialogueHistory.user_tg_id == user_tg_id)
        .order_by(DialogueHistory.created_at.desc())
        .limit(1)
    )
    thread_id = result.scalar_one_or_none()
    if thread_id is None:
        return None, 0
    return thread_id, _counter_from_thread_id(user_tg_id, thread_id)


def _counter_from_thread_id(user_tg_id: int, thread_id: str) -> int:
    if thread_id == str(user_tg_id):
        return 0
    prefix = f"{user_tg_id}_"
    if thread_id.startswith(prefix):
        suffix = thread_id[len(prefix):]
        if suffix.isdigit():
            return int(suffix)
    return 0


def _thread_id_from_counter(user_tg_id: int, counter: int) -> str:
    if counter <= 0:
        return str(user_tg_id)
    return f"{user_tg_id}_{counter}"


def _sync_memory_counter(user_tg_id: int, counter: int) -> None:
    _user_reset_counters[user_tg_id] = max(counter, _user_reset_counters.get(user_tg_id, 0))


async def create_agent(
    system_prompt: str,
    trace_id: str,
    prompt_meta: dict,
    provider_override: str | None = None,
    model_override: str | None = None,
):
    """Create a LangGraph ReAct agent with all registered tools."""
    provider = provider_override or await get_llm_provider()
    model = model_override or await get_llm_model()

    llm = create_llm(provider=provider, model=model, temperature=0.7)
    tools = get_all_tools()

    tags = [
        f"project:{settings.project_slug}",
        f"env:{settings.app_env}",
        "channel:telegram",
        f"bot-mode:{settings.bot_mode}",
    ]
    if settings.langsmith_tags:
        tags.extend([t.strip() for t in settings.langsmith_tags.split(",") if t.strip()])

    metadata = {
        "trace_id": trace_id,
        "project_slug": settings.project_slug,
        "app_env": settings.app_env,
        "bot_mode": settings.bot_mode,
        "system_prompt_version": prompt_meta.get("system_prompt_version", 0),
        "tools_instruction_version": prompt_meta.get("tools_instruction_version", 0),
        "assembled_prompt_hash": prompt_meta.get("assembled_prompt_hash", ""),
        "llm_provider": provider,
        "llm_model": model,
    }

    agent = create_react_agent(
        llm,
        tools=tools,
        state_modifier=system_prompt,
    )

    if settings.langsmith_tracing:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project or settings.project_slug
        if settings.langsmith_workspace_id:
            os.environ["LANGSMITH_WORKSPACE_ID"] = settings.langsmith_workspace_id
    else:
        os.environ.pop("LANGSMITH_TRACING", None)
        os.environ.pop("LANGSMITH_API_KEY", None)

    agent.metadata = metadata
    agent.tags = tags

    return agent
