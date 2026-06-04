"""Settings router — LLM provider and model management."""

import logging
import os
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from apps.admin.app.services.session import get_current_admin, require_role, get_or_create_csrf_token, set_csrf_cookie
from apps.bot.app.services.audit_service import log_audit_event
from apps.bot.app.services.settings_service import (
    get_censor_model,
    get_censor_provider,
    get_llm_model,
    get_llm_provider,
    save_llm_settings,
)
from apps.admin.app.db.session import async_session_factory
from packages.shared.models.database import Admin

logger = logging.getLogger(__name__)
router = APIRouter()

templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/admin/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    llm_provider = await get_llm_provider()
    llm_model = await get_llm_model()
    censor_provider = await get_censor_provider()
    censor_model = await get_censor_model()

    response = templates.TemplateResponse(
        "settings/settings.html",
        {
            "request": request,
            "admin": admin,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "censor_provider": censor_provider,
            "censor_model": censor_model,
        },
    )
    set_csrf_cookie(response)
    return response


@router.post("/admin/settings/save", response_class=HTMLResponse)
async def settings_save(request: Request):
    admin = require_role(request, "write")

    llm_provider = (await request.form()).get("llm_provider", "openai")
    llm_model = (await request.form()).get("llm_model", "")
    censor_provider = (await request.form()).get("censor_provider", "openai")
    censor_model = (await request.form()).get("censor_model", "")

    if not llm_model or not censor_model:
        response = templates.TemplateResponse(
            "settings/settings.html",
            {
                "request": request,
                "admin": admin,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "censor_provider": censor_provider,
                "censor_model": censor_model,
                "error": "Model names cannot be empty",
            },
        )
        set_csrf_cookie(response)
        return response

    async with async_session_factory() as session:
        admin_result = await session.execute(
            select(Admin).where(Admin.tg_id == admin["tg_id"])
        )
        admin_record = admin_result.scalar_one_or_none()
        admin_id = admin_record.id if admin_record else None

    await save_llm_settings(
        llm_provider=llm_provider,
        llm_model=llm_model,
        censor_provider=censor_provider,
        censor_model=censor_model,
        admin_id=admin_id,
    )

    async with async_session_factory() as session:
        await log_audit_event(
            session=session,
            admin_id=admin_id,
            admin_tg_id=admin["tg_id"],
            action="settings.updated",
            entity_type="app_settings",
            metadata={
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "censor_provider": censor_provider,
                "censor_model": censor_model,
            },
        )

    response = templates.TemplateResponse(
        "settings/settings.html",
        {
            "request": request,
            "admin": admin,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "censor_provider": censor_provider,
            "censor_model": censor_model,
            "success": "Settings saved successfully",
        },
    )
    set_csrf_cookie(response)
    return response
