"""Test the video frame extraction endpoint."""
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
FRAME_STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "storage", "frames")
)


def _create_real_mp4(path: str):
    """Create a minimal valid MP4 using the bundled ffmpeg."""
    import imageio_ffmpeg
    import subprocess
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=3", "-y", path],
            capture_output=True, timeout=10,
        )
        return os.path.exists(path) and os.path.getsize(path) > 0
    except Exception:
        return False


def _cleanup_frames():
    """Remove all generated frame directories."""
    if os.path.exists(FRAME_STORAGE_DIR):
        for d in glob.glob(os.path.join(FRAME_STORAGE_DIR, "*")):
            if os.path.isdir(d):
                import shutil
                shutil.rmtree(d)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Create test assets and clean up after each test."""
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)
    _cleanup_frames()


def test_extract_frames_nonexistent_video():
    """Test frame extraction for a video that doesn't exist returns 404."""
    response = client.post("/api/videos/nonexistent.mp4/frames/extract")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_extract_frames_invalid_filename():
    """Test frame extraction with path traversal returns 400."""
    response = client.post("/api/videos/..passwd/frames/extract")
    assert response.status_code == 400


def test_extract_frames_invalid_interval():
    """Test frame extraction with invalid interval returns 400."""
    response = client.post("/api/videos/test.mp4/frames/extract?interval_seconds=0")
    assert response.status_code == 422

    response = client.post("/api/videos/test.mp4/frames/extract?interval_seconds=-1")
    assert response.status_code == 422


def test_extract_frames_valid_interval():
    """Test frame extraction with a valid interval generates frames."""
    with open(TEST_VIDEO_PATH, "rb") as f:
        upload = client.post("/api/videos/upload", files={"file": ("test.mp4", f, "video/mp4")})
    assert upload.status_code == 200
    stored = upload.json()["video"]["stored_filename"]

    response = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds=1")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["frame_count"] > 0
    assert "frames" in data


def test_extract_frames_path_format():
    """Test frame paths are relative and contain no absolute filesystem paths."""
    with open(TEST_VIDEO_PATH, "rb") as f:
        upload = client.post("/api/videos/upload", files={"file": ("test.mp4", f, "video/mp4")})
    assert upload.status_code == 200
    stored = upload.json()["video"]["stored_filename"]

    response = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds=1")
    assert response.status_code == 200
    data = response.json()

    for frame in data["frames"]:
        assert not frame["path"].startswith("/")
        assert not frame["path"].startswith("\\")
        assert "storage/frames" in frame["path"]
        assert frame["filename"].endswith(".jpg")


def test_extract_frames_sequential_numbering():
    """Test frame numbering is sequential."""
    with open(TEST_VIDEO_PATH, "rb") as f:
        upload = client.post("/api/videos/upload", files={"file": ("test.mp4", f, "video/mp4")})
    assert upload.status_code == 200
    stored = upload.json()["video"]["stored_filename"]

    response = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds=1")
    assert response.status_code == 200
    data = response.json()

    for i, frame in enumerate(data["frames"], start=1):
        assert frame["index"] == i
        assert frame["filename"] == f"frame_{i:06d}.jpg"
