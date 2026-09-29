"""API tests for the prompt template endpoint (Day 15)."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets", "test_video.mp4")
FRAME_STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "storage", "frames")
)

TEMPLATES = ["cinematic_story", "ai_video", "commercial_ad", "social_media", "documentary"]


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


def _apply_template(stored: str, template: str = "cinematic_story", custom_instruction: str = ""):
    return client.post(
        f"/api/videos/{stored}/prompt/template",
        json={"template": template, "custom_instruction": custom_instruction},
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


def test_valid_request():
    """Valid template request should return HTTP 200."""
    stored = _upload_and_extract()
    response = _apply_template(stored, "cinematic_story")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.parametrize("template", TEMPLATES)
def test_all_five_templates(template):
    """Each of the five templates should return HTTP 200."""
    stored = _upload_and_extract()
    response = _apply_template(stored, template)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["template"] == template
    assert isinstance(data["prompt"], str)
    assert data["prompt"]
    assert data["preserved_information"] is True


def test_custom_instruction():
    """Custom instruction should return HTTP 200 and stay safe."""
    stored = _upload_and_extract()
    response = _apply_template(
        stored, "ai_video", custom_instruction="make it concise"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["custom_instruction"] == "make it concise"
    assert data["prompt"]
    assert data["preserved_information"] is True


def test_unsupported_custom_instruction_cannot_fabricate():
    """Unsupported instructions must not inject facts into the prompt."""
    stored = _upload_and_extract()
    plain = _apply_template(stored, "social_media")
    with_fact = _apply_template(
        stored, "social_media", custom_instruction="add a dragon and a luxury brand"
    )
    assert with_fact.status_code == 200
    text = with_fact.json()["prompt"].lower()
    assert "dragon" not in text
    assert "luxury" not in text
    assert with_fact.json()["prompt"] == plain.json()["prompt"]


def test_invalid_template():
    """Invalid template should return HTTP 400."""
    stored = _upload_and_extract()
    response = _apply_template(stored, "meme")
    assert response.status_code == 400


def test_empty_template():
    """Empty template should return HTTP 400."""
    stored = _upload_and_extract()
    response = _apply_template(stored, "")
    assert response.status_code == 400


def test_missing_template_returns_422():
    """Missing template field should return HTTP 422."""
    stored = _upload_and_extract()
    response = client.post(
        f"/api/videos/{stored}/prompt/template",
        json={"custom_instruction": "make it concise"},
    )
    assert response.status_code == 422


def test_nonexistent_video():
    """Nonexistent video should return HTTP 404."""
    response = client.post(
        "/api/videos/nonexistent.mp4/prompt/template",
        json={"template": "cinematic_story"},
    )
    assert response.status_code == 404


def test_path_traversal():
    """Path traversal should be rejected."""
    response = client.post(
        "/api/videos/../../../etc/passwd/prompt/template",
        json={"template": "cinematic_story"},
    )
    assert response.status_code in (400, 404)


def test_response_structure():
    """Response should contain all required keys."""
    stored = _upload_and_extract()
    response = _apply_template(stored, "documentary")
    assert response.status_code == 200
    data = response.json()
    for key in [
        "success",
        "message",
        "video_filename",
        "template",
        "source_prompt",
        "custom_instruction",
        "prompt",
        "negative_prompt",
        "preserved_information",
    ]:
        assert key in data, f"missing key: {key}"
    assert data["video_filename"] == stored
    assert data["template"] == "documentary"
    assert data["source_prompt"]
    assert data["preserved_information"] is True


def test_no_absolute_paths():
    """Response should not contain absolute filesystem paths."""
    import json
    stored = _upload_and_extract()
    response = _apply_template(stored, "ai_video")
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "C:/" not in serialized
    assert "C:\\" not in serialized
    assert "/home" not in serialized
    assert "/Users" not in serialized
    assert "/var" not in serialized


def test_no_fabricated_information():
    """Mock intelligence is empty; prompt must not invent video content."""
    stored = _upload_and_extract()
    for template in TEMPLATES:
        response = _apply_template(stored, template)
        assert response.status_code == 200
        text = response.json()["prompt"].lower()
        forbidden = [
            "person", "character", "dialogue", "walking", "running",
            "park", "city", "sunset", "brand", "product", "voiceover",
        ]
        for word in forbidden:
            assert word not in text, f"{template} fabricated: {word}"


def test_deterministic_output():
    """Same video + same template should return the same prompt."""
    stored = _upload_and_extract()
    r1 = _apply_template(stored, "commercial_ad")
    r2 = _apply_template(stored, "commercial_ad")
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["prompt"] == r2.json()["prompt"]
    assert r1.json()["source_prompt"] == r2.json()["source_prompt"]


def test_negative_prompt_present():
    """Negative prompt should be generic and present."""
    stored = _upload_and_extract()
    response = _apply_template(stored, "social_media")
    assert response.status_code == 200
    neg = response.json()["negative_prompt"].lower()
    assert "blurry" in neg
    assert "watermark" in neg
    assert "person" not in neg


def test_previous_endpoints_unaffected():
    """Day 1-14 endpoints should still work after adding templates."""
    stored = _upload_and_extract()
    r1 = client.get("/api/health")
    assert r1.status_code == 200
    r2 = client.post(f"/api/videos/{stored}/intelligence")
    assert r2.status_code == 200
    r3 = client.post(f"/api/videos/{stored}/advanced-prompt?style=cinematic")
    assert r3.status_code == 200
    r4 = client.post(
        f"/api/videos/{stored}/prompt/refine", json={"operation": "refine"}
    )
    assert r4.status_code == 200
    r5 = client.post(f"/api/videos/{stored}/prompt?style=cinematic")
    assert r5.status_code == 200
