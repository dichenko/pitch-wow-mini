"""Administrators management router."""

import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from apps.admin.app.config import get_settings
from apps.admin.app.db.session import async_session_factory
from apps.admin.app.services.session import (
    get_current_admin,
    get_or_create_csrf_token,
    require_role,
    set_csrf_cookie,
)
from apps.bot.app.services.audit_service import log_audit_event
from packages.shared.models.database import Admin

admin_settings = get_settings()
router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/admin/admins", response_class=HTMLResponse)
async def view_admins(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    async with async_session_factory() as session:
        result = await session.execute(
            select(Admin).order_by(Admin.created_at.desc())
        )
        admins_list = list(result.scalars().all())

    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        "admins/index.html",
        {
            "request": request,
            "admin": admin,
            "admins_list": admins_list,
            "root_tg_id": admin_settings.root_admin_tg_id,
            "csrf_token": csrf_token,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/admin/admins/add")
async def add_admin(
    request: Request,
    tg_id: int = Form(...),
    username: str = Form(""),
    display_name: str = Form(""),
    role: str = Form("read"),
):
    admin = require_role(request, "superadmin")

    async with async_session_factory() as session:
        # Check if already exists
        result = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
        existing = result.scalar_one_or_none()

        if existing:
            existing.role = role
            existing.is_active = True
            if username:
                existing.username = username
            if display_name:
                existing.display_name = display_name
        else:
            new_admin = Admin(
                tg_id=tg_id,
                username=username or None,
                display_name=display_name or None,
                role=role,
                is_active=True,
            )
            session.add(new_admin)
        await session.commit()

        # Audit log
        await log_audit_event(
            session=session,
            admin_id=None,
            admin_tg_id=admin["tg_id"],
            action="admin.created",
            entity_type="admin",
            metadata={"target_tg_id": tg_id, "role": role},
        )

    return RedirectResponse(url="/admin/admins", status_code=303)


@router.post("/admin/admins/deactivate/{admin_id}")
async def deactivate_admin(request: Request, admin_id: str):
    admin = require_role(request, "superadmin")

    async with async_session_factory() as session:
        result = await session.execute(select(Admin).where(Admin.id == admin_id))
        target = result.scalar_one_or_none()
        if target:
            # Prevent deactivating root admin
            if target.tg_id == admin_settings.root_admin_tg_id:
                return RedirectResponse(url="/admin/admins", status_code=303)
            target.is_active = False
            await session.commit()

            # Audit log
            await log_audit_event(
                session=session,
                admin_id=None,
                admin_tg_id=admin["tg_id"],
                action="admin.deactivated",
                entity_type="admin",
                entity_id=target.id,
                metadata={"target_tg_id": target.tg_id},
            )

    return RedirectResponse(url="/admin/admins", status_code=303)


@router.post("/admin/admins/change-role/{admin_id}")
async def change_role(request: Request, admin_id: str, role: str = Form(...)):
    admin = require_role(request, "superadmin")

    async with async_session_factory() as session:
        result = await session.execute(select(Admin).where(Admin.id == admin_id))
        target = result.scalar_one_or_none()
        if target:
            old_role = target.role
            target.role = role
            await session.commit()

            # Audit log
            await log_audit_event(
                session=session,
                admin_id=None,
                admin_tg_id=admin["tg_id"],
                action="admin.role_changed",
                entity_type="admin",
                entity_id=target.id,
                metadata={"target_tg_id": target.tg_id, "old_role": old_role, "new_role": role},
            )

    return RedirectResponse(url="/admin/admins", status_code=303)
