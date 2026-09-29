from abc import ABC, abstractmethod
from typing import Optional


class AudioProvider(ABC):
    """Abstract base class for audio transcription providers.

    Subclasses implement transcribe() to extract speech from audio.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier."""
        ...

    @abstractmethod
    def transcribe(self, audio_path: str) -> dict:
        """Transcribe audio and return structured result.

        Args:
            audio_path: Path to the audio file.

        Returns:
            Dict with transcription data: language, text, segments.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            RuntimeError: If transcription fails.
        """
        ...

    def has_audio(self, video_path: str) -> bool:
        """Check whether a video file contains an audio stream.

        Returns True if an audio stream is detected.
        """
        raise NotImplementedError
