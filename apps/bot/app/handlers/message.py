"""User message handler — invokes LangChain agent."""

import logging
import time
import uuid

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from apps.bot.app.agent.agent import create_agent, get_thread_id
from apps.bot.app.agent.prompt_assembler import assemble_prompt
from apps.bot.app.agent.tools.send_to_admin import set_tool_context
from apps.bot.app.config import get_settings
from apps.bot.app.services.censor_service import apply_censor
from apps.bot.app.services.history_service import (
    dialogue_history_to_messages,
    load_dialogue_history,
    save_dialogue_turn_best_effort,
)
from apps.bot.app.services.language_service import require_preferred_language
from apps.bot.app.services.settings_service import get_llm_history_messages
from apps.bot.app.services.telegram_messages import answer_markdown_or_text
from apps.bot.app.services.tool_log_service import log_tool_call

logger = logging.getLogger(__name__)
router = Router()
settings = get_settings()

PROCESSING_ERROR_MESSAGES = {
    "ru": "Извините, произошла ошибка при обработке вашего сообщения. Попробуйте позже.",
    "uz": "Kechirasiz, xabaringizni qayta ishlashda xatolik yuz berdi. Keyinroq urinib ko'ring.",
    "en": "Sorry, an error occurred while processing your message. Please try again later.",
}


async def send_typing_activity(message: Message) -> None:
    bot = getattr(message, "bot", None)
    chat = getattr(message, "chat", None)
    chat_id = getattr(chat, "id", None)
    if bot is None or chat_id is None:
        return

    try:
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception as exc:
        logger.warning("Failed to send typing chat action: %s", exc, exc_info=True)


@router.message(~Command("start", "admin", "restart"))
async def handle_message(message: Message) -> None:
    if not message.from_user or not message.text:
        return

    language = await require_preferred_language(message)
    if language is None:
        return

    await process_user_text(
        message=message,
        user_text=message.text,
        response_language=language,
    )


async def process_user_text(
    message: Message,
    user_text: str,
    response_language: str | None = None,
) -> str | None:
    if not message.from_user or not user_text:
        return None

    await send_typing_activity(message)

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
        current_user_message=user_text,
        current_thread_id=thread_id,
    )

    try:
        # Assemble prompt
        system_prompt, prompt_meta = await assemble_prompt()
        history_limit = await get_llm_history_messages()
        history_records = await load_dialogue_history(
            user_tg_id=user.id,
            thread_id=thread_id,
            limit=history_limit,
        )
        history_messages = dialogue_history_to_messages(history_records)

        # Add telegram user info to metadata for LangSmith
        prompt_meta["telegram_user_id"] = user.id
        prompt_meta["telegram_username"] = user.username or ""
        if response_language:
            prompt_meta["response_language"] = response_language

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
        language_instruction = _response_language_instruction(response_language)
        input_messages = [*history_messages]
        if language_instruction:
            input_messages.append(SystemMessage(content=language_instruction))
        input_messages.append(HumanMessage(content=user_text))

        response = await agent.ainvoke(
            {"messages": input_messages},
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
            user_message=user_text,
            trace_id=trace_id,
            user_tg_id=user.id,
            history_messages=history_messages,
        )

        await answer_markdown_or_text(message, final_response)
        await save_dialogue_turn_best_effort(
            user_tg_id=user.id,
            thread_id=thread_id,
            trace_id=trace_id,
            user_message=user_text,
            assistant_response=final_response,
            llm_provider=getattr(agent, "metadata", {}).get("llm_provider"),
            llm_model=getattr(agent, "metadata", {}).get("llm_model"),
        )
        logger.info(f"Message processed trace_id={trace_id} thread_id={thread_id} user_tg_id={user.id}")
        return final_response

    except Exception as e:
        logger.error(f"Agent error trace_id={trace_id}: {e}", exc_info=True)
        await answer_markdown_or_text(
            message,
            PROCESSING_ERROR_MESSAGES.get(
                response_language or "ru",
                PROCESSING_ERROR_MESSAGES["ru"],
            )
        )
        return None


def _response_language_instruction(language: str | None) -> str | None:
    if language == "uz":
        return (
            "The user's current message is Uzbek. Reply only in Uzbek Latin script. "
            "Do not switch to Russian or English unless the user explicitly asks."
        )
    if language == "ru":
        return (
            "The user's current message is Russian. Reply only in Russian. "
            "Do not switch to Uzbek or English unless the user explicitly asks."
        )
    if language == "en":
        return (
            "The user's current message is English. Reply only in English. "
            "Do not switch to Russian or Uzbek unless the user explicitly asks."
        )
    return None
