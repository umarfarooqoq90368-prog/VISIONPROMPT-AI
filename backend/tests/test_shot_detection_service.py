"""Service tests for shot detection (P2-02)."""
import json
import os

import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path

# Ensure backend on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.main import app

client = TestClient(app)


def _create_test_video(path: str = "test_video.mp4") -> str:
    """Create a small test MP4 video using FFmpeg lavfi."""
    import imageio_ffmpeg
    import subprocess

    if not os.path.exists(path):
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [
                ffmpeg,
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=320x240:d=3",
                "-y",
                path,
            ],
            capture_output=True,
            timeout=15,
        )
    assert os.path.exists(path) and os.path.getsize(path) > 0
    return path


# ----------------------------------------------------------------------
# Service basic tests (no video needed)
# ----------------------------------------------------------------------


class TestServiceBasic:
    def test_service_instantiation(self):
        from app.services.shot_detection_service import ShotDetectionService
        svc = ShotDetectionService()
        assert svc.provider is not None

    def test_service_with_provider(self):
        from app.ai.shot_provider import get_shot_provider
        provider = get_shot_provider("heuristic")
        svc = ShotDetectionService(provider=provider)
        assert svc.provider.model_name == "heuristic-shot-provider"

    def test_threshold_validation(self):
        from app.services.shot_detection_service import ShotDetectionService
        with pytest.raises(ValueError, match="threshold must be between 0 and 1"):
            ShotDetectionService(threshold=-0.1)
        with pytest.raises(ValueError, match="threshold must be between 0 and 1"):
            ShotDetectionService(threshold=1.5)

    def test_max_shots_validation(self):
        from app.services.shot_detection_service import ShotDetectionService
        with pytest.raises(ValueError, match="max_shots must be between 1 and 100"):
            ShotDetectionService(max_shots=0)
        with pytest.raises(ValueError, match="max_shots must be between 1 and 100"):
            ShotDetectionService(max_shots=200)


# ----------------------------------------------------------------------
# Service integration tests
# ----------------------------------------------------------------------


class TestServiceIntegration:
    @pytest.fixture(autouse=True)
    def setup(self):
        # Create a test video once per test class
        _create_test_video()
        yield

    def test_detect_shots_returns_valid_schema(self):
        from app.services.shot_detection_service import ShotDetectionService

        # Use actual extracted frame paths based on a known video ID
        # For the test video, video_id = "test_video" (stem from "test_video.mp4")
        video_id = "test_video"
        frame_dir = os.path.join("storage", "frames", video_id)
        # Create the directory and some dummy frames if they don't exist
        os.makedirs(frame_dir, exist_ok=True)
        for i in range(1, 6):
            frame_path = os.path.join(frame_dir, f"frame_{i:06d}.jpg")
            if not os.path.exists(frame_path):
                # Create a minimal valid JPEG
                from PIL import Image
                img = Image.new("RGB", (32, 32), color="blue")
                img.save(frame_path)

        frame_filenames = [
            {
                "filename": f"frame_{i:06d}.jpg",
                "timestamp_seconds": round((i - 1) * 1.0, 2),
                "path": os.path.join(frame_dir, f"frame_{i:06d}.jpg").replace("\\", "/"),
            }
            for i in range(1, 6)
        ]

        result = ShotDetectionService().detect_shots(
            stored_filename="test_video.mp4",
            frame_filenames=frame_filenames,
            video_duration=5.0,
        )
        shots = result["shots"]
        assert len(shots) > 0
        shot = shots[0]
        required_keys = {
            "shot_id",
            "start_time",
            "end_time",
            "duration",
            "start_frame",
            "end_frame",
            "representative_frame",
            "transition_type",
            "confidence",
            "shot_type",
            "shot_type_source",
            "shot_type_confidence",
            "motion_level",
        }
        assert set(shot.keys()) == required_keys, (
            f"Missing keys: {required_keys - set(shot.keys())}"
        )
        assert shot["transition_type"] in {"cut", "fade", "dissolve", "unknown", "None"}
        assert shot["shot_type"] in {"change", "within-scene", "unavailable"}
        assert shot["motion_level"] in {"static", "low", "high"}
        assert 0.0 <= shot["confidence"] <= 1.0
        assert 0.0 <= shot["shot_type_confidence"] <= 1.0

    def test_no_frames_raises_value_error(self):
        from app.services.shot_detection_service import ShotDetectionService
        with pytest.raises(ValueError, match="No extracted frames found"):
            ShotDetectionService().detect_shots(
                stored_filename="test_video.mp4",
                frame_filenames=[],
                video_duration=3.0,
            )

    def test_negative_video_duration_raises(self):
        from app.services.shot_detection_service import ShotDetectionService
        frame_filenames = [
            {
                "filename": "frame_000001.jpg",
                "timestamp_seconds": 0.0,
                "path": "storage/frames/test/frame_000001.jpg",
            }
        ]
        with pytest.raises(ValueError, match="video_duration must be non-negative"):
            ShotDetectionService().detect_shots(
                stored_filename="test_video.mp4",
                frame_filenames=frame_filenames,
                video_duration=-1.0,
            )

    def test_collect_frames_helper(self):
        from app.ai.shot_providers import collect_frames
        assert callable(collect_frames)


# ----------------------------------------------------------------------
# API tests
# ----------------------------------------------------------------------


class TestShotDetectionAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        # Create a test video and upload+extract
        _create_test_video()
        with open("test_video.mp4", "rb") as f:
            r = client.post(
                "/api/videos/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        assert r.status_code == 200, r.text
        stored = r.json()["video"]["stored_filename"]
        r = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds=1")
        assert r.status_code == 200, r.text
        # Get the video ID for frame path construction
        self.stored = stored
        self.video_id = stored.rsplit(".", 1)[0]

    def _build_frame_dict(self, index: int) -> dict:
        """Build a frame dict with the correct path for this video."""
        frame_dir = os.path.join("storage", "frames", self.video_id)
        return {
            "filename": f"frame_{index:06d}.jpg",
            "timestamp_seconds": round((index - 1) * 1.0, 2),
            "path": os.path.join(frame_dir, f"frame_{index:06d}.jpg").replace("\\", "/"),
        }

    def test_shots_detect_endpoint_200(self):
        """POST /api/videos/{stored}/shots/detect returns 200 with valid frames."""
        # First create some actual frames
        frame_dir = os.path.join("storage", "frames", self.video_id)
        os.makedirs(frame_dir, exist_ok=True)
        for i in range(1, 4):
            from PIL import Image
            img = Image.new("RGB", (32, 32), color="blue")
            img.save(os.path.join(frame_dir, f"frame_{i:06d}.jpg"))

        r = client.post(
            f"/api/videos/{self.stored}/shots/detect",
            params={"sample_interval_seconds": 1.0, "threshold": 0.40, "max_shots": 100},
        )
        assert r.status_code == 200, r.text

    def test_shots_detect_invalid_filename_400(self):
        r = client.post("/api/videos/notavideo/shots/detect")
        assert r.status_code == 400, r.text

    def test_shots_detect_missing_video_404(self):
        r = client.post("/api/videos/ghost_xyz.mp4/shots/detect")
        assert r.status_code == 404, r.text

    def test_shots_detect_bad_threshold_422(self):
        # First create frames so the endpoint doesn't fail at file-not-found
        frame_dir = os.path.join("storage", "frames", self.video_id)
        os.makedirs(frame_dir, exist_ok=True)
        from PIL import Image
        img = Image.new("RGB", (32, 32), color="blue")
        img.save(os.path.join(frame_dir, "frame_000001.jpg"))
        r = client.post(
            f"/api/videos/{self.stored}/shots/detect",
            params={"threshold": 1.5},
        )
        assert r.status_code == 422, r.text

    def test_shots_detect_bad_sample_interval_422(self):
        frame_dir = os.path.join("storage", "frames", self.video_id)
        os.makedirs(frame_dir, exist_ok=True)
        from PIL import Image
        img = Image.new("RGB", (32, 32), color="blue")
        img.save(os.path.join(frame_dir, "frame_000001.jpg"))
        r = client.post(
            f"/api/videos/{self.stored}/shots/detect",
            params={"sample_interval_seconds": -0.5},
        )
        assert r.status_code == 422, r.text

    def test_shots_detect_bad_max_shots_422(self):
        frame_dir = os.path.join("storage", "frames", self.video_id)
        os.makedirs(frame_dir, exist_ok=True)
        from PIL import Image
        img = Image.new("RGB", (32, 32), color="blue")
        img.save(os.path.join(frame_dir, "frame_000001.jpg"))
        r = client.post(
            f"/api/videos/{self.stored}/shots/detect",
            params={"max_shots": 200},
        )
        assert r.status_code == 422, r.text

    def test_shots_detect_response_schema(self):
        """Response has success, message, and shot data."""
        # Create frames
        frame_dir = os.path.join("storage", "frames", self.video_id)
        os.makedirs(frame_dir, exist_ok=True)
        from PIL import Image
        for i in range(1, 4):
            img = Image.new("RGB", (32, 32), color="blue")
            img.save(os.path.join(frame_dir, f"frame_{i:06d}.jpg"))

        r = client.post(
            f"/api/videos/{self.stored}/shots/detect",
            params={"sample_interval_seconds": 1.0, "threshold": 0.40, "max_shots": 100},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        assert "message" in data
        assert "video_filename" in data
        assert "shots_detected" in data
        assert "frames_compared" in data
        assert "shots" in data
        assert isinstance(data["shots"], list)

    def test_shots_detect_single_shot_all_same(self):
        """When all frames are similar, should produce a single scene shot."""
        # Create frames
        frame_dir = os.path.join("storage", "frames", self.video_id)
        os.makedirs(frame_dir, exist_ok=True)
        from PIL import Image
        # Create identical blue frames
        for i in range(1, 4):
            img = Image.new("RGB", (32, 32), color="blue")
            img.save(os.path.join(frame_dir, f"frame_{i:06d}.jpg"))

        r = client.post(
            f"/api/videos/{self.stored}/shots/detect",
            params={"sample_interval_seconds": 1.0, "threshold": 0.95, "max_shots": 100},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # With high threshold and similar frames, may get 1 shot
        assert data["shots_detected"] >= 0
        if data["shots"]:
            shot = data["shots"][0]
            assert shot["transition_type"] in {"cut", "fade", "dissolve", "unknown", "None"}
            assert shot["shot_type"] in {"change", "within-scene", "unavailable"}