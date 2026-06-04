"""Admin service — manages admin records and root admin bootstrap."""

import logging

from sqlalchemy import select

from apps.bot.app.config import get_settings
from apps.bot.app.db.session import async_session_factory
from packages.shared.models.database import Admin

logger = logging.getLogger(__name__)
settings = get_settings()


async def bootstrap_root_admin() -> None:
    """Ensure root admin from .env exists in the admins table as superadmin."""
    if not settings.root_admin_tg_id:
        logger.warning("ROOT_ADMIN_TG_ID not configured, skipping root admin bootstrap")
        return

    async with async_session_factory() as session:
        result = await session.execute(
            select(Admin).where(Admin.tg_id == settings.root_admin_tg_id)
        )
        admin = result.scalar_one_or_none()

        if admin is None:
            admin = Admin(
                tg_id=settings.root_admin_tg_id,
                username="root",
                display_name="Root Admin",
                role="superadmin",
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            logger.info(f"Root admin created: tg_id={settings.root_admin_tg_id}")
        elif admin.role != "superadmin":
            admin.role = "superadmin"
            admin.is_active = True
            await session.commit()
            logger.info(f"Root admin role corrected to superadmin: tg_id={settings.root_admin_tg_id}")
        else:
            logger.debug(f"Root admin already exists: tg_id={settings.root_admin_tg_id}")


def is_root_admin(tg_id: int) -> bool:
    """Check if a Telegram user is the root admin."""
    return tg_id == settings.root_admin_tg_id
