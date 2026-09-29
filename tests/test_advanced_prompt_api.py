"""API tests for the advanced prompt endpoint (Day 13)."""
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


def test_advanced_prompt_valid_request():
    """Valid advanced prompt request should return HTTP 200."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/advanced-prompt?style=cinematic")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_advanced_prompt_cinematic_style():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/advanced-prompt?style=cinematic")
    assert response.status_code == 200
    assert response.json()["style"] == "cinematic"


def test_advanced_prompt_realistic_style():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/advanced-prompt?style=realistic")
    assert response.status_code == 200
    assert response.json()["style"] == "realistic"


def test_advanced_prompt_commercial_style():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/advanced-prompt?style=commercial")
    assert response.status_code == 200
    assert response.json()["style"] == "commercial"


def test_advanced_prompt_invalid_style():
    """Invalid style should return HTTP 400."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/advanced-prompt?style=anime")
    assert response.status_code == 400


def test_advanced_prompt_nonexistent_video():
    """Nonexistent video should return HTTP 404."""
    response = client.post("/api/videos/nonexistent.mp4/advanced-prompt")
    assert response.status_code == 404


def test_advanced_prompt_path_traversal():
    """Path traversal should be rejected."""
    response = client.post("/api/videos/../../../etc/passwd/advanced-prompt")
    assert response.status_code in (400, 404)


def test_advanced_prompt_response_structure():
    """Response should contain all required keys."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/advanced-prompt?style=cinematic")
    assert response.status_code == 200
    data = response.json()
    for key in ["success", "message", "video_filename", "style", "prompt", "negative_prompt", "sections"]:
        assert key in data, f"missing key: {key}"
    for section in ["subject", "action", "environment", "camera", "lighting",
                    "visual_style", "color", "audio", "composition"]:
        assert section in data["sections"], f"missing section: {section}"
    assert data["video_filename"] == stored


def test_advanced_prompt_no_absolute_paths():
    """Response should not contain absolute filesystem paths."""
    import json
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/advanced-prompt?style=cinematic")
    assert response.status_code == 200
    data = response.json()
    serialized = json.dumps(data)
    assert "C:/" not in serialized
    assert "C:\\" not in serialized
    assert "/home" not in serialized
    assert "/Users" not in serialized
    assert "/var" not in serialized


def test_advanced_prompt_no_fabrication():
    """Mock intelligence has no subjects/actions; prompt must not fabricate them."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/advanced-prompt?style=cinematic")
    assert response.status_code == 200
    data = response.json()
    full_text = " ".join(data["sections"].values()).lower()
    # Mock providers return empty values, so content words must not appear
    forbidden = ["person", "character", "dialogue", "walking", "running",
                 "park", "city", "sunset", "music", "orchestral"]
    for word in forbidden:
        assert word not in full_text, f"fabricated content found: {word}"


def test_advanced_prompt_deterministic():
    """Same video + same style should return the same prompt."""
    stored = _upload_and_extract()
    r1 = client.post(f"/api/videos/{stored}/advanced-prompt?style=cinematic")
    r2 = client.post(f"/api/videos/{stored}/advanced-prompt?style=cinematic")
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["prompt"] == r2.json()["prompt"]
    assert r1.json()["negative_prompt"] == r2.json()["negative_prompt"]


def test_advanced_prompt_generic_negative_prompt():
    """Negative prompt should be generic quality-only."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/advanced-prompt?style=cinematic")
    assert response.status_code == 200
    neg = response.json()["negative_prompt"].lower()
    assert "blurry" in neg
    assert "watermark" in neg
    assert "person" not in neg
    assert "dialogue" not in neg


def test_advanced_prompt_previous_endpoints_still_work():
    """Day 1-12 endpoints should still work."""
    stored = _upload_and_extract()
    r1 = client.get("/api/health")
    assert r1.status_code == 200
    r2 = client.post(f"/api/videos/{stored}/intelligence")
    assert r2.status_code == 200
    r3 = client.post(f"/api/videos/{stored}/prompt?style=cinematic")
    assert r3.status_code == 200
