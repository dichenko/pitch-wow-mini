"""Artifact generator background worker."""

import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select

from apps.bot.app.config import get_settings
from apps.bot.app.db.session import async_session_factory
from apps.bot.app.services.artifact_delivery import send_artifact_markdown_to_admin
from apps.bot.app.services.artifact_generation import generate_artifacts_from_dialogue
from apps.bot.app.services.history_service import load_user_thread_history
from apps.bot.app.services.telegram_messages import send_message_markdown_or_text
from packages.shared.models.database import ArtifactJob, DialogueHistory
from packages.shared.utils.logging import setup_logging

logger = logging.getLogger(__name__)
settings = get_settings()


def _format_record_time(value: datetime | None) -> str:
    if not value:
        return "N/A"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def format_dialogue_markdown(records: Sequence[DialogueHistory]) -> str:
    """Format stored dialogue turns into simple Markdown for artifact generation."""
    if not records:
        return "_No saved dialogue history found._"

    lines: list[str] = ["# Dialogue History", ""]
    for index, record in enumerate(records, start=1):
        lines.extend(
            [
                f"## Turn {index}",
                "",
                f"**Time:** {_format_record_time(record.created_at)}",
                "",
                f"**Founder:** {record.user_message}",
                "",
                f"**Interviewer:** {record.assistant_response}",
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)


async def claim_next_job() -> ArtifactJob | None:
    """Atomically claim the oldest pending job."""
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(ArtifactJob)
                .where(ArtifactJob.status == "pending")
                .order_by(ArtifactJob.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            job = result.scalar_one_or_none()
            if not job:
                return None

            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.finished_at = None
            job.attempts += 1
            job.error = None

        return job


async def mark_job_success(
    job: ArtifactJob,
    dialogue_md: str,
    markdown: str,
    prompt_version: int,
    provider: str,
    model: str,
) -> None:
    async with async_session_factory() as session:
        stored = await session.get(ArtifactJob, job.id)
        if not stored:
            logger.error("Artifact job disappeared before success save job_id=%s", job.id)
            return

        stored.input_dialogue_md = dialogue_md
        stored.output_markdown = markdown
        stored.artifact_prompt_version = prompt_version
        stored.artifact_model_provider = provider
        stored.artifact_model = model
        stored.status = "success"
        stored.finished_at = datetime.now(timezone.utc)
        stored.error = None
        await session.commit()


async def mark_job_failure(job: ArtifactJob, exc: Exception) -> None:
    error = str(exc)[:4000]
    next_status = (
        "pending"
        if job.attempts < settings.artifact_generator_max_retries
        else "error"
    )

    async with async_session_factory() as session:
        stored = await session.get(ArtifactJob, job.id)
        if not stored:
            logger.error("Artifact job disappeared before failure save job_id=%s", job.id)
            return

        stored.status = next_status
        stored.error = error
        stored.finished_at = datetime.now(timezone.utc)
        await session.commit()

    if next_status == "error":
        await notify_failure(job, error)


async def notify_failure(job: ArtifactJob, error: str) -> None:
    if not settings.admin_telegram_chat_id:
        return

    try:
        from apps.bot.app.bot_instance import bot

        await send_message_markdown_or_text(
            bot,
            int(settings.admin_telegram_chat_id),
            (
                "*Pitch Wow artifact generation failed*\n\n"
                f"*Job:* `{job.id}`\n"
                f"*User TG ID:* `{job.user_tg_id}`\n"
                f"*Trace ID:* `{job.trace_id}`\n"
                f"*Error:* {error[:1000]}"
            ),
        )
    except Exception:
        logger.exception("Failed to send artifact failure notification job_id=%s", job.id)


async def process_job(job: ArtifactJob) -> None:
    logger.info(
        "Processing artifact job job_id=%s trace_id=%s user_tg_id=%s thread_id=%s",
        job.id,
        job.trace_id,
        job.user_tg_id,
        job.thread_id,
    )

    records = await load_user_thread_history(job.user_tg_id, job.thread_id)
    dialogue_md = format_dialogue_markdown(records)
    result = await generate_artifacts_from_dialogue(
        dialogue_md=dialogue_md,
        comment=job.input_comment,
        trace_id=job.trace_id,
    )

    await mark_job_success(
        job=job,
        dialogue_md=dialogue_md,
        markdown=result.markdown,
        prompt_version=result.prompt_version,
        provider=result.provider,
        model=result.model,
    )
    await send_artifact_markdown_to_admin(
        job_id=job.id,
        user_tg_id=job.user_tg_id,
        markdown=result.markdown,
    )

    logger.info("Artifact job completed job_id=%s", job.id)


async def run_worker() -> None:
    setup_logging("DEBUG" if settings.app_env == "dev" else "INFO")
    logger.info(
        "Artifact worker started poll_interval_sec=%s max_retries=%s",
        settings.artifact_worker_poll_interval_sec,
        settings.artifact_generator_max_retries,
    )

    while True:
        job = await claim_next_job()
        if not job:
            await asyncio.sleep(settings.artifact_worker_poll_interval_sec)
            continue

        try:
            await process_job(job)
        except Exception as exc:
            logger.exception("Artifact job failed job_id=%s", job.id)
            await mark_job_failure(job, exc)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

