"""Artifact generation service."""

from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select

from apps.bot.app.config import get_settings
from apps.bot.app.db.session import async_session_factory
from apps.bot.app.services.llm_factory import create_llm
from apps.bot.app.services.seed_service import DEFAULT_ARTIFACT_GENERATOR_PROMPT
from packages.shared.models.database import PromptVersion

settings = get_settings()


@dataclass
class ArtifactGenerationResult:
    markdown: str
    prompt_version: int
    provider: str
    model: str


async def get_active_artifact_prompt() -> tuple[str, int]:
    """Return active artifact generator prompt content and version."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(PromptVersion)
            .where(
                PromptVersion.kind == "artifact_generator_prompt",
                PromptVersion.is_active == True,
            )
            .order_by(PromptVersion.version_number.desc())
            .limit(1)
        )
        prompt = result.scalar_one_or_none()

    if not prompt:
        return DEFAULT_ARTIFACT_GENERATOR_PROMPT, 0

    return prompt.content, prompt.version_number


def get_artifact_model_settings() -> tuple[str, str]:
    """Resolve provider and model for artifact generation."""
    provider = settings.text_llm_provider
    if provider == "openai":
        return provider, settings.openai_text_model
    if provider == "anthropic":
        return provider, settings.anthropic_model
    if provider == "mistral":
        return provider, settings.mistral_model
    raise ValueError(f"Unknown LLM provider: {provider}")


async def generate_artifacts_from_dialogue(
    dialogue_md: str,
    comment: str | None,
    trace_id: str,
) -> ArtifactGenerationResult:
    """Generate the final artifact Markdown package from dialogue Markdown."""
    artifact_prompt, prompt_version = await get_active_artifact_prompt()
    provider, model = get_artifact_model_settings()
    llm = create_llm(
        provider=provider,
        model=model,
        temperature=settings.artifact_generator_temperature,
    )

    user_payload = (
        "# Founder Interview Dialogue\n\n"
        f"{dialogue_md}\n\n"
        "# send_to_admin Comment\n\n"
        f"{comment or ''}\n\n"
        f"# Trace ID\n\n{trace_id}"
    )

    response = await llm.ainvoke(
        [
            SystemMessage(content=artifact_prompt),
            HumanMessage(content=user_payload),
        ]
    )
    content = response.content
    if isinstance(content, list):
        markdown = "\n".join(str(part) for part in content)
    else:
        markdown = str(content)

    return ArtifactGenerationResult(
        markdown=markdown,
        prompt_version=prompt_version,
        provider=provider,
        model=model,
    )

