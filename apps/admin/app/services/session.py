"""Session and auth utilities for the admin service."""

import logging
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Form, HTTPException, Request, Response
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from starlette.middleware.base import BaseHTTPMiddleware

from apps.admin.app.config import get_settings
from packages.shared.models.database import Admin

logger = logging.getLogger(__name__)
settings = get_settings()

_serializer = URLSafeTimedSerializer(settings.session_secret or "dev_secret")
_SESSION_KEY = "admin_session"
_SESSION_MAX_AGE = 8 * 3600  # 8 hours

# Routes that do not require authentication
_PUBLIC_ROUTES = {"/admin/login", "/health", "/"}
# Routes exempt from CSRF (login token GET is safe, health check)
_CSRF_EXEMPT_METHODS = {"GET", "HEAD", "OPTIONS"}


def create_session_cookie(tg_id: int, role: str) -> str:
    """Create a signed session cookie value."""
    data = {"tg_id": tg_id, "role": role}
    return _serializer.dumps(data)


def decode_session(cookie_value: str) -> dict | None:
    """Decode and validate a session cookie. Returns session data or None."""
    try:
        data = _serializer.loads(cookie_value, max_age=_SESSION_MAX_AGE)
        return data
    except (BadSignature, SignatureExpired):
        return None


def get_current_admin(request: Request) -> dict | None:
    """Get current admin from session cookie. Returns dict with tg_id, role or None."""
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        return None
    session = decode_session(cookie)
    if not session:
        return None

    # Always treat root admin as superadmin
    if session.get("tg_id") == settings.root_admin_tg_id:
        session["role"] = "superadmin"

    return session


def require_admin(request: Request) -> dict:
    """Get current admin or raise. Returns session dict."""
    admin = get_current_admin(request)
    if not admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return admin


def require_role(request: Request, min_role: str) -> dict:
    """Require at least the specified role. Raises 403 if insufficient."""
    admin = require_admin(request)
    role_hierarchy = {"read": 0, "write": 1, "superadmin": 2}
    admin_level = role_hierarchy.get(admin["role"], -1)
    required_level = role_hierarchy.get(min_role, 99)

    if admin_level < required_level:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return admin


def set_session_cookie(response: Response, tg_id: int, role: str) -> None:
    """Set the session cookie on the response."""
    cookie_value = create_session_cookie(tg_id, role)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=cookie_value,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=_SESSION_MAX_AGE,
    )


def clear_session_cookie(response: Response) -> None:
    """Clear the session cookie."""
    response.delete_cookie(key=settings.session_cookie_name)


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def _get_csrf_from_cookie(request: Request) -> str | None:
    """Get CSRF token stored in a separate cookie."""
    return request.cookies.get("csrf_token")


def get_or_create_csrf_token(request: Request) -> str:
    """Get existing CSRF token from cookie or generate a new one."""
    existing = request.cookies.get("csrf_token")
    if existing:
        return existing
    return generate_csrf_token()


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    """Set a CSRF token cookie and return the token."""
    if token is None:
        token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # JS/HTMX may need to read it
        secure=settings.session_cookie_secure,
        samesite="strict",
        max_age=_SESSION_MAX_AGE,
    )
    return token


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication on admin routes."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for public routes, health, static
        if path in _PUBLIC_ROUTES or not path.startswith("/admin"):
            return await call_next(request)

        # Login route only needs to be public (GET is the token login)
        if path == "/admin/login":
            return await call_next(request)

        # Require session for all other /admin/* routes
        admin = get_current_admin(request)
        if not admin:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/admin/login?token=", status_code=303)

        return await call_next(request)


async def verify_csrf(
    request: Request,
    csrf_token: str = Form(default=""),
) -> None:
    """Dependency: verify CSRF token for POST routes.

    Must be added as a dependency on POST routes that use Form(...) fields.
    Uses Form(...) in signature so FastAPI caches the parsed form body —
    route handlers can then use their own Form(...) fields without re-reading.
    """
    if request.method != "POST":
        return

    csrf_cookie = _get_csrf_from_cookie(request)

    if not csrf_cookie or not csrf_token or csrf_cookie != csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token mismatch")
