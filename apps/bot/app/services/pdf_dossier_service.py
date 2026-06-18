"""PDF dossier generation service for admin notifications."""

import asyncio
import json
import logging
import tempfile
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from jsonschema import Draft202012Validator
from langchain_core.messages import HumanMessage, SystemMessage
from openai import AsyncOpenAI

from apps.bot.app.config import BotSettings, get_settings
from apps.bot.app.services.llm_factory import create_llm
from apps.bot.app.services.settings_service import get_llm_model, get_llm_provider
from packages.shared.models.database import DialogueHistory

logger = logging.getLogger(__name__)

PDF_DOSSIER_TIMEOUT_SECONDS = 120
PDF_DOSSIER_POLL_SECONDS = 10


@dataclass(slots=True)
class PdfDossierResult:
    """Result returned by the PDF dossier generation flow."""

    success: bool
    status: str
    metadata: dict[str, Any]
    pdf_path: str | None = None
    pdf_url: str | None = None
    error: str | None = None


class PdfDossierError(Exception):
    """Raised for expected PDF dossier generation failures."""


class PdfDossierService:
    """Generate founder dossier JSON and render it through the Pitch-wow PDF API."""

    def __init__(
        self,
        settings: BotSettings | None = None,
        client: Any | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        artifact_dir: Path | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.sleep = sleep or asyncio.sleep
        self.artifact_dir = artifact_dir or _default_artifact_dir()

    async def generate(
        self,
        *,
        records: Sequence[DialogueHistory],
        external_id: str,
        user_data: dict[str, Any],
        current_user_message: str | None = None,
        comment: str | None = None,
        timeout_seconds: int = PDF_DOSSIER_TIMEOUT_SECONDS,
    ) -> PdfDossierResult:
        """Generate, submit, poll, and download a PDF dossier."""
        if not self.settings.pitchwow_pdf_api_key:
            return _failure("not_configured", "PDF dossier generation is not configured")

        metadata: dict[str, Any] = {
            "status": "started",
            "external_id": external_id,
        }

        try:
            logger.info(
                "PDF dossier generation started trace_or_external_id=%s records=%s",
                external_id,
                len(records),
            )
            prompt = self._load_prompt()
            schema = self._load_schema()
            transcript = serialize_dialogue_for_dossier(
                records,
                user_data=user_data,
                current_user_message=current_user_message,
                comment=comment,
            )
            provider = await get_llm_provider()
            model = await get_llm_model()
            metadata["llm_provider"] = provider
            metadata["llm_model"] = model

            raw_json = await self._generate_json(
                provider=provider,
                model=model,
                prompt=prompt,
                schema=schema,
                transcript=transcript,
            )
            prepared_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            try:
                payload = parse_dossier_payload(raw_json)
                apply_generation_date(payload, prepared_at)
                validate_payload_object(payload, schema)
            except PdfDossierError as exc:
                logger.warning(
                    "PDF dossier validation failed before repair external_id=%s: %s",
                    external_id,
                    exc,
                )
                metadata["repair_attempted"] = True
                repaired_json = await self._repair_json(
                    provider=provider,
                    model=model,
                    prompt=prompt,
                    schema=schema,
                    transcript=transcript,
                    invalid_json=raw_json,
                    validation_error=str(exc),
                )
                payload = parse_dossier_payload(repaired_json)
                apply_generation_date(payload, prepared_at)
                validate_payload_object(payload, schema)

            metadata["payload"] = payload

            job = await self._create_pdf_job(external_id=external_id, payload=payload)
            metadata["job"] = _safe_job_metadata(job)
            logger.info(
                "PDF dossier job created external_id=%s job_id=%s status=%s",
                external_id,
                job.get("job_id"),
                job.get("status"),
            )

            final_job = await self._poll_job(job, timeout_seconds=timeout_seconds)
            metadata["job"] = _safe_job_metadata(final_job)

            if final_job.get("status") != "done":
                error = _job_error_message(final_job)
                return PdfDossierResult(
                    success=False,
                    status=str(final_job.get("status") or "failed"),
                    metadata={**metadata, "status": str(final_job.get("status") or "failed")},
                    error=error,
                )

            pdf_url = str(final_job.get("pdf_url") or "").strip()
            if not pdf_url:
                raise PdfDossierError("PDF job completed without pdf_url")
            pdf_path = await self._download_pdf(pdf_url, external_id=external_id)
            logger.info(
                "PDF dossier downloaded external_id=%s job_id=%s",
                external_id,
                final_job.get("job_id"),
            )
            return PdfDossierResult(
                success=True,
                status="done",
                pdf_path=pdf_path,
                pdf_url=pdf_url,
                metadata={**metadata, "status": "done", "pdf_url": pdf_url},
            )
        except Exception as exc:
            logger.error(
                "PDF dossier generation failed external_id=%s: %s",
                external_id,
                exc,
                exc_info=True,
            )
            return PdfDossierResult(
                success=False,
                status="failed",
                metadata={**metadata, "status": "failed", "error": str(exc)},
                error=str(exc),
            )

    def _load_prompt(self) -> str:
        return (self.artifact_dir / "prompt.md").read_text(encoding="utf-8")

    def _load_schema(self) -> dict[str, Any]:
        return json.loads((self.artifact_dir / "schema.json").read_text(encoding="utf-8"))

    async def _generate_json(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
        schema: dict[str, Any],
        transcript: str,
    ) -> str:
        user_content = (
            "Create the dossier JSON from this dialogue history.\n\n"
            f"{transcript}"
        )
        if provider == "openai":
            return await self._call_openai_structured(
                model=model,
                system_prompt=prompt,
                user_content=user_content,
                schema=schema,
            )
        return await self._call_langchain_json(
            provider=provider,
            model=model,
            system_prompt=(
                f"{prompt}\n\nReturn only JSON matching this schema:\n"
                f"{json.dumps(schema, ensure_ascii=False)}"
            ),
            user_content=user_content,
        )

    async def _repair_json(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
        schema: dict[str, Any],
        transcript: str,
        invalid_json: str,
        validation_error: str,
    ) -> str:
        logger.info("PDF dossier repair attempt model=%s provider=%s", model, provider)
        repair_prompt = (
            f"{prompt}\n\n"
            "Repair the JSON so it validates against the schema. "
            "Return only the corrected JSON."
        )
        repair_input = (
            f"Validation error:\n{validation_error}\n\n"
            f"Schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
            f"Original dialogue history:\n{transcript}\n\n"
            f"Invalid JSON:\n{invalid_json}"
        )
        if provider == "openai":
            return await self._call_openai_structured(
                model=model,
                system_prompt=repair_prompt,
                user_content=repair_input,
                schema=schema,
            )
        return await self._call_langchain_json(
            provider=provider,
            model=model,
            system_prompt=repair_prompt,
            user_content=repair_input,
        )

    async def _call_openai_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_content: str,
        schema: dict[str, Any],
    ) -> str:
        client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
        )
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "vc_founder_dossier",
                    "schema": schema,
                    "strict": True,
                },
            },
        )
        content = response.choices[0].message.content
        if not content:
            raise PdfDossierError("LLM returned empty dossier JSON")
        return content

    async def _call_langchain_json(
        self,
        *,
        provider: str,
        model: str,
        system_prompt: str,
        user_content: str,
    ) -> str:
        llm = create_llm(provider=provider, model=model, temperature=0)
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content),
            ]
        )
        content = getattr(response, "content", "")
        if isinstance(content, list):
            return "\n".join(str(part) for part in content)
        if not str(content).strip():
            raise PdfDossierError("LLM returned empty dossier JSON")
        return str(content)

    async def _create_pdf_job(self, *, external_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.pitchwow_pdf_base_url.rstrip('/')}/v1/reports"
        request_body = {"external_id": external_id, "payload": payload}
        logger.info(
            "Pitch-wow PDF API request method=POST url=%s body=%s",
            url,
            _json_for_log(request_body),
        )
        response = await self._post(
            url,
            headers={
                "Authorization": f"Bearer {self.settings.pitchwow_pdf_api_key}",
                "Content-Type": "application/json",
            },
            json=request_body,
            timeout=30,
        )
        logger.info(
            "Pitch-wow PDF API response method=POST url=%s status_code=%s body=%s",
            url,
            response.status_code,
            _response_body_for_log(response),
        )
        if response.status_code >= 400:
            raise PdfDossierError(_http_error("PDF API job creation failed", response))
        return response.json()

    async def _poll_job(self, job: dict[str, Any], *, timeout_seconds: int) -> dict[str, Any]:
        status_url = str(job.get("status_url") or "").strip()
        if not status_url:
            raise PdfDossierError("PDF API response did not include status_url")
        url = urljoin(f"{self.settings.pitchwow_pdf_base_url.rstrip('/')}/", status_url.lstrip("/"))
        deadline = time.monotonic() + timeout_seconds
        poll_after = _poll_after_seconds(job)

        while True:
            if poll_after > 0:
                await self.sleep(min(poll_after, max(0.0, deadline - time.monotonic())))
            if time.monotonic() >= deadline:
                logger.warning("PDF dossier polling timed out job_id=%s", job.get("job_id"))
                return {**job, "status": "timeout", "error": {"message": "PDF generation timed out"}}

            logger.info("Pitch-wow PDF API request method=GET url=%s", url)
            response = await self._get(
                url,
                headers={"Authorization": f"Bearer {self.settings.pitchwow_pdf_api_key}"},
                timeout=30,
            )
            logger.info(
                "Pitch-wow PDF API response method=GET url=%s status_code=%s body=%s",
                url,
                response.status_code,
                _response_body_for_log(response),
            )
            if response.status_code >= 400:
                raise PdfDossierError(_http_error("PDF API polling failed", response))
            payload = response.json()
            status = str(payload.get("status") or "").lower()
            logger.info(
                "PDF dossier polling result job_id=%s status=%s",
                payload.get("job_id") or job.get("job_id"),
                status,
            )
            if status in {"done", "failed", "expired"}:
                return payload
            poll_after = _poll_after_seconds(payload)

    async def _download_pdf(self, pdf_url: str, *, external_id: str) -> str:
        logger.info("Pitch-wow PDF download request method=GET url=%s", pdf_url)
        response = await self._get(pdf_url, timeout=60)
        logger.info(
            "Pitch-wow PDF download response method=GET url=%s status_code=%s bytes=%s",
            pdf_url,
            response.status_code,
            len(response.content or b""),
        )
        if response.status_code >= 400:
            raise PdfDossierError(_http_error("PDF download failed", response))
        if not response.content:
            raise PdfDossierError("PDF download returned empty content")
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".pdf",
            prefix=f"dossier_{external_id}_",
            delete=False,
        ) as tmp:
            tmp.write(response.content)
            return tmp.name

    async def _post(self, url: str, **kwargs: Any) -> httpx.Response:
        if self.client is not None:
            return await self.client.post(url, **kwargs)
        async with httpx.AsyncClient() as client:
            return await client.post(url, **kwargs)

    async def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        if self.client is not None:
            return await self.client.get(url, **kwargs)
        async with httpx.AsyncClient() as client:
            return await client.get(url, **kwargs)


def serialize_dialogue_for_dossier(
    records: Sequence[DialogueHistory],
    *,
    user_data: dict[str, Any],
    current_user_message: str | None = None,
    comment: str | None = None,
) -> str:
    """Serialize user metadata and full dialogue history for the dossier LLM."""
    lines = [
        "Telegram user:",
        f"- tg_id: {user_data.get('tg_id') or ''}",
        f"- first_name: {user_data.get('first_name') or ''}",
        f"- last_name: {user_data.get('last_name') or ''}",
        f"- username: {user_data.get('username') or ''}",
        f"- language_code: {user_data.get('language_code') or ''}",
        "",
        "Dialogue history:",
    ]
    for record in records:
        created_at = record.created_at.isoformat() if record.created_at else ""
        lines.extend(
            [
                f"[{created_at}] Founder: {record.user_message}",
                f"[{created_at}] Assistant: {record.assistant_response}",
                "",
            ]
        )
    if current_user_message:
        lines.extend(["Current founder message:", current_user_message, ""])
    if comment:
        lines.extend(["send_to_admin comment:", comment, ""])
    return "\n".join(lines)


def validate_dossier_payload(raw_json: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Parse and validate dossier JSON from model output."""
    payload = parse_dossier_payload(raw_json)
    validate_payload_object(payload, schema)
    return payload


def parse_dossier_payload(raw_json: str) -> dict[str, Any]:
    """Parse dossier JSON from model output."""
    try:
        payload = json.loads(_strip_json_fence(raw_json))
    except json.JSONDecodeError as exc:
        raise PdfDossierError(f"Generated dossier is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PdfDossierError("Generated dossier JSON must be an object")
    return payload


def apply_generation_date(payload: dict[str, Any], prepared_at: str) -> None:
    """Set the report generation date on a parsed payload when possible."""
    deck = payload.get("deck")
    if isinstance(deck, dict):
        deck["prepared_at"] = prepared_at


def validate_payload_object(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate a parsed dossier payload."""
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: e.path)
    if errors:
        first = errors[0]
        path = "/" + "/".join(str(part) for part in first.path)
        raise PdfDossierError(f"Generated dossier failed schema validation at {path}: {first.message}")


def _strip_json_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _default_artifact_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "new_task"


def _failure(status: str, error: str) -> PdfDossierResult:
    return PdfDossierResult(
        success=False,
        status=status,
        metadata={"status": status, "error": error},
        error=error,
    )


def _poll_after_seconds(payload: dict[str, Any]) -> float:
    value = payload.get("poll_after_seconds", PDF_DOSSIER_POLL_SECONDS)
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return float(PDF_DOSSIER_POLL_SECONDS)


def _safe_job_metadata(job: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "job_id",
        "status",
        "status_url",
        "poll_after_seconds",
        "created_at",
        "updated_at",
        "pdf_url",
        "expires_at",
        "error",
    }
    return {key: job[key] for key in allowed if key in job}


def _job_error_message(job: dict[str, Any]) -> str:
    error = job.get("error")
    if isinstance(error, dict):
        message = error.get("message") or error.get("code")
        if message:
            return str(message)
    return f"PDF job ended with status {job.get('status') or 'unknown'}"


def _http_error(prefix: str, response: httpx.Response) -> str:
    body = response.text[:1000] if response.text else ""
    return f"{prefix}: HTTP {response.status_code}: {body}"


def _json_for_log(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _response_body_for_log(response: httpx.Response) -> str:
    headers = getattr(response, "headers", {}) or {}
    content_type = headers.get("content-type", "")
    if "application/json" in content_type.lower():
        try:
            return _json_for_log(response.json())
        except ValueError:
            pass
    return response.text
