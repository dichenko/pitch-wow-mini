"""send_to_admin: required default tool for forwarding information to admins."""

import logging
import os
import tempfile
import time
from collections.abc import Sequence
from datetime import datetime, timezone

from langchain_core.tools import tool

from apps.bot.app.config import get_settings
from apps.bot.app.db.session import async_session_factory
from apps.bot.app.services.history_service import load_all_user_history
from packages.shared.models.database import AdminNotification, DialogueHistory

logger = logging.getLogger(__name__)
settings = get_settings()

# Context variable to hold current user data during tool invocation.
_current_context: dict = {}


def set_tool_context(
    user_data: dict,
    trace_id: str,
    current_user_message: str | None = None,
) -> None:
    """Set the current Telegram user context for tool invocations."""
    _current_context["user_data"] = user_data
    _current_context["trace_id"] = trace_id
    _current_context["current_user_message"] = current_user_message


def _format_dt(value: datetime | None) -> tuple[str, str]:
    if not value:
        return "N/A", "N/A"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%d"), value.strftime("%H:%M:%S UTC")


def _code_block(content: str | None) -> list[str]:
    safe_content = (content or "").replace("```", "`\u200b``")
    return ["```text", safe_content, "```"]


def _append_message_block(
    lines: list[str],
    date: str,
    time_text: str,
    role: str,
    content: str | None,
) -> None:
    lines.append(f"### {date} · {time_text} · {role}")
    lines.extend(_code_block(content))
    lines.append("")


def _format_history_markdown(
    first_name: str | None,
    last_name: str | None,
    username: str | None,
    tg_id: int,
    records: Sequence[DialogueHistory],
    current_user_message: str | None = None,
    current_comment: str | None = None,
) -> str:
    """Format full dialogue history as a markdown string."""
    name_parts = [p for p in (first_name, last_name) if p]
    display_name = " ".join(name_parts) if name_parts else "—"
    export_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# История диалога",
        "",
        f"**Пользователь:** {display_name} (@{username or '—'})",
        f"**TG ID:** {tg_id}",
        f"**Экспорт:** {export_time}",
        f"**Записей из БД:** {len(records)}",
        "",
        "---",
        "",
    ]

    if not records:
        lines.append("_В БД пока нет сохраненной истории диалога._")
        lines.append("")
    else:
        for index, record in enumerate(records, start=1):
            date, time_text = _format_dt(record.created_at)
            lines.append(f"## Запись {index}")
            lines.append("")
            lines.append(f"- **Thread:** `{record.thread_id}`")
            lines.append(f"- **Trace:** `{record.trace_id}`")
            lines.append("")
            _append_message_block(lines, date, time_text, "Пользователь", record.user_message)
            _append_message_block(lines, date, time_text, "Ассистент", record.assistant_response)
            lines.append("---")
            lines.append("")

    if current_user_message:
        date, time_text = _format_dt(datetime.now(timezone.utc))
        lines.append("## Текущий запрос")
        lines.append("")
        lines.append(
            "_Эта реплика добавлена из текущего tool context, потому что текущий ход "
            "еще не сохранен в `dialogue_history` на момент вызова `send_to_admin`._"
        )
        lines.append("")
        _append_message_block(lines, date, time_text, "Пользователь", current_user_message)

    if current_comment:
        date, time_text = _format_dt(datetime.now(timezone.utc))
        lines.append("## Передано администратору")
        lines.append("")
        _append_message_block(lines, date, time_text, "Комментарий", current_comment)

    return "\n".join(lines)


@tool
async def send_to_admin(comment: str) -> str:
    """Send information to administrators.

    Use this when the user wants to forward a message, request, or information
    to the admin team.

    Args:
        comment: The message or information to forward to administrators.
    """
    start_time = time.time()
    user_data = _current_context.get("user_data", {})
    trace_id = _current_context.get("trace_id", "unknown")
    current_user_message = _current_context.get("current_user_message")

    tg_id = user_data.get("tg_id", 0)
    first_name = user_data.get("first_name")
    last_name = user_data.get("last_name")
    username = user_data.get("username")
    language_code = user_data.get("language_code")

    telegram_link = f"https://t.me/{username}" if username else None
    timestamp = datetime.now(timezone.utc).isoformat()

    payload = {
        "tg_id": tg_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "telegram_link": telegram_link,
        "language_code": language_code,
        "comment": comment,
        "trace_id": trace_id,
        "created_at": timestamp,
    }

    delivered = False
    delivery_error = None

    if settings.admin_telegram_chat_id:
        try:
            from apps.bot.app.bot_instance import bot

            message_text = (
                "📨 <b>Сообщение от пользователя</b>\n\n"
                f"<b>Имя:</b> {first_name or '—'} {last_name or ''}\n"
                f"<b>Username:</b> @{username or '—'}\n"
                f"<b>Telegram:</b> {telegram_link or '—'}\n"
                f"<b>TG ID:</b> <code>{tg_id}</code>\n"
                f"<b>Язык:</b> {language_code or '—'}\n\n"
                f"<b>Сообщение:</b>\n{comment}"
            )
            await bot.send_message(int(settings.admin_telegram_chat_id), message_text)
            delivered = True

            tmp_path = None
            try:
                records = await load_all_user_history(tg_id)
                logger.info(
                    "Loaded %s dialogue history records for send_to_admin "
                    "trace_id=%s user_tg_id=%s",
                    len(records),
                    trace_id,
                    tg_id,
                )
                md_content = _format_history_markdown(
                    first_name=first_name,
                    last_name=last_name,
                    username=username,
                    tg_id=tg_id,
                    records=records,
                    current_user_message=current_user_message,
                    current_comment=comment,
                )

                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".md",
                    prefix=f"history_{tg_id}_",
                    encoding="utf-8",
                    delete=False,
                ) as tmp:
                    tmp.write(md_content)
                    tmp_path = tmp.name

                from aiogram.types import FSInputFile

                await bot.send_document(
                    int(settings.admin_telegram_chat_id),
                    document=FSInputFile(tmp_path),
                    caption=f"История диалога @{username or tg_id}",
                )
            except Exception as exc:
                logger.error(
                    "Failed to send history file to admin chat trace_id=%s: %s",
                    trace_id,
                    exc,
                    exc_info=True,
                )
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as exc:
            delivery_error = str(exc)
            logger.error(
                "Failed to send to admin chat trace_id=%s: %s",
                trace_id,
                exc,
                exc_info=True,
            )

    try:
        async with async_session_factory() as session:
            notification = AdminNotification(
                trace_id=trace_id,
                user_tg_id=tg_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                telegram_link=telegram_link,
                language_code=language_code,
                comment=comment,
                payload=payload,
                delivered=delivered,
                delivery_error=delivery_error,
            )
            session.add(notification)
            await session.commit()
    except Exception as exc:
        logger.error(
            "Failed to save notification to DB trace_id=%s: %s",
            trace_id,
            exc,
            exc_info=True,
        )

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "send_to_admin called trace_id=%s delivered=%s duration_ms=%s",
        trace_id,
        delivered,
        duration_ms,
    )

    return "Информация успешно передана администраторам."
