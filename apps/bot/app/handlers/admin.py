"""/admin command handler — generates one-time login link."""

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from apps.bot.app.config import get_settings
from apps.bot.app.db.session import async_session_factory
from apps.bot.app.services.audit_service import log_audit_event
from packages.shared.models.database import Admin, AdminLoginToken
from packages.shared.utils.hashing import generate_token, hash_token

logger = logging.getLogger(__name__)
router = Router()
settings = get_settings()


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not message.from_user:
        return

    tg_id = message.from_user.id
    is_root = tg_id == settings.root_admin_tg_id

    async with async_session_factory() as session:
        # Check if user is an admin (or root)
        result = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
        admin_record = result.scalar_one_or_none()

        if not is_root and (admin_record is None or not admin_record.is_active):
            await message.answer("У вас нет доступа к панели администратора.")
            return

        # Generate secure token
        raw_token = generate_token(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.admin_login_token_ttl_minutes
        )

        # Store hash in DB
        token_record = AdminLoginToken(
            admin_tg_id=tg_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(token_record)
        await session.commit()

        # Log audit event
        await log_audit_event(
            session=session,
            admin_id=admin_record.id if admin_record else None,
            admin_tg_id=tg_id,
            action="admin.login_link_created",
            entity_type="admin_login_token",
        )

    # Send login link
    login_url = f"{settings.admin_public_url.rstrip('/')}/admin/login?token={raw_token}"
    await message.answer(
        f"Ваша одноразовая ссылка для входа в панель администратора:\n\n"
        f"{login_url}\n\n"
        f"Ссылка действительна {settings.admin_login_token_ttl_minutes} минут."
    )
    logger.info(f"Admin login link generated for tg_id={tg_id}")
