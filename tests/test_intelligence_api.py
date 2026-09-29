"""API tests for the unified intelligence endpoint."""
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


def test_intelligence_valid_request():
    """Valid intelligence request should return HTTP 200."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/intelligence")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_intelligence_nonexistent_video():
    """Nonexistent video should return HTTP 404."""
    response = client.post("/api/videos/nonexistent.mp4/intelligence")
    assert response.status_code == 404


def test_intelligence_path_traversal():
    """Path traversal should be rejected."""
    response = client.post("/api/videos/../../../etc/passwd/intelligence")
    assert response.status_code == 404


def test_intelligence_invalid_max_frames():
    """Invalid max_frames should return HTTP 400."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/intelligence?max_frames=0")
    assert response.status_code == 400
    response = client.post(f"/api/videos/{stored}/intelligence?max_frames=51")
    assert response.status_code == 400


def test_intelligence_response_structure():
    """Response should have all required sections."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/intelligence")
    assert response.status_code == 200
    data = response.json()
    assert "video_filename" in data
    assert "duration_seconds" in data
    assert "visual" in data
    assert "scenes" in data
    assert "subjects" in data
    assert "audio" in data
    # Check visual sub-keys
    visual = data["visual"]
    assert "frames_analyzed" in visual
    assert "subjects" in visual
    assert "actions" in visual
    assert "environment" in visual
    assert "camera" in visual
    assert "lighting" in visual
    assert "visual_style" in visual
    assert "color_palette" in visual
    assert "objects" in visual
    # Check scenes sub-keys
    assert "scenes_detected" in data["scenes"]
    assert "timeline" in data["scenes"]
    # Check subjects sub-keys
    assert "subjects_detected" in data["subjects"]
    assert "profiles" in data["subjects"]
    # Check audio sub-keys
    audio = data["audio"]
    assert "has_audio" in audio
    assert "transcription" in audio
    assert "provider" in audio


def test_intelligence_no_absolute_paths():
    """Response should not contain absolute filesystem paths."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/intelligence")
    assert response.status_code == 200
    data = response.json()
    assert not data["video_filename"].startswith("/")
    # Check no absolute paths in any section
    for scene in data["scenes"]["timeline"]:
        for key in ["start_frame", "end_frame", "representative_frame"]:
            val = scene.get(key, "")
            assert not val.startswith("/"), f"Absolute path found in {key}: {val}"
    for profile in data["subjects"]["profiles"]:
        for frame in profile.get("frames_seen", []):
            assert not frame.startswith("/"), f"Absolute path in frames_seen: {frame}"


def test_intelligence_no_frames():
    """Video with no extracted frames should return empty sections."""
    stored = _upload_and_extract()
    _cleanup_frames()
    response = client.post(f"/api/videos/{stored}/intelligence")
    assert response.status_code == 200
    data = response.json()
    assert data["visual"]["frames_analyzed"] == 0
    assert data["scenes"]["scenes_detected"] == 0
    assert data["subjects"]["subjects_detected"] == 0


def test_intelligence_previous_endpoints_still_work():
    """Previous endpoints should still work after adding intelligence."""
    stored = _upload_and_extract()
    r1 = client.get("/api/health")
    assert r1.status_code == 200
    r2 = client.post(f"/api/videos/{stored}/analyze?max_frames=2")
    assert r2.status_code == 200
    r3 = client.post(f"/api/videos/{stored}/subjects/analyze")
    assert r3.status_code == 200
    r4 = client.post(f"/api/videos/{stored}/audio/analyze")
    assert r4.status_code == 200
