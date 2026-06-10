"""Seed service — inserts missing default prompts on startup."""

import logging

from sqlalchemy import select, func

from apps.bot.app.db.session import async_session_factory
from packages.shared.models.database import AppSetting, PromptVersion
from packages.shared.utils.welcome_messages import DEFAULT_WELCOME_MESSAGES, WELCOME_PROMPT_KINDS

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant.
You answer questions clearly and concisely.
You help users with their inquiries and provide useful information."""

DEFAULT_TOOLS_INSTRUCTION = """You have access to the following tools:

- **send_to_admin**: Use this tool when the user wants to forward information, make a request, or contact the administration team. The tool will automatically include the user's contact details.
- **save_lead**: Use this tool when the user wants to leave their contact information for follow-up.
- **get_project_knowledge**: Use this tool when you need to look up information from the project knowledge base.
- **create_followup_task**: Use this tool when the user requests a follow-up action or reminder.

Always call tools when they are relevant. Do not fabricate tool results."""

DEFAULT_CENSOR_PROMPT = """You are a response reviewer. Your job is to review AI assistant responses before they are sent to users.

Rules:
- Remove any inappropriate content
- Ensure the response is professional and helpful
- Do not add information that was not in the original response
- Return the edited response directly, without explanations"""

async def seed_defaults() -> None:
    """Seed default prompt versions and settings that are not present yet."""
    async with async_session_factory() as session:
        await _seed_prompt_if_missing(
            session=session,
            kind="system_prompt",
            content=DEFAULT_SYSTEM_PROMPT,
        )
        await _seed_prompt_if_missing(
            session=session,
            kind="tools_instruction",
            content=DEFAULT_TOOLS_INSTRUCTION,
        )
        await _seed_prompt_if_missing(
            session=session,
            kind="censor_prompt",
            content=DEFAULT_CENSOR_PROMPT,
        )

        legacy_welcome = await _get_legacy_welcome_content(session)
        await _seed_prompt_if_missing(
            session=session,
            kind=WELCOME_PROMPT_KINDS["ru"],
            content=legacy_welcome or DEFAULT_WELCOME_MESSAGES["ru"],
            change_note=(
                "Initial localized seed from legacy welcome_message"
                if legacy_welcome
                else "Initial localized seed"
            ),
        )
        await _seed_prompt_if_missing(
            session=session,
            kind=WELCOME_PROMPT_KINDS["uz"],
            content=DEFAULT_WELCOME_MESSAGES["uz"],
            change_note="Initial localized seed",
        )
        await _seed_prompt_if_missing(
            session=session,
            kind=WELCOME_PROMPT_KINDS["en"],
            content=DEFAULT_WELCOME_MESSAGES["en"],
            change_note="Initial localized seed",
        )

        result = await session.execute(
            select(AppSetting).where(AppSetting.key == "censor_enabled")
        )
        if not result.scalar_one_or_none():
            session.add(AppSetting(key="censor_enabled", value="false"))

        await session.commit()
        logger.info("Missing default prompts and settings seeded successfully")


async def _seed_prompt_if_missing(
    session,
    kind: str,
    content: str,
    change_note: str = "Initial seed",
) -> None:
    result = await session.execute(
        select(func.count()).select_from(PromptVersion).where(PromptVersion.kind == kind)
    )
    if result.scalar_one() > 0:
        logger.debug("Prompt kind %s already exists, skipping seed", kind)
        return

    session.add(
        PromptVersion(
            kind=kind,
            version_number=1,
            content=content,
            is_active=True,
            created_by_username="system",
            change_note=change_note,
        )
    )


async def _get_legacy_welcome_content(session) -> str | None:
    result = await session.execute(
        select(PromptVersion.content)
        .where(PromptVersion.kind == "welcome_message", PromptVersion.is_active == True)
        .order_by(PromptVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
