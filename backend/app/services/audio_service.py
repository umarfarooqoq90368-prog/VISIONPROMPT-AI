import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import imageio_ffmpeg

from app.ai.audio_providers import get_audio_provider
from app.core.config import settings
from app.utils.ffprobe import extract_metadata

AUDIO_STORAGE_DIR = Path("storage/audio")


def _get_video_path(stored_filename: str) -> Path:
    """Get the full path to an uploaded video with path traversal protection."""
    filepath = (Path("storage/uploads") / stored_filename).resolve()
    storage_root = Path("storage/uploads").resolve()
    if not str(filepath).startswith(str(storage_root)) or not filepath.exists():
        raise ValueError("Video file not found.")
    return filepath


def _get_audio_path(stored_filename: str) -> Path:
    """Get the audio output path for a video."""
    video_id = stored_filename.rsplit(".", 1)[0]
    return AUDIO_STORAGE_DIR / f"{video_id}.wav"


def _has_audio_stream(video_path: Path) -> bool:
    """Check if a video file contains an audio stream using ffmpeg."""
    try:
        metadata = extract_metadata(video_path)
        return metadata.get("audio_codec") is not None
    except Exception:
        return False


def extract_audio(stored_filename: str) -> dict:
    """Extract audio from a video as 16kHz mono WAV.

    Returns a dict with audio metadata. Cleans up partial files on failure.

    Args:
        stored_filename: The stored video filename.

    Returns:
        Dict with audio_path, duration_seconds, sample_rate, channels.

    Raises:
        ValueError: If video file not found.
        RuntimeError: If extraction fails.
    """
    video_path = _get_video_path(stored_filename)
    audio_path = _get_audio_path(stored_filename)

    # Ensure audio storage directory exists
    AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # Check for audio stream before extraction
    if not _has_audio_stream(video_path):
        return {
            "audio_path": None,
            "duration_seconds": None,
            "sample_rate": None,
            "channels": None,
            "audio_format": None,
        }

    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-hide_banner",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-y",
        str(audio_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            # Clean up partial file
            if audio_path.exists():
                audio_path.unlink()
            raise RuntimeError(
                f"Audio extraction failed: {result.stderr.strip()}"
            )
    except subprocess.TimeoutExpired:
        if audio_path.exists():
            audio_path.unlink()
        raise RuntimeError("Audio extraction timed out.")
    except Exception as e:
        if audio_path.exists():
            audio_path.unlink()
        raise RuntimeError(f"Audio extraction failed: {str(e)}")

    if not audio_path.exists():
        raise RuntimeError("Audio extraction produced no output file.")

    # Get duration from video metadata
    duration = None
    try:
        metadata = extract_metadata(video_path)
        duration = metadata["duration_seconds"]
    except Exception:
        pass

    return {
        "audio_path": str(audio_path),
        "duration_seconds": round(duration, 2) if duration is not None else None,
        "sample_rate": 16000,
        "channels": 1,
        "audio_format": "wav",
    }


class AudioService:
    """Service for audio analysis and speech transcription.

    Reuses existing frame extraction and video analysis infrastructure.
    """

    def __init__(self, audio_provider: Optional = None):
        self.audio_provider = audio_provider or get_audio_provider(
            settings.audio_provider
        )

    def analyze_audio(self, stored_filename: str) -> dict:
        """Analyze video audio and return structured transcription result.

        Args:
            stored_filename: The stored video filename.

        Returns:
            Dict with full audio analysis result.

        Raises:
            ValueError: If video file not found or invalid.
            RuntimeError: If analysis fails.
        """
        # Validate video
        video_path = _get_video_path(stored_filename)

        # Get video metadata
        try:
            metadata = extract_metadata(video_path)
            duration = metadata["duration_seconds"]
        except Exception:
            duration = None

        # Check for audio stream
        has_audio = _has_audio_stream(video_path)

        if not has_audio:
            return {
                "video_filename": stored_filename,
                "has_audio": False,
                "duration_seconds": round(duration, 2) if duration is not None else None,
                "audio_format": None,
                "sample_rate": None,
                "channels": None,
                "transcription": {
                    "language": None,
                    "text": "",
                    "segments": [],
                    "provider": self.audio_provider.provider_name,
                },
                "provider": self.audio_provider.provider_name,
            }

        # Extract audio
        try:
            audio_info = extract_audio(stored_filename)
        except RuntimeError as e:
            raise RuntimeError(f"Audio extraction failed: {str(e)}")

        audio_path = audio_info["audio_path"]

        # Run transcription
        try:
            transcription = self.audio_provider.transcribe(audio_path)
        except FileNotFoundError:
            transcription = {
                "language": None,
                "text": "",
                "segments": [],
                "provider": self.audio_provider.provider_name,
            }
        except RuntimeError as e:
            raise RuntimeError(f"Transcription failed: {str(e)}")

        return {
            "video_filename": stored_filename,
            "has_audio": True,
            "duration_seconds": audio_info["duration_seconds"],
            "audio_format": audio_info["audio_format"],
            "sample_rate": audio_info["sample_rate"],
            "channels": audio_info["channels"],
            "transcription": transcription,
            "provider": self.audio_provider.provider_name,
        }
