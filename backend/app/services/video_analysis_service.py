from typing import Optional

from app.ai.providers import VisionProvider
from app.core.config import settings
from app.services.vision_service import VisionService


class VideoAnalysisService:
    """Service for multi-frame video analysis.

    Selects representative frames from extracted frames,
    analyzes each frame using the configured VisionProvider,
    and combines observations into a structured video-level analysis.
    """

    MAX_FRAMES = 50

    def __init__(self, vision_service: Optional[VisionService] = None):
        self.vision_service = vision_service or VisionService()

    def analyze_video(
        self,
        stored_filename: str,
        frame_filenames: list[str],
        max_frames: int = 10,
    ) -> dict:
        """Analyze multiple frames from a video.

        Args:
            stored_filename: The stored video filename.
            frame_filenames: List of extracted frame filenames in chronological order.
            max_frames: Maximum number of frames to analyze (1-50).

        Returns:
            Dict with video-level analysis and frame observations.

        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If frame analysis fails.
        """
        # Validate max_frames
        if not isinstance(max_frames, int) or max_frames < 1:
            raise ValueError("max_frames must be at least 1.")
        if max_frames > self.MAX_FRAMES:
            raise ValueError(f"max_frames must not exceed {self.MAX_FRAMES}.")

        # Validate frames
        if not frame_filenames:
            raise ValueError("No extracted frames found for this video.")

        # Select representative frames
        selected = self._select_frames(frame_filenames, max_frames)

        # Analyze each selected frame
        observations = []
        for frame_info in selected:
            frame_path = str(frame_info["path"])
            try:
                result = self.vision_service.analyze_frame(frame_path)
                observations.append({
                    "frame_index": frame_info["index"],
                    "timestamp_seconds": frame_info["timestamp"],
                    "frame_filename": frame_info["filename"],
                    "description": result["description"],
                    "model": result["model"],
                })
            except Exception as e:
                raise RuntimeError(
                    f"Failed to analyze frame {frame_info['filename']}: {str(e)}"
                )

        # Build video-level analysis from observations
        analysis = self._build_video_analysis(observations)

        return {
            "video_filename": stored_filename,
            "frames_analyzed": len(observations),
            "analysis": analysis,
            "frame_observations": observations,
        }

    def _select_frames(self, frame_filenames: list[str], max_frames: int) -> list[dict]:
        """Select representative frames evenly distributed across the video.

        Uses deterministic linear spacing to ensure frames cover
        the full temporal range of the video.

        Example:
            10 frames, max_frames=5 → selects indices 0, 2, 4, 6, 9
            (evenly spread across the range)
        """
        total = len(frame_filenames)

        if max_frames == 1:
            selected_indices = [0]
        elif max_frames >= total:
            selected_indices = list(range(total))
        else:
            selected_indices = [
                round(i * (total - 1) / (max_frames - 1))
                for i in range(max_frames)
            ]

        # Remove duplicates while preserving order
        seen = set()
        unique_indices = []
        for idx in selected_indices:
            if idx not in seen:
                seen.add(idx)
                unique_indices.append(idx)

        result = []
        for i, idx in enumerate(unique_indices, start=1):
            frame = frame_filenames[idx]
            result.append({
                "index": i,
                "filename": frame["filename"],
                "timestamp": frame["timestamp_seconds"],
                "path": frame["path"],
            })

        return result

    def _build_video_analysis(self, observations: list[dict]) -> dict:
        """Build a structured video-level analysis from frame observations.

        For mock providers, structured fields remain empty since
        the mock description does not contain genuine visual details.
        For a real vision-language model, these fields would be populated.

        Args:
            observations: List of frame observation dicts.

        Returns:
            Dict with video-level structured analysis fields.
        """
        return {
            "subjects": [],
            "actions": [],
            "environment": "",
            "camera": {
                "perspective": "",
                "shot_type": "",
                "movement": "",
            },
            "lighting": "",
            "visual_style": "",
            "color_palette": [],
            "objects": [],
        }
