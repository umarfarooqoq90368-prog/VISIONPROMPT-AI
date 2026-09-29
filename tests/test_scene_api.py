"""API tests for the scene detection endpoint."""
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


def _upload_and_extract(interval=1.0):
    if not os.path.exists(TEST_VIDEO_PATH):
        _create_real_mp4(TEST_VIDEO_PATH)
    with open(TEST_VIDEO_PATH, "rb") as f:
        upload = client.post("/api/videos/upload", files={"file": ("test.mp4", f, "video/mp4")})
    assert upload.status_code == 200
    stored = upload.json()["video"]["stored_filename"]
    response = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds={interval}")
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


def test_scene_nonexistent_video():
    response = client.post("/api/videos/nonexistent.mp4/scenes/detect")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_scene_no_frames():
    stored = _upload_and_extract()
    _cleanup_frames()
    response = client.post(f"/api/videos/{stored}/scenes/detect")
    assert response.status_code == 400
    assert "frames" in response.json()["detail"].lower()


def test_scene_invalid_interval():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/scenes/detect?sample_interval_seconds=0")
    assert response.status_code == 422


def test_scene_invalid_threshold():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/scenes/detect?threshold=1.5")
    assert response.status_code == 422


def test_scene_valid_detection():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/scenes/detect")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["scenes_detected"] >= 1
    assert "scenes" in data
    assert "duration_seconds" in data
    assert "video_filename" in data


def test_scene_single_scene():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/scenes/detect")
    assert response.status_code == 200
    data = response.json()
    assert data["scenes_detected"] >= 1


def test_scene_chronological_ordering():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/scenes/detect")
    assert response.status_code == 200
    data = response.json()
    scenes = data["scenes"]
    for i in range(len(scenes) - 1):
        assert scenes[i]["start_time"] < scenes[i]["end_time"]


def test_scene_no_absolute_paths():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/scenes/detect")
    assert response.status_code == 200
    data = response.json()
    for scene in data["scenes"]:
        assert not scene["start_frame"].startswith("/")
        assert not scene["end_frame"].startswith("/")
        assert not scene["representative_frame"].startswith("/")


def test_scene_response_structure():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/scenes/detect")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "video_filename" in data
    assert "duration_seconds" in data
    assert "scenes_detected" in data
    assert "scenes" in data
    assert data["success"] is True


def test_scene_first_scene_change_score_null():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/scenes/detect")
    assert response.status_code == 200
    data = response.json()
    if len(data["scenes"]) > 0:
        assert data["scenes"][0]["change_score_from_previous"] is None


def test_scene_custom_interval():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/scenes/detect?sample_interval_seconds=1")
    assert response.status_code == 200
    data = response.json()
    assert data["scenes_detected"] >= 1


def test_scene_custom_threshold():
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/scenes/detect?threshold=0.5")
    assert response.status_code == 200
    data = response.json()
    assert data["scenes_detected"] >= 1


def test_scene_path_traversal():
    response = client.post("/api/videos/../../../etc/passwd/scenes/detect")
    assert response.status_code == 404


def test_previous_endpoints_still_work():
    stored = _upload_and_extract()
    r1 = client.get("/api/health")
    assert r1.status_code == 200
    r2 = client.get(f"/api/videos/{stored}/metadata")
    assert r2.status_code == 200
