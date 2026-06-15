"""Auth router — token login, logout."""

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from apps.admin.app.config import get_settings
from apps.admin.app.db.session import async_session_factory
from apps.admin.app.services.session import (
    clear_session_cookie,
    get_or_create_csrf_token,
    set_csrf_cookie,
    set_session_cookie,
    verify_csrf,
)
from apps.bot.app.services.audit_service import log_audit_event
from packages.shared.models.database import Admin, AdminLoginToken
from packages.shared.utils.hashing import hash_token

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request, token: str = "") -> Response:
    if not token:
        return templates.TemplateResponse("auth/login_error.html", {"request": request, "error": "No token provided"})

    token_hash = hash_token(token)

    async with async_session_factory() as session:
        result = await session.execute(
            select(AdminLoginToken).where(AdminLoginToken.token_hash == token_hash)
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            logger.warning(f"Login failed: token not found")
            return templates.TemplateResponse(
                "auth/login_error.html", {"request": request, "error": "Invalid or expired login link"}
            )

        # Check expiry
        if token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            logger.warning(f"Login failed: token expired")
            return templates.TemplateResponse(
                "auth/login_error.html", {"request": request, "error": "Login link has expired"}
            )

        # Check if already used
        if token_record.used_at:
            logger.warning(f"Login failed: token already used")
            return templates.TemplateResponse(
                "auth/login_error.html", {"request": request, "error": "Login link has already been used"}
            )

    # Token is valid — show confirmation form (does NOT consume token yet)
    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "token": token, "csrf_token": csrf_token},
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/admin/login")
async def login_action(
    request: Request,
    token: str = Form(...),
    _csrf_ok: None = Depends(verify_csrf),
) -> Response:
    if not token:
        return templates.TemplateResponse("auth/login_error.html", {"request": request, "error": "No token provided"})

    token_hash = hash_token(token)

    async with async_session_factory() as session:
        result = await session.execute(
            select(AdminLoginToken).where(AdminLoginToken.token_hash == token_hash)
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            logger.warning(f"Login failed: token not found")
            return templates.TemplateResponse(
                "auth/login_error.html", {"request": request, "error": "Invalid or expired login link"}
            )

        # Check expiry
        if token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            logger.warning(f"Login failed: token expired")
            return templates.TemplateResponse(
                "auth/login_error.html", {"request": request, "error": "Login link has expired"}
            )

        # Check if already used
        if token_record.used_at:
            logger.warning(f"Login failed: token already used")
            return templates.TemplateResponse(
                "auth/login_error.html", {"request": request, "error": "Login link has already been used"}
            )

        # Mark as used
        token_record.used_at = datetime.now(timezone.utc)
        await session.commit()

        # Look up admin record to get role
        admin_result = await session.execute(
            select(Admin).where(Admin.tg_id == token_record.admin_tg_id)
        )
        admin = admin_result.scalar_one_or_none()

        tg_id = token_record.admin_tg_id
        if tg_id == settings.root_admin_tg_id:
            role = "superadmin"
        elif admin:
            role = admin.role
        else:
            return templates.TemplateResponse(
                "auth/login_error.html", {"request": request, "error": "Admin account not found"}
            )

    # Create session
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    set_session_cookie(response, tg_id=tg_id, role=role)

    # Audit log login success
    async with async_session_factory() as session:
        await log_audit_event(
            session=session,
            admin_id=None,
            admin_tg_id=tg_id,
            action="admin.login_success",
            entity_type="admin_login_token",
        )

    logger.info(f"Admin login success: tg_id={tg_id}, role={role}")
    return response


@router.get("/admin/logout")
async def logout(response: Response) -> RedirectResponse:
    redirect = RedirectResponse(url="/admin/login?token=", status_code=303)
    clear_session_cookie(redirect)
    return redirect
