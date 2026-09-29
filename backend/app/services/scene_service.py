"""Scene detection service for video timeline generation.

Uses deterministic frame-level visual difference heuristics to identify
likely scene boundaries. Does NOT require AI model inference.

The algorithm:
1. Sample frames at a configurable interval.
2. Compare consecutive sampled frames using pixel-level difference.
3. When the difference exceeds a threshold, mark a scene boundary.
4. Group frames into scenes and compute representative frames.
"""

from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from app.core.config import settings

MAX_SCENES = 100
DEFAULT_SAMPLE_INTERVAL = 1.0
DEFAULT_THRESHOLD = 0.30
DEFAULT_TARGET_SIZE = (32, 32)


def _load_image_grayscale(path: str) -> Optional[np.ndarray]:
    """Load an image as a normalized grayscale NumPy array.

    Returns None if the image cannot be loaded.
    """
    try:
        img = Image.open(path).convert("L")
        img = img.resize(DEFAULT_TARGET_SIZE)
        return np.array(img, dtype=np.float64) / 255.0
    except Exception:
        return None


def _frame_difference(path1: str, path2: str) -> float:
    """Calculate normalized visual difference between two frames.

    Returns a value between 0.0 (identical) and ~2.0 (completely different).
    """
    arr1 = _load_image_grayscale(path1)
    arr2 = _load_image_grayscale(path2)

    if arr1 is None or arr2 is None:
        return 0.0

    if arr1.shape != arr2.shape:
        return 0.0

    diff = np.abs(arr1 - arr2).mean()
    return float(diff)


class SceneDetectionService:
    """Detects visual scene boundaries in a video using frame-level differences.

    Uses deterministic heuristics based on pixel-level frame comparison.
    Does NOT provide semantic scene understanding.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        sample_interval: float = DEFAULT_SAMPLE_INTERVAL,
        max_scenes: int = MAX_SCENES,
    ):
        self.threshold = threshold
        self.sample_interval = sample_interval
        self.max_scenes = max_scenes

    def detect_scenes(
        self,
        stored_filename: str,
        frame_filenames: list[dict],
        video_duration: float = 0.0,
    ) -> dict:
        """Detect scenes from a list of extracted frames.

        Args:
            stored_filename: The stored video filename.
            frame_filenames: List of frame dicts with 'filename',
                'timestamp_seconds', and 'path' keys, sorted chronologically.
            video_duration: Total video duration in seconds.

        Returns:
            Dict with scene timeline metadata.
        """
        if not frame_filenames:
            return {
                "video_filename": stored_filename,
                "duration_seconds": video_duration,
                "scenes_detected": 1,
                "scenes": [self._single_scene(stored_filename, video_duration)],
            }

        # Sample frames at the configured interval
        sampled = self._sample_frames(frame_filenames)

        if len(sampled) <= 1:
            return {
                "video_filename": stored_filename,
                "duration_seconds": video_duration,
                "scenes_detected": 1,
                "scenes": [self._build_scene(stored_filename, sampled, video_duration, None)],
            }

        # Detect scene boundaries
        boundaries = []
        for i in range(1, len(sampled)):
            score = _frame_difference(
                sampled[i - 1]["path"], sampled[i]["path"]
            )
            if score >= self.threshold:
                boundaries.append((i, score))

        # Group frames into scenes based on boundaries
        scenes = self._build_scenes(stored_filename, sampled, boundaries, video_duration)

        # First scene always has null change_score
        if scenes:
            scenes[0]["change_score_from_previous"] = None

        # Enforce maximum scene limit
        if len(scenes) > self.max_scenes:
            # Merge last scenes to stay within limit
            scenes = self._merge_scenes(scenes, self.max_scenes, video_duration)

        # Ensure last scene ends at video_duration
        if scenes and video_duration > 0:
            scenes[-1]["end_time"] = round(video_duration, 4)
            scenes[-1]["duration"] = round(
                video_duration - scenes[-1]["start_time"], 4
            )

        return {
            "video_filename": stored_filename,
            "duration_seconds": video_duration,
            "scenes_detected": len(scenes),
            "scenes": scenes,
        }

    def _sample_frames(self, frame_filenames: list[dict]) -> list[dict]:
        """Sample frames at the configured interval."""
        if self.sample_interval <= 0:
            return frame_filenames[:]

        sampled = []
        for frame in frame_filenames:
            ts = frame["timestamp_seconds"]
            if abs(ts - round(ts / self.sample_interval) * self.sample_interval) < 0.01:
                sampled.append(frame)

        # If no frames matched the interval, use all frames
        if not sampled:
            return frame_filenames[:]

        return sampled

    def _build_scenes(
        self,
        stored_filename: str,
        sampled: list[dict],
        boundaries: list[tuple[int, float]],
        video_duration: float,
    ) -> list[dict]:
        """Group sampled frames into scenes based on detected boundaries."""
        if not boundaries:
            return [self._build_scene(stored_filename, sampled, video_duration, None)]

        scenes = []
        start_idx = 0

        for boundary_idx, score in boundaries:
            if len(scenes) >= self.max_scenes - 1:
                break

            scene_frames = sampled[start_idx:boundary_idx]
            if scene_frames:
                scenes.append(
                    self._build_scene(
                        stored_filename, scene_frames, video_duration, score
                    )
                )
            start_idx = boundary_idx

        # Add final scene
        remaining = sampled[start_idx:]
        if remaining:
            scenes.append(
                self._build_scene(stored_filename, remaining, video_duration, None)
            )
        elif not scenes:
            scenes.append(
                self._build_scene(stored_filename, sampled, video_duration, None)
            )

        return scenes

    def _build_scene(
        self,
        stored_filename: str,
        scene_frames: list[dict],
        video_duration: float,
        change_score: Optional[float],
    ) -> dict:
        """Build a single scene dict from a list of frame dicts."""
        if not scene_frames:
            return {
                "scene_id": 0,
                "start_time": 0.0,
                "end_time": video_duration,
                "duration": video_duration,
                "start_frame": "",
                "end_frame": "",
                "representative_frame": "",
                "change_score_from_previous": change_score,
            }

        start_time = scene_frames[0]["timestamp_seconds"]
        end_time = scene_frames[-1]["timestamp_seconds"]

        if abs(end_time - start_time) < 0.01:
            end_time = start_time + 0.1

        # Clamp end_time to video duration
        if video_duration > 0 and end_time > video_duration:
            end_time = video_duration

        duration = end_time - start_time
        if duration < 0.01:
            duration = 0.01

        # Representative frame = middle frame of scene
        mid = len(scene_frames) // 2
        rep_frame = scene_frames[mid]["filename"]

        return {
            "scene_id": 0,  # Will be set by caller
            "start_time": round(start_time, 4),
            "end_time": round(end_time, 4),
            "duration": round(duration, 4),
            "start_frame": scene_frames[0]["filename"],
            "end_frame": scene_frames[-1]["filename"],
            "representative_frame": rep_frame,
            "change_score_from_previous": change_score,
        }

    def _single_scene(
        self, stored_filename: str, video_duration: float
    ) -> dict:
        """Create a single scene covering the entire video."""
        return {
            "scene_id": 0,
            "start_time": 0.0,
            "end_time": round(video_duration, 4),
            "duration": round(video_duration, 4),
            "start_frame": "",
            "end_frame": "",
            "representative_frame": "",
            "change_score_from_previous": None,
        }

    def _merge_scenes(
        self, scenes: list[dict], max_scenes: int, video_duration: float
    ) -> list[dict]:
        """Merge scenes to stay within max_scenes limit."""
        while len(scenes) > max_scenes:
            # Merge the two smallest adjacent scenes
            min_idx = 0
            min_size = float("inf")
            for i in range(len(scenes) - 1):
                size = scenes[i]["duration"] + scenes[i + 1]["duration"]
                if size < min_size:
                    min_size = size
                    min_idx = i

            # Merge scenes[min_idx] and scenes[min_idx+1]
            merged = {
                "scene_id": 0,
                "start_time": scenes[min_idx]["start_time"],
                "end_time": scenes[min_idx + 1]["end_time"],
                "duration": scenes[min_idx + 1]["end_time"] - scenes[min_idx]["start_time"],
                "start_frame": scenes[min_idx]["start_frame"],
                "end_frame": scenes[min_idx + 1]["end_frame"],
                "representative_frame": scenes[min_idx]["representative_frame"],
                "change_score_from_previous": scenes[min_idx]["change_score_from_previous"],
            }
            scenes = scenes[:min_idx] + [merged] + scenes[min_idx + 2:]

        # Re-number scene IDs
        for i, scene in enumerate(scenes):
            scene["scene_id"] = i + 1
            if i == 0:
                scene["change_score_from_previous"] = None

        return scenes
