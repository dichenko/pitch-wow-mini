"""System prompt management router."""

import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from apps.admin.app.db.session import async_session_factory
from apps.admin.app.services.session import (
    get_current_admin,
    get_or_create_csrf_token,
    require_role,
    set_csrf_cookie,
)
from apps.bot.app.services.audit_service import log_audit_event
from packages.shared.models.database import PromptVersion

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/admin/system-prompt", response_class=HTMLResponse)
async def view_system_prompt(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    async with async_session_factory() as session:
        # Get active version
        result = await session.execute(
            select(PromptVersion).where(
                PromptVersion.kind == "system_prompt", PromptVersion.is_active == True
            )
        )
        active = result.scalar_one_or_none()

        # Get last 3 previous versions
        result = await session.execute(
            select(PromptVersion)
            .where(PromptVersion.kind == "system_prompt")
            .order_by(PromptVersion.version_number.desc())
            .limit(4)
        )
        versions = list(result.scalars().all())

    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        "prompt/edit.html",
        {
            "request": request,
            "admin": admin,
            "kind": "system_prompt",
            "title": "System Prompt",
            "active": active,
            "versions": versions,
            "page_url": "/admin/system-prompt",
            "csrf_token": csrf_token,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/admin/system-prompt/save")
async def save_system_prompt(request: Request, content: str = Form(...), change_note: str = Form("")):
    admin = require_role(request, "write")

    from apps.bot.app.services.prompt_service import create_prompt_version

    new_version = await create_prompt_version(
        kind="system_prompt",
        content=content,
        admin_tg_id=admin["tg_id"],
        change_note=change_note or None,
    )

    # Audit log
    async with async_session_factory() as session:
        await log_audit_event(
            session=session,
            admin_id=None,
            admin_tg_id=admin["tg_id"],
            action="prompt.created",
            entity_type="prompt_version",
            entity_id=new_version.id,
            metadata={"kind": "system_prompt", "version": new_version.version_number},
        )

    return RedirectResponse(url="/admin/system-prompt", status_code=303)


@router.post("/admin/system-prompt/restore/{version_id}")
async def restore_system_prompt(request: Request, version_id: str):
    admin = require_role(request, "write")

    from apps.bot.app.services.prompt_service import restore_prompt_version

    new_version = await restore_prompt_version(
        kind="system_prompt",
        source_version_id=version_id,
        admin_tg_id=admin["tg_id"],
    )

    # Audit log
    async with async_session_factory() as session:
        await log_audit_event(
            session=session,
            admin_id=None,
            admin_tg_id=admin["tg_id"],
            action="prompt.restored",
            entity_type="prompt_version",
            entity_id=new_version.id,
            metadata={"kind": "system_prompt", "version": new_version.version_number},
        )

    return RedirectResponse(url="/admin/system-prompt", status_code=303)
