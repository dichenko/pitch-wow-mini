"""Censor management router."""

import os

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from apps.admin.app.db.session import async_session_factory
from apps.admin.app.services.session import (
    get_current_admin,
    get_or_create_csrf_token,
    require_role,
    set_csrf_cookie,
    verify_csrf,
)
from apps.bot.app.services.audit_service import log_audit_event
from packages.shared.models.database import AppSetting, PromptVersion

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/admin/censor", response_class=HTMLResponse)
async def view_censor(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    async with async_session_factory() as session:
        # Get censor enabled setting
        result = await session.execute(
            select(AppSetting).where(AppSetting.key == "censor_enabled")
        )
        setting = result.scalar_one_or_none()
        censor_enabled = setting.value == "true" if setting else False

        # Get active censor prompt
        result = await session.execute(
            select(PromptVersion).where(
                PromptVersion.kind == "censor_prompt", PromptVersion.is_active == True
            )
        )
        active = result.scalar_one_or_none()

        # Get last versions
        result = await session.execute(
            select(PromptVersion)
            .where(PromptVersion.kind == "censor_prompt")
            .order_by(PromptVersion.version_number.desc())
            .limit(4)
        )
        versions = list(result.scalars().all())

    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        "censor/index.html",
        {
            "request": request,
            "admin": admin,
            "censor_enabled": censor_enabled,
            "active": active,
            "versions": versions,
            "csrf_token": csrf_token,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/admin/censor/save")
async def save_censor(
    request: Request,
    content: str = Form(...),
    change_note: str = Form(""),
    censor_enabled: str = Form("false"),
    csrf_token: str = Form(""),
    _csrf=Depends(verify_csrf),
):
    admin = require_role(request, "write")

    enabled_value = "true" if censor_enabled == "true" else "false"

    async with async_session_factory() as session:
        # Update setting
        result = await session.execute(
            select(AppSetting).where(AppSetting.key == "censor_enabled")
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = enabled_value
        else:
            session.add(AppSetting(key="censor_enabled", value=enabled_value))
        await session.commit()

        # Audit log for toggle
        await log_audit_event(
            session=session,
            admin_id=None,
            admin_tg_id=admin["tg_id"],
            action="censor.toggled",
            entity_type="app_setting",
            metadata={"censor_enabled": enabled_value},
        )

    # Save censor prompt version
    from apps.bot.app.services.prompt_service import create_prompt_version

    new_version = await create_prompt_version(
        kind="censor_prompt",
        content=content,
        admin_tg_id=admin["tg_id"],
        change_note=change_note or None,
    )

    # Audit log for prompt creation
    async with async_session_factory() as session:
        await log_audit_event(
            session=session,
            admin_id=None,
            admin_tg_id=admin["tg_id"],
            action="censor_prompt.created",
            entity_type="prompt_version",
            entity_id=new_version.id,
            metadata={"kind": "censor_prompt", "version": new_version.version_number},
        )

    return RedirectResponse(url="/admin/censor", status_code=303)


@router.post("/admin/censor/restore/{version_id}")
async def restore_censor(request: Request, version_id: str, csrf_token: str = Form(""), _csrf=Depends(verify_csrf)):
    admin = require_role(request, "write")

    from apps.bot.app.services.prompt_service import restore_prompt_version

    new_version = await restore_prompt_version(
        kind="censor_prompt",
        source_version_id=version_id,
        admin_tg_id=admin["tg_id"],
    )

    # Audit log
    async with async_session_factory() as session:
        await log_audit_event(
            session=session,
            admin_id=None,
            admin_tg_id=admin["tg_id"],
            action="censor_prompt.restored",
            entity_type="prompt_version",
            entity_id=new_version.id,
            metadata={"kind": "censor_prompt", "version": new_version.version_number},
        )

    return RedirectResponse(url="/admin/censor", status_code=303)
