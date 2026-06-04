"""Prompt assembler — combines guardrails + system prompt + tools instruction."""

import hashlib
import logging

from apps.bot.app.agent.core_guardrails import GUARDRAILS
from apps.bot.app.services.prompt_service import (
    get_active_system_prompt,
    get_active_tools_instruction,
)

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant. Answer questions clearly and concisely."
DEFAULT_TOOLS_INSTRUCTION = (
    "Use available tools when appropriate. "
    "Call send_to_admin when the user wants to forward information to administrators."
)


async def assemble_prompt() -> tuple[str, dict]:
    """Assemble the full system prompt.

    Returns:
        Tuple of (assembled_prompt, metadata_dict)
    """
    system_prompt = await get_active_system_prompt()
    if not system_prompt:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    tools_instruction = await get_active_tools_instruction()
    if not tools_instruction:
        tools_instruction = DEFAULT_TOOLS_INSTRUCTION

    # Get version numbers for metadata
    from apps.bot.app.db.session import async_session_factory
    from sqlalchemy import select, func
    from packages.shared.models.database import PromptVersion

    meta = {"system_prompt_version": 0, "tools_instruction_version": 0}
    async with async_session_factory() as session:
        for kind, key in [("system_prompt", "system_prompt_version"),
                          ("tools_instruction", "tools_instruction_version")]:
            result = await session.execute(
                select(PromptVersion.version_number).where(
                    PromptVersion.kind == kind, PromptVersion.is_active == True
                )
            )
            version = result.scalar_one_or_none()
            if version is not None:
                meta[key] = version

    assembled = (
        f"{GUARDRAILS}\n\n"
        f"{system_prompt}\n\n"
        f"# Tools usage instruction\n\n"
        f"{tools_instruction}"
    )

    assembled_hash = hashlib.sha256(assembled.encode("utf-8")).hexdigest()
    meta["assembled_prompt_hash"] = assembled_hash

    logger.debug(f"Prompt assembled, hash={assembled_hash[:12]}...")
    return assembled, meta
