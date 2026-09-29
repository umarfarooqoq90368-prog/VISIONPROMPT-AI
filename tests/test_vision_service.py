"""Test the vision service and image analysis endpoint."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ai.providers import MockVisionProvider, VisionProvider
from app.services.vision_service import VisionService

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets", "test_video.mp4")
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


def _extract_frame():
    """Upload a video and extract a frame. Returns (stored_filename, frame_filename)."""
    if not os.path.exists(TEST_VIDEO_PATH):
        _create_real_mp4(TEST_VIDEO_PATH)
    with open(TEST_VIDEO_PATH, "rb") as f:
        upload = client.post("/api/videos/upload", files={"file": ("test.mp4", f, "video/mp4")})
    assert upload.status_code == 200
    stored = upload.json()["video"]["stored_filename"]
    response = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds=1")
    assert response.status_code == 200
    frame_data = response.json()["frames"][0]
    return stored, frame_data["filename"]


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Create test assets and clean up after each test."""
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)
    import shutil, glob
    if os.path.exists(FRAME_STORAGE_DIR):
        for d in glob.glob(os.path.join(FRAME_STORAGE_DIR, "*")):
            if os.path.isdir(d):
                shutil.rmtree(d)


def test_vision_provider_is_abstract():
    """Test that VisionProvider is an abstract base class."""
    assert issubclass(VisionProvider, object)
    assert hasattr(VisionProvider, "describe_image")


def test_mock_provider_description():
    """Test MockVisionProvider returns a description."""
    provider = MockVisionProvider()
    assert provider.model_name == "mock-vision-provider"
    description = provider.describe_image(TEST_VIDEO_PATH)
    assert isinstance(description, str)
    assert len(description) > 0


def test_vision_service_with_mock():
    """Test VisionService works with the mock provider."""
    service = VisionService(MockVisionProvider())
    # Create a dummy image inside frame storage for validation
    dummy_image = os.path.join(FRAME_STORAGE_DIR, "dummy_test.jpg")
    os.makedirs(FRAME_STORAGE_DIR, exist_ok=True)
    from PIL import Image
    img = Image.new("RGB", (320, 240), color=(0, 0, 255))
    img.save(dummy_image)
    result = service.analyze_frame(dummy_image)
    assert result["success"] is True
    assert "description" in result
    assert result["model"] == "mock-vision-provider"
    os.remove(dummy_image)


def test_vision_service_invalid_path():
    """Test VisionService rejects invalid paths."""
    service = VisionService(MockVisionProvider())
    with pytest.raises(ValueError):
        service.analyze_frame("/etc/passwd.txt")


def test_analyze_nonexistent_frame():
    """Test analyzing a nonexistent frame returns 404."""
    response = client.post(
        "/api/videos/nonexistent.mp4/frames/analyze",
        params={"frame_filename": "frame_000001.jpg"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_analyze_invalid_frame_filename():
    """Test analyzing with an invalid frame filename returns 400."""
    response = client.post(
        "/api/videos/test.mp4/frames/analyze",
        params={"frame_filename": "../etc/passwd"},
    )
    assert response.status_code == 400


def test_analyze_invalid_frame_format():
    """Test analyzing with a non-image frame filename returns 400."""
    response = client.post(
        "/api/videos/test.mp4/frames/analyze",
        params={"frame_filename": "not_an_image.txt"},
    )
    assert response.status_code == 400


def test_analyze_valid_frame():
    """Test analyzing a real extracted frame returns 200."""
    stored, frame_filename = _extract_frame()

    response = client.post(
        f"/api/videos/{stored}/frames/analyze",
        params={"frame_filename": frame_filename},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["video_filename"] == stored
    assert data["frame_filename"] == frame_filename
    assert "description" in data
    assert data["model"] == "mock-vision-provider"


def test_analyze_no_frame_filename():
    """Test analyzing without frame_filename returns 422."""
    stored, frame_filename = _extract_frame()
    response = client.post(f"/api/videos/{stored}/frames/analyze")
    assert response.status_code == 422