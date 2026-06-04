"""Prompt service — loads active prompts from DB."""

import logging

from sqlalchemy import select, func

from apps.bot.app.db.session import async_session_factory
from packages.shared.models.database import PromptVersion

logger = logging.getLogger(__name__)


async def get_active_system_prompt() -> str | None:
    """Return the active system prompt content."""
    return await _get_active_content("system_prompt")


async def get_active_tools_instruction() -> str | None:
    """Return the active tools instruction content."""
    return await _get_active_content("tools_instruction")


async def get_active_censor_prompt() -> str | None:
    """Return the active censor prompt content."""
    return await _get_active_content("censor_prompt")


async def get_prompt_versions(kind: str, limit: int = 3) -> list[PromptVersion]:
    """Return last N versions for a given kind (newest first)."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(PromptVersion)
            .where(PromptVersion.kind == kind)
            .order_by(PromptVersion.version_number.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def create_prompt_version(
    kind: str,
    content: str,
    admin_id=None,
    admin_tg_id: int | None = None,
    admin_username: str | None = None,
    change_note: str | None = None,
) -> PromptVersion:
    """Create a new prompt version and mark it active."""
    async with async_session_factory() as session:
        # Get next version number
        result = await session.execute(
            select(func.max(PromptVersion.version_number)).where(PromptVersion.kind == kind)
        )
        max_version = result.scalar_one_or_none() or 0
        next_version = max_version + 1

        # Deactivate all current versions
        await session.execute(
            PromptVersion.__table__.update()
            .where(PromptVersion.kind == kind, PromptVersion.is_active == True)
            .values(is_active=False)
        )

        # Create new version
        new_version = PromptVersion(
            kind=kind,
            version_number=next_version,
            content=content,
            is_active=True,
            created_by_admin_id=admin_id,
            created_by_tg_id=admin_tg_id,
            created_by_username=admin_username,
            change_note=change_note,
        )
        session.add(new_version)
        await session.commit()
        await session.refresh(new_version)
        return new_version


async def restore_prompt_version(
    kind: str,
    source_version_id,
    admin_id=None,
    admin_tg_id: int | None = None,
    admin_username: str | None = None,
) -> PromptVersion:
    """Restore a previous version by creating a new version copied from source."""
    async with async_session_factory() as session:
        # Get source version
        result = await session.execute(
            select(PromptVersion).where(PromptVersion.id == source_version_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            raise ValueError(f"Source version {source_version_id} not found")

        # Get next version number
        result = await session.execute(
            select(func.max(PromptVersion.version_number)).where(PromptVersion.kind == kind)
        )
        max_version = result.scalar_one_or_none() or 0
        next_version = max_version + 1

        # Deactivate all current versions
        await session.execute(
            PromptVersion.__table__.update()
            .where(PromptVersion.kind == kind, PromptVersion.is_active == True)
            .values(is_active=False)
        )

        # Create new version from source
        new_version = PromptVersion(
            kind=kind,
            version_number=next_version,
            content=source.content,
            is_active=True,
            created_by_admin_id=admin_id,
            created_by_tg_id=admin_tg_id,
            created_by_username=admin_username,
            change_note=f"Restored from version {source.version_number}",
            restored_from_version_id=source.id,
        )
        session.add(new_version)
        await session.commit()
        await session.refresh(new_version)
        return new_version


async def _get_active_content(kind: str) -> str | None:
    """Load the active content for a given kind."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(PromptVersion.content).where(
                PromptVersion.kind == kind, PromptVersion.is_active == True
            )
        )
        return result.scalar_one_or_none()
