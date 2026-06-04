"""Tool call logging service — records every tool invocation to DB."""

import logging
import time

from apps.bot.app.db.session import async_session_factory
from packages.shared.models.database import ToolCallLog

logger = logging.getLogger(__name__)


async def log_tool_call(
    trace_id: str,
    user_tg_id: int | None,
    tool_name: str,
    tool_input: dict | None,
    tool_output: str | None,
    status: str,
    error: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Log a tool call to the tool_call_logs table."""
    try:
        async with async_session_factory() as session:
            entry = ToolCallLog(
                trace_id=trace_id,
                user_tg_id=user_tg_id,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                status=status,
                error=error,
                duration_ms=duration_ms,
            )
            session.add(entry)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to log tool call: {e}")
