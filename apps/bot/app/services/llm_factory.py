"""LLM factory — creates LLM instances based on provider settings."""

import logging

from langchain_openai import ChatOpenAI

from apps.bot.app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def create_llm(provider: str, model: str, temperature: float = 0.7):
    """Create an LLM instance for the given provider and model.

    Args:
        provider: "openai", "anthropic", or "mistral".
        model: Model name string.
        temperature: LLM temperature.

    Returns:
        A LangChain chat model instance.

    Raises:
        ValueError: If provider is unknown or required API key is missing.
    """
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        return ChatOpenAI(
            model=model,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_base_url,
            temperature=temperature,
        )

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
        )

    if provider == "mistral":
        if not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is not set")
        from langchain_mistralai import ChatMistralAI

        return ChatMistralAI(
            model=model,
            api_key=settings.mistral_api_key,
            temperature=temperature,
        )

    raise ValueError(f"Unknown LLM provider: {provider}")
