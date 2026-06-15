"""Statistics router — user and message analytics."""

import json
import os
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Date, cast, func, select

from apps.admin.app.db.session import async_session_factory
from apps.admin.app.services.session import get_current_admin, get_or_create_csrf_token, set_csrf_cookie
from packages.shared.models.database import DialogueHistory

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)

DAYS = 30


def _date_range() -> tuple[date, date, list[str]]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=DAYS - 1)
    labels = [(start + timedelta(days=i)).isoformat() for i in range(DAYS)]
    return start, today, labels


def _fill(labels: list[str], rows) -> list[int]:
    table = {str(r[0]): r[1] for r in rows}
    return [table.get(label, 0) for label in labels]


@router.get("/admin/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    start_date, end_date, labels = _date_range()

    day_col = cast(DialogueHistory.created_at, Date)
    not_start = DialogueHistory.user_message != "[start]"

    async with async_session_factory() as session:
        # 1. New users per day — first message date per user
        first_msg_subq = (
            select(
                DialogueHistory.user_tg_id,
                cast(func.min(DialogueHistory.created_at), Date).label("first_day"),
            )
            .where(not_start)
            .group_by(DialogueHistory.user_tg_id)
            .subquery()
        )
        q1 = (
            select(first_msg_subq.c.first_day, func.count().label("cnt"))
            .where(first_msg_subq.c.first_day.between(start_date, end_date))
            .group_by(first_msg_subq.c.first_day)
            .order_by(first_msg_subq.c.first_day)
        )
        new_users_rows = (await session.execute(q1)).all()
        new_users = _fill(labels, new_users_rows)

        # 2. Messages per day
        q2 = (
            select(day_col, func.count().label("cnt"))
            .where(not_start, day_col.between(start_date, end_date))
            .group_by(day_col)
            .order_by(day_col)
        )
        msg_rows = (await session.execute(q2)).all()
        messages = _fill(labels, msg_rows)

        # 3. Active users per day
        q3 = (
            select(day_col, func.count(func.distinct(DialogueHistory.user_tg_id)).label("cnt"))
            .where(not_start, day_col.between(start_date, end_date))
            .group_by(day_col)
            .order_by(day_col)
        )
        active_rows = (await session.execute(q3)).all()
        active_users = _fill(labels, active_rows)

    # 4. Average messages per user per day
    avg_per_user: list[float] = []
    for i in range(DAYS):
        m = messages[i]
        a = active_users[i]
        avg_per_user.append(round(m / a, 1) if a > 0 else 0.0)

    total_new = sum(new_users)
    total_msgs = sum(messages)

    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "admin": admin,
            "csrf_token": csrf_token,
            "labels": json.dumps(labels),
            "new_users": json.dumps(new_users),
            "messages": json.dumps(messages),
            "active_users": json.dumps(active_users),
            "avg_per_user": json.dumps(avg_per_user),
            "total_new": total_new,
            "total_msgs": total_msgs,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response
