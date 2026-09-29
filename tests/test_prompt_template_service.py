"""Tests for the prompt template service (Day 15)."""
import pytest
from app.services.prompt_template_service import (
    PromptTemplateService,
    VALID_TEMPLATES,
)
from app.services.advanced_prompt_service import DEFAULT_NEGATIVE_PROMPT


@pytest.fixture
def service():
    return PromptTemplateService()


SOURCE_PROMPT = (
    "Subject: a person; Action: walking through a market; "
    "Environment: an outdoor market Objects: a red stall; "
    "Camera perspective: eye-level Shot type: close-up Camera movement: static; "
    "Lighting: warm sunlight Color palette: amber, gold; "
    "Visual style: naturalistic; Color: amber; "
    "Audio language: en Audio text: fresh bread today; "
    "Composition: close-up shot Scene progression across 3 scenes, cinematic composition."
)

CONTENT_SNIPPETS = [
    "a person",
    "walking through a market",
    "an outdoor market",
    "a red stall",
    "eye-level",
    "close-up",
    "static",
    "warm sunlight",
    "amber",
    "gold",
    "naturalistic",
    "fresh bread today",
    "3 scenes",
]


def empty_intelligence():
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


class TestAllTemplates:
    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_all_five_templates(self, service, template):
        result = service.apply_template(SOURCE_PROMPT, template)
        assert set(result.keys()) == {
            "template",
            "source_prompt",
            "custom_instruction",
            "prompt",
            "negative_prompt",
            "preserved_information",
        }
        assert result["template"] == template
        assert result["source_prompt"] == SOURCE_PROMPT
        assert result["custom_instruction"] == ""
        assert isinstance(result["prompt"], str)
        assert result["prompt"]
        assert result["preserved_information"] is True

    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_templates_are_distinct(self, service, template):
        prompts = {
            t: service.apply_template(SOURCE_PROMPT, t)["prompt"]
            for t in VALID_TEMPLATES
        }
        assert len(set(prompts.values())) == 5

    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_templates_preserve_source_information(self, service, template):
        result = service.apply_template(SOURCE_PROMPT, template)
        for snippet in CONTENT_SNIPPETS:
            assert snippet in result["prompt"], f"{template} lost: {snippet}"
        assert result["preserved_information"] is True


class TestEmptyData:
    def test_empty_source_and_no_intelligence(self, service):
        result = service.apply_template("", "ai_video")
        assert result["source_prompt"] == ""
        assert result["prompt"] == ""
        assert result["preserved_information"] is True

    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_empty_intelligence_generates_safe_source(self, service, template):
        result = service.apply_template(
            "", template, intelligence=empty_intelligence()
        )
        assert result["source_prompt"]
        assert result["prompt"]
        assert result["preserved_information"] is True

    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_empty_intelligence_fabricates_nothing(self, service, template):
        result = service.apply_template(
            "", template, intelligence=empty_intelligence()
        )
        text = result["prompt"].lower()
        for word in ["person", "park", "walking", "dialogue", "sunset", "brand"]:
            assert word not in text, f"{template} fabricated: {word}"

    def test_whitespace_source_handled_safely(self, service):
        result = service.apply_template("   ", "documentary")
        assert result["prompt"] == "   "
        assert result["preserved_information"] is True


class TestValidSourcePrompt:
    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_valid_source_prompt_used(self, service, template):
        result = service.apply_template(SOURCE_PROMPT, template)
        assert result["source_prompt"] == SOURCE_PROMPT
        assert result["prompt"] != ""

    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_template_changes_presentation(self, service, template):
        result = service.apply_template(SOURCE_PROMPT, template)
        assert result["prompt"] != SOURCE_PROMPT

    def test_source_prompt_takes_precedence_over_intelligence(self, service):
        result = service.apply_template(
            SOURCE_PROMPT, "ai_video", intelligence=empty_intelligence()
        )
        assert result["source_prompt"] == SOURCE_PROMPT


class TestCustomInstructions:
    def test_empty_custom_instruction(self, service):
        with_empty = service.apply_template(
            SOURCE_PROMPT, "documentary", custom_instruction=""
        )
        with_none = service.apply_template(
            SOURCE_PROMPT, "documentary", custom_instruction=None
        )
        plain = service.apply_template(SOURCE_PROMPT, "documentary")
        assert with_empty == with_none == plain
        assert with_empty["custom_instruction"] == ""

    def test_make_it_concise(self, service):
        plain = service.apply_template(SOURCE_PROMPT, "cinematic_story")
        concise = service.apply_template(
            SOURCE_PROMPT, "cinematic_story", custom_instruction="make it concise"
        )
        assert len(concise["prompt"]) < len(plain["prompt"])
        assert "Subject:" not in concise["prompt"]
        for snippet in ["a person", "eye-level", "warm sunlight"]:
            assert snippet in concise["prompt"]
        assert concise["preserved_information"] is True

    def test_focus_on_camera_movement(self, service):
        result = service.apply_template(
            SOURCE_PROMPT, "cinematic_story", custom_instruction="focus on camera movement"
        )
        prompt = result["prompt"]
        assert prompt.index("eye-level") < prompt.index("a person")
        assert result["preserved_information"] is True

    def test_emphasize_lighting(self, service):
        result = service.apply_template(
            SOURCE_PROMPT, "documentary", custom_instruction="emphasize lighting"
        )
        prompt = result["prompt"]
        assert prompt.index("warm sunlight") < prompt.index("a person")
        assert result["preserved_information"] is True

    def test_suitable_for_ai_video_generator(self, service):
        plain = service.apply_template(SOURCE_PROMPT, "commercial_ad")
        ai = service.apply_template(
            SOURCE_PROMPT,
            "commercial_ad",
            custom_instruction="make the prompt suitable for an AI video generator",
        )
        assert "Subject:" not in ai["prompt"]
        assert len(ai["prompt"]) < len(plain["prompt"])
        for snippet in ["a person", "fresh bread today", "3 scenes"]:
            assert snippet in ai["prompt"]
        assert ai["preserved_information"] is True

    def test_unsupported_instruction_cannot_add_facts(self, service):
        plain = service.apply_template(SOURCE_PROMPT, "social_media")
        with_dragon = service.apply_template(
            SOURCE_PROMPT, "social_media", custom_instruction="add a dragon flying over a city"
        )
        assert "dragon" not in with_dragon["prompt"]
        assert "city" not in with_dragon["prompt"]
        assert with_dragon["prompt"] == plain["prompt"]
        assert with_dragon["custom_instruction"] == "add a dragon flying over a city"

    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_instruction_never_enters_prompt(self, service, template):
        instruction = "insert a celebrity cameo and luxury brands"
        result = service.apply_template(
            SOURCE_PROMPT, template, custom_instruction=instruction
        )
        text = result["prompt"].lower()
        for word in ["celebrity", "cameo", "luxury", "brands"]:
            assert word not in text, f"{template}: instruction leaked: {word}"


class TestInvalidTemplate:
    def test_invalid_template_raises(self, service):
        with pytest.raises(ValueError):
            service.apply_template(SOURCE_PROMPT, "meme")

    def test_empty_template_raises(self, service):
        with pytest.raises(ValueError):
            service.apply_template(SOURCE_PROMPT, "")

    def test_none_template_raises(self, service):
        with pytest.raises(ValueError):
            service.apply_template(SOURCE_PROMPT, None)

    def test_non_string_template_raises(self, service):
        with pytest.raises(ValueError):
            service.apply_template(SOURCE_PROMPT, 42)


class TestDeterminism:
    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_deterministic_output(self, service, template):
        r1 = service.apply_template(SOURCE_PROMPT, template)
        r2 = service.apply_template(SOURCE_PROMPT, template)
        assert r1 == r2

    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_deterministic_with_instruction(self, service, template):
        r1 = service.apply_template(
            SOURCE_PROMPT, template, custom_instruction="make it concise"
        )
        r2 = service.apply_template(
            SOURCE_PROMPT, template, custom_instruction="make it concise"
        )
        assert r1 == r2


class TestNoFabrication:
    FORBIDDEN = [
        "spaceship", "dragon", "celebrity", "luxury", "brand",
        "product", "voiceover", "orchestral", "neon", "sunset", "car chase",
    ]

    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_no_fabricated_information(self, service, template):
        result = service.apply_template(SOURCE_PROMPT, template)
        text = result["prompt"].lower()
        for word in self.FORBIDDEN:
            assert word not in text, f"{template} fabricated: {word}"

    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_only_source_words_rephrased(self, service, template):
        result = service.apply_template(SOURCE_PROMPT, template)
        text = result["prompt"]
        for snippet in CONTENT_SNIPPETS:
            assert snippet in text, f"{template} lost: {snippet}"


class TestNegativePrompt:
    def test_negative_prompt_preserved(self, service):
        result = service.apply_template(
            SOURCE_PROMPT, "ai_video", negative_prompt="custom negative"
        )
        assert result["negative_prompt"] == "custom negative"

    def test_negative_prompt_defaults_to_generic(self, service):
        result = service.apply_template(SOURCE_PROMPT, "ai_video")
        assert result["negative_prompt"] == DEFAULT_NEGATIVE_PROMPT

    def test_negative_prompt_none_defaults(self, service):
        result = service.apply_template(
            SOURCE_PROMPT, "ai_video", negative_prompt=None
        )
        assert result["negative_prompt"] == DEFAULT_NEGATIVE_PROMPT

    @pytest.mark.parametrize("template", sorted(VALID_TEMPLATES))
    def test_negative_prompt_stays_generic(self, service, template):
        result = service.apply_template(SOURCE_PROMPT, template)
        neg = result["negative_prompt"].lower()
        assert "blurry" in neg
        assert "watermark" in neg
        for word in ["person", "market", "dialogue"]:
            assert word not in neg


class TestMalformedInput:
    def test_none_source_raises(self, service):
        with pytest.raises(ValueError):
            service.apply_template(None, "ai_video")

    def test_list_source_raises(self, service):
        with pytest.raises(ValueError):
            service.apply_template(["prompt"], "ai_video")

    def test_dict_source_raises(self, service):
        with pytest.raises(ValueError):
            service.apply_template({"prompt": "x"}, "ai_video")

    def test_numeric_source_raises(self, service):
        with pytest.raises(ValueError):
            service.apply_template(123, "ai_video")

    def test_non_string_instruction_raises(self, service):
        with pytest.raises(ValueError):
            service.apply_template(SOURCE_PROMPT, "ai_video", custom_instruction=42)
        with pytest.raises(ValueError):
            service.apply_template(
                SOURCE_PROMPT, "ai_video", custom_instruction=["concise"]
            )

    def test_non_dict_intelligence_raises(self, service):
        with pytest.raises(ValueError):
            service.apply_template(SOURCE_PROMPT, "ai_video", intelligence="intel")
        with pytest.raises(ValueError):
            service.apply_template(SOURCE_PROMPT, "ai_video", intelligence=[1, 2])
