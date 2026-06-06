"""LangChain agent definition with tool calling."""

import logging
import os

from langgraph.prebuilt import create_react_agent

from apps.bot.app.agent.tools import get_all_tools
from apps.bot.app.config import get_settings
from apps.bot.app.services.llm_factory import create_llm
from apps.bot.app.services.settings_service import get_llm_model, get_llm_provider

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


async def create_agent(system_prompt: str, trace_id: str, prompt_meta: dict):
    """Create a LangGraph ReAct agent with all registered tools."""
    provider = await get_llm_provider()
    model = await get_llm_model()

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
