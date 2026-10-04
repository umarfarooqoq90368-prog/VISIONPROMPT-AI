"""Tests for the video reconstruction service (Phase 2, P2-01)."""
import json
import os
import shutil

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.prompt_quality_service import PromptQualityService
from app.services.prompt_readiness_service import PromptReadinessService
from app.services.video_reconstruction_service import (
    VideoReconstructionService,
    VALID_DEPTHS,
    DEPTH_MAX_FRAMES,
    OBSERVED,
    ESTIMATED,
    UNAVAILABLE,
)

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(
    os.path.dirname(__file__), "test_assets", "test_video.mp4"
)
UPLOADS_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "backend", "storage", "uploads",
    )
)
FRAME_STORAGE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "backend", "storage", "frames",
    )
)
SERVICE_VIDEO = "reconstruction_service_test.mp4"
ANALYSIS_DOMAINS = [
    "shots", "subjects", "actions", "environment", "camera", "lens",
    "lighting", "color", "composition", "visual_style", "audio",
    "characters",
]
BLOCK_KEYS = ["availability", "source", "value", "confidence", "note"]
VALID_AVAILABILITIES = {OBSERVED, ESTIMATED, UNAVAILABLE}


def _create_real_mp4(path: str) -> bool:
    import imageio_ffmpeg
    import subprocess
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=green:s=320x240:d=3",
             "-y", path],
            capture_output=True, timeout=15,
        )
        return os.path.exists(path) and os.path.getsize(path) > 0
    except Exception:
        return False


def _cleanup_frames():
    if os.path.exists(FRAME_STORAGE_DIR):
        for d in os.listdir(FRAME_STORAGE_DIR):
            full = os.path.join(FRAME_STORAGE_DIR, d)
            if os.path.isdir(full):
                shutil.rmtree(full, ignore_errors=True)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    video_path = os.path.join(UPLOADS_DIR, SERVICE_VIDEO)
    if not os.path.exists(video_path):
        _create_real_mp4(video_path)
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)
    _cleanup_frames()


# ----------------------------------------------------------------------
# fakes
# ----------------------------------------------------------------------

RICH_INTELLIGENCE = {
    "video_filename": SERVICE_VIDEO,
    "duration_seconds": 3.0,
    "visual": {
        "frames_analyzed": 5,
        "subjects": ["person"],
        "actions": ["walking"],
        "environment": "an outdoor forest street",
        "camera": {
            "perspective": "eye level",
            "shot_type": "wide",
            "movement": "static",
        },
        "lighting": "soft natural light",
        "visual_style": "documentary",
        "color_palette": ["green", "brown"],
        "objects": ["tree"],
    },
    "scenes": {
        "scenes_detected": 2,
        "timeline": [
            {"scene_id": 1, "start_time": 0.0, "end_time": 1.5},
            {"scene_id": 2, "start_time": 1.5, "end_time": 3.0},
        ],
    },
    "subjects": {
        "subjects_detected": 1,
        "profiles": [
            {
                "subject_id": 1,
                "label": "person",
                "description": "a person",
                "appearance_observations": ["a person"],
                "actions": [],
                "first_seen": 0.0,
                "last_seen": 3.0,
                "frames_seen": ["frame_1.jpg"],
                "confidence": 0.8,
            }
        ],
    },
    "audio": {
        "has_audio": True,
        "duration_seconds": 3.0,
        "audio_format": "wav",
        "sample_rate": 16000,
        "channels": 1,
        "transcription": {
            "language": "en",
            "text": "hello there",
            "segments": [],
            "provider": "whisper",
        },
        "provider": "whisper",
    },
}

SPARSE_INTELLIGENCE = {
    "video_filename": SERVICE_VIDEO,
    "duration_seconds": 3.0,
    "visual": {
        "frames_analyzed": 3,
        "subjects": [],
        "actions": [],
        "environment": "",
        "camera": {"perspective": "", "shot_type": "", "movement": ""},
        "lighting": "",
        "visual_style": "",
        "color_palette": [],
        "objects": [],
    },
    "scenes": {"scenes_detected": 0, "timeline": []},
    "subjects": {"subjects_detected": 0, "profiles": []},
    "audio": {
        "has_audio": False,
        "duration_seconds": 3.0,
        "audio_format": None,
        "sample_rate": None,
        "channels": None,
        "transcription": {
            "language": None,
            "text": "",
            "segments": [],
            "provider": "mock",
        },
        "provider": "mock",
    },
}

ADVANCED_RESULT = {
    "video_filename": SERVICE_VIDEO,
    "style": "cinematic",
    "prompt": "Subject: person; Action: walking; Composition: wide shot.",
    "negative_prompt": "blurry, low quality",
    "sections": {
        "subject": "Subject: person",
        "action": "Action: walking",
        "environment": "Environment: an outdoor forest street",
        "camera": "Camera perspective: eye level",
        "lighting": "Lighting: soft natural light",
        "visual_style": "Visual style: documentary",
        "color": "Color: green, brown",
        "audio": "Audio text: hello there",
        "composition": "Scene progression across 2 scenes",
    },
}


class FakeIntelligence:
    def __init__(self, result=None, error=None):
        self.result = result if result is not None else RICH_INTELLIGENCE
        self.error = error
        self.calls = []

    def analyze(self, stored_filename, max_frames=10):
        self.calls.append(
            {"stored_filename": stored_filename, "max_frames": max_frames}
        )
        if self.error is not None:
            raise self.error
        return json.loads(json.dumps(self.result))


class FakeAdvanced:
    def __init__(self, result=None, error=None):
        self.result = result if result is not None else ADVANCED_RESULT
        self.error = error
        self.calls = []

    def generate_prompt(self, intelligence, style="cinematic"):
        self.calls.append({"intelligence": intelligence, "style": style})
        if self.error is not None:
            raise self.error
        result = json.loads(json.dumps(self.result))
        result["style"] = style
        return result


class FakeShotDetection:
    def detect(self, video_filename):
        return {
            "shots_detected": 2,
            "shots": [
                {"shot_id": 1, "start_time": 0.0, "end_time": 1.5},
                {"shot_id": 2, "start_time": 1.5, "end_time": 3.0},
            ],
        }


class FakeCameraEstimation:
    def estimate_lens(self):
        return {"value": "50mm", "confidence": "low", "source": "mock"}


class FakeColorAnalysis:
    def analyze(self, palette):
        return {"palette": palette, "dominant": "green"}


class FakeEmotionAction:
    def analyze(self, visual):
        return {"actions": ["walking"], "emotions": []}


class FakeCharacterConsistency:
    def analyze(self):
        return {"characters": [], "availability": "unavailable"}


def make_service(intelligence=None, advanced=None, **optional):
    quality = PromptQualityService()
    return VideoReconstructionService(
        intelligence_service=intelligence or FakeIntelligence(),
        advanced_prompt_service=advanced or FakeAdvanced(),
        quality_service=quality,
        readiness_service=PromptReadinessService(quality),
        shot_detection_service=optional.get("shots"),
        camera_estimation_service=optional.get("camera"),
        color_analysis_service=optional.get("color"),
        emotion_action_service=optional.get("emotion"),
        character_consistency_service=optional.get("characters"),
    )


@pytest.fixture
def service():
    return make_service()


# ----------------------------------------------------------------------
# validation
# ----------------------------------------------------------------------

class TestValidation:
    def test_valid_depths(self):
        assert set(VALID_DEPTHS) == {"quick", "standard", "deep"}

    def test_depth_max_frames_mapping(self):
        assert DEPTH_MAX_FRAMES == {
            "quick": 2, "standard": 10, "deep": 25,
        }

    @pytest.mark.parametrize("depth", ["", "FAST", "normal", "1", "deepish"])
    def test_invalid_depth_raises(self, depth):
        svc = make_service()
        with pytest.raises(ValueError) as exc:
            svc.reconstruct(SERVICE_VIDEO, depth=depth)
        assert str(exc.value) == (
            "Invalid depth. Must be one of: deep, quick, standard"
        )

    @pytest.mark.parametrize("style", ["", "gritty", "CINEMATIC", "fast"])
    def test_invalid_style_raises(self, style):
        svc = make_service()
        with pytest.raises(ValueError) as exc:
            svc.reconstruct(SERVICE_VIDEO, style=style)
        assert str(exc.value) == (
            "Invalid style. Must be one of: cinematic, commercial, realistic"
        )

    def test_missing_video_raises(self):
        svc = make_service()
        with pytest.raises(ValueError) as exc:
            svc.reconstruct("does_not_exist_xyz.mp4")
        assert str(exc.value) == "Video file not found."

    def test_path_traversal_raises(self):
        svc = make_service()
        with pytest.raises(ValueError) as exc:
            svc.reconstruct("../../../etc/passwd")
        assert str(exc.value) == "Video file not found."

    def test_invalid_depth_checked_before_file(self):
        svc = make_service()
        with pytest.raises(ValueError) as exc:
            svc.reconstruct("missing.mp4", depth="turbo")
        assert "Invalid depth" in str(exc.value)


# ----------------------------------------------------------------------
# depth -> analysis size
# ----------------------------------------------------------------------

class TestDepthFrames:
    @pytest.mark.parametrize("depth,expected", [
        ("quick", 2), ("standard", 10), ("deep", 25),
    ])
    def test_depth_maps_to_max_frames(self, depth, expected):
        fake = FakeIntelligence()
        svc = make_service(intelligence=fake)
        svc.reconstruct(SERVICE_VIDEO, depth=depth)
        assert fake.calls[0]["max_frames"] == expected

    def test_default_depth_is_standard(self):
        fake = FakeIntelligence()
        svc = make_service(intelligence=fake)
        svc.reconstruct(SERVICE_VIDEO)
        assert fake.calls[0]["max_frames"] == 10

    def test_receives_stored_filename(self):
        fake = FakeIntelligence()
        svc = make_service(intelligence=fake)
        svc.reconstruct(SERVICE_VIDEO)
        assert fake.calls[0]["stored_filename"] == SERVICE_VIDEO


# ----------------------------------------------------------------------
# top-level result shape
# ----------------------------------------------------------------------

class TestResultShape:
    def test_top_level_keys(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        assert list(result.keys()) == [
            "video_filename", "depth", "style", "video_information",
            "analysis", "provider_status", "confidence", "prompt",
            "quality", "readiness",
        ]

    def test_identity_fields(self, service):
        result = service.reconstruct(
            SERVICE_VIDEO, depth="deep", style="realistic"
        )
        assert result["video_filename"] == SERVICE_VIDEO
        assert result["depth"] == "deep"
        assert result["style"] == "realistic"

    def test_analysis_has_all_domains(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        assert list(result["analysis"].keys()) == ANALYSIS_DOMAINS

    @pytest.mark.parametrize("domain", ANALYSIS_DOMAINS)
    def test_each_block_has_uniform_keys(self, service, domain):
        result = service.reconstruct(SERVICE_VIDEO)
        block = result["analysis"][domain]
        assert list(block.keys()) == BLOCK_KEYS
        assert block["availability"] in VALID_AVAILABILITIES

    def test_video_information_block(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        block = result["video_information"]
        assert list(block.keys()) == BLOCK_KEYS
        assert block["availability"] == OBSERVED
        assert block["source"] == "ffprobe"
        assert block["confidence"] == "high"
        value = block["value"]
        assert value["filename"] == SERVICE_VIDEO
        assert value["duration_seconds"] > 0
        assert value["width"] == 320
        assert value["height"] == 240
        assert value["file_size_bytes"] > 0

    def test_prompt_block_shape(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        prompt = result["prompt"]
        assert set(prompt.keys()) == {
            "production_prompt", "negative_prompt", "style", "sections",
            "source",
        }
        assert prompt["production_prompt"].strip()
        assert prompt["negative_prompt"].strip()
        assert prompt["source"] == "advanced_prompt_service"
        assert set(prompt["sections"].keys()) == {
            "subject", "action", "environment", "camera", "lighting",
            "visual_style", "color", "audio", "composition",
        }

    def test_quality_block_shape(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        quality = result["quality"]
        assert isinstance(quality["overall_score"], int)
        assert 0 <= quality["overall_score"] <= 100
        assert 0 <= quality["completeness_percentage"] <= 100
        assert set(quality["dimensions"].keys()) == {
            "subject", "action", "environment", "camera", "lighting",
            "visual_style", "color", "composition", "audio",
        }

    def test_readiness_block_shape(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        readiness = result["readiness"]
        assert readiness["status"] in {"ready", "needs_attention"}
        assert len(readiness["checklist"]) == 9
        assert "coverage" in readiness
        assert isinstance(readiness["suggestions"], list)

    def test_result_is_json_serializable(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        text = json.dumps(result, ensure_ascii=False)
        assert "video_filename" in text


# ----------------------------------------------------------------------
# rich intelligence -> observed domains
# ----------------------------------------------------------------------

class TestRichIntelligence:
    @pytest.fixture
    def result(self):
        return make_service().reconstruct(SERVICE_VIDEO)

    @pytest.mark.parametrize("domain", [
        "environment", "lighting", "visual_style",
    ])
    def test_text_domains_observed(self, result, domain):
        block = result["analysis"][domain]
        assert block["availability"] == OBSERVED
        assert block["confidence"] == "medium"
        assert block["source"] == "vision_analysis"
        assert isinstance(block["value"], str) and block["value"].strip()

    def test_camera_observed_with_all_fields(self, result):
        block = result["analysis"]["camera"]
        assert block["availability"] == OBSERVED
        assert block["value"] == {
            "perspective": "eye level",
            "shot_type": "wide",
            "movement": "static",
        }

    def test_actions_observed(self, result):
        block = result["analysis"]["actions"]
        assert block["availability"] == OBSERVED
        assert block["value"] == ["walking"]

    def test_color_observed_from_palette(self, result):
        block = result["analysis"]["color"]
        assert block["availability"] == OBSERVED
        assert block["value"] == ["green", "brown"]
        assert block["source"] == "vision_analysis"

    def test_shots_observed_from_scenes(self, result):
        block = result["analysis"]["shots"]
        assert block["availability"] == OBSERVED
        assert block["source"] == "scene_detection"
        assert block["value"]["scenes_detected"] == 2
        assert len(block["value"]["timeline"]) == 2
        assert block["confidence"] == "high"

    def test_subjects_observed_with_profiles(self, result):
        block = result["analysis"]["subjects"]
        assert block["availability"] == OBSERVED
        assert block["value"]["subjects_detected"] == 1
        assert block["value"]["profiles"][0]["label"] == "person"

    def test_composition_estimated(self, result):
        block = result["analysis"]["composition"]
        assert block["availability"] == ESTIMATED
        assert block["source"] == "advanced_prompt_service"
        assert block["confidence"] == "low"
        assert block["value"] == "Scene progression across 2 scenes"

    def test_audio_observed(self, result):
        block = result["analysis"]["audio"]
        assert block["availability"] == OBSERVED
        assert block["value"]["has_audio"] is True
        assert block["value"]["transcription"]["text"] == "hello there"
        assert block["note"] == ""

    @pytest.mark.parametrize("domain", ["lens", "characters"])
    def test_optional_services_unavailable(self, result, domain):
        block = result["analysis"][domain]
        assert block["availability"] == UNAVAILABLE
        assert block["value"] is None
        assert block["note"].strip()

    def test_unavailable_domains_list(self, result):
        conf = result["confidence"]
        assert conf["unavailable_domains"] == ["lens", "characters"]
        assert conf["estimated_domains"] == ["composition"]
        for domain in ANALYSIS_DOMAINS:
            assert domain in (
                conf["observed_domains"]
                + conf["estimated_domains"]
                + conf["unavailable_domains"]
            )

    def test_overall_confidence_high(self, result):
        assert result["confidence"]["overall"] == "high"


# ----------------------------------------------------------------------
# sparse intelligence -> honest unavailable domains
# ----------------------------------------------------------------------

class TestSparseIntelligence:
    @pytest.fixture
    def result(self):
        return make_service(
            intelligence=FakeIntelligence(result=SPARSE_INTELLIGENCE),
        ).reconstruct(SERVICE_VIDEO)

    @pytest.mark.parametrize("domain", [
        "actions", "environment", "camera", "lighting", "visual_style",
    ])
    def test_vision_domains_unavailable(self, result, domain):
        block = result["analysis"][domain]
        assert block["availability"] == UNAVAILABLE
        assert block["confidence"] is None
        assert "vision provider returned no structured details" in block["note"]

    def test_text_domain_values_are_none(self, result):
        for domain in ["environment", "lighting", "visual_style"]:
            assert result["analysis"][domain]["value"] is None

    def test_camera_value_keeps_empty_dict(self, result):
        assert result["analysis"]["camera"]["value"] == {
            "perspective": "", "shot_type": "", "movement": "",
        }

    def test_color_unavailable(self):
        result = make_service(
            intelligence=FakeIntelligence(result=SPARSE_INTELLIGENCE),
        ).reconstruct(SERVICE_VIDEO)
        block = result["analysis"]["color"]
        assert block["availability"] == UNAVAILABLE
        assert "Color analysis is not available" in block["note"]

    def test_shots_unavailable_with_zero_scenes(self, result):
        block = result["analysis"]["shots"]
        assert block["availability"] == UNAVAILABLE
        assert block["value"]["scenes_detected"] == 0
        assert block["value"]["timeline"] == []
        assert "No scenes were detected" in block["note"]

    def test_subjects_unavailable_without_profiles(self, result):
        block = result["analysis"]["subjects"]
        assert block["availability"] == UNAVAILABLE
        assert block["value"]["subjects_detected"] == 0
        assert "No subject profiles were tracked" in block["note"]

    def test_audio_observed_even_without_audio(self, result):
        block = result["analysis"]["audio"]
        assert block["availability"] == OBSERVED
        assert block["value"]["has_audio"] is False

    def test_audio_note_empty_when_no_audio(self, result):
        assert result["analysis"]["audio"]["note"] == ""

    def test_overall_confidence_low(self, result):
        assert result["confidence"]["overall"] == "low"

    def test_unavailable_domains_count(self, result):
        conf = result["confidence"]
        assert len(conf["unavailable_domains"]) == 10
        assert set(conf["unavailable_domains"]) == {
            "shots", "subjects", "actions", "environment", "camera",
            "lens", "lighting", "color", "visual_style", "characters",
        }

    def test_uncertainty_notes_listed(self, result):
        notes = result["confidence"]["uncertainty_notes"]
        assert any("vision provider" in n for n in notes)
        assert any("Lens estimation" in n for n in notes)
        assert any("Character consistency" in n for n in notes)

    def test_provider_note_in_uncertainty(self, result):
        if settings.vision_provider == "mock":
            notes = result["confidence"]["uncertainty_notes"]
            assert any("local mock" in n for n in notes)


# ----------------------------------------------------------------------
# audio transcription note
# ----------------------------------------------------------------------

class TestAudioNotes:
    def test_transcription_note_when_audio_but_no_text(self):
        intel = json.loads(json.dumps(RICH_INTELLIGENCE))
        intel["audio"]["transcription"]["text"] = ""
        result = make_service(
            intelligence=FakeIntelligence(result=intel),
        ).reconstruct(SERVICE_VIDEO)
        block = result["analysis"]["audio"]
        assert block["availability"] == OBSERVED
        assert "Speech transcription is not available" in block["note"]


# ----------------------------------------------------------------------
# provider status
# ----------------------------------------------------------------------

class TestProviderStatus:
    def test_provider_status_keys(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        assert list(result["provider_status"].keys()) == [
            "vision_provider", "audio_provider",
            "structured_visual_details_available", "note",
        ]

    def test_provider_names_match_settings(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        assert result["provider_status"]["vision_provider"] == (
            settings.vision_provider
        )
        assert result["provider_status"]["audio_provider"] == (
            settings.audio_provider
        )

    def test_structured_flag_true_for_rich(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        assert result["provider_status"][
            "structured_visual_details_available"
        ] is True

    def test_structured_flag_false_for_sparse(self):
        result = make_service(
            intelligence=FakeIntelligence(result=SPARSE_INTELLIGENCE),
        ).reconstruct(SERVICE_VIDEO)
        assert result["provider_status"][
            "structured_visual_details_available"
        ] is False

    def test_mock_note_present(self, service, monkeypatch):
        monkeypatch.setattr(settings, "vision_provider", "mock")
        result = service.reconstruct(SERVICE_VIDEO)
        assert "local mock" in result["provider_status"]["note"]

    def test_no_note_for_real_provider(self, service, monkeypatch):
        monkeypatch.setattr(settings, "vision_provider", "qwen2vl")
        result = service.reconstruct(SERVICE_VIDEO)
        assert result["provider_status"]["note"] == ""


# ----------------------------------------------------------------------
# confidence summary consistency
# ----------------------------------------------------------------------

class TestConfidenceSummary:
    def test_confidence_keys(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        assert list(result["confidence"].keys()) == [
            "overall", "observed_domains", "estimated_domains",
            "unavailable_domains", "uncertainty_notes",
        ]

    def test_lists_partition_domains(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        conf = result["confidence"]
        combined = (
            conf["observed_domains"]
            + conf["estimated_domains"]
            + conf["unavailable_domains"]
        )
        assert sorted(combined) == sorted(ANALYSIS_DOMAINS)
        assert len(combined) == len(set(combined))

    def test_lists_match_block_availability(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        analysis = result["analysis"]
        conf = result["confidence"]
        for domain in conf["observed_domains"]:
            assert analysis[domain]["availability"] == OBSERVED
        for domain in conf["estimated_domains"]:
            assert analysis[domain]["availability"] == ESTIMATED
        for domain in conf["unavailable_domains"]:
            assert analysis[domain]["availability"] == UNAVAILABLE

    @pytest.mark.parametrize("unavailable_count,expected", [
        (2, "high"), (6, "medium"), (10, "low"),
    ])
    def test_overall_boundaries(self, unavailable_count, expected):
        if unavailable_count == 10:
            intel = json.loads(json.dumps(SPARSE_INTELLIGENCE))
        elif unavailable_count == 6:
            intel = json.loads(json.dumps(RICH_INTELLIGENCE))
            for key in ("lighting", "environment", "visual_style"):
                intel["visual"][key] = ""
            intel["visual"]["actions"] = []
        else:
            intel = json.loads(json.dumps(RICH_INTELLIGENCE))
        result = make_service(
            intelligence=FakeIntelligence(result=intel),
        ).reconstruct(SERVICE_VIDEO)
        conf = result["confidence"]
        assert len(conf["unavailable_domains"]) == unavailable_count
        assert conf["overall"] == expected

    def test_medium_when_some_missing(self):
        intel = json.loads(json.dumps(RICH_INTELLIGENCE))
        intel["visual"]["lighting"] = ""
        intel["visual"]["environment"] = ""
        result = make_service(
            intelligence=FakeIntelligence(result=intel),
        ).reconstruct(SERVICE_VIDEO)
        conf = result["confidence"]
        assert conf["overall"] == "medium"
        assert "lighting" in conf["unavailable_domains"]
        assert "environment" in conf["unavailable_domains"]

    def test_uncertainty_notes_are_strings(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        for note in result["confidence"]["uncertainty_notes"]:
            assert isinstance(note, str)
            assert note.strip()


# ----------------------------------------------------------------------
# optional Phase 2 service wiring
# ----------------------------------------------------------------------

class TestOptionalServices:
    def test_shot_detection_replaces_scene_detection(self):
        result = make_service(shots=FakeShotDetection()).reconstruct(
            SERVICE_VIDEO
        )
        block = result["analysis"]["shots"]
        assert block["source"] == "shot_detection"
        assert block["value"]["shots_detected"] == 2
        assert block["availability"] == OBSERVED

    def test_camera_estimation_populates_lens(self):
        result = make_service(camera=FakeCameraEstimation()).reconstruct(
            SERVICE_VIDEO
        )
        block = result["analysis"]["lens"]
        assert block["availability"] == ESTIMATED
        assert block["value"] == {
            "value": "50mm", "confidence": "low", "source": "mock",
        }
        assert block["source"] == "camera_estimation"

    def test_color_service_populates_color(self):
        result = make_service(color=FakeColorAnalysis()).reconstruct(
            SERVICE_VIDEO
        )
        block = result["analysis"]["color"]
        assert block["availability"] == OBSERVED
        assert block["source"] == "color_analysis"
        assert block["value"]["dominant"] == "green"

    def test_emotion_action_service_populates_actions(self):
        result = make_service(emotion=FakeEmotionAction()).reconstruct(
            SERVICE_VIDEO
        )
        block = result["analysis"]["actions"]
        assert block["availability"] == ESTIMATED
        assert block["source"] == "emotion_action_analysis"
        assert block["value"]["actions"] == ["walking"]

    def test_character_service_populates_characters(self):
        result = make_service(
            characters=FakeCharacterConsistency(),
        ).reconstruct(SERVICE_VIDEO)
        block = result["analysis"]["characters"]
        assert block["availability"] == ESTIMATED
        assert block["source"] == "character_consistency"
        assert block["value"]["availability"] == "unavailable"

    def test_wired_services_reduce_unavailable_count(self):
        result = make_service(
            camera=FakeCameraEstimation(),
            color=FakeColorAnalysis(),
            characters=FakeCharacterConsistency(),
        ).reconstruct(SERVICE_VIDEO)
        conf = result["confidence"]
        assert "lens" not in conf["unavailable_domains"]
        assert "color" not in conf["unavailable_domains"]
        assert "characters" not in conf["unavailable_domains"]
        assert conf["overall"] == "high"


# ----------------------------------------------------------------------
# upstream errors propagate
# ----------------------------------------------------------------------

class TestUpstreamErrors:
    def test_intelligence_value_error_propagates(self):
        svc = make_service(
            intelligence=FakeIntelligence(
                error=ValueError("Video file not found.")
            ),
        )
        with pytest.raises(ValueError) as exc:
            svc.reconstruct(SERVICE_VIDEO)
        assert str(exc.value) == "Video file not found."

    def test_advanced_value_error_propagates(self):
        svc = make_service(
            advanced=FakeAdvanced(
                error=ValueError("Invalid style. Must be one of: cinematic, "
                                 "commercial, realistic")
            ),
        )
        with pytest.raises(ValueError):
            svc.reconstruct(SERVICE_VIDEO)

    def test_empty_prompt_rejected_by_quality(self):
        empty = json.loads(json.dumps(ADVANCED_RESULT))
        empty["prompt"] = ""
        svc = make_service(advanced=FakeAdvanced(result=empty))
        with pytest.raises(ValueError) as exc:
            svc.reconstruct(SERVICE_VIDEO)
        assert str(exc.value) == "prompt must not be empty."

    def test_intelligence_error_raised_before_advanced(self):
        intel = FakeIntelligence(error=ValueError("boom"))
        adv = FakeAdvanced()
        svc = make_service(intelligence=intel, advanced=adv)
        with pytest.raises(ValueError):
            svc.reconstruct(SERVICE_VIDEO)
        assert adv.calls == []


# ----------------------------------------------------------------------
# determinism + safety
# ----------------------------------------------------------------------

class TestDeterminismAndSafety:
    def test_two_calls_equal(self, service):
        first = service.reconstruct(SERVICE_VIDEO)
        second = service.reconstruct(SERVICE_VIDEO)
        assert json.dumps(first, sort_keys=True) == json.dumps(
            second, sort_keys=True
        )

    def test_no_absolute_paths_in_result(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        text = json.dumps(result)
        for bad in ("C:\\", "C:/", "/home", "/Users", "/var/",
                    "storage/uploads", "test_assets"):
            assert bad not in text, f"path leak: {bad}"

    def test_video_filename_is_stored_name(self, service):
        result = service.reconstruct(SERVICE_VIDEO)
        assert "/" not in result["video_filename"]
        assert "\\" not in result["video_filename"]

    def test_no_prompt_history_side_effect(self, service):
        service.reconstruct(SERVICE_VIDEO)
        response = client.get(f"/api/videos/{SERVICE_VIDEO}/prompt/history")
        assert response.status_code == 200
        assert response.json() == {
            "video_filename": SERVICE_VIDEO,
            "versions": [],
        }


# ----------------------------------------------------------------------
# real integration stack
# ----------------------------------------------------------------------

class TestRealStack:
    def test_real_reconstruction(self):
        from app.services.video_reconstruction_service import (
            VideoReconstructionService as Real,
        )
        result = Real().reconstruct(SERVICE_VIDEO)
        assert result["video_filename"] == SERVICE_VIDEO
        assert result["prompt"]["production_prompt"].strip()
        assert len(result["analysis"]) == 12
        assert result["video_information"]["availability"] == OBSERVED

    def test_real_reconstruction_with_frames(self):
        with open(TEST_VIDEO_PATH, "rb") as f:
            upload = client.post(
                "/api/videos/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        assert upload.status_code == 200
        stored = upload.json()["video"]["stored_filename"]
        extract = client.post(
            f"/api/videos/{stored}/frames/extract?interval_seconds=1"
        )
        assert extract.status_code == 200
        try:
            from app.services.video_reconstruction_service import (
                VideoReconstructionService as Real,
            )
            result = Real().reconstruct(stored)
            assert result["analysis"]["shots"]["availability"] in (
                OBSERVED, UNAVAILABLE,
            )
            text = json.dumps(result)
            for bad in ("C:\\", "C:/", "/home", "test_assets"):
                assert bad not in text
        finally:
            video_path = os.path.join(UPLOADS_DIR, stored)
            if os.path.exists(video_path):
                os.remove(video_path)

    def test_real_quick_and_deep_differ_in_frames(self):
        from app.services.video_reconstruction_service import (
            VideoReconstructionService as Real,
        )
        quick = Real().reconstruct(SERVICE_VIDEO, depth="quick")
        deep = Real().reconstruct(SERVICE_VIDEO, depth="deep")
        assert quick["depth"] == "quick"
        assert deep["depth"] == "deep"
        assert quick["video_information"] == deep["video_information"]
