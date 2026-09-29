"""Tests for the prompt generation service."""
import pytest
from app.services.prompt_service import PromptGenerationService


@pytest.fixture
def prompt_service():
    return PromptGenerationService()


@pytest.fixture
def sample_analysis():
    return {
        "video_filename": "example.mp4",
        "frames_analyzed": 5,
        "analysis": {
            "subjects": ["a young man"],
            "actions": ["walking toward a car"],
            "environment": "urban street at sunset",
            "camera": {
                "perspective": "eye level",
                "shot_type": "medium shot",
                "movement": "slow tracking shot",
            },
            "lighting": "warm sunset lighting",
            "visual_style": "cinematic realistic",
            "color_palette": ["amber", "orange"],
            "objects": ["a red car"],
        },
        "frame_observations": [
            {
                "frame_index": 1,
                "timestamp_seconds": 0.0,
                "frame_filename": "frame_000001.jpg",
                "description": "A mock description",
                "model": "mock-vision-provider",
            }
        ],
    }


class TestPromptServiceCore:
    def test_empty_analysis_produces_minimal_prompt(self, prompt_service):
        analysis = {
            "video_filename": "test.mp4",
            "frames_analyzed": 0,
            "analysis": {},
            "frame_observations": [],
        }
        result = prompt_service.generate_prompt(analysis, style="cinematic")
        assert result["prompt"]
        assert len(result["prompt"]) > 0
        assert result["negative_prompt"] is None

    def test_subjects_appear_in_prompt(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert "young man" in result["prompt"].lower()

    def test_actions_appear_in_prompt(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert "walking" in result["prompt"].lower()

    def test_environment_appears_in_prompt(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert "urban street" in result["prompt"].lower()

    def test_camera_information_appears_in_prompt(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert "eye level" in result["prompt"].lower()
        assert "medium shot" in result["prompt"].lower()

    def test_lighting_appears_in_prompt(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert "sunset" in result["prompt"].lower()

    def test_visual_style_appears_in_prompt(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert "cinematic" in result["prompt"].lower()

    def test_empty_fields_are_not_fabricated(self, prompt_service):
        analysis = {
            "video_filename": "test.mp4",
            "frames_analyzed": 0,
            "analysis": {
                "subjects": [],
                "actions": [],
                "environment": "",
                "camera": {},
                "lighting": "",
                "visual_style": "",
                "color_palette": [],
                "objects": [],
            },
            "frame_observations": [],
        }
        result = prompt_service.generate_prompt(analysis, style="cinematic")
        assert "a young man" not in result["prompt"].lower()
        assert "walking" not in result["prompt"].lower()
        assert "car" not in result["prompt"].lower()

    def test_cinematic_style_works(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert result["style"] == "cinematic"
        assert "cinematic" in result["prompt"].lower()

    def test_realistic_style_works(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="realistic")
        assert result["style"] == "realistic"

    def test_commercial_style_works(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="commercial")
        assert result["style"] == "commercial"

    def test_invalid_style_rejected(self, prompt_service, sample_analysis):
        with pytest.raises(ValueError):
            prompt_service.generate_prompt(sample_analysis, style="fantasy")

    def test_no_raw_json_in_prompt(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert "{" not in result["prompt"]
        assert "}" not in result["prompt"]
        assert '"' not in result["prompt"]

    def test_no_absolute_paths_in_prompt(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert "/" not in result["prompt"]
        assert "\\" not in result["prompt"]
        assert "storage" not in result["prompt"].lower()

    def test_deterministic_output(self, prompt_service, sample_analysis):
        result1 = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        result2 = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert result1["prompt"] == result2["prompt"]

    def test_color_palette_appears_when_provided(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert "amber" in result["prompt"].lower() or "orange" in result["prompt"].lower()

    def test_objects_appear_in_prompt(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        assert "red car" in result["prompt"].lower()

    def test_prompt_reads_naturally(self, prompt_service, sample_analysis):
        result = prompt_service.generate_prompt(sample_analysis, style="cinematic")
        prompt = result["prompt"]
        assert prompt[0].isupper()
        assert prompt.endswith(".")

    def test_empty_analysis_cinematic_default(self, prompt_service):
        analysis = {
            "video_filename": "test.mp4",
            "frames_analyzed": 0,
            "analysis": {},
            "frame_observations": [],
        }
        result = prompt_service.generate_prompt(analysis, style="cinematic")
        assert "cinematic" in result["prompt"].lower()

    def test_empty_analysis_realistic(self, prompt_service):
        analysis = {
            "video_filename": "test.mp4",
            "frames_analyzed": 0,
            "analysis": {},
            "frame_observations": [],
        }
        result = prompt_service.generate_prompt(analysis, style="realistic")
        assert "realistic" in result["prompt"].lower()

    def test_no_fabricated_people(self, prompt_service, sample_analysis):
        empty_analysis = {
            "video_filename": "test.mp4",
            "frames_analyzed": 0,
            "analysis": {
                "subjects": [],
                "actions": [],
                "environment": "",
                "camera": {},
                "lighting": "",
                "visual_style": "",
                "color_palette": [],
                "objects": [],
            },
            "frame_observations": [],
        }
        result = prompt_service.generate_prompt(empty_analysis, style="cinematic")
        assert "person" not in result["prompt"].lower()
        assert "man" not in result["prompt"].lower()
        assert "woman" not in result["prompt"].lower()

    def test_commercial_style_no_fabrication(self, prompt_service, sample_analysis):
        empty_analysis = {
            "video_filename": "test.mp4",
            "frames_analyzed": 0,
            "analysis": {
                "subjects": [],
                "actions": [],
                "environment": "",
                "camera": {},
                "lighting": "",
                "visual_style": "",
                "color_palette": [],
                "objects": [],
            },
            "frame_observations": [],
        }
        result = prompt_service.generate_prompt(empty_analysis, style="commercial")
        assert result["style"] == "commercial"
        assert "commercial" in result["prompt"].lower()
