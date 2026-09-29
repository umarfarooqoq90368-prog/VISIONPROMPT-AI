"""Test the multi-frame video analysis endpoint."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.video_analysis_service import VideoAnalysisService

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


def _upload_and_extract():
    """Upload a video, extract frames, and return stored filename."""
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
    """Remove all generated frame directories."""
    import shutil, glob
    if os.path.exists(FRAME_STORAGE_DIR):
        for d in glob.glob(os.path.join(FRAME_STORAGE_DIR, "*")):
            if os.path.isdir(d):
                shutil.rmtree(d)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Create test assets and clean up after each test."""
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)
    _cleanup_frames()


def test_analyze_nonexistent_video():
    """Test analyzing a nonexistent video returns 404."""
    response = client.post("/api/videos/nonexistent.mp4/analyze")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_analyze_no_frames():
    """Test analyzing a video with no extracted frames returns 400."""
    stored = _upload_and_extract()
    _cleanup_frames()
    response = client.post(f"/api/videos/{stored}/analyze")
    assert response.status_code == 400
    assert "frames" in response.json()["detail"].lower()


def test_analyze_invalid_max_frames():
    """Test analyzing with invalid max_frames returns 422."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/analyze?max_frames=0")
    assert response.status_code == 422

    response = client.post(f"/api/videos/{stored}/analyze?max_frames=51")
    assert response.status_code == 422


def test_analyze_valid():
    """Test successful multi-frame video analysis."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/analyze?max_frames=5")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["frames_analyzed"] <= 5
    assert data["frames_analyzed"] > 0
    assert "analysis" in data
    assert "frame_observations" in data
    assert len(data["frame_observations"]) == data["frames_analyzed"]


def test_frame_observations_have_timestamps():
    """Test that frame observations contain timestamps."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/analyze?max_frames=3")
    assert response.status_code == 200
    data = response.json()
    for obs in data["frame_observations"]:
        assert "timestamp_seconds" in obs
        assert "frame_filename" in obs
        assert "frame_index" in obs
        assert "description" in obs
        assert "model" in obs


def test_frame_observations_ordered():
    """Test that frame observations are in chronological order."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/analyze?max_frames=5")
    assert response.status_code == 200
    data = response.json()
    indices = [obs["frame_index"] for obs in data["frame_observations"]]
    assert indices == sorted(indices)


def test_max_frames_respected():
    """Test that max_frames is respected."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/analyze?max_frames=3")
    assert response.status_code == 200
    data = response.json()
    assert data["frames_analyzed"] == 3


def test_frame_selection_representative():
    """Test that frame selection is representative, not just first N."""
    service = VideoAnalysisService()
    # Create 10 frame filenames
    frames = [{"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": f"storage/frames/test/frame_{i:06d}.jpg"} for i in range(10)]
    selected = service._select_frames(frames, max_frames=5)
    # Should have 5 frames
    assert len(selected) == 5
    # Should not be just the first 5
    selected_indices = [f["index"] for f in selected]
    # With 10 frames and max=5, should spread across range
    assert selected_indices[0] > 0 or len(selected_indices) == 1


def test_frame_selection_all_frames():
    """Test that selecting all frames works when max_frames >= total."""
    service = VideoAnalysisService()
    frames = [{"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": f"storage/frames/test/frame_{i:06d}.jpg"} for i in range(5)]
    selected = service._select_frames(frames, max_frames=10)
    assert len(selected) == 5


def test_analyze_no_absolute_paths():
    """Test that no absolute filesystem paths are exposed."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/analyze?max_frames=3")
    assert response.status_code == 200
    data = response.json()
    for obs in data["frame_observations"]:
        assert not obs["frame_filename"].startswith("/")
        assert not obs["frame_filename"].startswith("\\")


def test_analyze_analysis_structure():
    """Test that the analysis object has the correct structure."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/analyze?max_frames=3")
    assert response.status_code == 200
    data = response.json()
    analysis = data["analysis"]
    assert "subjects" in analysis
    assert "actions" in analysis
    assert "environment" in analysis
    assert "camera" in analysis
    assert "lighting" in analysis
    assert "visual_style" in analysis
    assert "color_palette" in analysis
    assert "objects" in analysis
    assert isinstance(analysis["camera"], dict)
    assert "perspective" in analysis["camera"]
    assert "shot_type" in analysis["camera"]
    assert "movement" in analysis["camera"]


def test_analyze_no_frames_parameter():
    """Test analyzing without max_frames uses default of 10."""
    stored = _upload_and_extract()
    response = client.post(f"/api/videos/{stored}/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["frames_analyzed"] <= 10