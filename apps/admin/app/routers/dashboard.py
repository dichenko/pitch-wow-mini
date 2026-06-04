"""Dashboard router."""

import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from apps.admin.app.services.session import get_current_admin, get_or_create_csrf_token, set_csrf_cookie

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "admin": admin, "csrf_token": csrf_token},
    )
    set_csrf_cookie(response, csrf_token)
    return response
