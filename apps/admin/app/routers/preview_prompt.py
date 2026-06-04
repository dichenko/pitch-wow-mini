"""Preview assembled prompt router."""

import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from apps.admin.app.services.session import get_current_admin

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/admin/preview-prompt", response_class=HTMLResponse)
async def preview_prompt(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    # Assemble prompt using bot service prompt assembler
    try:
        from apps.bot.app.agent.prompt_assembler import assemble_prompt

        assembled, meta = await assemble_prompt()
    except Exception as e:
        assembled = f"Error assembling prompt: {e}"
        meta = {}

    return templates.TemplateResponse(
        "prompt/preview.html",
        {
            "request": request,
            "admin": admin,
            "assembled_prompt": assembled,
            "meta": meta,
        },
    )
