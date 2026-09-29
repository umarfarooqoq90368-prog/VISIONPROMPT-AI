"""Tests for the unified intelligence service."""
import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services.intelligence_service import IntelligenceService
from app.services.video_analysis_service import VideoAnalysisService
from app.services.scene_service import SceneDetectionService
from app.services.subject_service import SubjectTrackingService
from app.services.audio_service import AudioService

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


@pytest.fixture
def intelligence_service():
    return IntelligenceService()


class TestIntelligenceService:
    def test_valid_video(self, intelligence_service):
        """Valid video should return unified response with all sections."""
        storage_dir = Path("storage/uploads")
        storage_dir.mkdir(parents=True, exist_ok=True)
        video_path = storage_dir / "intelligence_test.mp4"
        import imageio_ffmpeg, subprocess
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2", "-y", str(video_path)],
            capture_output=True, timeout=10,
        )
        result = intelligence_service.analyze("intelligence_test.mp4")
        assert "video_filename" in result
        assert "visual" in result
        assert "scenes" in result
        assert "subjects" in result
        assert "audio" in result
        if video_path.exists():
            video_path.unlink()

    def test_nonexistent_video(self, intelligence_service):
        """Nonexistent video should raise ValueError."""
        with pytest.raises(ValueError):
            intelligence_service.analyze("nonexistent.mp4")

    def test_path_traversal(self, intelligence_service):
        """Path traversal attempts should raise ValueError."""
        with pytest.raises(ValueError):
            intelligence_service.analyze("../../../etc/passwd")

    def test_no_frames(self, intelligence_service):
        """Video with no extracted frames should return empty sections."""
        storage_dir = Path("storage/uploads")
        storage_dir.mkdir(parents=True, exist_ok=True)
        video_path = storage_dir / "no_frames_test.mp4"
        import imageio_ffmpeg, subprocess
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2", "-y", str(video_path)],
            capture_output=True, timeout=10,
        )
        result = intelligence_service.analyze("no_frames_test.mp4")
        assert result["visual"]["frames_analyzed"] == 0
        assert result["scenes"]["scenes_detected"] == 0
        assert result["subjects"]["subjects_detected"] == 0
        if video_path.exists():
            video_path.unlink()

    def test_max_frames_handling(self, intelligence_service):
        """max_frames should be validated."""
        with pytest.raises(ValueError):
            intelligence_service.analyze("test.mp4", max_frames=0)
        with pytest.raises(ValueError):
            intelligence_service.analyze("test.mp4", max_frames=51)

    def test_audio_available(self, intelligence_service):
        """Video with audio should return has_audio=True in audio section."""
        storage_dir = Path("storage/uploads")
        storage_dir.mkdir(parents=True, exist_ok=True)
        video_path = storage_dir / "audio_test.mp4"
        import imageio_ffmpeg, subprocess
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
             "-c:v", "libx264", "-c:a", "aac", "-y", str(video_path)],
            capture_output=True, timeout=10,
        )
        result = intelligence_service.analyze("audio_test.mp4")
        assert "audio" in result
        assert result["audio"]["has_audio"] is True
        if video_path.exists():
            video_path.unlink()

    def test_no_audio(self, intelligence_service):
        """Video without audio should return has_audio=False."""
        storage_dir = Path("storage/uploads")
        storage_dir.mkdir(parents=True, exist_ok=True)
        video_path = storage_dir / "no_audio_test.mp4"
        import imageio_ffmpeg, subprocess
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2", "-y", str(video_path)],
            capture_output=True, timeout=10,
        )
        result = intelligence_service.analyze("no_audio_test.mp4")
        assert result["audio"]["has_audio"] is False
        if video_path.exists():
            video_path.unlink()

    def test_unified_response_structure(self, intelligence_service):
        """Unified response should have all required top-level keys."""
        storage_dir = Path("storage/uploads")
        storage_dir.mkdir(parents=True, exist_ok=True)
        video_path = storage_dir / "structure_test.mp4"
        import imageio_ffmpeg, subprocess
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2", "-y", str(video_path)],
            capture_output=True, timeout=10,
        )
        result = intelligence_service.analyze("structure_test.mp4")
        assert "video_filename" in result
        assert "duration_seconds" in result
        assert "visual" in result
        assert "scenes" in result
        assert "subjects" in result
        assert "audio" in result
        # Check visual sub-keys
        visual = result["visual"]
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
        assert "scenes_detected" in result["scenes"]
        assert "timeline" in result["scenes"]
        # Check subjects sub-keys
        assert "subjects_detected" in result["subjects"]
        assert "profiles" in result["subjects"]
        # Check audio sub-keys
        audio = result["audio"]
        assert "has_audio" in audio
        assert "transcription" in audio
        assert "provider" in audio
        if video_path.exists():
            video_path.unlink()

    def test_no_fabricated_values(self, intelligence_service):
        """Mock providers should not fabricate visual information."""
        storage_dir = Path("storage/uploads")
        storage_dir.mkdir(parents=True, exist_ok=True)
        video_path = storage_dir / "fabrication_test.mp4"
        import imageio_ffmpeg, subprocess
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2", "-y", str(video_path)],
            capture_output=True, timeout=10,
        )
        result = intelligence_service.analyze("fabrication_test.mp4")
        visual = result["visual"]
        assert visual["subjects"] == []
        assert visual["actions"] == []
        assert visual["environment"] == ""
        assert visual["objects"] == []
        assert visual["color_palette"] == []
        if video_path.exists():
            video_path.unlink()

    def test_visual_analysis_integration(self, intelligence_service):
        """Visual analysis should be properly integrated."""
        storage_dir = Path("storage/uploads")
        storage_dir.mkdir(parents=True, exist_ok=True)
        video_path = storage_dir / "visual_test.mp4"
        import imageio_ffmpeg, subprocess
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2", "-y", str(video_path)],
            capture_output=True, timeout=10,
        )
        result = intelligence_service.analyze("visual_test.mp4")
        assert isinstance(result["visual"]["frames_analyzed"], int)
        assert isinstance(result["visual"]["camera"], dict)
        if video_path.exists():
            video_path.unlink()

    def test_scene_integration(self, intelligence_service):
        """Scene detection should be properly integrated."""
        storage_dir = Path("storage/uploads")
        storage_dir.mkdir(parents=True, exist_ok=True)
        video_path = storage_dir / "scene_test.mp4"
        import imageio_ffmpeg, subprocess
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2", "-y", str(video_path)],
            capture_output=True, timeout=10,
        )
        result = intelligence_service.analyze("scene_test.mp4")
        assert isinstance(result["scenes"]["scenes_detected"], int)
        assert isinstance(result["scenes"]["timeline"], list)
        if video_path.exists():
            video_path.unlink()

    def test_subject_integration(self, intelligence_service):
        """Subject tracking should be properly integrated."""
        storage_dir = Path("storage/uploads")
        storage_dir.mkdir(parents=True, exist_ok=True)
        video_path = storage_dir / "subject_test.mp4"
        import imageio_ffmpeg, subprocess
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2", "-y", str(video_path)],
            capture_output=True, timeout=10,
        )
        result = intelligence_service.analyze("subject_test.mp4")
        assert isinstance(result["subjects"]["subjects_detected"], int)
        assert isinstance(result["subjects"]["profiles"], list)
        if video_path.exists():
            video_path.unlink()
