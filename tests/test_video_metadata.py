"""Test the video metadata extraction endpoint."""
import glob
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets", "test_video.mp4")
STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "storage", "uploads")
)


def _create_test_file(path: str, size_bytes: int = 1024):
    """Create a minimal test file for uploading."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"fake_mp4_content" * (size_bytes // 16))


def _cleanup_storage():
    """Remove all files from the uploads directory."""
    if os.path.exists(STORAGE_DIR):
        for f in glob.glob(os.path.join(STORAGE_DIR, "*")):
            os.remove(f)


def _create_real_mp4(path: str):
    """Create a minimal valid MP4 using the bundled ffmpeg."""
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        import subprocess
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1", "-y", path],
            capture_output=True, timeout=10,
        )
        return os.path.exists(path) and os.path.getsize(path) > 0
    except Exception:
        return False


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Create test assets and clean up after each test."""
    _create_test_file(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)
    _cleanup_storage()


def test_metadata_nonexistent_video():
    """Test metadata for a video that doesn't exist returns 404."""
    response = client.get("/api/videos/nonexistent.mp4/metadata")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_metadata_invalid_filename():
    """Test metadata with an invalid filename returns 400."""
    response = client.get("/api/videos/..passwd/metadata")
    assert response.status_code == 400


def test_metadata_valid_video():
    """Test metadata extraction for a real MP4 video (requires ffmpeg)."""
    real_video = os.path.join(os.path.dirname(__file__), "test_assets", "real_test.mp4")
    if not _create_real_mp4(real_video):
        pytest.skip("ffmpeg not available; skipping real video metadata test")

    with open(real_video, "rb") as f:
        upload = client.post("/api/videos/upload", files={"file": ("real_test.mp4", f, "video/mp4")})
    assert upload.status_code == 200
    stored = upload.json()["video"]["stored_filename"]

    response = client.get(f"/api/videos/{stored}/metadata")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "video" in data
    video = data["video"]
    assert video["width"] == 320
    assert video["height"] == 240
    assert video["duration_seconds"] is not None
    assert video["fps"] is not None
    assert video["video_codec"] == "h264"

    os.remove(real_video)