"""Video-to-Video Prompt Reconstruction service (Phase 2, P2-01).

Reconstructs a structured production-ready prompt and a domain-by-domain
analysis report directly from a stored video by reusing existing services:

- Day 9/12: unified intelligence (scenes, subjects, audio, vision fields)
- Day 13: advanced prompt generation (production prompt + sections)
- Day 21: prompt quality analysis
- Day 24: prompt readiness validation
- P2-02..P2-06: optional specialized services when wired

AI safety rules followed here:

- Every domain block reports availability as one of ``observed``,
  ``estimated``, or ``unavailable``.
- Nothing is fabricated: empty intelligence fields become
  ``unavailable`` blocks with an explicit note instead of invented text.
- Provider configuration is surfaced through ``provider_status`` so
  callers can tell when a local mock provider produced the analysis.
"""

from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.advanced_prompt_service import AdvancedPromptService, VALID_STYLES
from app.services.intelligence_service import IntelligenceService
from app.services.prompt_quality_service import PromptQualityService
from app.services.prompt_readiness_service import PromptReadinessService
from app.utils.ffprobe import extract_metadata

STORAGE_DIR = Path("storage/uploads")

VALID_DEPTHS = ("quick", "standard", "deep")
DEPTH_MAX_FRAMES = {"quick": 2, "standard": 10, "deep": 25}

OBSERVED = "observed"
ESTIMATED = "estimated"
UNAVAILABLE = "unavailable"

_NO_STRUCTURED_VISION = (
    "The vision provider returned no structured details for this domain."
)
_NO_LENS = (
    "Lens estimation is not available from any configured provider."
)
_NO_COLOR = (
    "Color analysis is not available from any configured provider."
)
_NO_CHARACTERS = (
    "Character consistency analysis is not available from any configured "
    "provider."
)
_NO_TRANSCRIPTION = (
    "Speech transcription is not available from the configured audio provider."
)


def _block(availability, source, value=None, confidence=None, note=""):
    """Uniform provenance block used by every reconstruction domain."""
    return {
        "availability": availability,
        "source": source,
        "value": value,
        "confidence": confidence,
        "note": note,
    }


class VideoReconstructionService:
    """Reconstruct a production prompt + structured report from a video."""

    def __init__(
        self,
        intelligence_service: Optional[IntelligenceService] = None,
        advanced_prompt_service: Optional[AdvancedPromptService] = None,
        quality_service: Optional[PromptQualityService] = None,
        readiness_service: Optional[PromptReadinessService] = None,
        shot_detection_service=None,
        camera_estimation_service=None,
        color_analysis_service=None,
        emotion_action_service=None,
        character_consistency_service=None,
    ):
        self.intelligence_service = (
            intelligence_service or IntelligenceService()
        )
        self.advanced_prompt_service = (
            advanced_prompt_service or AdvancedPromptService()
        )
        self.quality_service = quality_service or PromptQualityService()
        self.readiness_service = readiness_service or PromptReadinessService(
            self.quality_service
        )
        self.shot_detection_service = shot_detection_service
        self.camera_estimation_service = camera_estimation_service
        self.color_analysis_service = color_analysis_service
        self.emotion_action_service = emotion_action_service
        self.character_consistency_service = character_consistency_service

    def reconstruct(
        self,
        stored_filename: str,
        depth: str = "standard",
        style: str = "cinematic",
    ) -> dict:
        """Reconstruct analysis + production prompt from one stored video.

        Args:
            stored_filename: Stored video filename inside storage/uploads.
            depth: Analysis depth - quick, standard, or deep. Controls how
                many frames are analyzed (2, 10, or 25).
            style: Prompt style - cinematic, realistic, or commercial.

        Returns:
            Dict with video_filename, depth, style, video_information,
            analysis, provider_status, confidence, prompt, quality,
            readiness.

        Raises:
            ValueError: Invalid depth/style, missing video, or an
                upstream service rejected its input.
        """
        if depth not in VALID_DEPTHS:
            raise ValueError(
                "Invalid depth. Must be one of: "
                f"{', '.join(sorted(VALID_DEPTHS))}"
            )
        if style not in VALID_STYLES:
            raise ValueError(
                "Invalid style. Must be one of: "
                f"{', '.join(sorted(VALID_STYLES))}"
            )

        filepath = self._resolve_video(stored_filename)
        metadata = extract_metadata(filepath)

        intelligence = self.intelligence_service.analyze(
            stored_filename=stored_filename,
            max_frames=DEPTH_MAX_FRAMES[depth],
        )

        advanced = self.advanced_prompt_service.generate_prompt(
            intelligence=intelligence,
            style=style,
        )

        analysis = self._build_analysis(intelligence, advanced)
        provider_status = self._provider_status(intelligence, analysis)
        confidence = self._confidence_summary(analysis, provider_status)

        production_prompt = advanced["prompt"]
        quality = self.quality_service.analyze_prompt(production_prompt)
        readiness = self.readiness_service.validate_prompt(production_prompt)

        return {
            "video_filename": stored_filename,
            "depth": depth,
            "style": style,
            "video_information": _block(
                OBSERVED, "ffprobe", value=metadata, confidence="high"
            ),
            "analysis": analysis,
            "provider_status": provider_status,
            "confidence": confidence,
            "prompt": {
                "production_prompt": production_prompt,
                "negative_prompt": advanced["negative_prompt"],
                "style": style,
                "sections": advanced["sections"],
                "source": "advanced_prompt_service",
            },
            "quality": quality["quality"],
            "readiness": readiness["readiness"],
        }

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_video(stored_filename: str) -> Path:
        storage_root = STORAGE_DIR.resolve()
        filepath = (STORAGE_DIR / stored_filename).resolve()
        if not str(filepath).startswith(str(storage_root)):
            raise ValueError("Video file not found.")
        if not filepath.exists():
            raise ValueError("Video file not found.")
        return filepath

    def _build_analysis(self, intelligence: dict, advanced: dict) -> dict:
        visual = intelligence.get("visual", {}) or {}
        audio = intelligence.get("audio", {}) or {}
        subjects = intelligence.get("subjects", {}) or {}
        scenes = intelligence.get("scenes", {}) or {}
        sections = advanced.get("sections", {}) or {}

        analysis = {}
        analysis["shots"] = self._shots_block(intelligence, scenes)
        analysis["subjects"] = self._subjects_block(subjects)
        analysis["actions"] = self._actions_block(visual)
        analysis["environment"] = self._text_block(
            visual.get("environment", ""),
            source="vision_analysis",
            note=_NO_STRUCTURED_VISION,
        )
        analysis["camera"] = self._camera_block(visual)
        analysis["lens"] = self._lens_block()
        analysis["lighting"] = self._text_block(
            visual.get("lighting", ""),
            source="vision_analysis",
            note=_NO_STRUCTURED_VISION,
        )
        analysis["color"] = self._color_block(visual)
        analysis["composition"] = self._composition_block(sections)
        analysis["visual_style"] = self._text_block(
            visual.get("visual_style", ""),
            source="vision_analysis",
            note=_NO_STRUCTURED_VISION,
        )
        analysis["audio"] = self._audio_block(audio)
        analysis["characters"] = self._characters_block()
        return analysis

    def _shots_block(self, intelligence: dict, scenes: dict) -> dict:
        video_filename = intelligence.get("video_filename", "")
        # Try P2-02 shot detection with frame collection
        if self.shot_detection_service is not None:
            try:
                from app.ai.shot_providers import collect_frames

                frame_filenames = collect_frames(stored_filename=video_filename)
                result = self.shot_detection_service.detect_shots(
                    stored_filename=video_filename,
                    frame_filenames=frame_filenames,
                    video_duration=0.0,
                )
                shots_value = result["shots"]
                shots_detected = result["shots_detected"]
                frames_compared = result["frames_compared"]
                # Build a value block for the analysis
                value = {
                    "shots_detected": shots_detected,
                    "frames_compared": frames_compared,
                    "shots": [
                        {
                            "shot_id": s["shot_id"],
                            "start_time": s["start_time"],
                            "end_time": s["end_time"],
                            "duration": s["duration"],
                            "start_frame": s["start_frame"],
                            "end_frame": s["end_frame"],
                            "representative_frame": s["representative_frame"],
                            "transition_type": s["transition_type"],
                            "confidence": s["confidence"],
                            "shot_type": s["shot_type"],
                            "shot_type_source": s.get("shot_type_source", "unavailable"),
                            "shot_type_confidence": s.get("shot_type_confidence", 0.0),
                            "motion_level": s.get("motion_level", "static"),
                        }
                        for s in shots_value
                    ],
                }
                return _block(
                    OBSERVED,
                    "shot_detection",
                    value=value,
                    confidence="medium",
                )
            except Exception:
                # Fall back to Day 9 scene data on any error
                pass

        # Fallback to Day 9 scene data
        timeline = scenes.get("timeline", [])
        value = {
            "scenes_detected": scenes.get("scenes_detected", 0),
            "timeline": timeline,
        }
        if not timeline:
            return _block(
                UNAVAILABLE,
                "scene_detection",
                value=value,
                confidence=None,
                note="No scenes were detected; frames may not be extracted.",
            )
        return _block(
            OBSERVED, "scene_detection", value=value, confidence="high"
        )

    @staticmethod
    def _subjects_block(subjects: dict) -> dict:
        profiles = subjects.get("profiles", [])
        value = {
            "subjects_detected": subjects.get("subjects_detected", 0),
            "profiles": profiles,
        }
        if not profiles:
            return _block(
                UNAVAILABLE,
                "subject_tracking",
                value=value,
                confidence=None,
                note=(
                    "No subject profiles were tracked; frames may not be "
                    "extracted."
                ),
            )
        return _block(
            OBSERVED, "subject_tracking", value=value, confidence="medium"
        )

    def _actions_block(self, visual: dict) -> dict:
        if self.emotion_action_service is not None:
            value = self.emotion_action_service.analyze(visual)
            return _block(
                ESTIMATED,
                "emotion_action_analysis",
                value=value,
                confidence="low",
            )
        actions = visual.get("actions", [])
        if not actions:
            return _block(
                UNAVAILABLE,
                "vision_analysis",
                value=actions,
                confidence=None,
                note=_NO_STRUCTURED_VISION,
            )
        return _block(
            OBSERVED, "vision_analysis", value=actions, confidence="medium"
        )

    @staticmethod
    def _text_block(raw: str, source: str, note: str) -> dict:
        if isinstance(raw, str) and raw.strip():
            return _block(OBSERVED, source, value=raw, confidence="medium")
        return _block(
            UNAVAILABLE, source, value=None, confidence=None, note=note
        )

    @staticmethod
    def _camera_block(visual: dict) -> dict:
        camera = visual.get("camera", {}) or {}
        has_detail = any(
            str(camera.get(key, "")).strip()
            for key in ("perspective", "shot_type", "movement")
        )
        if not has_detail:
            return _block(
                UNAVAILABLE,
                "vision_analysis",
                value=camera or None,
                confidence=None,
                note=_NO_STRUCTURED_VISION,
            )
        return _block(
            OBSERVED, "vision_analysis", value=camera, confidence="medium"
        )

    def _lens_block(self) -> dict:
        if self.camera_estimation_service is None:
            return _block(
                UNAVAILABLE,
                "camera_estimation",
                value=None,
                confidence=None,
                note=_NO_LENS,
            )
        value = self.camera_estimation_service.estimate_lens()
        return _block(
            ESTIMATED, "camera_estimation", value=value, confidence="low"
        )

    def _color_block(self, visual: dict) -> dict:
        if self.color_analysis_service is not None:
            value = self.color_analysis_service.analyze(
                visual.get("color_palette", [])
            )
            return _block(
                OBSERVED, "color_analysis", value=value, confidence="medium"
            )
        palette = visual.get("color_palette", [])
        if palette:
            return _block(
                OBSERVED, "vision_analysis", value=palette, confidence="medium"
            )
        return _block(
            UNAVAILABLE,
            "color_analysis",
            value=None,
            confidence=None,
            note=_NO_COLOR,
        )

    @staticmethod
    def _composition_block(sections: dict) -> dict:
        composition = sections.get("composition", "")
        if composition:
            return _block(
                ESTIMATED,
                "advanced_prompt_service",
                value=composition,
                confidence="low",
            )
        return _block(
            UNAVAILABLE,
            "advanced_prompt_service",
            value=None,
            confidence=None,
            note="No composition details were derived from the analysis.",
        )

    @staticmethod
    def _audio_block(audio: dict) -> dict:
        value = dict(audio)
        transcription = value.get("transcription", {}) or {}
        note = ""
        if value.get("has_audio") and not str(
            transcription.get("text", "")
        ).strip():
            note = _NO_TRANSCRIPTION
        return _block(
            OBSERVED, "audio_analysis", value=value, confidence="high",
            note=note,
        )

    def _characters_block(self) -> dict:
        if self.character_consistency_service is None:
            return _block(
                UNAVAILABLE,
                "character_consistency",
                value=None,
                confidence=None,
                note=_NO_CHARACTERS,
            )
        value = self.character_consistency_service.analyze()
        return _block(
            ESTIMATED,
            "character_consistency",
            value=value,
            confidence="low",
        )

    def _provider_status(self, intelligence: dict, analysis: dict) -> dict:
        visual = intelligence.get("visual", {}) or {}
        structured = bool(
            visual.get("environment")
            or visual.get("lighting")
            or visual.get("visual_style")
            or visual.get("subjects")
            or visual.get("actions")
            or visual.get("color_palette")
        )
        vision_provider = settings.vision_provider
        audio_provider = settings.audio_provider
        note = ""
        if vision_provider == "mock":
            note = (
                "Vision provider is the local mock; no vision-language "
                "model was used for this reconstruction."
            )
        return {
            "vision_provider": vision_provider,
            "audio_provider": audio_provider,
            "structured_visual_details_available": structured,
            "note": note,
        }

    @staticmethod
    def _confidence_summary(analysis: dict, provider_status: dict) -> dict:
        observed = [
            key
            for key, block in analysis.items()
            if block["availability"] == OBSERVED
        ]
        estimated = [
            key
            for key, block in analysis.items()
            if block["availability"] == ESTIMATED
        ]
        unavailable = [
            key
            for key, block in analysis.items()
            if block["availability"] == UNAVAILABLE
        ]

        if len(unavailable) <= 2:
            overall = "high"
        elif len(unavailable) <= 6:
            overall = "medium"
        else:
            overall = "low"

        uncertainty_notes = [
            f"{key}: {analysis[key]['note']}"
            for key in estimated + unavailable
            if analysis[key].get("note")
        ]
        if provider_status.get("note"):
            uncertainty_notes.append(provider_status["note"])

        return {
            "overall": overall,
            "observed_domains": observed,
            "estimated_domains": estimated,
            "unavailable_domains": unavailable,
            "uncertainty_notes": uncertainty_notes,
        }
