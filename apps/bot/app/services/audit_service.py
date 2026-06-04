"""Audit service — logs admin actions to DB."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.models.database import AdminAuditLog

logger = logging.getLogger(__name__)


async def log_audit_event(
    session: AsyncSession,
    admin_id: uuid.UUID | None,
    admin_tg_id: int | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Write an audit log entry to the database."""
    entry = AdminAuditLog(
        admin_id=admin_id,
        admin_tg_id=admin_tg_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(entry)
    await session.commit()
    logger.info(f"Audit: {action} by tg_id={admin_tg_id}")
