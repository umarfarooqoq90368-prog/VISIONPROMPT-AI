"""Tests for the prompt generation API endpoint."""
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


def test_prompt_nonexistent_video():
    response = client.post("/api/videos/nonexistent.mp4/prompt")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_prompt_no_frames():
    stored = _upload_and_extract()
    _cleanup_frames()
    response = client.post(f"/api/videos/{stored}/prompt")
    assert response.status_code == 400
    assert "frames" in response.json()["detail"].lower()


def test_prompt_invalid_style():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/prompt?style=fantasy")
    assert response.status_code == 400


def test_prompt_valid_cinematic():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/prompt?style=cinematic")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["style"] == "cinematic"
    assert data["prompt"]
    assert len(data["prompt"]) > 0


def test_prompt_valid_realistic():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/prompt?style=realistic")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["style"] == "realistic"
    assert data["prompt"]


def test_prompt_valid_commercial():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/prompt?style=commercial")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["style"] == "commercial"
    assert data["prompt"]


def test_prompt_default_style_is_cinematic():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/prompt")
    assert response.status_code == 200
    data = response.json()
    assert data["style"] == "cinematic"
    assert data["prompt"]


def test_prompt_no_absolute_paths():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/prompt?style=cinematic")
    assert response.status_code == 200
    data = response.json()
    prompt = data["prompt"]
    assert not prompt.startswith("/")
    assert "\\" not in prompt
    assert "storage" not in prompt.lower()


def test_prompt_no_json_syntax():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/prompt?style=cinematic")
    assert response.status_code == 200
    data = response.json()
    prompt = data["prompt"]
    assert "{" not in prompt
    assert "}" not in prompt
    assert '"' not in prompt


def test_prompt_response_structure():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/prompt?style=cinematic")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "video_filename" in data
    assert "style" in data
    assert "prompt" in data
    assert "negative_prompt" in data
    assert data["negative_prompt"] is None


def test_prompt_nonnegative_video_filename():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/prompt?style=cinematic")
    assert response.status_code == 200
    data = response.json()
    assert not data["video_filename"].startswith("/")
    assert not data["video_filename"].startswith("\\")
