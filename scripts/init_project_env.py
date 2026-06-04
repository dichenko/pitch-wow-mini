"""Init script for generating project environment configuration.

Usage:
    python scripts/init_project_env.py

Responsibilities:
- Copy .env.example to .env if .env does not exist
- Generate PROJECT_SLUG if missing
- Generate random free BOT_HOST_PORT
- Generate random free ADMIN_HOST_PORT
- Generate SESSION_SECRET
- Print Caddyfile snippet for the new project
"""

import os
import secrets
import shutil
import socket
import sys
from pathlib import Path


def find_free_port(start: int = 18000, end: int = 19000) -> int:
    """Find a random free port in the given range."""
    import random

    ports = list(range(start, end))
    random.shuffle(ports)
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}-{end}")


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    env_example = project_root / ".env.example"
    env_file = project_root / ".env"

    if not env_example.exists():
        print(f"Error: {env_example} not found")
        sys.exit(1)

    # Copy .env.example to .env if not exists
    if not env_file.exists():
        shutil.copy2(env_example, env_file)
        print(f"Created .env from .env.example")
    else:
        print(f".env already exists, skipping copy")

    # Read .env
    env_vars = {}
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    changes = []

    # Generate PROJECT_SLUG if missing or default
    if not env_vars.get("PROJECT_SLUG") or env_vars["PROJECT_SLUG"] == "ai-assistant-template":
        slug = f"assistant-{secrets.token_hex(3)}"
        env_vars["PROJECT_SLUG"] = slug
        env_vars["COMPOSE_PROJECT_NAME"] = slug
        changes.append(f"PROJECT_SLUG={slug}")
        changes.append(f"COMPOSE_PROJECT_NAME={slug}")

    # Generate BOT_HOST_PORT if default
    if not env_vars.get("BOT_HOST_PORT") or env_vars["BOT_HOST_PORT"] == "18001":
        port = find_free_port(18000, 18500)
        env_vars["BOT_HOST_PORT"] = str(port)
        changes.append(f"BOT_HOST_PORT={port}")

    # Generate ADMIN_HOST_PORT if default
    if not env_vars.get("ADMIN_HOST_PORT") or env_vars["ADMIN_HOST_PORT"] == "18002":
        port = find_free_port(18500, 19000)
        env_vars["ADMIN_HOST_PORT"] = str(port)
        changes.append(f"ADMIN_HOST_PORT={port}")

    # Generate SESSION_SECRET if missing
    if not env_vars.get("SESSION_SECRET"):
        secret = secrets.token_urlsafe(48)
        env_vars["SESSION_SECRET"] = secret
        changes.append(f"SESSION_SECRET={secret}")

    # Write back changes
    if changes:
        with open(env_file, "w", encoding="utf-8") as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        print(f"\nUpdated .env:")
        for change in changes:
            print(f"  {change}")

    # Print Caddyfile snippet
    bot_port = env_vars.get("BOT_HOST_PORT", "18001")
    admin_port = env_vars.get("ADMIN_HOST_PORT", "18002")
    slug = env_vars.get("PROJECT_SLUG", "assistant")

    print(f"\n--- Caddyfile snippet for {slug} ---")
    print(f"bot.{slug}.example.com {{")
    print(f"    reverse_proxy 127.0.0.1:{bot_port}")
    print(f"}}")
    print()
    print(f"admin.{slug}.example.com {{")
    print(f"    reverse_proxy 127.0.0.1:{admin_port}")
    print(f"}}")
    print(f"--- End Caddyfile snippet ---")

    print(f"\nDone! Next steps:")
    print(f"  1. Edit .env and fill in TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ROOT_ADMIN_TG_ID, etc.")
    print(f"  2. cd infra && docker compose up -d --build")
    print(f"  3. Configure Caddy with the snippet above")


if __name__ == "__main__":
    main()
