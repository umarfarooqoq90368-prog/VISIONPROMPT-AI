"""API tests for the prompt refinement endpoint (Day 14)."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets", "test_video.mp4")
FRAME_STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "storage", "frames")
)

OPERATIONS = ["refine", "shorten", "expand", "cinematic", "realistic", "commercial"]


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


def _refine(stored: str, operation: str = "refine"):
    return client.post(
        f"/api/videos/{stored}/prompt/refine",
        json={"operation": operation},
    )


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


def test_refine_valid_request():
    """Valid refinement request should return HTTP 200."""
    stored = _upload_and_extract()
    response = _refine(stored, "refine")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.parametrize("operation", OPERATIONS)
def test_each_supported_operation(operation):
    """Each of the six operations should return HTTP 200."""
    stored = _upload_and_extract()
    response = _refine(stored, operation)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["operation"] == operation
    assert isinstance(data["refined_prompt"], str)
    assert data["refined_prompt"]


def test_invalid_operation():
    """Invalid operation should return HTTP 400."""
    stored = _upload_and_extract()
    response = _refine(stored, "reformat")
    assert response.status_code == 400


def test_empty_operation():
    """Empty operation should return HTTP 400."""
    stored = _upload_and_extract()
    response = _refine(stored, "")
    assert response.status_code == 400


def test_nonexistent_video():
    """Nonexistent video should return HTTP 404."""
    response = client.post(
        "/api/videos/nonexistent.mp4/prompt/refine",
        json={"operation": "refine"},
    )
    assert response.status_code == 404


def test_path_traversal():
    """Path traversal should be rejected."""
    response = client.post(
        "/api/videos/../../../etc/passwd/prompt/refine",
        json={"operation": "refine"},
    )
    assert response.status_code in (400, 404)


def test_response_structure():
    """Response should contain all required keys."""
    stored = _upload_and_extract()
    response = _refine(stored, "refine")
    assert response.status_code == 200
    data = response.json()
    for key in [
        "success",
        "message",
        "video_filename",
        "operation",
        "source_prompt",
        "refined_prompt",
        "negative_prompt",
        "preserved_information",
    ]:
        assert key in data, f"missing key: {key}"
    assert data["video_filename"] == stored
    assert data["operation"] == "refine"
    assert data["preserved_information"] is True


def test_no_absolute_paths():
    """Response should not contain absolute filesystem paths."""
    import json
    stored = _upload_and_extract()
    response = _refine(stored, "refine")
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "C:/" not in serialized
    assert "C:\\" not in serialized
    assert "/home" not in serialized
    assert "/Users" not in serialized
    assert "/var" not in serialized


def test_no_fabricated_information():
    """Mock intelligence is empty; refined prompt must not invent content."""
    stored = _upload_and_extract()
    for operation in OPERATIONS:
        response = _refine(stored, operation)
        assert response.status_code == 200
        data = response.json()
        text = data["refined_prompt"].lower()
        forbidden = [
            "person", "character", "dialogue", "walking", "running",
            "park", "city", "sunset", "brand", "product", "voiceover",
        ]
        for word in forbidden:
            assert word not in text, f"{operation} fabricated: {word}"


def test_deterministic_output():
    """Same video + same operation should return the same refined prompt."""
    stored = _upload_and_extract()
    r1 = _refine(stored, "shorten")
    r2 = _refine(stored, "shorten")
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["refined_prompt"] == r2.json()["refined_prompt"]
    assert r1.json()["source_prompt"] == r2.json()["source_prompt"]


def test_source_and_refined_both_present():
    """source_prompt and refined_prompt should both be non-empty."""
    stored = _upload_and_extract()
    response = _refine(stored, "expand")
    assert response.status_code == 200
    data = response.json()
    assert data["source_prompt"]
    assert data["refined_prompt"]


def test_negative_prompt_present():
    """Negative prompt should be generic and present."""
    stored = _upload_and_extract()
    response = _refine(stored, "refine")
    assert response.status_code == 200
    neg = response.json()["negative_prompt"].lower()
    assert "blurry" in neg
    assert "watermark" in neg
    assert "person" not in neg


def test_missing_operation_field():
    """Malformed body missing operation should return HTTP 422."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/prompt/refine", json={})
    assert response.status_code == 422


def test_previous_endpoints_still_work():
    """Day 1-13 endpoints should still work after adding refinement."""
    stored = _upload_and_extract()
    r1 = client.get("/api/health")
    assert r1.status_code == 200
    r2 = client.post(f"/api/videos/{stored}/intelligence")
    assert r2.status_code == 200
    r3 = client.post(f"/api/videos/{stored}/advanced-prompt?style=cinematic")
    assert r3.status_code == 200
    r4 = client.post(f"/api/videos/{stored}/prompt?style=cinematic")
    assert r4.status_code == 200
