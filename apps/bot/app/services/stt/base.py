"""STT provider base interface."""

from abc import ABC, abstractmethod


class BaseSttProvider(ABC):
    """Abstract base class for speech-to-text providers."""

    @abstractmethod
    async def transcribe(self, audio_path: str) -> str | None:
        """Transcribe audio file to text.

        Args:
            audio_path: Path to the normalized audio file.

        Returns:
            Transcribed text or None if transcription failed.
        """
        ...
