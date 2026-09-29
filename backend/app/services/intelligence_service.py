"""Unified Video Intelligence Analysis service (Day 12).

Combines Day 6-11 analysis outputs (visual analysis, scene detection,
subject tracking, audio analysis) into one structured response.

Reuses existing services without duplicating their internal logic.
"""

from pathlib import Path
from typing import Optional

from app.services.audio_service import AudioService
from app.services.frame_service import extract_frames, validate_interval
from app.services.scene_service import SceneDetectionService
from app.services.subject_service import SubjectTrackingService
from app.services.video_analysis_service import VideoAnalysisService
from app.utils.ffprobe import extract_metadata

STORAGE_DIR = Path("storage/uploads")
FRAME_STORAGE_DIR = Path("storage/frames")

MAX_FRAMES = 50


class IntelligenceService:
    """Unified orchestration layer combining all analysis outputs.

    Reuses VideoAnalysisService, SceneDetectionService,
    SubjectTrackingService, and AudioService without duplicating
    their internal logic.
    """

    def __init__(
        self,
        analysis_service: Optional[VideoAnalysisService] = None,
        scene_service: Optional[SceneDetectionService] = None,
        subject_service: Optional[SubjectTrackingService] = None,
        audio_service: Optional[AudioService] = None,
    ):
        self.analysis_service = analysis_service or VideoAnalysisService()
        self.scene_service = scene_service or SceneDetectionService()
        self.subject_service = subject_service or SubjectTrackingService()
        self.audio_service = audio_service or AudioService()

    def analyze(
        self,
        stored_filename: str,
        max_frames: int = 10,
    ) -> dict:
        """Run unified intelligence analysis on an uploaded video.

        Args:
            stored_filename: The stored video filename.
            max_frames: Maximum number of frames to analyze (1-50).

        Returns:
            Dict with unified visual, scene, subject, and audio data.

        Raises:
            ValueError: If parameters are invalid or video not found.
            RuntimeError: If any analysis step fails.
        """
        if not isinstance(max_frames, int) or max_frames < 1:
            raise ValueError("max_frames must be at least 1.")
        if max_frames > MAX_FRAMES:
            raise ValueError(f"max_frames must not exceed {MAX_FRAMES}.")

        video_path = self._get_video_path(stored_filename)
        video_id = stored_filename.rsplit(".", 1)[0]
        frame_dir = FRAME_STORAGE_DIR / video_id

        # Get video duration
        try:
            metadata = extract_metadata(video_path)
            duration = metadata["duration_seconds"]
        except Exception:
            duration = None

        # Build frame filenames list
        frame_filenames = []
        if frame_dir.exists():
            frame_files = sorted(f for f in frame_dir.glob("frame_*.jpg") if f.is_file())
            for i, fpath in enumerate(frame_files, start=1):
                frame_filenames.append({
                    "index": i,
                    "filename": fpath.name,
                    "timestamp_seconds": round((i - 1) * 1.0, 2),
                    "path": str(fpath),
                })

        # --- Visual Analysis (Day 6) ---
        visual_result = self._run_visual_analysis(stored_filename, frame_filenames, max_frames)
        visual = visual_result["visual"]
        frame_observations = visual_result["frame_observations"]

        # --- Scene Detection (Day 9) ---
        scenes = self._run_scene_detection(stored_filename, frame_filenames, duration or 0.0)

        # --- Subject Tracking (Day 10) ---
        subjects = self._run_subject_tracking(frame_observations)

        # --- Audio Analysis (Day 11) ---
        audio = self._run_audio_analysis(stored_filename)

        return {
            "video_filename": stored_filename,
            "duration_seconds": round(duration, 2) if duration is not None else None,
            "visual": visual,
            "scenes": scenes,
            "subjects": subjects,
            "audio": audio,
        }

    def _get_video_path(self, stored_filename: str) -> Path:
        """Get the full path to an uploaded video with path traversal protection."""
        filepath = (STORAGE_DIR / stored_filename).resolve()
        storage_root = STORAGE_DIR.resolve()
        if not str(filepath).startswith(str(storage_root)) or not filepath.exists():
            raise ValueError("Video file not found.")
        return filepath

    def _run_visual_analysis(self, stored_filename, frame_filenames, max_frames):
        """Run VideoAnalysisService and return visual dict + frame_observations."""
        if not frame_filenames:
            return {
                "visual": {
                    "frames_analyzed": 0,
                    "subjects": [],
                    "actions": [],
                    "environment": "",
                    "camera": {"perspective": "", "shot_type": "", "movement": ""},
                    "lighting": "",
                    "visual_style": "",
                    "color_palette": [],
                    "objects": [],
                },
                "frame_observations": [],
            }

        try:
            result = self.analysis_service.analyze_video(
                stored_filename=stored_filename,
                frame_filenames=frame_filenames,
                max_frames=max_frames,
            )
            analysis = result.get("analysis", {})
            observations = result.get("frame_observations", [])
            visual = {
                "frames_analyzed": result.get("frames_analyzed", 0),
                "subjects": analysis.get("subjects", []),
                "actions": analysis.get("actions", []),
                "environment": analysis.get("environment", ""),
                "camera": analysis.get("camera", {"perspective": "", "shot_type": "", "movement": ""}),
                "lighting": analysis.get("lighting", ""),
                "visual_style": analysis.get("visual_style", ""),
                "color_palette": analysis.get("color_palette", []),
                "objects": analysis.get("objects", []),
            }
            return {"visual": visual, "frame_observations": observations}
        except Exception:
            return {
                "visual": {
                    "frames_analyzed": 0,
                    "subjects": [],
                    "actions": [],
                    "environment": "",
                    "camera": {"perspective": "", "shot_type": "", "movement": ""},
                    "lighting": "",
                    "visual_style": "",
                    "color_palette": [],
                    "objects": [],
                },
                "frame_observations": [],
            }

    def _run_scene_detection(self, stored_filename, frame_filenames, video_duration):
        """Run SceneDetectionService and return the scenes dict."""
        if not frame_filenames:
            return {
                "scenes_detected": 0,
                "timeline": [],
            }

        try:
            result = self.scene_service.detect_scenes(
                stored_filename=stored_filename,
                frame_filenames=frame_filenames,
                video_duration=video_duration,
            )
            scenes = result.get("scenes", [])
            for scene in scenes:
                for key in ["start_frame", "end_frame", "representative_frame"]:
                    val = scene.get(key, "")
                    if val.startswith("/") or val.startswith("\\"):
                        scene[key] = val.split("\\")[-1].split("/")[-1]
            return {
                "scenes_detected": result.get("scenes_detected", 0),
                "timeline": scenes,
            }
        except Exception:
            return {
                "scenes_detected": 0,
                "timeline": [],
            }

    def _run_subject_tracking(self, frame_observations):
        """Run SubjectTrackingService and return the subjects dict."""
        if not frame_observations:
            return {
                "subjects_detected": 0,
                "profiles": [],
            }

        try:
            result = self.subject_service.analyze_observations(
                frame_observations=frame_observations,
                analysis_subjects=[],
                analysis_actions=[],
            )
            return {
                "subjects_detected": result.get("subjects_detected", 0),
                "profiles": result.get("subjects", []),
            }
        except Exception:
            return {
                "subjects_detected": 0,
                "profiles": [],
            }

    def _run_audio_analysis(self, stored_filename):
        """Run AudioService and return the audio dict."""
        try:
            result = self.audio_service.analyze_audio(stored_filename)
            return {
                "has_audio": result.get("has_audio", False),
                "duration_seconds": result.get("duration_seconds", 0),
                "audio_format": result.get("audio_format", ""),
                "sample_rate": result.get("sample_rate", 16000),
                "channels": result.get("channels", 1),
                "transcription": result.get("transcription", {
                    "language": "",
                    "text": "",
                    "segments": [],
                    "provider": "mock",
                }),
                "provider": result.get("provider", "mock"),
            }
        except Exception:
            return {
                "has_audio": False,
                "duration_seconds": 0,
                "audio_format": "",
                "sample_rate": 16000,
                "channels": 1,
                "transcription": {
                    "language": "",
                    "text": "",
                    "segments": [],
                    "provider": "mock",
                },
                "provider": "mock",
            }
