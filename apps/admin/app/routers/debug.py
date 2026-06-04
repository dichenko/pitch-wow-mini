"""Debug page router."""

import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from apps.admin.app.config import get_settings
from apps.admin.app.db.session import async_session_factory
from apps.admin.app.services.session import get_current_admin, get_or_create_csrf_token, set_csrf_cookie
from packages.shared.models.database import (
    AdminNotification,
    AppSetting,
    CensorRun,
    PromptVersion,
)

debug_settings = get_settings()
router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/admin/debug", response_class=HTMLResponse)
async def debug_page(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    debug_data = {
        "app_env": debug_settings.app_env,
        "project_slug": debug_settings.project_slug,
        "text_llm_provider": debug_settings.text_llm_provider,
        "openai_text_model": debug_settings.openai_text_model,
        "bot_mode": debug_settings.bot_mode,
        "langsmith_tracing": debug_settings.langsmith_tracing,
        "langsmith_project": debug_settings.langsmith_project,
        "langsmith_endpoint": debug_settings.langsmith_endpoint,
        "langsmith_workspace_configured": bool(debug_settings.langsmith_workspace_id),
        "admin_telegram_chat_configured": bool(debug_settings.admin_telegram_chat_id),
    }

    async with async_session_factory() as session:
        # Active prompt versions
        for kind in ["system_prompt", "tools_instruction", "censor_prompt"]:
            result = await session.execute(
                select(PromptVersion.version_number).where(
                    PromptVersion.kind == kind, PromptVersion.is_active == True
                )
            )
            debug_data[f"{kind}_version"] = result.scalar_one_or_none() or "N/A"

        # Censor enabled
        result = await session.execute(
            select(AppSetting.value).where(AppSetting.key == "censor_enabled")
        )
        censor_val = result.scalar_one_or_none()
        debug_data["censor_enabled"] = censor_val == "true" if censor_val else False

        # Last notification
        result = await session.execute(
            select(AdminNotification.created_at).order_by(
                AdminNotification.created_at.desc()
            ).limit(1)
        )
        debug_data["last_notification_at"] = result.scalar_one_or_none()

        # Last censor run
        result = await session.execute(
            select(CensorRun).order_by(CensorRun.created_at.desc()).limit(1)
        )
        last_censor = result.scalar_one_or_none()
        if last_censor:
            debug_data["last_censor_run_at"] = last_censor.created_at
            debug_data["last_censor_run_status"] = last_censor.status
        else:
            debug_data["last_censor_run_at"] = None
            debug_data["last_censor_run_status"] = None

        # DB connection
        try:
            await session.execute(select(func.now()))
            debug_data["db_status"] = "OK"
        except Exception as e:
            debug_data["db_status"] = f"Error: {e}"

    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        "debug/index.html",
        {"request": request, "admin": admin, "debug": debug_data, "csrf_token": csrf_token},
    )
    set_csrf_cookie(response, csrf_token)
    return response
