"""Tests for the advanced prompt generation service (Day 13)."""
import pytest
from app.services.advanced_prompt_service import AdvancedPromptService, VALID_STYLES


@pytest.fixture
def advanced_service():
    return AdvancedPromptService()


def sample_intelligence():
    """A fully-populated unified intelligence dict from Day 12."""
    return {
        "video_filename": "sample.mp4",
        "duration_seconds": 4.0,
        "visual": {
            "frames_analyzed": 4,
            "subjects": ["a person"],
            "actions": ["walking"],
            "environment": "an outdoor park",
            "camera": {
                "perspective": "eye-level",
                "shot_type": "wide",
                "movement": "static",
            },
            "lighting": "soft daylight",
            "visual_style": "naturalistic",
            "color_palette": ["green", "blue"],
            "objects": ["a bench"],
        },
        "scenes": {
            "scenes_detected": 2,
            "timeline": [
                {"start_time": 0.0, "end_time": 2.0, "description": "opening shot"},
                {"start_time": 2.0, "end_time": 4.0, "description": "wide park view"},
            ],
        },
        "subjects": {
            "subjects_detected": 1,
            "profiles": [
                {
                    "label": "subject_1",
                    "description": "a person wearing a jacket",
                    "first_seen": 0.0,
                    "last_seen": 4.0,
                    "frames_seen": ["frame_001.jpg"],
                }
            ],
        },
        "audio": {
            "has_audio": True,
            "duration_seconds": 4.0,
            "transcription": {
                "text": "hello world",
                "language": "en",
                "segments": [],
            },
            "provider": "mock",
        },
    }


def empty_intelligence():
    """An intelligence dict with no useful information (mock provider output)."""
    return {
        "video_filename": "empty.mp4",
        "duration_seconds": 2.0,
        "visual": {
            "frames_analyzed": 0,
            "subjects": [],
            "actions": [],
            "environment": "",
            "camera": {},
            "lighting": "",
            "visual_style": "",
            "color_palette": [],
            "objects": [],
        },
        "scenes": {"scenes_detected": 0, "timeline": []},
        "subjects": {"subjects_detected": 0, "profiles": []},
        "audio": {
            "has_audio": False,
            "duration_seconds": 2.0,
            "transcription": {"text": "", "language": None, "segments": []},
            "provider": "mock",
        },
    }


class TestValidInput:
    def test_valid_intelligence_input(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        assert result["video_filename"] == "sample.mp4"
        assert result["style"] == "cinematic"
        assert isinstance(result["prompt"], str)
        assert result["prompt"]
        assert isinstance(result["sections"], dict)

    def test_output_structure(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        expected_keys = [
            "video_filename", "style", "prompt", "negative_prompt", "sections",
        ]
        for key in expected_keys:
            assert key in result, f"missing key: {key}"
        expected_sections = [
            "subject", "action", "environment", "camera", "lighting",
            "visual_style", "color", "audio", "composition",
        ]
        for key in expected_sections:
            assert key in result["sections"], f"missing section: {key}"


class TestStyles:
    def test_cinematic_style(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence(), style="cinematic")
        assert result["style"] == "cinematic"
        assert "cinematic" in result["prompt"] or "cinematic" in result["sections"]["composition"]

    def test_realistic_style(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence(), style="realistic")
        assert result["style"] == "realistic"
        assert "realistic" in result["prompt"]

    def test_commercial_style(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence(), style="commercial")
        assert result["style"] == "commercial"
        assert "commercial" in result["prompt"]

    def test_style_influences_wording(self, advanced_service):
        results = {
            s: advanced_service.generate_prompt(sample_intelligence(), style=s)["prompt"]
            for s in VALID_STYLES
        }
        assert len(set(results.values())) == 3, "styles should produce distinct prompts"

    def test_invalid_style(self, advanced_service):
        with pytest.raises(ValueError):
            advanced_service.generate_prompt(sample_intelligence(), style="anime")


class TestEmptyIntelligence:
    def test_empty_intelligence_fields(self, advanced_service):
        result = advanced_service.generate_prompt(empty_intelligence())
        assert result["video_filename"] == "empty.mp4"
        assert isinstance(result["prompt"], str)
        assert result["prompt"]

    def test_empty_sections_are_empty(self, advanced_service):
        result = advanced_service.generate_prompt(empty_intelligence())
        sections = result["sections"]
        assert sections["subject"] == ""
        assert sections["action"] == ""
        assert sections["environment"] == ""
        assert sections["camera"] == ""
        assert sections["lighting"] == ""
        assert sections["color"] == ""
        assert sections["audio"] == ""

    def test_empty_prompt_does_not_fabricate(self, advanced_service):
        result = advanced_service.generate_prompt(empty_intelligence())
        prompt = result["prompt"].lower()
        forbidden = [
            "person", "character", "location", "dialogue", "walking",
            "park", "daylight", "bench", "jacket", "camera",
        ]
        for word in forbidden:
            assert word not in prompt, f"fabricated word found: {word}"


class TestSceneAwareness:
    def test_scene_aware_generation(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        composition = result["sections"]["composition"]
        assert "2 scenes" in composition
        assert "Scene progression" in composition

    def test_no_scenes_no_scene_text(self, advanced_service):
        result = advanced_service.generate_prompt(empty_intelligence())
        assert "Scene progression" not in result["prompt"]


class TestSubjectInformation:
    def test_subject_included(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        assert "a person" in result["sections"]["subject"]
        assert "a person" in result["prompt"]

    def test_subject_profile_description(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        assert "a person wearing a jacket" in result["sections"]["subject"]

    def test_no_subjects_empty_section(self, advanced_service):
        result = advanced_service.generate_prompt(empty_intelligence())
        assert result["sections"]["subject"] == ""


class TestCameraInformation:
    def test_camera_information(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        camera = result["sections"]["camera"]
        assert "eye-level" in camera
        assert "wide" in camera
        assert "static" in camera
        assert "eye-level" in result["prompt"]

    def test_no_camera_empty_section(self, advanced_service):
        result = advanced_service.generate_prompt(empty_intelligence())
        assert result["sections"]["camera"] == ""


class TestLightingInformation:
    def test_lighting_information(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        assert "soft daylight" in result["sections"]["lighting"]
        assert "soft daylight" in result["prompt"]

    def test_no_lighting_empty_section(self, advanced_service):
        result = advanced_service.generate_prompt(empty_intelligence())
        assert result["sections"]["lighting"] == ""


class TestColorInformation:
    def test_color_information(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        assert "green" in result["sections"]["color"]
        assert "blue" in result["sections"]["color"]
        assert "green" in result["prompt"]

    def test_no_color_empty_section(self, advanced_service):
        result = advanced_service.generate_prompt(empty_intelligence())
        assert result["sections"]["color"] == ""


class TestAudioInformation:
    def test_audio_transcription_information(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        audio = result["sections"]["audio"]
        assert "hello world" in audio
        assert "en" in audio
        assert "hello world" in result["prompt"]

    def test_no_audio_no_invention(self, advanced_service):
        result = advanced_service.generate_prompt(empty_intelligence())
        assert result["sections"]["audio"] == ""
        prompt = result["prompt"].lower()
        assert "hello" not in prompt
        assert "speech" not in prompt
        assert "dialogue" not in prompt
        assert "sound" not in prompt


class TestNegativePrompt:
    def test_generic_negative_prompt(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        neg = result["negative_prompt"]
        assert neg is not None
        assert "blurry" in neg
        assert "low quality" in neg
        assert "watermark" in neg

    def test_negative_prompt_is_generic_only(self, advanced_service):
        result = advanced_service.generate_prompt(sample_intelligence())
        neg = result["negative_prompt"].lower()
        content_specific = ["person", "park", "jacket", "bench", "hello", "daylight"]
        for word in content_specific:
            assert word not in neg, f"content-specific negative found: {word}"

    def test_negative_prompt_deterministic(self, advanced_service):
        r1 = advanced_service.generate_prompt(sample_intelligence())
        r2 = advanced_service.generate_prompt(sample_intelligence())
        assert r1["negative_prompt"] == r2["negative_prompt"]


class TestNoFabrication:
    def test_strict_no_fabrication(self, advanced_service):
        intel = empty_intelligence()
        result = advanced_service.generate_prompt(intel)
        full_text = " ".join(result["sections"].values()).lower()
        forbidden = [
            "sunset", "city", "street", "car", "dog", "cat", "child",
            "running", "jumping", "dramatic", "orchestral", "music",
            "close-up", "zoom", "pan", "dolly", "neon", "golden hour",
            "interior", "exterior", "dialogue", "voiceover",
        ]
        for word in forbidden:
            assert word not in full_text, f"fabricated content found: {word}"

    def test_only_intelligence_data_used(self, advanced_service):
        intel = sample_intelligence()
        result = advanced_service.generate_prompt(intel)
        assert "walking" in result["prompt"]
        assert "outdoor park" in result["prompt"]
        # No invented extras
        assert "flying" not in result["prompt"]
        assert "spaceship" not in result["prompt"]


class TestDeterministicOutput:
    def test_deterministic_output(self, advanced_service):
        r1 = advanced_service.generate_prompt(sample_intelligence(), style="cinematic")
        r2 = advanced_service.generate_prompt(sample_intelligence(), style="cinematic")
        assert r1 == r2

    def test_deterministic_across_styles(self, advanced_service):
        for style in VALID_STYLES:
            r1 = advanced_service.generate_prompt(sample_intelligence(), style=style)
            r2 = advanced_service.generate_prompt(sample_intelligence(), style=style)
            assert r1 == r2, f"non-deterministic output for style: {style}"


class TestNoAbsolutePaths:
    def test_no_absolute_paths_in_output(self, advanced_service):
        import json
        intel = sample_intelligence()
        result = advanced_service.generate_prompt(intel)
        serialized = json.dumps(result)
        assert '"C:/' not in serialized
        assert '"C:\\' not in serialized
        assert '"/home' not in serialized
        assert '"/Users' not in serialized
        assert '"/var' not in serialized
        # video_filename is a bare stored filename
        assert "/" not in result["video_filename"]
        assert "\\" not in result["video_filename"]

    def test_no_absolute_paths_empty(self, advanced_service):
        import json
        result = advanced_service.generate_prompt(empty_intelligence())
        serialized = json.dumps(result)
        assert "C:/" not in serialized
        assert "/home" not in serialized
