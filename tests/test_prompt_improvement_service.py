"""Tests for the quality-guided prompt improvement service (Day 22)."""
import inspect
import re

import pytest

from app.services.prompt_quality_service import (
    PromptQualityService,
    DIMENSIONS,
    WEAK_SCORE,
)
from app.services.prompt_improvement_service import (
    PromptImprovementService,
    GUIDANCE,
    IMPROVEMENT_HEADER,
)


@pytest.fixture
def quality():
    return PromptQualityService()


@pytest.fixture
def service(quality):
    return PromptImprovementService(quality)


DETAILED = (
    "Cinematic film grain style portrait of a person, the subject "
    "walking, looking around and gesturing in an outdoor forest street, "
    "camera tracking with shallow depth of field, soft lighting with rim "
    "light and golden hour glow, vibrant teal and orange palette with "
    "warm tones, layered foreground and rule of thirds composition, "
    "ambient sound with quiet music score."
)

SOURCE = "A person walks down a road."

EXPECTED_KEYS = {
    "source_prompt",
    "improved_prompt",
    "quality_before",
    "quality_after",
    "improvement_applied",
    "improvements",
    "preserved_information",
    "guidance_added",
    "guided_dimensions",
}

QUALITY_KEYS = {
    "overall_score",
    "completeness_percentage",
    "dimensions",
    "missing_dimensions",
    "suggestions",
}


def expected_improvements(quality, prompt):
    """Derive the expected improvements list from Day 21 directly."""
    report = quality.analyze_prompt(prompt)["quality"]
    expected = []
    for dim in DIMENSIONS:
        entry = report["dimensions"][dim]
        if not entry["present"]:
            reason = "missing"
        elif entry["score"] == WEAK_SCORE:
            reason = "weak"
        else:
            continue
        expected.append({
            "dimension": dim,
            "reason": reason,
            "guidance": GUIDANCE[dim],
        })
    return expected


def added_text(result):
    return result["improved_prompt"][len(result["source_prompt"]):]


class TestInputValidation:
    def test_empty_prompt_rejected(self, service):
        with pytest.raises(ValueError):
            service.improve_prompt("")

    @pytest.mark.parametrize("bad", ["   ", "\n", "\t", " \n \t "])
    def test_whitespace_only_rejected(self, service, bad):
        with pytest.raises(ValueError):
            service.improve_prompt(bad)

    @pytest.mark.parametrize("bad", [None, 1, 3.14, True, [], {}, b"bytes"])
    def test_non_string_rejected(self, service, bad):
        with pytest.raises(ValueError):
            service.improve_prompt(bad)


class TestResultStructure:
    def test_all_expected_keys_present(self, service):
        result = service.improve_prompt(SOURCE)
        assert set(result.keys()) == EXPECTED_KEYS

    def test_types(self, service):
        result = service.improve_prompt(SOURCE)
        assert isinstance(result["source_prompt"], str)
        assert isinstance(result["improved_prompt"], str)
        assert isinstance(result["quality_before"], dict)
        assert isinstance(result["quality_after"], dict)
        assert isinstance(result["improvement_applied"], bool)
        assert isinstance(result["improvements"], list)
        assert isinstance(result["preserved_information"], bool)
        assert isinstance(result["guidance_added"], bool)
        assert isinstance(result["guided_dimensions"], list)

    def test_quality_reports_have_day21_keys(self, service):
        result = service.improve_prompt(SOURCE)
        assert set(result["quality_before"].keys()) == QUALITY_KEYS
        assert set(result["quality_after"].keys()) == QUALITY_KEYS
        assert list(result["quality_before"]["dimensions"].keys()) == list(DIMENSIONS)
        assert list(result["quality_after"]["dimensions"].keys()) == list(DIMENSIONS)

    def test_quality_before_equals_direct_day21_analysis(self, quality, service):
        result = service.improve_prompt(SOURCE)
        direct = quality.analyze_prompt(SOURCE)["quality"]
        assert result["quality_before"] == direct

    def test_quality_after_equals_direct_analysis_of_improved(self, quality,
                                                              service):
        result = service.improve_prompt(SOURCE)
        direct = quality.analyze_prompt(result["improved_prompt"])["quality"]
        assert result["quality_after"] == direct

    def test_improvement_item_shape(self, service):
        result = service.improve_prompt(SOURCE)
        assert len(result["improvements"]) > 0
        for item in result["improvements"]:
            assert set(item.keys()) == {"dimension", "reason", "guidance"}


class TestImprovementsMapping:
    def test_improvements_match_missing_and_weak_only(self, quality, service):
        result = service.improve_prompt(SOURCE)
        assert result["improvements"] == expected_improvements(quality, SOURCE)

    def test_improvements_ordered_by_dimension_order(self, service):
        result = service.improve_prompt(SOURCE)
        dims = [i["dimension"] for i in result["improvements"]]
        assert dims == [d for d in DIMENSIONS if d in set(dims)]

    def test_no_duplicate_dimensions(self, service):
        result = service.improve_prompt(SOURCE)
        dims = [i["dimension"] for i in result["improvements"]]
        assert len(dims) == len(set(dims))

    def test_all_dimensions_valid_day21(self, service):
        result = service.improve_prompt(SOURCE)
        for item in result["improvements"]:
            assert item["dimension"] in DIMENSIONS
            assert item["reason"] in ("missing", "weak")
            assert item["guidance"] == GUIDANCE[item["dimension"]]

    def test_reason_matches_quality_before(self, service):
        result = service.improve_prompt(SOURCE)
        for item in result["improvements"]:
            entry = result["quality_before"]["dimensions"][item["dimension"]]
            if not entry["present"]:
                assert item["reason"] == "missing"
            else:
                assert entry["score"] == WEAK_SCORE
                assert item["reason"] == "weak"

    @pytest.mark.parametrize("prompt,expected_dim,expected_reason", [
        ("with shadows", "lighting", "weak"),
        ("Hello world.", "subject", "missing"),
        ("Hello world.", "audio", "missing"),
    ])
    def test_known_reasons(self, service, prompt, expected_dim,
                           expected_reason):
        result = service.improve_prompt(prompt)
        matched = [i for i in result["improvements"]
                   if i["dimension"] == expected_dim]
        assert len(matched) == 1
        assert matched[0]["reason"] == expected_reason

    def test_strong_dimensions_never_guided(self, quality, service):
        result = service.improve_prompt(DETAILED)
        guided = set(result["guided_dimensions"])
        for dim in DIMENSIONS:
            entry = result["quality_before"]["dimensions"][dim]
            if entry["present"] and entry["score"] > WEAK_SCORE:
                assert dim not in guided

    def test_fully_covered_prompt_no_improvements(self, service):
        result = service.improve_prompt(DETAILED)
        assert result["quality_before"]["missing_dimensions"] == []
        assert result["improvements"] == []
        assert result["improvement_applied"] is False
        assert result["guidance_added"] is False
        assert result["guided_dimensions"] == []
        assert result["improved_prompt"] == DETAILED

    def test_guided_dimensions_matches_improvements(self, service):
        result = service.improve_prompt(SOURCE)
        assert result["guided_dimensions"] == [
            i["dimension"] for i in result["improvements"]
        ]


class TestImprovedPromptFormat:
    def test_exact_expected_construction(self, service):
        result = service.improve_prompt(SOURCE)
        guidance_lines = "\n".join(
            i["guidance"] for i in result["improvements"]
        )
        expected = f"{SOURCE}\n\n{IMPROVEMENT_HEADER}\n{guidance_lines}"
        assert result["improved_prompt"] == expected

    def test_header_appears_exactly_once(self, service):
        result = service.improve_prompt(SOURCE)
        assert result["improved_prompt"].count(IMPROVEMENT_HEADER) == 1

    def test_source_is_prefix_of_improved(self, service):
        result = service.improve_prompt(SOURCE)
        assert result["improved_prompt"].startswith(SOURCE)
        assert SOURCE in result["improved_prompt"]

    def test_no_duplicate_guidance_lines(self, service):
        result = service.improve_prompt(SOURCE)
        lines = added_text(result).splitlines()
        guidance_lines = [ln for ln in lines if ln.startswith("[")]
        assert len(guidance_lines) > 0
        assert len(guidance_lines) == len(set(guidance_lines))

    def test_improved_is_source_plus_append_only(self, service):
        result = service.improve_prompt(SOURCE)
        assert result["improved_prompt"][:len(SOURCE)] == SOURCE


class TestNoFabrication:
    def test_added_text_is_only_guidance_and_header(self, service):
        result = service.improve_prompt(SOURCE)
        expected_added = (
            "\n\n" + IMPROVEMENT_HEADER + "\n"
            + "\n".join(i["guidance"] for i in result["improvements"])
        )
        assert added_text(result) == expected_added

    @pytest.mark.parametrize("word", [
        "sunset", "rain", "neon", "night", "dusk", "dawn", "beautiful",
        "Sarah", "Tokyo", "Ferrari", "woman", "car ", "dramatic music",
        "luxury", "cinematic",
    ])
    def test_fabricated_words_not_introduced(self, service, word):
        result = service.improve_prompt(SOURCE)
        added = added_text(result).lower()
        assert word.lower() not in added

    def test_no_fabricated_words_in_full_improved_prompt(self, service):
        result = service.improve_prompt(SOURCE)
        improved_lower = result["improved_prompt"].lower()
        for word in ("sunset", "rain", "neon", "beautiful", "sarah",
                     "tokyo", "ferrari", "luxury", "woman"):
            if word in SOURCE.lower():
                continue
            assert word not in improved_lower, word

    def test_preserved_information_true(self, service):
        result = service.improve_prompt(SOURCE)
        assert result["preserved_information"] is True

    def test_all_original_sentences_still_present(self, service):
        source = "A person walks down a road. The camera holds still."
        result = service.improve_prompt(source)
        for sentence in source.split(". "):
            assert sentence in result["improved_prompt"]
        assert result["source_prompt"] == source

    def test_guidance_is_instruction_not_claim(self, service):
        result = service.improve_prompt(SOURCE)
        for item in result["improvements"]:
            g = item["guidance"]
            assert g.startswith("[") and g.endswith("]")
            assert "if known" in g


class TestQualityAfterImprovement:
    def test_missing_dimensions_cleared_after_guidance(self, service):
        result = service.improve_prompt(SOURCE)
        assert result["improvement_applied"] is True
        assert result["quality_after"]["missing_dimensions"] == []

    def test_guided_dimensions_present_after(self, service):
        result = service.improve_prompt(SOURCE)
        for dim in result["guided_dimensions"]:
            assert result["quality_after"]["dimensions"][dim]["present"] is True

    def test_quality_after_deterministic(self, service):
        first = service.improve_prompt(SOURCE)
        second = service.improve_prompt(SOURCE)
        assert first["quality_after"] == second["quality_after"]

    def test_overall_score_not_decreased(self, service):
        result = service.improve_prompt(SOURCE)
        assert (result["quality_after"]["overall_score"]
                >= result["quality_before"]["overall_score"])
        assert (result["quality_after"]["completeness_percentage"]
                >= result["quality_before"]["completeness_percentage"])

    def test_no_guidance_means_quality_equal(self, service):
        result = service.improve_prompt(DETAILED)
        assert result["quality_after"] == result["quality_before"]


class TestDeterminism:
    def test_repeated_calls_identical(self, service):
        first = service.improve_prompt(SOURCE)
        second = service.improve_prompt(SOURCE)
        third = service.improve_prompt(SOURCE)
        assert first == second == third

    def test_case_insensitive_consistent_with_day21(self, quality, service):
        lower = service.improve_prompt(SOURCE)
        upper = service.improve_prompt(SOURCE.upper())
        assert lower["guided_dimensions"] == upper["guided_dimensions"]
        assert lower["improvements"] == upper["improvements"]
        assert upper["source_prompt"] == SOURCE.upper()
        assert upper["improved_prompt"].startswith(SOURCE.upper())
        # guidance suffix identical regardless of source casing
        assert added_text(lower) == added_text(upper)
        # Day21 quality reports are case-insensitive too
        assert lower["quality_before"] == upper["quality_before"]

    def test_no_timestamps_or_dates_in_improved_prompt(self, service):
        result = service.improve_prompt(SOURCE)
        assert not re.search(r"\d{4}-\d{2}-\d{2}", result["improved_prompt"])
        assert not re.search(r"\d{2}:\d{2}", result["improved_prompt"])
        assert "created" not in result["improved_prompt"].lower()
        assert "timestamp" not in result["improved_prompt"].lower()

    def test_no_random_values(self, quality, service):
        outputs = {service.improve_prompt(SOURCE)["improved_prompt"]
                   for _ in range(5)}
        assert len(outputs) == 1


class TestPreservation:
    def test_source_prompt_exactly_input(self, service):
        messy = "  Odd   spacing\nprompt  "
        result = service.improve_prompt(messy)
        assert result["source_prompt"] == messy

    def test_original_content_never_rewritten(self, service):
        source = "Alpha fact one. Beta fact two."
        result = service.improve_prompt(source)
        assert result["improved_prompt"].startswith(source)
        assert "Alpha fact one." in result["improved_prompt"]
        assert "Beta fact two." in result["improved_prompt"]

    def test_nothing_removed_from_source(self, quality, service):
        source = "A person walks down a road."
        result = service.improve_prompt(source)
        # every source word still present in order
        source_words = source.split()
        improved_words = result["improved_prompt"].split()
        assert improved_words[:len(source_words)] == source_words


class TestSafety:
    def test_no_absolute_paths_in_output(self, service):
        result = service.improve_prompt(SOURCE)
        text = str(result)
        for bad in ("C:\\", "C:/", "/home", "/Users", "/var/"):
            assert bad not in text

    def test_no_internal_object_names_in_output(self, service):
        result = service.improve_prompt(SOURCE)
        text = str(result)
        for token in ("PromptImprovementService", "PromptQualityService",
                      "_quality_service", "Traceback", "_storage",
                      "GUIDANCE"):
            assert token not in text, token

    def test_service_state_is_only_quality_service(self, service):
        assert set(vars(service).keys()) == {"quality_service"}

    def test_service_module_no_network_or_filesystem_access(self):
        source = inspect.getsource(
            __import__("app.services.prompt_improvement_service",
                       fromlist=["x"])
        )
        for forbidden in ("requests", "urllib", "socket", "http.client",
                          "subprocess", "open(", "os.path", "Path(",
                          "httpx", "aiohttp", "ftp", "import random",
                          "import datetime"):
            assert forbidden not in source, (
                f"forbidden dependency in improvement service: {forbidden}"
            )

    def test_no_state_modifying_helpers_in_module(self):
        import app.services.prompt_improvement_service as mod
        for name in dir(mod):
            if name.startswith("_"):
                continue
            for bad in ("write", "save", "delete", "store"):
                assert bad not in name.lower(), name

    def test_improvement_not_persisted_anywhere(self, service, quality):
        # The service is stateless: different prompts produce independent
        # results with no shared accumulation between calls.
        a = service.improve_prompt("A person walks down a road.")
        b = service.improve_prompt(DETAILED)
        assert a["improved_prompt"] != b["improved_prompt"]
        assert len(a["improvements"]) > 0
        assert b["improvements"] == []
        assert set(vars(service).keys()) == {"quality_service"}

    def test_guidance_map_covers_exactly_day21_dimensions(self):
        assert set(GUIDANCE.keys()) == set(DIMENSIONS)
        for dim in DIMENSIONS:
            g = GUIDANCE[dim]
            assert g.startswith("[") and g.endswith("]")
            assert "if known" in g
