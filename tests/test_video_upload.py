import os
import glob
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


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Create test assets and clean up after each test."""
    _create_test_file(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)
    _cleanup_storage()


def test_upload_video_success():
    """Test uploading a valid video file returns 200 and correct response."""
    with open(TEST_VIDEO_PATH, "rb") as f:
        response = client.post(
            "/api/videos/upload",
            files={"file": ("test_video.mp4", f, "video/mp4")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Video uploaded successfully"
    assert data["video"]["original_filename"] == "test_video.mp4"
    assert data["video"]["stored_filename"].endswith(".mp4")
    assert data["video"]["extension"] == ".mp4"
    assert data["video"]["content_type"] == "video/mp4"
    assert "file_size" in data["video"]
    assert data["video"]["file_size"] > 0


def test_upload_missing_file():
    """Test uploading without a file returns 422."""
    response = client.post("/api/videos/upload")
    assert response.status_code == 422


def test_upload_unsupported_extension():
    """Test uploading an unsupported file type returns 400."""
    test_file = os.path.join(os.path.dirname(__file__), "test_assets", "test.txt")
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, "w") as f:
        f.write("not a video")

    with open(test_file, "rb") as f:
        response = client.post(
            "/api/videos/upload",
            files={"file": ("test.txt", f, "text/plain")},
        )

    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]

    os.remove(test_file)


def test_upload_too_large(monkeypatch):
    """Test uploading a file exceeding the size limit returns 413."""
    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "max_video_size_mb", 1)

    large_video = os.path.join(os.path.dirname(__file__), "test_assets", "large_video.mp4")
    os.makedirs(os.path.dirname(large_video), exist_ok=True)
    with open(large_video, "wb") as f:
        f.write(b"x" * (2 * 1024 * 1024))

    with open(large_video, "rb") as f:
        response = client.post(
            "/api/videos/upload",
            files={"file": ("large_video.mp4", f, "video/mp4")},
        )

    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()

    os.remove(large_video)