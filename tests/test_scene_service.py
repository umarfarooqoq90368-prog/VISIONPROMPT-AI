"""Tests for the scene detection service."""
import os
import tempfile
import pytest
from PIL import Image
import numpy as np
from app.services.scene_service import (
    SceneDetectionService,
    _frame_difference,
    _load_image_grayscale,
    DEFAULT_THRESHOLD,
    DEFAULT_SAMPLE_INTERVAL,
    MAX_SCENES,
)


def _create_test_frame(path: str, color: tuple = (128, 128, 128)):
    """Create a simple test frame image."""
    img = Image.new("RGB", (64, 64), color)
    img.save(path)


@pytest.fixture
def scene_service():
    return SceneDetectionService()


@pytest.fixture
def scene_service_low_threshold():
    return SceneDetectionService(threshold=0.05)


@pytest.fixture
def scene_service_high_threshold():
    return SceneDetectionService(threshold=0.95)


class TestFrameDifference:
    def test_identical_frames_have_zero_difference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = os.path.join(tmpdir, "frame1.jpg")
            path2 = os.path.join(tmpdir, "frame2.jpg")
            _create_test_frame(path1, (100, 100, 100))
            _create_test_frame(path2, (100, 100, 100))
            score = _frame_difference(path1, path2)
            assert score == 0.0

    def test_different_frames_have_nonzero_difference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = os.path.join(tmpdir, "frame1.jpg")
            path2 = os.path.join(tmpdir, "frame2.jpg")
            _create_test_frame(path1, (0, 0, 0))
            _create_test_frame(path2, (255, 255, 255))
            score = _frame_difference(path1, path2)
            assert score > 0.0

    def test_missing_file_returns_zero(self):
        score = _frame_difference("/nonexistent/1.jpg", "/nonexistent/2.jpg")
        assert score == 0.0


class TestLoadImageGrayscale:
    def test_valid_image_returns_array(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.jpg")
            _create_test_frame(path, (128, 128, 128))
            arr = _load_image_grayscale(path)
            assert arr is not None
            assert arr.shape == (32, 32)
            assert arr.dtype == np.float64

    def test_missing_file_returns_none(self):
        arr = _load_image_grayscale("/nonexistent/image.jpg")
        assert arr is None

    def test_invalid_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.txt")
            with open(path, "w") as f:
                f.write("not an image")
            arr = _load_image_grayscale(path)
            assert arr is None


class TestSceneDetectionCore:
    def test_missing_video_returns_single_scene(self, scene_service):
        result = scene_service.detect_scenes(
            stored_filename="test.mp4",
            frame_filenames=[],
            video_duration=10.0,
        )
        assert result["scenes_detected"] == 1
        assert len(result["scenes"]) == 1
        assert result["scenes"][0]["start_time"] == 0.0
        assert result["scenes"][0]["end_time"] == 10.0

    def test_one_frame_returns_single_scene(self, scene_service):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "frame_000001.jpg")
            _create_test_frame(path)
            result = scene_service.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=[{"filename": "frame_000001.jpg", "timestamp_seconds": 0.0, "path": path}],
                video_duration=1.0,
            )
            assert result["scenes_detected"] == 1

    def test_no_visual_changes_produces_one_scene(self, scene_service):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for i in range(5):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, (128, 128, 128))
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=frames,
                video_duration=5.0,
            )
            assert result["scenes_detected"] == 1

    def test_obvious_visual_changes_produces_multiple_scenes(self, scene_service_low_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            colors = [(0, 0, 0), (255, 255, 255), (0, 0, 0), (255, 255, 255)]
            for i, color in enumerate(colors):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, color)
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=frames,
                video_duration=4.0,
            )
            assert result["scenes_detected"] >= 2

    def test_chronological_ordering(self, scene_service_low_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            colors = [(0, 0, 0), (255, 255, 255), (128, 128, 128), (0, 0, 0)]
            for i, color in enumerate(colors):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, color)
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=frames,
                video_duration=4.0,
            )
            scenes = result["scenes"]
            for i in range(len(scenes) - 1):
                assert scenes[i]["start_time"] < scenes[i]["end_time"]
                assert scenes[i]["end_time"] <= scenes[i + 1]["start_time"]

    def test_no_overlapping_scenes(self, scene_service_low_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            colors = [(0, 0, 0), (255, 255, 255), (0, 0, 0)]
            for i, color in enumerate(colors):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, color)
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=frames,
                video_duration=3.0,
            )
            scenes = result["scenes"]
            for i in range(len(scenes) - 1):
                assert scenes[i]["end_time"] <= scenes[i + 1]["start_time"]

    def test_scene_duration_correctness(self, scene_service_low_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            colors = [(0, 0, 0), (255, 255, 255), (0, 0, 0)]
            for i, color in enumerate(colors):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, color)
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=frames,
                video_duration=3.0,
            )
            for scene in result["scenes"]:
                expected_duration = scene["end_time"] - scene["start_time"]
                assert abs(scene["duration"] - expected_duration) < 0.01

    def test_first_scene_change_score_is_null(self, scene_service_low_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            colors = [(0, 0, 0), (255, 255, 255)]
            for i, color in enumerate(colors):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, color)
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=frames,
                video_duration=2.0,
            )
            assert result["scenes"][0]["change_score_from_previous"] is None

    def test_later_scenes_have_change_score(self, scene_service_low_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            colors = [(0, 0, 0), (255, 255, 255), (0, 0, 0)]
            for i, color in enumerate(colors):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, color)
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=frames,
                video_duration=3.0,
            )
            # First scene has null, second scene has a score
            assert result["scenes"][0]["change_score_from_previous"] is None
            if len(result["scenes"]) > 1:
                assert result["scenes"][1]["change_score_from_previous"] is not None
                assert result["scenes"][1]["change_score_from_previous"] >= 0.0

    def test_representative_frame_exists(self, scene_service_low_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            colors = [(0, 0, 0), (255, 255, 255)]
            for i, color in enumerate(colors):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, color)
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=frames,
                video_duration=2.0,
            )
            for scene in result["scenes"]:
                assert scene["representative_frame"] != ""
                assert scene["representative_frame"].endswith(".jpg")

    def test_final_scene_reaches_video_duration(self, scene_service_low_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            colors = [(0, 0, 0), (255, 255, 255), (0, 0, 0), (255, 255, 255)]
            for i, color in enumerate(colors):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, color)
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=frames,
                video_duration=4.0,
            )
            assert result["scenes"][-1]["end_time"] >= 3.9

    def test_deterministic_output(self, scene_service_low_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for i in range(4):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, (i * 64, i * 64, i * 64))
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result1 = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4", frame_filenames=frames, video_duration=4.0
            )
            result2 = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4", frame_filenames=frames, video_duration=4.0
            )
            assert result1["scenes_detected"] == result2["scenes_detected"]

    def test_max_scene_limit(self, scene_service_high_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            colors = [(i * 255 // 5, i * 255 // 5, i * 255 // 5) for i in range(20)]
            for i, color in enumerate(colors):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path, color)
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service_high_threshold.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=frames,
                video_duration=20.0,
            )
            assert result["scenes_detected"] <= MAX_SCENES

    def test_no_absolute_paths_in_frames(self, scene_service_low_threshold):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for i in range(3):
                path = os.path.join(tmpdir, f"frame_{i:06d}.jpg")
                _create_test_frame(path)
                paths.append(path)

            frames = [
                {"filename": f"frame_{i:06d}.jpg", "timestamp_seconds": float(i), "path": p}
                for i, p in enumerate(paths)
            ]
            result = scene_service_low_threshold.detect_scenes(
                stored_filename="test.mp4", frame_filenames=frames, video_duration=3.0
            )
            for scene in result["scenes"]:
                assert not scene["start_frame"].startswith("/")
                assert not scene["end_frame"].startswith("/")
                assert not scene["representative_frame"].startswith("/")

    def test_single_scene_video_has_correct_defaults(self, scene_service):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "frame_000001.jpg")
            _create_test_frame(path, (128, 128, 128))
            result = scene_service.detect_scenes(
                stored_filename="test.mp4",
                frame_filenames=[{"filename": "frame_000001.jpg", "timestamp_seconds": 0.0, "path": path}],
                video_duration=1.0,
            )
            scene = result["scenes"][0]
            assert scene["start_time"] == 0.0
            assert scene["duration"] > 0
            assert scene["change_score_from_previous"] is None


class TestSceneServiceInitialization:
    def test_default_threshold(self):
        svc = SceneDetectionService()
        assert svc.threshold == DEFAULT_THRESHOLD

    def test_default_sample_interval(self):
        svc = SceneDetectionService()
        assert svc.sample_interval == DEFAULT_SAMPLE_INTERVAL

    def test_default_max_scenes(self):
        svc = SceneDetectionService()
        assert svc.max_scenes == MAX_SCENES

    def test_custom_threshold(self):
        svc = SceneDetectionService(threshold=0.50)
        assert svc.threshold == 0.50

    def test_custom_sample_interval(self):
        svc = SceneDetectionService(sample_interval=2.0)
        assert svc.sample_interval == 2.0
