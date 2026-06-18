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
from apps.bot.app.services.history_service import (
    load_latest_user_thread_history,
    load_user_thread_history,
)
from apps.bot.app.services.pdf_dossier_service import PdfDossierService
from packages.shared.models.database import AdminNotification, DialogueHistory

logger = logging.getLogger(__name__)
settings = get_settings()

# Context variable to hold current user data during tool invocation.
_current_context: dict = {}


def set_tool_context(
    user_data: dict,
    trace_id: str,
    current_user_message: str | None = None,
    current_thread_id: str | None = None,
) -> None:
    """Set the current Telegram user context for tool invocations."""
    _current_context["user_data"] = user_data
    _current_context["trace_id"] = trace_id
    _current_context["current_user_message"] = current_user_message
    _current_context["current_thread_id"] = current_thread_id


def _format_dt(value: datetime | None) -> tuple[str, str]:
    if not value:
        return "N/A", "N/A"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%d"), value.strftime("%H:%M")


def _append_dialogue_turn(
    lines: list[str],
    time_text: str,
    user_message: str | None,
    assistant_response: str | None = None,
) -> None:
    lines.append(f"**{time_text} Фаундер**: {user_message or ''}")
    lines.append("")
    if assistant_response:
        lines.append(f"**Ассистент**: {assistant_response}")
        lines.append("")
    lines.append("---")
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
    """Format dialogue history as a date-grouped markdown string."""
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
        current_date = None
        for record in records:
            date, time_text = _format_dt(record.created_at)
            if date != current_date:
                lines.append(f"## {date}")
                lines.append("")
                current_date = date
            _append_dialogue_turn(
                lines,
                time_text,
                record.user_message,
                record.assistant_response,
            )

    if current_user_message:
        date, time_text = _format_dt(datetime.now(timezone.utc))
        last_date_heading = f"## {date}"
        if last_date_heading not in lines:
            lines.append(f"## {date}")
            lines.append("")
        _append_dialogue_turn(lines, time_text, current_user_message)

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
    current_thread_id = _current_context.get("current_thread_id")

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
    pdf_dossier_metadata = None

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
            records: list[DialogueHistory] = []
            try:
                if current_thread_id:
                    records = await load_user_thread_history(tg_id, current_thread_id)
                else:
                    records = await load_latest_user_thread_history(tg_id)
                logger.info(
                    "Loaded %s dialogue history records for send_to_admin "
                    "trace_id=%s user_tg_id=%s thread_id=%s",
                    len(records),
                    trace_id,
                    tg_id,
                    current_thread_id or "latest",
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

            pdf_path = None
            try:
                pdf_result = await PdfDossierService(settings=settings).generate(
                    records=records,
                    external_id=trace_id,
                    user_data=user_data,
                    current_user_message=current_user_message,
                    comment=comment,
                )
                pdf_dossier_metadata = pdf_result.metadata
                if pdf_result.success and pdf_result.pdf_path:
                    pdf_path = pdf_result.pdf_path

                    from aiogram.types import FSInputFile

                    await bot.send_document(
                        int(settings.admin_telegram_chat_id),
                        document=FSInputFile(pdf_path),
                        caption=f"PDF dossier @{username or tg_id}",
                    )
                else:
                    await bot.send_message(
                        int(settings.admin_telegram_chat_id),
                        f"PDF не создан: {pdf_result.error or pdf_result.status}",
                    )
            except Exception as exc:
                pdf_dossier_metadata = {"status": "failed", "error": str(exc)}
                logger.error(
                    "Failed to generate or send PDF dossier trace_id=%s: %s",
                    trace_id,
                    exc,
                    exc_info=True,
                )
                try:
                    await bot.send_message(
                        int(settings.admin_telegram_chat_id),
                        f"PDF не создан: {exc}",
                    )
                except Exception:
                    logger.error(
                        "Failed to send PDF failure message trace_id=%s",
                        trace_id,
                        exc_info=True,
                    )
            finally:
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)
        except Exception as exc:
            delivery_error = str(exc)
            logger.error(
                "Failed to send to admin chat trace_id=%s: %s",
                trace_id,
                exc,
                exc_info=True,
            )

    try:
        if pdf_dossier_metadata is not None:
            payload["pdf_dossier"] = pdf_dossier_metadata
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
