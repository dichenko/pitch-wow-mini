"""User message handler — invokes LangChain agent."""

import logging
import time
import uuid

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from langchain_core.messages import ToolMessage

from apps.bot.app.agent.agent import create_agent, get_thread_id
from apps.bot.app.agent.prompt_assembler import assemble_prompt
from apps.bot.app.agent.tools.send_to_admin import set_tool_context
from apps.bot.app.config import get_settings
from apps.bot.app.services.censor_service import apply_censor
from apps.bot.app.services.tool_log_service import log_tool_call

logger = logging.getLogger(__name__)
router = Router()
settings = get_settings()


@router.message(~Command("start", "admin", "restart"))
async def handle_message(message: Message) -> None:
    if not message.from_user or not message.text:
        return

    trace_id = str(uuid.uuid4())
    user = message.from_user
    thread_id = get_thread_id(user.id)

    # Set tool context so tools can access user data
    set_tool_context(
        user_data={
            "tg_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "language_code": user.language_code,
        },
        trace_id=trace_id,
    )

    try:
        # Assemble prompt
        system_prompt, prompt_meta = await assemble_prompt()

        # Add telegram user info to metadata for LangSmith
        prompt_meta["telegram_user_id"] = user.id
        prompt_meta["telegram_username"] = user.username or ""

        # Create agent
        agent = await create_agent(
            system_prompt=system_prompt, trace_id=trace_id, prompt_meta=prompt_meta
        )

        # Build LangSmith config with metadata and tags
        config = {
            "metadata": getattr(agent, "metadata", {}),
            "tags": getattr(agent, "tags", []),
            "configurable": {"thread_id": thread_id},
        }

        # Invoke agent with config
        response = await agent.ainvoke(
            {"messages": [("user", message.text)]},
            config=config,
        )

        # Log tool calls from the response
        for msg in response.get("messages", []):
            if isinstance(msg, ToolMessage):
                await log_tool_call(
                    trace_id=trace_id,
                    user_tg_id=user.id,
                    tool_name=msg.name or "unknown",
                    tool_input=None,
                    tool_output=str(msg.content)[:1000],
                    status="success",
                )

        # Extract final text from agent response
        draft_response = (
            response["messages"][-1].content if response.get("messages") else ""
        )

        # Apply censor if enabled
        final_response = await apply_censor(
            draft_response=draft_response,
            user_message=message.text,
            trace_id=trace_id,
            user_tg_id=user.id,
        )

        await message.answer(final_response)
        logger.info(f"Message processed trace_id={trace_id} thread_id={thread_id} user_tg_id={user.id}")

    except Exception as e:
        logger.error(f"Agent error trace_id={trace_id}: {e}", exc_info=True)
        await message.answer(
            "Извините, произошла ошибка при обработке вашего сообщения. Попробуйте позже."
        )
