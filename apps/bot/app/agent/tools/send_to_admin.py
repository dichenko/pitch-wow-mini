"""send_to_admin — REQUIRED default tool for forwarding information to admins."""

import logging
import os
import tempfile
import time
from datetime import datetime, timezone

from langchain_core.tools import tool
from sqlalchemy import select

from apps.bot.app.config import get_settings
from apps.bot.app.db.session import async_session_factory
from apps.bot.app.services.history_service import load_all_user_history
from packages.shared.models.database import AdminNotification

logger = logging.getLogger(__name__)
settings = get_settings()

# Context variable to hold current user data during tool invocation
_current_context: dict = {}


def set_tool_context(user_data: dict, trace_id: str) -> None:
    """Set the current Telegram user context for tool invocations."""
    _current_context["user_data"] = user_data
    _current_context["trace_id"] = trace_id


def _format_history_markdown(
    first_name: str | None,
    last_name: str | None,
    username: str | None,
    tg_id: int,
    records,
) -> str:
    """Format dialogue history as a markdown string."""
    name_parts = [p for p in (first_name, last_name) if p]
    display_name = " ".join(name_parts) if name_parts else "—"
    export_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Dialogue History",
        "",
        f"**User:** {display_name} (@{username or '—'})",
        f"**TG ID:** {tg_id}",
        f"**Exported at:** {export_time}",
        "",
        "---",
        "",
    ]

    if not records:
        lines.append("*No dialogue history recorded*")
    else:
        for record in records:
            lines.append(f"## User:")
            lines.append(record.user_message or "")
            lines.append("")
            lines.append(f"## Assistant:")
            lines.append(record.assistant_response or "")
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


@tool
async def send_to_admin(comment: str) -> str:
    """Send information to the administrators. Use this when the user wants to forward a message, request, or information to the admin team.

    Args:
        comment: The message or information to forward to administrators.
    """
    start_time = time.time()
    user_data = _current_context.get("user_data", {})
    trace_id = _current_context.get("trace_id", "unknown")

    tg_id = user_data.get("tg_id", 0)
    first_name = user_data.get("first_name")
    last_name = user_data.get("last_name")
    username = user_data.get("username")
    language_code = user_data.get("language_code")

    telegram_link = f"https://t.me/{username}" if username else None
    timestamp = datetime.now(timezone.utc).isoformat()

    # Build notification payload
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

    # Try to send to Telegram admin chat
    if settings.admin_telegram_chat_id:
        try:
            from apps.bot.app.bot_instance import bot

            message_text = (
                f"📨 <b>Сообщение от пользователя</b>\n\n"
                f"<b>Имя:</b> {first_name or '—'} {last_name or ''}\n"
                f"<b>Username:</b> @{username or '—'}\n"
                f"<b>Telegram:</b> {telegram_link or '—'}\n"
                f"<b>TG ID:</b> <code>{tg_id}</code>\n"
                f"<b>Язык:</b> {language_code or '—'}\n\n"
                f"<b>Сообщение:</b>\n{comment}"
            )
            await bot.send_message(int(settings.admin_telegram_chat_id), message_text)
            delivered = True

            # Send dialogue history as markdown file
            tmp_path = None
            try:
                records = await load_all_user_history(tg_id)
                md_content = _format_history_markdown(
                    first_name=first_name,
                    last_name=last_name,
                    username=username,
                    tg_id=tg_id,
                    records=records,
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
            except Exception as e:
                logger.error(f"Failed to send history file to admin chat: {e}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as e:
            delivery_error = str(e)
            logger.error(f"Failed to send to admin chat: {e}")

    # Always save to DB
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
    except Exception as e:
        logger.error(f"Failed to save notification to DB: {e}")

    # Log tool call
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        f"send_to_admin called trace_id={trace_id} "
        f"delivered={delivered} duration_ms={duration_ms}"
    )

    return "Информация успешно передана администраторам."
