import glob
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import imageio_ffmpeg

from app.utils.ffprobe import extract_metadata

FFMPEG_BINARY = imageio_ffmpeg.get_ffmpeg_exe()
FRAME_STORAGE_DIR = Path("storage/frames")

MAX_INTERVAL = 60.0
MIN_INTERVAL = 0.1


def extract_frames(
    stored_filename: str,
    interval_seconds: float,
) -> dict:
    """Extract JPEG frames from an uploaded video at a given interval.

    Returns a dict with frame metadata. Cleans up on failure.
    """
    video_path = _get_video_path(stored_filename)
    frame_dir = _get_frame_dir(stored_filename)

    duration = _get_duration(video_path)
    if duration is None or duration <= 0:
        raise RuntimeError("Could not determine video duration.")

    _create_frame_dir(frame_dir)

    output_pattern = str(frame_dir / "frame_%06d.jpg")
    cmd = [
        FFMPEG_BINARY,
        "-hide_banner",
        "-i", str(video_path),
        "-vf", f"fps=1/{interval_seconds}",
        "-q:v", "2",
        "-y",
        output_pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode not in (0, 1):
        _cleanup_frame_dir(frame_dir)
        raise RuntimeError(f"Frame extraction failed: {result.stderr.strip()}")

    frame_files = sorted(
        f for f in glob.glob(str(frame_dir / "frame_*.jpg"))
        if os.path.isfile(f)
    )

    if not frame_files:
        _cleanup_frame_dir(frame_dir)
        raise RuntimeError("No frames were generated.")

    frames = []
    for i, fpath in enumerate(frame_files, start=1):
        timestamp = round((i - 1) * interval_seconds, 2)
        frames.append(
            {
                "index": i,
                "filename": os.path.basename(fpath),
                "path": str(Path("storage/frames") / frame_dir.name / os.path.basename(fpath)).replace("\\", "/"),
                "timestamp_seconds": timestamp,
            }
        )

    return {
        "video_filename": stored_filename,
        "interval_seconds": interval_seconds,
        "frame_count": len(frames),
        "frames": frames,
    }


def _get_video_path(stored_filename: str) -> Path:
    """Get the full path to an uploaded video with path traversal protection."""
    filepath = (Path("storage/uploads") / stored_filename).resolve()
    storage_root = Path("storage/uploads").resolve()
    if not str(filepath).startswith(str(storage_root)) or not filepath.exists():
        raise ValueError("Video file not found.")
    return filepath


def _get_frame_dir(stored_filename: str) -> Path:
    """Get the frame directory for a video, based on the video ID."""
    video_id = stored_filename.rsplit(".", 1)[0]
    frame_dir = FRAME_STORAGE_DIR / video_id
    return frame_dir


def _get_duration(video_path: Path) -> Optional[float]:
    """Get video duration in seconds."""
    try:
        metadata = extract_metadata(video_path)
        return metadata["duration_seconds"]
    except Exception:
        return None


def _create_frame_dir(frame_dir: Path) -> None:
    """Create the frame directory, cleaning any previous contents."""
    frame_dir.mkdir(parents=True, exist_ok=True)
    for f in glob.glob(str(frame_dir / "*.jpg")):
        os.remove(f)


def _cleanup_frame_dir(frame_dir: Path) -> None:
    """Remove all generated frames from the directory."""
    if frame_dir.exists():
        for f in glob.glob(str(frame_dir / "*.jpg")):
            os.remove(f)
        try:
            frame_dir.rmdir()
        except OSError:
            pass


def validate_interval(interval_seconds: float) -> None:
    """Validate the interval_seconds parameter."""
    try:
        interval_seconds = float(interval_seconds)
    except (ValueError, TypeError):
        raise ValueError("interval_seconds must be a number.")
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than 0.")
    if interval_seconds > MAX_INTERVAL:
        raise ValueError(
            f"interval_seconds must not exceed {MAX_INTERVAL}."
        )
    if interval_seconds < MIN_INTERVAL:
        raise ValueError(
            f"interval_seconds must be at least {MIN_INTERVAL}."
        )
