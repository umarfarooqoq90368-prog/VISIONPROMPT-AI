"""Tests for the prompt quality analyzer service (Day 21)."""
import inspect

import pytest

from app.services.prompt_quality_service import (
    PromptQualityService,
    DIMENSIONS,
    SIGNALS,
    WEAK_SCORE,
)


@pytest.fixture
def service():
    return PromptQualityService()


DETAILED = (
    "Cinematic film grain style portrait of a person, the subject "
    "walking, looking around and gesturing in an outdoor forest street, "
    "camera tracking with shallow depth of field, soft lighting with rim "
    "light and golden hour glow, vibrant teal and orange palette with "
    "warm tones, layered foreground and rule of thirds composition, "
    "ambient sound with quiet music score."
)

SINGLE_DIMENSION_PROMPTS = {
    "subject": ("a portrait of a person", 70),
    "action": ("walking slowly then running", 70),
    "environment": ("in a forest environment", 70),
    "camera": ("a wide shot with camera tracking", 100),
    "lighting": ("soft lighting with rim light", 100),
    "visual_style": ("cinematic film grain style", 100),
    "color": ("vibrant teal and orange palette", 100),
    "composition": ("layered foreground with negative space and symmetry", 100),
    "audio": ("ambient sound and quiet music", 100),
}


class TestInputValidation:
    def test_empty_prompt_rejected(self, service):
        with pytest.raises(ValueError):
            service.analyze_prompt("")

    @pytest.mark.parametrize("bad", ["   ", "\n", "\t", " \n \t "])
    def test_whitespace_only_rejected(self, service, bad):
        with pytest.raises(ValueError):
            service.analyze_prompt(bad)

    @pytest.mark.parametrize("bad", [None, 1, 3.14, True, [], {}, b"bytes"])
    def test_non_string_rejected(self, service, bad):
        with pytest.raises(ValueError):
            service.analyze_prompt(bad)


class TestBasicStructure:
    def test_short_prompt_all_missing(self, service):
        report = service.analyze_prompt("Hello world.")
        assert set(report.keys()) == {"prompt", "quality"}
        quality = report["quality"]
        assert set(quality.keys()) == {
            "overall_score",
            "completeness_percentage",
            "dimensions",
            "missing_dimensions",
            "suggestions",
        }
        assert list(quality["dimensions"].keys()) == list(DIMENSIONS)
        for dim in DIMENSIONS:
            assert quality["dimensions"][dim] == {"present": False, "score": 0}
        assert quality["missing_dimensions"] == list(DIMENSIONS)
        assert quality["overall_score"] == 0
        assert quality["completeness_percentage"] == 0

    def test_short_prompt_suggestions_are_add_each_dim(self, service):
        report = service.analyze_prompt("Hello world.")
        assert report["quality"]["suggestions"] == [
            f"Add {dim.replace('_', ' ')} information." for dim in DIMENSIONS
        ]

    def test_detailed_prompt_all_present_max_score(self, service):
        report = service.analyze_prompt(DETAILED)
        quality = report["quality"]
        for dim in DIMENSIONS:
            assert quality["dimensions"][dim] == {"present": True, "score": 100}
        assert quality["missing_dimensions"] == []
        assert quality["suggestions"] == []
        assert quality["overall_score"] == 100
        assert quality["completeness_percentage"] == 100

    def test_prompt_echoed_unchanged(self, service):
        original = "  Cinematic   portrait\n of PERSON  "
        report = service.analyze_prompt(original)
        assert report["prompt"] == original


class TestSingleDimensionDetection:
    @pytest.mark.parametrize("dim,prompt,expected_score", [
        (d, p, s) for d, (p, s) in SINGLE_DIMENSION_PROMPTS.items()
    ])
    def test_only_target_dimension_present(self, service, dim, prompt,
                                           expected_score):
        report = service.analyze_prompt(prompt)
        dimensions = report["quality"]["dimensions"]
        for other in DIMENSIONS:
            if other == dim:
                assert dimensions[other]["present"] is True
                assert dimensions[other]["score"] == expected_score
            else:
                assert dimensions[other]["present"] is False, (
                    f"{other} falsely detected for prompt: {prompt!r}"
                )
                assert dimensions[other]["score"] == 0

    @pytest.mark.parametrize("dim", DIMENSIONS)
    def test_missing_list_matches_present_flags(self, service, dim):
        prompt = SINGLE_DIMENSION_PROMPTS[dim][0]
        quality = service.analyze_prompt(prompt)["quality"]
        expected_missing = [d for d in DIMENSIONS
                            if not quality["dimensions"][d]["present"]]
        assert quality["missing_dimensions"] == expected_missing


class TestScoringModel:
    @pytest.mark.parametrize("prompt,score", [
        ("with shadows", WEAK_SCORE),
        ("a portrait of a person", 70),
        ("soft lighting with rim light", 100),
    ])
    def test_tier_scores(self, service, prompt, score):
        quality = service.analyze_prompt(prompt)["quality"]
        scores = [quality["dimensions"][d]["score"] for d in DIMENSIONS]
        assert max(scores) == score

    @pytest.mark.parametrize("prompt", [
        "Hello world.",
        "a portrait of a person",
        "soft lighting with rim light",
        DETAILED,
    ])
    def test_scores_are_ints_in_bounds(self, service, prompt):
        quality = service.analyze_prompt(prompt)["quality"]
        assert type(quality["overall_score"]) is int
        assert type(quality["completeness_percentage"]) is int
        assert 0 <= quality["overall_score"] <= 100
        assert 0 <= quality["completeness_percentage"] <= 100
        for dim in DIMENSIONS:
            entry = quality["dimensions"][dim]
            assert type(entry["present"]) is bool
            assert type(entry["score"]) is int
            assert 0 <= entry["score"] <= 100
            assert entry["score"] in (0, WEAK_SCORE, 70, 100)

    def test_overall_and_completeness_math(self, service):
        quality = service.analyze_prompt("a portrait of a person")["quality"]
        # Only subject present with score 70: mean = 70/9 -> 8,
        # completeness = 1/9 -> 11.
        assert quality["overall_score"] == 8
        assert quality["completeness_percentage"] == 11

    def test_six_present_dimensions_completeness(self, service):
        prompt = (
            "a portrait of a person walking in a forest street "
            "camera tracking soft lighting vibrant teal palette"
        )
        quality = service.analyze_prompt(prompt)["quality"]
        present = [d for d in DIMENSIONS if quality["dimensions"][d]["present"]]
        assert len(present) == 6
        assert quality["completeness_percentage"] == 67


class TestSuggestions:
    def test_weak_dimension_gets_expand_suggestion(self, service):
        quality = service.analyze_prompt("with shadows")["quality"]
        assert quality["dimensions"]["lighting"] == {
            "present": True, "score": WEAK_SCORE,
        }
        assert "Expand lighting information for better coverage." in (
            quality["suggestions"]
        )

    def test_suggestions_cover_missing_then_weak(self, service):
        quality = service.analyze_prompt("with shadows")["quality"]
        assert len(quality["suggestions"]) == 9  # 8 missing + 1 weak

    def test_no_suggestions_for_strong_dimensions(self, service):
        quality = service.analyze_prompt(DETAILED)["quality"]
        assert quality["suggestions"] == []

    def test_suggestion_order_follows_dimension_order(self, service):
        quality = service.analyze_prompt("with shadows")["quality"]
        lighting_index = DIMENSIONS.index("lighting")
        expand = [
            i for i, s in enumerate(quality["suggestions"])
            if s.startswith("Expand")
        ]
        assert expand == [lighting_index]

    def test_suggestions_match_missing_and_weak_only(self, service):
        quality = service.analyze_prompt("with shadows")["quality"]
        for suggestion in quality["suggestions"]:
            name = suggestion.split()[1] + (
                " " + suggestion.split()[2]
                if suggestion.split()[1] == "visual" else ""
            )
            normalized = name.replace(" ", "_").rstrip(".")
            if suggestion.startswith("Add"):
                assert normalized in quality["missing_dimensions"]


class TestDeterminismAndSafety:
    def test_repeated_analysis_identical(self, service):
        first = service.analyze_prompt(DETAILED)
        second = service.analyze_prompt(DETAILED)
        third = service.analyze_prompt(DETAILED)
        assert first == second == third

    def test_case_insensitive_detection(self, service):
        lower = service.analyze_prompt("a portrait of a person")
        upper = service.analyze_prompt("A PORTRAIT OF A PERSON")
        assert lower["quality"] == upper["quality"]

    def test_whitespace_normalization(self, service):
        messy = service.analyze_prompt("a   portrait\t of\n a person")
        clean = service.analyze_prompt("a portrait of a person")
        assert messy["quality"] == clean["quality"]

    def test_no_internal_state_on_service(self, service):
        assert not hasattr(service, "_storage")
        assert not hasattr(service, "history")
        assert not hasattr(service, "prompt")
        assert vars(service) == {}

    def test_service_module_no_network_or_filesystem_access(self):
        source = inspect.getsource(
            __import__("app.services.prompt_quality_service",
                       fromlist=["x"])
        )
        for forbidden in ("requests", "urllib", "socket", "http.client",
                          "subprocess", "open(", "os.path", "Path(",
                          "httpx", "aiohttp", "ftp"):
            assert forbidden not in source, (
                f"forbidden dependency in quality service: {forbidden}"
            )

    def test_report_contains_no_absolute_paths(self, service):
        report = service.analyze_prompt(DETAILED)
        text = str(report)
        assert "C:\\" not in text
        assert "/home/" not in text
        assert "C:/" not in text
        assert "PromptQualityService" not in text

    def test_all_dimension_names_have_signals(self):
        assert set(SIGNALS.keys()) == set(DIMENSIONS)
        for dim in DIMENSIONS:
            assert len(SIGNALS[dim]) >= 3

    def test_module_has_no_state_modifying_helpers(self):
        import app.services.prompt_quality_service as mod
        public = [name for name in dir(mod) if not name.startswith("_")]
        for name in public:
            assert "write" not in name.lower()
            assert "save" not in name.lower()
            assert "delete" not in name.lower()
            assert "store" not in name.lower()
