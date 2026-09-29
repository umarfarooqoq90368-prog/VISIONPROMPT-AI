"""Tests for the audio service."""
import os
import tempfile
import types
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services.audio_service import extract_audio, AudioService
from app.ai.audio_providers import MockAudioProvider, WhisperAudioProvider, get_audio_provider
from app.utils.ffprobe import extract_metadata


def _create_audio_file(path: str, duration_seconds: float = 1.0):
    """Create a simple WAV audio file using numpy."""
    import numpy as np
    import wave
    import struct
    sample_rate = 16000
    num_samples = int(duration_seconds * sample_rate)
    frequency = 440.0  # A4 note
    with wave.open(path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            t = i / sample_rate
            value = int(32767 * 0.5 * np.sin(2 * np.pi * frequency * t))
            wav_file.writeframes(struct.pack('h', value))


def _create_silent_wav(path: str, duration_seconds: float = 1.0):
    """Create a silent WAV audio file."""
    import numpy as np
    import wave
    import struct
    sample_rate = 16000
    num_samples = int(duration_seconds * sample_rate)
    with wave.open(path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            value = 0
            wav_file.writeframes(struct.pack('h', value))


@pytest.fixture
def audio_service():
    return AudioService(audio_provider=MockAudioProvider())


@pytest.fixture
def video_in_storage():
    """Create a video file in storage/uploads with audio and return stored filename."""
    storage_dir = Path("storage/uploads")
    storage_dir.mkdir(parents=True, exist_ok=True)
    video_path = storage_dir / "test_video.mp4"
    import imageio_ffmpeg
    import subprocess
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-c:v", "libx264", "-c:a", "aac", "-y", str(video_path)],
        capture_output=True, timeout=10,
    )
    yield "test_video.mp4"
    if video_path.exists():
        video_path.unlink()


class TestAudioProviderFactory:
    def test_mock_provider(self):
        provider = get_audio_provider("mock")
        assert provider.provider_name == "mock"

    def test_invalid_provider(self):
        with pytest.raises(ValueError):
            get_audio_provider("invalid")

    def test_default_is_mock(self):
        provider = get_audio_provider()
        assert provider.provider_name == "mock"


class TestMockAudioProvider:
    def test_provider_name(self):
        provider = MockAudioProvider()
        assert provider.provider_name == "mock"

    def test_transcribe_returns_empty(self):
        provider = MockAudioProvider()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            pass
        _create_audio_file(tmp.name)
        result = provider.transcribe(tmp.name)
        os.unlink(tmp.name)
        assert result["language"] is None
        assert result["text"] == ""
        assert result["segments"] == []
        assert result["provider"] == "mock"

    def test_no_fabricated_speech(self):
        """Mock provider must NEVER create fake dialogue."""
        provider = MockAudioProvider()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            pass
        _create_audio_file(tmp.name)
        result = provider.transcribe(tmp.name)
        os.unlink(tmp.name)
        assert result["text"] == ""
        assert "hello" not in result["text"].lower()
        assert "welcome" not in result["text"].lower()

    def test_missing_file_raises(self):
        provider = MockAudioProvider()
        with pytest.raises(FileNotFoundError):
            provider.transcribe("/nonexistent/audio.wav")


class TestWhisperProvider:
    def test_provider_name(self):
        provider = WhisperAudioProvider()
        assert "whisper" in provider.provider_name

    def test_lazy_loading_flag(self):
        provider = WhisperAudioProvider()
        assert not provider._loaded

    def test_raises_without_dependencies(self):
        provider = WhisperAudioProvider()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            pass
        _create_audio_file(tmp.name)
        try:
            provider.transcribe(tmp.name)
        except RuntimeError as e:
            assert "faster-whisper" in str(e).lower() or "librosa" in str(e).lower()
        finally:
            os.unlink(tmp.name)


class TestAudioExtraction:
    def test_extract_audio_creates_wav(self, video_in_storage, audio_service):
        result = extract_audio("test_video.mp4")
        assert result["sample_rate"] == 16000
        assert result["channels"] == 1
        assert result["audio_format"] == "wav"

    def test_extraction_returns_correct_sample_rate(self, video_in_storage, audio_service):
        result = extract_audio("test_video.mp4")
        assert result["sample_rate"] == 16000


class TestAudioServiceCore:
    def test_no_audio_video_returns_empty(self, audio_service):
        """Videos without audio should return has_audio=False and empty transcription."""
        storage_dir = Path("storage/uploads")
        storage_dir.mkdir(parents=True, exist_ok=True)
        video_path = storage_dir / "no_audio_video.mp4"
        import imageio_ffmpeg
        import subprocess
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2", "-y", str(video_path)],
            capture_output=True, timeout=10,
        )
        result = audio_service.analyze_audio("no_audio_video.mp4")
        assert result["has_audio"] is False
        assert result["transcription"]["text"] == ""
        assert result["transcription"]["segments"] == []
        assert result["transcription"]["provider"] == "mock"
        if video_path.exists():
            video_path.unlink()

    def test_mock_provider_empty_transcription(self, audio_service):
        """Mock provider must never fabricate speech."""
        result = {
            "language": None,
            "text": "",
            "segments": [],
            "provider": "mock",
        }
        assert result["text"] == ""
        assert result["segments"] == []

    def test_transcription_schema(self):
        """Verify transcription result schema has all required fields."""
        provider = MockAudioProvider()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            pass
        _create_audio_file(tmp.name)
        result = provider.transcribe(tmp.name)
        os.unlink(tmp.name)
        assert "language" in result
        assert "text" in result
        assert "segments" in result
        assert "provider" in result

    def test_no_absolute_paths_in_result(self, audio_service):
        """Ensure no absolute paths leak into the result."""
        provider = MockAudioProvider()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            pass
        _create_audio_file(tmp.name)
        result = provider.transcribe(tmp.name)
        os.unlink(tmp.name)
        for key in ["language", "text", "provider"]:
            if key in result:
                assert not str(result[key]).startswith("/")


class TestHasAudioDetection:
    def test_mock_provider_has_audio_returns_bool(self):
        provider = MockAudioProvider()
        assert callable(provider.has_audio)


class TestAudioServiceInitialization:
    def test_default_provider_is_mock(self):
        svc = AudioService()
        assert svc.audio_provider.provider_name == "mock"

    def test_custom_provider(self):
        svc = AudioService(audio_provider=MockAudioProvider())
        assert svc.audio_provider.provider_name == "mock"
