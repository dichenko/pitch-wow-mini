"""Message history router — paginated dialogue with tool calls."""

import math
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

from apps.admin.app.db.session import async_session_factory
from apps.admin.app.services.session import get_current_admin, get_or_create_csrf_token, set_csrf_cookie
from packages.shared.models.database import DialogueHistory, ToolCallLog

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)

PER_PAGE = 100


@router.get("/admin/history", response_class=HTMLResponse)
async def history_page(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    page = int(request.query_params.get("page", "1"))
    if page < 1:
        page = 1
    offset = (page - 1) * PER_PAGE

    not_start = DialogueHistory.user_message != "[start]"

    async with async_session_factory() as session:
        total = await session.scalar(
            select(func.count()).select_from(DialogueHistory).where(not_start)
        )
        total_pages = max(1, math.ceil(total / PER_PAGE)) if total else 1

        result = await session.execute(
            select(DialogueHistory)
            .where(not_start)
            .order_by(DialogueHistory.created_at.desc())
            .offset(offset)
            .limit(PER_PAGE)
        )
        history = list(result.scalars().all())

        tools_by_trace: dict[str, list[ToolCallLog]] = {}
        if history:
            trace_ids = [h.trace_id for h in history]
            tc_result = await session.execute(
                select(ToolCallLog)
                .where(ToolCallLog.trace_id.in_(trace_ids))
                .order_by(ToolCallLog.created_at)
            )
            for tc in tc_result.scalars().all():
                tools_by_trace.setdefault(tc.trace_id, []).append(tc)

    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        "history/index.html",
        {
            "request": request,
            "admin": admin,
            "csrf_token": csrf_token,
            "history": history,
            "tools_by_trace": tools_by_trace,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response
