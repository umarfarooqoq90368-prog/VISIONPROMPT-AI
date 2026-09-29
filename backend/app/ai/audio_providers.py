import os
from typing import Optional

from app.ai.audio_provider import AudioProvider
from app.core.config import settings


DEFAULT_AUDIO_PROMPT = (
    "Transcribe the speech in this audio. "
    "Return timestamped segments with start time, end time, and text. "
    "Do not invent dialogue that is not present in the audio."
)


class MockAudioProvider(AudioProvider):
    """Mock audio provider for development and testing.

    Returns empty transcription structure. Does NOT fabricate speech.
    Replace with WhisperAudioProvider for real transcription.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    def transcribe(self, audio_path: str) -> dict:
        """Return empty transcription without fabricating speech."""
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        return {
            "language": None,
            "text": "",
            "segments": [],
            "provider": self.provider_name,
        }

    def has_audio(self, video_path: str) -> bool:
        """Use ffmpeg to check if video has an audio stream."""
        import imageio_ffmpeg
        import subprocess

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        try:
            cmd = [ffmpeg, "-hide_banner", "-i", video_path]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            stderr = result.stderr + result.stdout
            return "Audio:" in stderr or "Stream #0:1" in stderr
        except Exception:
            return False


class WhisperAudioProvider(AudioProvider):
    """Real audio transcription provider using Whisper/faster-whisper.

    Loads the model lazily on the first transcribe() call.
    Does not load the model during application startup.
    """

    _instance: Optional["WhisperAudioProvider"] = None
    _model = None
    _processor = None
    _loaded = False

    def __init__(self, model_name: str = "small"):
        super().__init__()
        self._model_name = model_name
        self._device = "cuda" if self._check_cuda() else "cpu"

    @staticmethod
    def _check_cuda() -> bool:
        """Check if CUDA GPU is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _lazy_load_model(self):
        """Load the Whisper model lazily on first use."""
        if self._loaded:
            return

        try:
            import faster_whisper
        except ImportError:
            raise RuntimeError(
                "WhisperAudioProvider requires faster-whisper but it is not installed. "
                "Install faster-whisper to enable real speech transcription."
            )

        try:
            self._processor = faster_whisper.WhisperProcessor.from_pretrained(
                self._model_name
            )
            self._model = faster_whisper.WhisperModel.from_pretrained(
                self._model_name, device=self._device
            )
            self._loaded = True
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Whisper model '{self._model_name}': {str(e)}. "
                "Ensure the model identifier is correct and the model weights "
                "are accessible."
            )

    @property
    def provider_name(self) -> str:
        return f"whisper-{self._model_name}"

    def transcribe(self, audio_path: str) -> dict:
        """Transcribe audio and return structured result with timestamped segments."""
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._lazy_load_model()

        try:
            import numpy as np
            import librosa
        except ImportError:
            raise RuntimeError(
                "WhisperAudioProvider requires librosa for audio loading. "
                "Install librosa to enable real speech transcription."
            )

        try:
            audio_data, sr = librosa.load(audio_path, sr=16000)
            audio_array = np.array(audio_data, dtype=np.float32)
        except Exception as e:
            raise RuntimeError(f"Failed to load audio '{audio_path}': {str(e)}")

        try:
            segments, info = self._model.transcribe(
                audio_array, beam_size=5, best_of=5
            )
            result_segments = []
            full_text = []
            for segment in segments:
                result_segments.append({
                    "start": round(float(segment.start), 4),
                    "end": round(float(segment.end), 4),
                    "text": segment.text.strip(),
                })
                full_text.append(segment.text.strip())

            return {
                "language": info.language if hasattr(info, "language") else None,
                "text": " ".join(full_text),
                "segments": result_segments,
                "provider": self.provider_name,
            }
        except Exception as e:
            raise RuntimeError(
                f"Whisper transcription failed for '{audio_path}': {str(e)}"
            )

    def has_audio(self, video_path: str) -> bool:
        """Use ffmpeg to check if video has an audio stream."""
        import imageio_ffmpeg
        import subprocess

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        try:
            cmd = [ffmpeg, "-hide_banner", "-i", video_path]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            stderr = result.stderr + result.stdout
            return "Audio:" in stderr or "Stream #0:1" in stderr
        except Exception:
            return False


def get_audio_provider(provider_name: str = "mock") -> AudioProvider:
    """Create an audio provider by name.

    Args:
        provider_name: 'mock', 'whisper', or a custom provider name.

    Returns:
        An instance of the requested AudioProvider.
    """
    if provider_name == "mock":
        return MockAudioProvider()
    if provider_name == "whisper":
        return WhisperAudioProvider()
    raise ValueError(f"Unknown audio provider: {provider_name}")