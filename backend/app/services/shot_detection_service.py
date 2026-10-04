import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any

from PIL import Image

from app.ai.shot_provider import ShotBoundaryProvider, get_shot_provider as _get_shot_provider
from app.ai.shot_providers import collect_frames


class ShotDetectionService:
    """Detect shot boundaries in a video using extracted frames.

    Uses heuristic image comparison (RGB histogram + pixel difference)
    to identify shot boundaries. Does NOT require AI model inference.

    The service operates on pre-extracted frames and produces a structured
    shot detection report with transition types, confidence, and motion levels.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        provider: Optional[ShotBoundaryProvider] = None,
        threshold: float = 0.40,
        max_shots: int = 100,
    ):
        if provider is None:
            provider = _get_shot_provider("heuristic")
        if not isinstance(provider, ShotBoundaryProvider):
            raise ValueError("provider must be a ShotBoundaryProvider instance.")
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1.")
        if not 1 <= max_shots <= 100:
            raise ValueError("max_shots must be between 1 and 100.")
        self.provider = provider
        self.threshold = threshold
        self.max_shots = max_shots

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_shots(
        self,
        stored_filename: str,
        frame_filenames: Optional[List[Dict[str, Any]]] = None,
        video_duration: float = 0.0,
    ) -> Dict[str, Any]:
        """Detect shot boundaries from extracted frames.

        Args:
            stored_filename: The stored video filename.
            frame_filenames: List of frame dicts with ``filename``,
                ``timestamp_seconds``, and ``path`` keys, sorted
                chronologically. If ``None``, frames are collected
                automatically from the frame storage directory.
            video_duration: Total video duration in seconds. Used when
                frame_filenames is None or for clamping end times.

        Returns:
            A dict with the following top-level keys:

            - ``video_filename``: The stored filename.
            - ``duration_seconds``: Video duration.
            - ``method``: Dict with ``approach``, ``provider``,
              ``threshold``, ``semantic_accuracy_claimed``,
              and ``limitations``.
            - ``frames_compared``: Number of frame pairs compared.
            - ``shots_detected``: Integer count of shots detected.
            - ``shots[]``: List of shot dicts (see shot schema below).

        Raises:
            ValueError: If no frames are available, threshold/max_shots
              are out of range, or frame data is invalid.
        """
        if frame_filenames is None:
            frame_filenames = collect_frames(stored_filename)

        if not frame_filenames:
            raise ValueError(
                "No extracted frames found for this video. Extract frames first."
            )

        if video_duration < 0:
            raise ValueError("video_duration must be non-negative.")

        # Validate frame data
        valid_frames = []
        for i, f in enumerate(frame_filenames):
            if not isinstance(f, dict):
                raise ValueError(f"Invalid frame data at index {i}.")
            if "filename" not in f or "timestamp_seconds" not in f:
                raise ValueError(
                    f"Frame {i} missing required keys (filename, timestamp_seconds)."
                )
            if not isinstance(f["filename"], str) or not f["filename"]:
                raise ValueError(f"Frame {i} has an invalid filename.")
            if not isinstance(f["timestamp_seconds"], (int, float)):
                raise ValueError(f"Frame {i} has an invalid timestamp.")
            valid_frames.append(f)

        frames_compared = 0
        shots: List[Dict[str, Any]] = []

        # Threshold for motion-level classification
        static_threshold = 0.05
        low_threshold = 0.15

        # Iterate consecutive frame pairs
        for i in range(1, len(valid_frames)):
            if len(shots) >= self.max_shots:
                break

            prev_frame = valid_frames[i - 1]
            curr_frame = valid_frames[i]

            try:
                score = self.provider.compare(
                    prev_frame["path"], curr_frame["path"]
                )
            except ValueError:
                raise ValueError(f"Invalid frame data at index {i}.")

            frames_compared += 1

            shot_type = "unavailable"
            shot_type_confidence = 0.0
            motion_level = "static"
            transition_type = "unknown"
            confidence = 0.5

            if i > 1:
                prev_prev_frame = valid_frames[i - 2]
                try:
                    prev_score = self.provider.compare(
                        prev_prev_frame["path"], prev_frame["path"]
                    )
                except ValueError:
                    prev_score = self.threshold
                transition_type = self.provider.infer_shot_type(
                    prev_score, score, prev_change_score=None
                )

            # Determine motion level from pixel difference
            # (reuse provider.compare for a rough motion measure)
            try:
                motion_score = self.provider.compare(
                    prev_frame["path"], curr_frame["path"]
                )
            except ValueError:
                motion_score = 1.0

            if motion_score < static_threshold:
                motion_level = "static"
            elif motion_score < low_threshold:
                motion_level = "low"
            else:
                motion_level = "high"

            # Determine shot_type when sufficiently different
            if score >= self.threshold:
                shot_type = "change"
                shot_type_confidence = min(score, 1.0)
                confidence = min(score * 0.8 + 0.2, 1.0)
            else:
                shot_type = "within-scene"
                confidence = 1.0 - score * 0.5

            # Compute shot duration and times
            start_time = prev_frame["timestamp_seconds"]
            end_time = curr_frame["timestamp_seconds"]
            duration = end_time - start_time

            # Clamp duration to video_duration if available
            if video_duration > 0 and end_time > video_duration:
                end_time = video_duration
                duration = end_time - start_time

            shot = {
                "shot_id": i,
                "start_time": round(start_time, 4),
                "end_time": round(end_time, 4),
                "duration": round(max(duration, 0.0), 4),
                "start_frame": prev_frame["filename"],
                "end_frame": curr_frame["filename"],
                "representative_frame": curr_frame["filename"],
                "transition_type": transition_type,
                "confidence": round(confidence, 4),
                "shot_type": shot_type,
                "shot_type_source": "unavailable",
                "shot_type_confidence": round(shot_type_confidence, 4),
                "motion_level": motion_level,
            }
            shots.append(shot)

        # If no shots were detected (all frames within scene), create a single scene shot
        if not shots:
            first = valid_frames[0]
            last = valid_frames[-1]
            shots.append(
                {
                    "shot_id": 1,
                    "start_time": round(first["timestamp_seconds"], 4),
                    "end_time": round(video_duration if video_duration > 0 else last["timestamp_seconds"], 4),
                    "duration": round(
                        max((video_duration if video_duration > 0 else last["timestamp_seconds"])
                            - first["timestamp_seconds"], 0.0), 4
                    ),
                    "start_frame": first["filename"],
                    "end_frame": last["filename"],
                    "representative_frame": last["filename"],
                    "transition_type": "None",
                    "confidence": 1.0,
                    "shot_type": "unavailable",
                    "shot_type_source": "unavailable",
                    "shot_type_confidence": 0.0,
                    "motion_level": "static",
                }
            )

        return {
            "video_filename": stored_filename,
            "duration_seconds": round(video_duration, 4) if video_duration > 0 else round(valid_frames[-1]["timestamp_seconds"], 4),
            "method": {
                "approach": "heuristic",
                "provider": self.provider.model_name,
                "threshold": self.threshold,
                "semantic_accuracy_claimed": False,
                "limitations": [
                    "Heuristic comparison based on RGB histogram and pixel difference",
                    "No semantic content understanding",
                    "Performance depends on frame sampling interval and quality",
                    "May misclassify complex transitions",
                ],
            },
            "frames_compared": frames_compared,
            "shots_detected": len(shots),
            "shots": shots,
        }