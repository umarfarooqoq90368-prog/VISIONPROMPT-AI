"""Tests for the prompt refinement service (Day 14)."""
import pytest
from app.services.prompt_refinement_service import (
    PromptRefinementService,
    VALID_OPERATIONS,
)
from app.services.advanced_prompt_service import DEFAULT_NEGATIVE_PROMPT


@pytest.fixture
def service():
    return PromptRefinementService()


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

DEFAULT_PROMPT = "A cinematic scene awaiting detailed visual content."


class TestAllOperations:
    @pytest.mark.parametrize("operation", sorted(VALID_OPERATIONS))
    def test_all_six_operations(self, service, operation):
        result = service.refine(SOURCE_PROMPT, operation)
        assert set(result.keys()) == {
            "operation",
            "source_prompt",
            "refined_prompt",
            "negative_prompt",
            "preserved_information",
        }
        assert result["operation"] == operation
        assert result["source_prompt"] == SOURCE_PROMPT
        assert isinstance(result["refined_prompt"], str)
        assert result["refined_prompt"]
        assert result["preserved_information"] is True

    @pytest.mark.parametrize("operation", sorted(VALID_OPERATIONS))
    def test_deterministic_output(self, service, operation):
        r1 = service.refine(SOURCE_PROMPT, operation)
        r2 = service.refine(SOURCE_PROMPT, operation)
        assert r1 == r2


class TestRefine:
    def test_refine_restructures_sentences(self, service):
        result = service.refine(SOURCE_PROMPT, "refine")
        refined = result["refined_prompt"]
        assert ";" not in refined
        assert refined.endswith(".")
        assert refined != SOURCE_PROMPT

    def test_refine_preserves_content(self, service):
        result = service.refine(SOURCE_PROMPT, "refine")
        for snippet in CONTENT_SNIPPETS:
            assert snippet in result["refined_prompt"], f"missing: {snippet}"


class TestShorten:
    def test_shorten_produces_concise_output(self, service):
        result = service.refine(SOURCE_PROMPT, "shorten")
        refined = result["refined_prompt"]
        assert len(refined) < len(SOURCE_PROMPT)
        assert "Subject:" not in refined
        assert "Camera perspective:" not in refined
        assert "Composition:" not in refined

    def test_shorten_preserves_facts(self, service):
        result = service.refine(SOURCE_PROMPT, "shorten")
        refined = result["refined_prompt"]
        for snippet in ["a person", "eye-level", "warm sunlight", "fresh bread today", "3 scenes"]:
            assert snippet in refined, f"missing: {snippet}"
        assert result["preserved_information"] is True


class TestExpand:
    def test_expand_adds_structural_detail(self, service):
        result = service.refine(SOURCE_PROMPT, "expand")
        refined = result["refined_prompt"]
        assert refined != SOURCE_PROMPT
        assert len(refined) > len(SOURCE_PROMPT)
        assert "Objects: a red stall." in refined
        assert "Camera movement: static." in refined

    def test_expand_distinct_from_refine(self, service):
        expanded = service.refine(SOURCE_PROMPT, "expand")
        refined = service.refine(SOURCE_PROMPT, "refine")
        assert expanded["refined_prompt"] != refined["refined_prompt"]

    def test_expand_preserves_content(self, service):
        result = service.refine(SOURCE_PROMPT, "expand")
        for snippet in CONTENT_SNIPPETS:
            assert snippet in result["refined_prompt"], f"missing: {snippet}"


class TestStyleOperations:
    def test_cinematic_operation(self, service):
        result = service.refine(SOURCE_PROMPT, "cinematic")
        refined = result["refined_prompt"]
        assert "cinematic composition" in refined
        assert "commercial presentation" not in refined
        assert "realistic presentation" not in refined

    def test_realistic_operation(self, service):
        result = service.refine(SOURCE_PROMPT, "realistic")
        refined = result["refined_prompt"]
        assert "realistic presentation" in refined
        assert "cinematic composition" not in refined
        assert "naturalistic" in refined

    def test_commercial_operation(self, service):
        result = service.refine(SOURCE_PROMPT, "commercial")
        refined = result["refined_prompt"]
        assert "commercial presentation" in refined
        assert "cinematic composition" not in refined

    def test_commercial_invents_no_products_or_brands(self, service):
        result = service.refine(SOURCE_PROMPT, "commercial")
        refined = result["refined_prompt"].lower()
        for word in ["brand", "product", "luxury", "sale", "advert", "logo"]:
            assert word not in refined, f"fabricated: {word}"

    def test_style_operations_preserve_visual_style(self, service):
        for operation in ["cinematic", "realistic", "commercial"]:
            result = service.refine(SOURCE_PROMPT, operation)
            assert "naturalistic" in result["refined_prompt"]

    def test_style_operation_on_default_prompt(self, service):
        result = service.refine(DEFAULT_PROMPT, "commercial")
        refined = result["refined_prompt"]
        assert "A polished commercial scene" in refined
        assert "commercial presentation" in refined
        assert result["preserved_information"] is True


class TestEmptyInput:
    @pytest.mark.parametrize("operation", sorted(VALID_OPERATIONS))
    def test_empty_input_handled_safely(self, service, operation):
        result = service.refine("", operation)
        assert result["source_prompt"] == ""
        assert result["refined_prompt"] == ""
        assert result["preserved_information"] is True

    def test_whitespace_input(self, service):
        result = service.refine("   ", "refine")
        assert result["refined_prompt"] == "   "
        assert result["preserved_information"] is True


class TestInvalidOperation:
    def test_invalid_operation_raises(self, service):
        with pytest.raises(ValueError):
            service.refine(SOURCE_PROMPT, "reformat")

    def test_empty_operation_raises(self, service):
        with pytest.raises(ValueError):
            service.refine(SOURCE_PROMPT, "")

    def test_wrong_case_operation_raises(self, service):
        with pytest.raises(ValueError):
            service.refine(SOURCE_PROMPT, "REFINE")

    def test_non_string_operation_raises(self, service):
        with pytest.raises(ValueError):
            service.refine(SOURCE_PROMPT, None)
        with pytest.raises(ValueError):
            service.refine(SOURCE_PROMPT, 42)


class TestPreservation:
    @pytest.mark.parametrize("operation", sorted(VALID_OPERATIONS))
    def test_preserved_information_flag(self, service, operation):
        result = service.refine(SOURCE_PROMPT, operation)
        assert result["preserved_information"] is True

    @pytest.mark.parametrize("operation", sorted(VALID_OPERATIONS))
    def test_content_survives_every_operation(self, service, operation):
        result = service.refine(SOURCE_PROMPT, operation)
        refined = result["refined_prompt"]
        for snippet in CONTENT_SNIPPETS:
            assert snippet in refined, f"{operation} lost: {snippet}"


class TestNoFabrication:
    FORBIDDEN = [
        "spaceship",
        "dragon",
        "dialogue",
        "orchestral",
        "neon",
        "sunset",
        "car chase",
        "voiceover",
        "monster",
    ]

    @pytest.mark.parametrize("operation", sorted(VALID_OPERATIONS))
    def test_no_fabricated_information(self, service, operation):
        result = service.refine(SOURCE_PROMPT, operation)
        refined = result["refined_prompt"].lower()
        for word in self.FORBIDDEN:
            assert word not in refined, f"{operation} fabricated: {word}"

    @pytest.mark.parametrize("operation", sorted(VALID_OPERATIONS))
    def test_empty_source_gains_no_content(self, service, operation):
        result = service.refine("", operation)
        assert result["refined_prompt"] == ""


class TestNegativePrompt:
    def test_negative_prompt_preserved(self, service):
        result = service.refine(SOURCE_PROMPT, "refine", negative_prompt="custom negative")
        assert result["negative_prompt"] == "custom negative"

    def test_negative_prompt_defaults_to_generic(self, service):
        result = service.refine(SOURCE_PROMPT, "refine")
        assert result["negative_prompt"] == DEFAULT_NEGATIVE_PROMPT

    def test_negative_prompt_none_defaults(self, service):
        result = service.refine(SOURCE_PROMPT, "refine", negative_prompt=None)
        assert result["negative_prompt"] == DEFAULT_NEGATIVE_PROMPT

    def test_negative_prompt_blank_defaults(self, service):
        result = service.refine(SOURCE_PROMPT, "refine", negative_prompt="   ")
        assert result["negative_prompt"] == DEFAULT_NEGATIVE_PROMPT

    def test_negative_prompt_stays_generic(self, service):
        result = service.refine(SOURCE_PROMPT, "shorten")
        neg = result["negative_prompt"].lower()
        assert "blurry" in neg
        assert "watermark" in neg
        for word in ["person", "market", "dialogue"]:
            assert word not in neg


class TestMalformedInput:
    def test_none_source_raises(self, service):
        with pytest.raises(ValueError):
            service.refine(None, "refine")

    def test_list_source_raises(self, service):
        with pytest.raises(ValueError):
            service.refine(["prompt"], "refine")

    def test_dict_source_raises(self, service):
        with pytest.raises(ValueError):
            service.refine({"prompt": "x"}, "refine")

    def test_numeric_source_raises(self, service):
        with pytest.raises(ValueError):
            service.refine(123, "refine")
