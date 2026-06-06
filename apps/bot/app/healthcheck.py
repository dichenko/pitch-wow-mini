"""Docker healthcheck for the bot service."""

import os
import urllib.request


def _main_process_is_bot() -> bool:
    try:
        with open("/proc/1/cmdline", "rb") as f:
            cmdline = f.read()
    except OSError:
        return False
    return b"apps.bot.app.main" in cmdline


def main() -> int:
    mode = os.getenv("BOT_MODE", "polling").strip().lower()

    if mode == "polling":
        return 0 if _main_process_is_bot() else 1

    if mode == "webhook":
        try:
            urllib.request.urlopen("http://localhost:8000/health", timeout=5).read()
        except Exception:
            return 1
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
