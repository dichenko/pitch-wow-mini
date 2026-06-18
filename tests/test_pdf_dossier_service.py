import json
from pathlib import Path

import pytest

from apps.bot.app.config import BotSettings
from apps.bot.app.services import pdf_dossier_service as module
from apps.bot.app.services.pdf_dossier_service import (
    PdfDossierService,
    to_pitchwow_pdf_payload,
    validate_dossier_payload,
)


class FakeResponse:
    def __init__(self, status_code=200, *, json_data=None, content=b"%PDF", text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.content = content
        self.text = text

    def json(self):
        return self._json_data


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.posts = []
        self.gets = []

    async def post(self, url, **kwargs):
        self.posts.append({"url": url, **kwargs})
        return self.responses.pop(0)

    async def get(self, url, **kwargs):
        self.gets.append({"url": url, **kwargs})
        return self.responses.pop(0)


async def no_sleep(_seconds):
    return None


def _schema():
    return json.loads(Path("new_task/schema.json").read_text(encoding="utf-8"))


def _sample_json():
    return Path("new_task/sample.json").read_text(encoding="utf-8")


def test_validate_dossier_payload_accepts_sample():
    payload = validate_dossier_payload(_sample_json(), _schema())

    assert payload["schema_version"] == "1.0"
    assert payload["template_id"] == "vc_founder_dossier_v1"


def test_to_pitchwow_pdf_payload_maps_to_current_api_template():
    rich_payload = validate_dossier_payload(_sample_json(), _schema())

    api_payload = to_pitchwow_pdf_payload(rich_payload)

    assert set(api_payload) == {
        "schema_version",
        "startup",
        "founder",
        "summary",
        "traction",
        "market",
        "risks",
    }
    assert set(api_payload["startup"]) == {"name", "tagline", "stage"}
    assert set(api_payload["founder"]) == {"name", "role", "background"}
    assert set(api_payload["market"]) == {"segment", "size", "insight"}
    assert api_payload["traction"]
    assert api_payload["risks"]


@pytest.mark.asyncio
async def test_generate_repairs_invalid_json_and_downloads_pdf(monkeypatch):
    async def fake_provider():
        return "openai"

    async def fake_model():
        return "gpt-5.4-mini"

    async def fake_generate_json(self, **_kwargs):
        return '{"schema_version": "1.0"}'

    async def fake_repair_json(self, **_kwargs):
        return _sample_json()

    monkeypatch.setattr(module, "get_llm_provider", fake_provider)
    monkeypatch.setattr(module, "get_llm_model", fake_model)
    monkeypatch.setattr(PdfDossierService, "_generate_json", fake_generate_json)
    monkeypatch.setattr(PdfDossierService, "_repair_json", fake_repair_json)

    client = FakeHttpClient(
        [
            FakeResponse(
                json_data={
                    "job_id": "job_1",
                    "status": "queued",
                    "status_url": "/v1/reports/job_1",
                    "poll_after_seconds": 0,
                }
            ),
            FakeResponse(
                json_data={
                    "job_id": "job_1",
                    "status": "done",
                    "pdf_url": "https://api-pitchwow-pdf.liven8n.site/r/report.pdf",
                }
            ),
            FakeResponse(content=b"%PDF bytes"),
        ]
    )
    settings = BotSettings(
        pitchwow_pdf_api_key="secret",
        pitchwow_pdf_base_url="https://api-pitchwow-pdf.liven8n.site",
    )
    service = PdfDossierService(settings=settings, client=client, sleep=no_sleep)

    result = await service.generate(
        records=[],
        external_id="trace-1",
        user_data={"tg_id": 1},
        timeout_seconds=5,
    )

    assert result.success is True
    assert result.status == "done"
    assert result.pdf_url == "https://api-pitchwow-pdf.liven8n.site/r/report.pdf"
    assert Path(result.pdf_path).read_bytes() == b"%PDF bytes"
    assert result.metadata["repair_attempted"] is True
    assert client.posts[0]["json"]["external_id"] == "trace-1"
    assert set(client.posts[0]["json"]["payload"]) == {
        "schema_version",
        "startup",
        "founder",
        "summary",
        "traction",
        "market",
        "risks",
    }
    assert client.posts[0]["headers"]["Authorization"] == "Bearer secret"
    Path(result.pdf_path).unlink()


@pytest.mark.asyncio
async def test_generate_returns_failed_status_from_pdf_api(monkeypatch):
    async def fake_provider():
        return "openai"

    async def fake_model():
        return "gpt-5.4-mini"

    async def fake_generate_json(self, **_kwargs):
        return _sample_json()

    monkeypatch.setattr(module, "get_llm_provider", fake_provider)
    monkeypatch.setattr(module, "get_llm_model", fake_model)
    monkeypatch.setattr(PdfDossierService, "_generate_json", fake_generate_json)

    client = FakeHttpClient(
        [
            FakeResponse(
                json_data={
                    "job_id": "job_2",
                    "status": "queued",
                    "status_url": "/v1/reports/job_2",
                    "poll_after_seconds": 0,
                }
            ),
            FakeResponse(
                json_data={
                    "job_id": "job_2",
                    "status": "failed",
                    "error": {"message": "PDF rendering failed"},
                }
            ),
        ]
    )
    settings = BotSettings(pitchwow_pdf_api_key="secret")
    service = PdfDossierService(settings=settings, client=client, sleep=no_sleep)

    result = await service.generate(
        records=[],
        external_id="trace-2",
        user_data={"tg_id": 1},
        timeout_seconds=5,
    )

    assert result.success is False
    assert result.status == "failed"
    assert result.error == "PDF rendering failed"
    assert result.metadata["job"]["job_id"] == "job_2"


@pytest.mark.asyncio
async def test_poll_job_times_out_without_fetching_status():
    settings = BotSettings(pitchwow_pdf_api_key="secret")
    service = PdfDossierService(
        settings=settings,
        client=FakeHttpClient([]),
        sleep=no_sleep,
    )

    result = await service._poll_job(
        {
            "job_id": "job_timeout",
            "status": "queued",
            "status_url": "/v1/reports/job_timeout",
            "poll_after_seconds": 0,
        },
        timeout_seconds=0,
    )

    assert result["status"] == "timeout"
