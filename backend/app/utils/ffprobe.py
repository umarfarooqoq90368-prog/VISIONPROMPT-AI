import re
import subprocess
from pathlib import Path
from typing import Optional

import imageio_ffmpeg


FFMPEG_BINARY = imageio_ffmpeg.get_ffmpeg_exe()


def extract_metadata(storage_path: Path) -> dict:
    """Extract video metadata using the bundled ffmpeg binary.

    Returns a dictionary with video metadata fields.
    Handles missing audio, missing frame counts, etc.
    """
    output = _run_ffmpeg(storage_path)

    duration = _parse_duration(output)
    format_name = _parse_format(output)
    dimensions = _parse_dimensions(output)
    fps = _parse_fps(output)
    video_codec = _parse_codec(output, "Video")
    audio_codec = _parse_codec(output, "Audio")

    return {
        "filename": storage_path.name,
        "format": format_name,
        "duration_seconds": duration,
        "file_size_bytes": storage_path.stat().st_size,
        "width": dimensions[0],
        "height": dimensions[1],
        "fps": fps,
        "frame_count": None,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
    }


def _run_ffmpeg(storage_path: Path) -> str:
    """Run ffmpeg -i on the file and return stderr output."""
    cmd = [FFMPEG_BINARY, "-hide_banner", "-i", str(storage_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode not in (0, 1):
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()}")
    return result.stderr


def _parse_duration(text: str) -> Optional[float]:
    """Parse duration from ffmpeg stderr output (HH:MM:SS.mmm)."""
    match = re.search(r"Duration:\s+(\d+):(\d+):(\d+\.\d+)", text)
    if match:
        h, m, s = match.groups()
        return round(int(h) * 3600 + int(m) * 60 + float(s), 2)
    return None


def _parse_format(text: str) -> str:
    """Parse format name from ffmpeg stderr output."""
    match = re.search(r"Input #0,\s+([\w,\-]+),", text)
    if match:
        return match.group(1).split(",")[0]
    return ""


def _parse_dimensions(text: str) -> tuple[Optional[int], Optional[int]]:
    """Parse width and height from the Video stream line in ffmpeg stderr output."""
    match = re.search(r"Video:\s+.*?(\d+)x(\d+)\s+\[SAR", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def _parse_fps(text: str) -> Optional[float]:
    """Parse FPS, handling fractions like 30000/1001."""
    match = re.search(r"(\d+(?:/\d+)?)\s+fps", text)
    if not match:
        return None
    fps_str = match.group(1)
    if "/" in fps_str:
        num, den = fps_str.split("/")
        try:
            den = float(den)
            if den == 0:
                return None
            return round(float(num) / den, 2)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(fps_str)
    except (ValueError, TypeError):
        return None


def _parse_codec(text: str, stream_type: str) -> Optional[str]:
    """Parse codec name for Video or Audio stream."""
    pattern = rf"{stream_type}:\s+(\w+)"
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None
