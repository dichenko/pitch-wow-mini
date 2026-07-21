"""User message handler — invokes LangChain agent."""

import logging
import time
import uuid
from datetime import datetime, timezone

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from apps.bot.app.agent.agent import create_agent, get_current_thread_id
from apps.bot.app.agent.prompt_assembler import assemble_prompt
from apps.bot.app.agent.tools.send_to_admin import set_tool_context
from apps.bot.app.db.session import async_session_factory
from apps.bot.app.config import get_settings
from apps.bot.app.services.censor_service import apply_censor
from apps.bot.app.services.history_service import (
    dialogue_history_to_messages,
    load_dialogue_history,
    save_dialogue_turn_best_effort,
)
from apps.bot.app.services.language_service import require_preferred_language
from apps.bot.app.services.settings_service import (
    get_llm_history_messages,
    get_llm_model,
    get_llm_provider,
)
from apps.bot.app.services.telegram_messages import (
    answer_markdown_or_text,
    send_message_markdown_or_text,
)
from apps.bot.app.services.tool_log_service import log_tool_call
from packages.shared.models.database import AdminNotification

logger = logging.getLogger(__name__)
router = Router()
settings = get_settings()

FALLBACK_LLM_PROVIDER = "openai"

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
    thread_id = await get_current_thread_id(user.id)

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

        # Invoke agent with config
        language_instruction = _response_language_instruction(response_language)
        input_messages = [*history_messages]
        if language_instruction:
            input_messages.append(SystemMessage(content=language_instruction))
        input_messages.append(HumanMessage(content=user_text))

        try:
            agent = await create_agent(
                system_prompt=system_prompt,
                trace_id=trace_id,
                prompt_meta=prompt_meta,
            )
        except Exception as primary_exc:
            primary_provider = await _safe_current_provider()
            primary_model = await _safe_current_model()
            logger.error(
                "Primary LLM provider initialization failed trace_id=%s "
                "provider=%s model=%s: %s",
                trace_id,
                primary_provider,
                primary_model,
                primary_exc,
                exc_info=True,
            )
            await _notify_provider_failure(
                trace_id=trace_id,
                user_data={
                    "tg_id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "username": user.username,
                    "language_code": user.language_code,
                },
                thread_id=thread_id,
                provider=primary_provider,
                model=primary_model,
                stage="primary_init",
                error=primary_exc,
                fallback_provider=FALLBACK_LLM_PROVIDER,
                fallback_model=settings.openai_text_model,
                user_text=user_text,
            )
            agent = await _create_fallback_agent_or_notify(
                system_prompt=system_prompt,
                trace_id=trace_id,
                prompt_meta=prompt_meta,
                thread_id=thread_id,
                user_data={
                    "tg_id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "username": user.username,
                    "language_code": user.language_code,
                },
                user_text=user_text,
            )
            allow_fallback = False
        else:
            allow_fallback = True

        agent, response = await _invoke_agent_with_provider_fallback(
            agent=agent,
            input_messages=input_messages,
            system_prompt=system_prompt,
            trace_id=trace_id,
            prompt_meta=prompt_meta,
            thread_id=thread_id,
            user_data={
                "tg_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "language_code": user.language_code,
            },
            user_text=user_text,
            allow_fallback=allow_fallback,
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


def _agent_config(agent, thread_id: str) -> dict:
    return {
        "metadata": getattr(agent, "metadata", {}),
        "tags": getattr(agent, "tags", []),
        "configurable": {"thread_id": thread_id},
    }


async def _safe_current_provider() -> str:
    try:
        return await get_llm_provider()
    except Exception as exc:
        logger.warning("Failed to read current LLM provider: %s", exc, exc_info=True)
        return "unknown"


async def _safe_current_model() -> str:
    try:
        return await get_llm_model()
    except Exception as exc:
        logger.warning("Failed to read current LLM model: %s", exc, exc_info=True)
        return "unknown"


async def _invoke_agent_with_provider_fallback(
    agent,
    input_messages: list,
    system_prompt: str,
    trace_id: str,
    prompt_meta: dict,
    thread_id: str,
    user_data: dict,
    user_text: str,
    allow_fallback: bool = True,
) -> tuple[object, dict]:
    primary_provider = getattr(agent, "metadata", {}).get("llm_provider")
    primary_model = getattr(agent, "metadata", {}).get("llm_model")

    try:
        response = await agent.ainvoke(
            {"messages": input_messages},
            config=_agent_config(agent, thread_id),
        )
        return agent, response
    except Exception as primary_exc:
        if not allow_fallback:
            logger.error(
                "Fallback LLM provider failed trace_id=%s provider=%s model=%s: %s",
                trace_id,
                primary_provider,
                primary_model,
                primary_exc,
                exc_info=True,
            )
            await _notify_provider_failure(
                trace_id=trace_id,
                user_data=user_data,
                thread_id=thread_id,
                provider=primary_provider or FALLBACK_LLM_PROVIDER,
                model=primary_model or settings.openai_text_model,
                stage="fallback",
                error=primary_exc,
                fallback_provider=None,
                fallback_model=None,
                user_text=user_text,
            )
            raise primary_exc

        logger.error(
            "Primary LLM provider failed trace_id=%s provider=%s model=%s: %s",
            trace_id,
            primary_provider,
            primary_model,
            primary_exc,
            exc_info=True,
        )
        await _notify_provider_failure(
            trace_id=trace_id,
            user_data=user_data,
            thread_id=thread_id,
            provider=primary_provider or "unknown",
            model=primary_model or "unknown",
            stage="primary",
            error=primary_exc,
            fallback_provider=FALLBACK_LLM_PROVIDER,
            fallback_model=settings.openai_text_model,
            user_text=user_text,
        )

    fallback_agent = await _create_fallback_agent_or_notify(
        system_prompt=system_prompt,
        trace_id=trace_id,
        prompt_meta=prompt_meta,
        thread_id=thread_id,
        user_data=user_data,
        user_text=user_text,
    )

    try:
        response = await fallback_agent.ainvoke(
            {"messages": input_messages},
            config=_agent_config(fallback_agent, thread_id),
        )
        logger.info(
            "Fallback LLM provider succeeded trace_id=%s provider=%s model=%s",
            trace_id,
            FALLBACK_LLM_PROVIDER,
            settings.openai_text_model,
        )
        return fallback_agent, response
    except Exception as fallback_exc:
        logger.error(
            "Fallback LLM provider failed trace_id=%s provider=%s model=%s: %s",
            trace_id,
            FALLBACK_LLM_PROVIDER,
            settings.openai_text_model,
            fallback_exc,
            exc_info=True,
        )
        await _notify_provider_failure(
            trace_id=trace_id,
            user_data=user_data,
            thread_id=thread_id,
            provider=FALLBACK_LLM_PROVIDER,
            model=settings.openai_text_model,
            stage="fallback",
            error=fallback_exc,
            fallback_provider=None,
            fallback_model=None,
            user_text=user_text,
        )
        raise


async def _create_fallback_agent_or_notify(
    system_prompt: str,
    trace_id: str,
    prompt_meta: dict,
    thread_id: str,
    user_data: dict,
    user_text: str,
):
    try:
        return await create_agent(
            system_prompt=system_prompt,
            trace_id=trace_id,
            prompt_meta=prompt_meta,
            provider_override=FALLBACK_LLM_PROVIDER,
            model_override=settings.openai_text_model,
        )
    except Exception as fallback_exc:
        logger.error(
            "Fallback LLM provider initialization failed trace_id=%s "
            "provider=%s model=%s: %s",
            trace_id,
            FALLBACK_LLM_PROVIDER,
            settings.openai_text_model,
            fallback_exc,
            exc_info=True,
        )
        await _notify_provider_failure(
            trace_id=trace_id,
            user_data=user_data,
            thread_id=thread_id,
            provider=FALLBACK_LLM_PROVIDER,
            model=settings.openai_text_model,
            stage="fallback_init",
            error=fallback_exc,
            fallback_provider=None,
            fallback_model=None,
            user_text=user_text,
        )
        raise


async def _notify_provider_failure(
    trace_id: str,
    user_data: dict,
    thread_id: str,
    provider: str,
    model: str,
    stage: str,
    error: Exception,
    fallback_provider: str | None,
    fallback_model: str | None,
    user_text: str,
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    error_text = str(error)
    if len(error_text) > 1500:
        error_text = f"{error_text[:1500]}..."

    tg_id = int(user_data.get("tg_id") or 0)
    username = user_data.get("username")
    first_name = user_data.get("first_name")
    last_name = user_data.get("last_name")
    language_code = user_data.get("language_code")
    telegram_link = f"https://t.me/{username}" if username else None

    next_step = (
        f"Retrying with {fallback_provider}/{fallback_model}"
        if fallback_provider and fallback_model
        else "No further fallback configured"
    )
    comment = (
        "LLM provider failure\n\n"
        f"Stage: {stage}\n"
        f"Provider: {provider}\n"
        f"Model: {model}\n"
        f"Trace ID: {trace_id}\n"
        f"Thread ID: {thread_id}\n"
        f"User TG ID: {tg_id}\n"
        f"Username: @{username or '-'}\n"
        f"Next step: {next_step}\n\n"
        f"Error:\n{error_text}\n\n"
        f"User message:\n{user_text[:1000]}"
    )

    delivered = False
    delivery_error = None

    try:
        from apps.bot.app.bot_instance import bot

        await send_message_markdown_or_text(
            bot,
            _provider_failure_admin_chat_id(),
            comment,
        )
        delivered = True
    except Exception as exc:
        delivery_error = str(exc)
        logger.error(
            "Failed to send provider failure alert trace_id=%s: %s",
            trace_id,
            exc,
            exc_info=True,
        )
    try:
        async with async_session_factory() as session:
            session.add(
                AdminNotification(
                    trace_id=trace_id,
                    user_tg_id=tg_id,
                    first_name=first_name,
                    last_name=last_name,
                    username=username,
                    telegram_link=telegram_link,
                    language_code=language_code,
                    comment=comment,
                    payload={
                        "type": "llm_provider_failure",
                        "stage": stage,
                        "provider": provider,
                        "model": model,
                        "fallback_provider": fallback_provider,
                        "fallback_model": fallback_model,
                        "thread_id": thread_id,
                        "trace_id": trace_id,
                        "created_at": timestamp,
                    },
                    delivered=delivered,
                    delivery_error=delivery_error,
                )
            )
            await session.commit()
    except Exception as exc:
        logger.error(
            "Failed to save provider failure alert trace_id=%s: %s",
            trace_id,
            exc,
            exc_info=True,
        )


def _provider_failure_admin_chat_id() -> int:
    if not settings.admin_telegram_chat_id:
        raise ValueError("ADMIN_TELEGRAM_CHAT_ID is not set")
    return int(settings.admin_telegram_chat_id)
