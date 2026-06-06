"""Seed service — inserts default prompts on first startup."""

import logging

from sqlalchemy import select, func

from apps.bot.app.db.session import async_session_factory
from packages.shared.models.database import AppSetting, PromptVersion

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

DEFAULT_WELCOME_MESSAGE = (
    "Привет! Я AI-ассистент. Чем могу помочь?\n\n"
    "Для администраторов: используйте /admin для входа в панель управления."
)


async def seed_defaults() -> None:
    """Seed default prompt versions if the prompt_versions table is empty."""
    async with async_session_factory() as session:
        result = await session.execute(select(func.count()).select_from(PromptVersion))
        count = result.scalar_one()

        if count > 0:
            logger.debug("Prompt versions already exist, skipping seed")
            return

        # Seed system prompt
        session.add(
            PromptVersion(
                kind="system_prompt",
                version_number=1,
                content=DEFAULT_SYSTEM_PROMPT,
                is_active=True,
                created_by_username="system",
                change_note="Initial seed",
            )
        )

        # Seed tools instruction
        session.add(
            PromptVersion(
                kind="tools_instruction",
                version_number=1,
                content=DEFAULT_TOOLS_INSTRUCTION,
                is_active=True,
                created_by_username="system",
                change_note="Initial seed",
            )
        )

        # Seed censor prompt
        session.add(
            PromptVersion(
                kind="censor_prompt",
                version_number=1,
                content=DEFAULT_CENSOR_PROMPT,
                is_active=True,
                created_by_username="system",
                change_note="Initial seed",
            )
        )

        # Seed welcome message
        session.add(
            PromptVersion(
                kind="welcome_message",
                version_number=1,
                content=DEFAULT_WELCOME_MESSAGE,
                is_active=True,
                created_by_username="system",
                change_note="Initial seed",
            )
        )

        # Seed default censor_enabled setting
        result = await session.execute(
            select(AppSetting).where(AppSetting.key == "censor_enabled")
        )
        if not result.scalar_one_or_none():
            session.add(AppSetting(key="censor_enabled", value="false"))

        await session.commit()
        logger.info("Default prompts and settings seeded successfully")
