import uuid
import shutil
from pathlib import Path

from app.core.config import settings

STORAGE_DIR = Path("storage/uploads")

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


def get_stored_filepath(original_filename: str) -> tuple[Path, str, str]:
    """Generate a unique stored filename and return the full path and extension."""
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext}")

    unique_name = f"{uuid.uuid4()}{ext}"
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    filepath = STORAGE_DIR / unique_name

    return filepath, unique_name, ext


def save_uploaded_file(file, filepath: Path) -> int:
    """Stream the uploaded file to disk and return its size in bytes."""
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    file.file.seek(0)
    return filepath.stat().st_size


def validate_file_extension(filename: str) -> str:
    """Validate and return the file extension if allowed."""
    ext = Path(filename).suffix.lower()
    if not ext:
        raise ValueError("File has no extension.")
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    return ext


def get_file_size(file) -> int:
    """Return the file size without loading it into memory."""
    current_pos = file.file.tell()
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(current_pos)
    return size


def validate_file_size(file) -> None:
    """Validate file size against the configured maximum."""
    size = get_file_size(file)
    max_size = settings.max_video_size_mb * 1024 * 1024
    if size > max_size:
        raise ValueError(
            f"File too large: {size} bytes exceeds the maximum allowed size of {settings.max_video_size_mb} MB."
        )
