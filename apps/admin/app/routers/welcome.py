"""Localized welcome message management router."""

import os

from fastapi import APIRouter, Depends, Form, HTTPException, Request
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
from packages.shared.models.database import PromptVersion
from packages.shared.utils.languages import LANGUAGE_LABELS, normalize_preferred_language
from packages.shared.utils.welcome_messages import DEFAULT_WELCOME_MESSAGES, WELCOME_PROMPT_KINDS

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/admin/welcome", response_class=HTMLResponse)
async def view_welcome(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    welcome_languages = []
    async with async_session_factory() as session:
        for language, kind in WELCOME_PROMPT_KINDS.items():
            result = await session.execute(
                select(PromptVersion).where(
                    PromptVersion.kind == kind,
                    PromptVersion.is_active == True,
                )
            )
            active = result.scalar_one_or_none()

            result = await session.execute(
                select(PromptVersion)
                .where(PromptVersion.kind == kind)
                .order_by(PromptVersion.version_number.desc())
                .limit(4)
            )
            versions = list(result.scalars().all())

            welcome_languages.append(
                {
                    "code": language,
                    "label": LANGUAGE_LABELS[language],
                    "kind": kind,
                    "active": active,
                    "versions": versions,
                    "default_content": DEFAULT_WELCOME_MESSAGES[language],
                }
            )

    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        "prompt/welcome_localized.html",
        {
            "request": request,
            "admin": admin,
            "title": "Welcome Messages",
            "welcome_languages": welcome_languages,
            "page_url": "/admin/welcome",
            "csrf_token": csrf_token,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/admin/welcome/save")
async def save_welcome(
    request: Request,
    language: str = Form(...),
    content: str = Form(...),
    change_note: str = Form(""),
    _csrf=Depends(verify_csrf),
):
    admin = require_role(request, "write")
    normalized = normalize_preferred_language(language)
    if normalized is None:
        raise HTTPException(status_code=400, detail="Unsupported language")

    from apps.bot.app.services.prompt_service import create_prompt_version

    kind = WELCOME_PROMPT_KINDS[normalized]
    new_version = await create_prompt_version(
        kind=kind,
        content=content,
        admin_tg_id=admin["tg_id"],
        change_note=change_note or None,
    )

    async with async_session_factory() as session:
        await log_audit_event(
            session=session,
            admin_id=None,
            admin_tg_id=admin["tg_id"],
            action="prompt.created",
            entity_type="prompt_version",
            entity_id=new_version.id,
            metadata={
                "kind": kind,
                "language": normalized,
                "version": new_version.version_number,
            },
        )

    return RedirectResponse(url="/admin/welcome", status_code=303)


@router.post("/admin/welcome/restore/{language}/{version_id}")
async def restore_welcome(
    request: Request,
    language: str,
    version_id: str,
    csrf_token: str = Form(""),
    _csrf=Depends(verify_csrf),
):
    admin = require_role(request, "write")
    normalized = normalize_preferred_language(language)
    if normalized is None:
        raise HTTPException(status_code=400, detail="Unsupported language")

    from apps.bot.app.services.prompt_service import restore_prompt_version

    kind = WELCOME_PROMPT_KINDS[normalized]
    new_version = await restore_prompt_version(
        kind=kind,
        source_version_id=version_id,
        admin_tg_id=admin["tg_id"],
    )

    async with async_session_factory() as session:
        await log_audit_event(
            session=session,
            admin_id=None,
            admin_tg_id=admin["tg_id"],
            action="prompt.restored",
            entity_type="prompt_version",
            entity_id=new_version.id,
            metadata={
                "kind": kind,
                "language": normalized,
                "version": new_version.version_number,
            },
        )

    return RedirectResponse(url="/admin/welcome", status_code=303)
