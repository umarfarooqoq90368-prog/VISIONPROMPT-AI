"""API tests for the audio analysis endpoint."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets", "test_video.mp4")
FRAME_STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "storage", "frames")
)


def _create_real_mp4(path: str):
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


def _upload_and_extract():
    if not os.path.exists(TEST_VIDEO_PATH):
        _create_real_mp4(TEST_VIDEO_PATH)
    with open(TEST_VIDEO_PATH, "rb") as f:
        upload = client.post("/api/videos/upload", files={"file": ("test.mp4", f, "video/mp4")})
    assert upload.status_code == 200
    stored = upload.json()["video"]["stored_filename"]
    response = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds=1")
    assert response.status_code == 200
    return stored


def _cleanup_frames():
    import shutil, glob
    if os.path.exists(FRAME_STORAGE_DIR):
        for d in glob.glob(os.path.join(FRAME_STORAGE_DIR, "*")):
            if os.path.isdir(d):
                shutil.rmtree(d)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)
    _cleanup_frames()


def test_audio_nonexistent_video():
    response = client.post("/api/videos/nonexistent.mp4/audio/analyze")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_audio_no_frames():
    stored = _upload_and_extract()
    _cleanup_frames()
    response = client.post(f"/api/videos/{stored}/audio/analyze")
    # Should still work because audio extraction doesn't need frames
    assert response.status_code == 200


def test_audio_valid():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/audio/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "video_filename" in data
    assert "has_audio" in data
    assert "transcription" in data
    assert "provider" in data


def test_audio_response_structure():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/audio/analyze")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "video_filename" in data
    assert "has_audio" in data
    assert "duration_seconds" in data
    assert "audio_format" in data
    assert "sample_rate" in data
    assert "channels" in data
    assert "transcription" in data
    assert "provider" in data


def test_audio_mock_provider_no_fabricated_speech():
    """Mock provider must NEVER invent dialogue."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/audio/analyze")
    assert response.status_code == 200
    data = response.json()
    transcription = data["transcription"]
    assert transcription["text"] == ""
    assert transcription["segments"] == []
    assert transcription["language"] is None or transcription["language"] is None
    assert transcription["provider"] == "mock"


def test_audio_provider_field():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/audio/analyze")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert data["provider"] == "mock"


def test_audio_no_absolute_paths():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/audio/analyze")
    assert response.status_code == 200
    data = response.json()
    assert not data["video_filename"].startswith("/")
    for segment in data["transcription"]["segments"]:
        if "text" in segment:
            assert not segment["text"].startswith("/")


def test_audio_path_traversal():
    response = client.post("/api/videos/../../../etc/passwd/audio/analyze")
    assert response.status_code == 404


def test_audio_previous_endpoints_still_work():
    stored = _upload_and_extract()
    r1 = client.get("/api/health")
    assert r1.status_code == 200
    r2 = client.post(f"/api/videos/{stored}/analyze?max_frames=2")
    assert r2.status_code == 200
    r3 = client.post(f"/api/videos/{stored}/subjects/analyze")
    assert r3.status_code == 200


def test_audio_video_filename():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/audio/analyze")
    assert response.status_code == 200
    data = response.json()
    assert "video_filename" in data
    assert not data["video_filename"].startswith("/")