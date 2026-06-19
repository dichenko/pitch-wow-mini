"""Admin web service entry point."""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from apps.admin.app.config import get_settings
from apps.admin.app.routers import (
    admins,
    artifact_generator_prompt,
    auth,
    censor,
    dashboard,
    debug,
    history,
    preview_prompt,
    settings as settings_router,
    stats,
    system_prompt,
    tools_instruction,
    welcome,
)
from apps.admin.app.services.session import AuthMiddleware
from packages.shared.utils.logging import setup_logging

logger = logging.getLogger(__name__)
settings = get_settings()

setup_logging("DEBUG" if settings.app_env == "dev" else "INFO")

app = FastAPI(title="AI Assistant Admin", version="0.1.0")

# Auth + CSRF middleware
app.add_middleware(AuthMiddleware)

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Include routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(system_prompt.router)
app.include_router(artifact_generator_prompt.router)
app.include_router(tools_instruction.router)
app.include_router(welcome.router)
app.include_router(censor.router)
app.include_router(admins.router)
app.include_router(debug.router)
app.include_router(preview_prompt.router)
app.include_router(settings_router.router)
app.include_router(stats.router)
app.include_router(history.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "OK", "service": "admin"}


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/admin/dashboard")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
