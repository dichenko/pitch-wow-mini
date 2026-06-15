"""Statistics router — user and message analytics."""

import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from apps.admin.app.db.session import async_session_factory
from apps.admin.app.services.session import get_current_admin, get_or_create_csrf_token, set_csrf_cookie

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)

DAYS = 30


def _date_range() -> tuple[str, str, list[str]]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=DAYS - 1)
    labels: list[str] = []
    for i in range(DAYS):
        d = start + timedelta(days=i)
        labels.append(d.isoformat())
    return start.isoformat(), today.isoformat(), labels


def _fill(labels: list[str], rows) -> list[int | float]:
    """Fill missing days with zeros. `rows` is a list of (day_str, value)."""
    table = {str(r[0]): r[1] for r in rows}
    return [table.get(label, 0) for label in labels]


@router.get("/admin/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login?token=", status_code=303)

    start_str, end_str, labels = _date_range()

    async with async_session_factory() as session:
        # 1. New users per day (first message date, excluding [start])
        new_users_rows = await session.execute(
            text("""
                SELECT first_day::date as day, COUNT(*) as cnt
                FROM (
                    SELECT user_tg_id, MIN(created_at)::date as first_day
                    FROM dialogue_history
                    WHERE user_message != '[start]'
                    GROUP BY user_tg_id
                ) sub
                WHERE first_day BETWEEN :start AND :end
                GROUP BY first_day
                ORDER BY first_day
            """),
            {"start": start_str, "end": end_str},
        )
        new_users = _fill(labels, new_users_rows.fetchall())

        # 2. Messages per day
        msg_rows = await session.execute(
            text("""
                SELECT created_at::date as day, COUNT(*) as cnt
                FROM dialogue_history
                WHERE user_message != '[start]'
                  AND created_at::date BETWEEN :start AND :end
                GROUP BY created_at::date
                ORDER BY day
            """),
            {"start": start_str, "end": end_str},
        )
        messages = _fill(labels, msg_rows.fetchall())

        # 3. Active users per day
        active_rows = await session.execute(
            text("""
                SELECT created_at::date as day, COUNT(DISTINCT user_tg_id) as cnt
                FROM dialogue_history
                WHERE user_message != '[start]'
                  AND created_at::date BETWEEN :start AND :end
                GROUP BY created_at::date
                ORDER BY day
            """),
            {"start": start_str, "end": end_str},
        )
        active_users = _fill(labels, active_rows.fetchall())

        # 4. Average messages per user per day
        avg_per_user: list[float] = []
        for i in range(DAYS):
            m = messages[i]
            a = active_users[i]
            avg = round(m / a, 1) if a > 0 else 0.0
            avg_per_user.append(avg)

        # Totals
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
