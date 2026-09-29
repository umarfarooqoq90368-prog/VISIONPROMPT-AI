"""Tests for the production readiness validator service (Day 24)."""
import inspect
import json

import pytest

from app.services.prompt_quality_service import (
    PromptQualityService,
    DIMENSIONS,
)
from app.services.prompt_readiness_service import (
    PromptReadinessService,
    REQUIRED_DIMENSIONS,
    SUPPORTING_DIMENSIONS,
)

# --- Fixture prompts (Day 21 verified) -------------------------------------
# FULL: all 9 dimensions present at score 100 -> ready, coverage 100
FULL = ("Cinematic film grain style portrait of a person, the subject "
        "walking, looking around and gesturing in an outdoor forest "
        "street, camera tracking with shallow depth of field, soft "
        "lighting with rim light and golden hour glow, vibrant teal and "
        "orange palette with warm tones, layered foreground and rule of "
        "thirds composition, ambient sound with quiet music score.")

# REQ_ONLY: all 7 required present, color/audio absent -> ready
REQ_ONLY = ("Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, camera tracking with shallow depth of field, soft "
            "lighting with rim light and golden hour glow, layered "
            "foreground and rule of thirds composition.")

# CITY: subject weak (40), environment present (70), rest missing -> 14
CITY = "A person walks through a city street."

# WEAK_CAM: camera weak (40), all other required present -> 86
WEAK_CAM = ("Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, tracking only, soft lighting with rim light and "
            "golden hour glow, vibrant teal and orange palette with warm "
            "tones, layered foreground and rule of thirds composition, "
            "ambient sound with quiet music score.")

# COV71: 5 required present, 1 missing (composition), 1 weak (camera)
COV71 = ("Cinematic film grain style portrait of a person, the subject "
         "walking, looking around and gesturing in an outdoor forest "
         "street, tracking only, soft lighting with rim light and golden "
         "hour glow, vibrant teal and orange palette with warm tones, "
         "ambient sound with quiet music score.")

MINIMAL = "nothing specific at all"


class FakeQualityService:
    """Deterministic stub returning pre-set Day 21 scores per dimension."""

    def __init__(self, scores):
        self._scores = scores

    def analyze_prompt(self, prompt):
        return {
            "prompt": prompt,
            "quality": {
                "dimensions": {
                    dim: {"present": self._scores[dim] > 0,
                          "score": self._scores[dim]}
                    for dim in DIMENSIONS
                },
            },
        }


def service_with(scores):
    return PromptReadinessService(FakeQualityService(scores))


@pytest.fixture
def service():
    return PromptReadinessService(PromptQualityService())


class TestValidation:
    @pytest.mark.parametrize("bad", [None, 42, ["a"], {"a": 1}, True])
    def test_non_string_prompt_raises(self, service, bad):
        with pytest.raises(ValueError, match="prompt must be a string"):
            service.validate_prompt(bad)

    @pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
    def test_empty_or_whitespace_prompt_raises(self, service, bad):
        with pytest.raises(ValueError, match="prompt must not be empty"):
            service.validate_prompt(bad)

    def test_service_state_only_constructor_dep(self):
        qs = PromptQualityService()
        svc = PromptReadinessService(qs)
        assert set(vars(svc).keys()) == {"quality_service"}
        assert svc.quality_service is qs


class TestStructure:
    def test_result_keys(self, service):
        result = service.validate_prompt(FULL)
        assert set(result.keys()) == {"prompt", "readiness"}
        assert result["prompt"] == FULL

    def test_readiness_keys(self, service):
        readiness = service.validate_prompt(FULL)["readiness"]
        assert set(readiness.keys()) == {
            "status", "required_dimensions", "supporting_dimensions",
            "checklist", "coverage", "missing_dimensions",
            "weak_dimensions", "suggestions",
        }

    def test_required_and_supporting_dimension_lists(self, service):
        readiness = service.validate_prompt(FULL)["readiness"]
        assert readiness["required_dimensions"] == [
            "subject", "action", "environment", "camera", "lighting",
            "visual_style", "composition",
        ]
        assert readiness["supporting_dimensions"] == ["color", "audio"]
        combined = (readiness["required_dimensions"]
                    + readiness["supporting_dimensions"])
        assert set(combined) == set(DIMENSIONS), "covers Day21 dimensions"
        assert set(readiness["required_dimensions"]).isdisjoint(
            readiness["supporting_dimensions"]
        )

    def test_service_reuses_day21_dimension_order(self, service):
        checklist = service.validate_prompt(FULL)["readiness"]["checklist"]
        assert [c["dimension"] for c in checklist] == list(DIMENSIONS)

    def test_checklist_item_keys(self, service):
        checklist = service.validate_prompt(CITY)["readiness"]["checklist"]
        for item in checklist:
            assert set(item.keys()) == {
                "dimension", "status", "present", "score", "message",
            }
            assert item["status"] in ("present", "weak", "missing")
            assert type(item["present"]) is bool
            assert type(item["score"]) is int

    def test_coverage_keys(self, service):
        coverage = service.validate_prompt(CITY)["readiness"]["coverage"]
        assert set(coverage.keys()) == {
            "required_total", "required_present", "required_missing",
            "required_weak", "required_coverage_percentage",
            "supporting_total", "supporting_present",
            "supporting_missing", "supporting_weak",
            "supporting_coverage_percentage",
        }
        assert coverage["required_total"] == 7
        assert coverage["supporting_total"] == 2


class TestStatusMapping:
    """Day21 scores map: 100/70 -> present, 40 -> weak, 0 -> missing."""

    @pytest.mark.parametrize("scores,expected", [
        ({d: 100 for d in DIMENSIONS}, "present"),
        ({d: 70 for d in DIMENSIONS}, "present"),
        ({d: 40 for d in DIMENSIONS}, "weak"),
        ({d: 0 for d in DIMENSIONS}, "missing"),
    ])
    def test_all_scores_map_consistently(self, scores, expected):
        svc = service_with(scores)
        readiness = svc.validate_prompt(FULL)["readiness"]
        for item in readiness["checklist"]:
            assert item["status"] == expected, item["dimension"]

    @pytest.mark.parametrize("score,status,present_flag", [
        (100, "present", True),
        (70, "present", True),
        (40, "weak", False),
        (0, "missing", False),
    ])
    def test_single_dimension_mapping(self, score, status, present_flag):
        scores = {d: 100 for d in DIMENSIONS}
        scores["camera"] = score
        checklist = service_with(scores).validate_prompt(FULL)["readiness"][
            "checklist"]
        camera = next(c for c in checklist if c["dimension"] == "camera")
        assert camera["status"] == status
        assert camera["present"] is present_flag
        assert camera["score"] == score, "Day21 score echoed unaltered"

    def test_status_mapping_against_real_day21(self, service):
        checklist = service.validate_prompt(CITY)["readiness"]["checklist"]
        day21 = PromptQualityService().analyze_prompt(CITY)["quality"]
        for item in checklist:
            score = day21["dimensions"][item["dimension"]]["score"]
            assert item["score"] == score
            expected = ("present" if score >= 70
                        else "weak" if score > 0 else "missing")
            assert item["status"] == expected

    def test_no_second_scoring_logic(self, service):
        # checklist score must be byte-identical to Day21 for every dim
        day21 = PromptQualityService().analyze_prompt(FULL)["quality"]
        checklist = service.validate_prompt(FULL)["readiness"]["checklist"]
        for item in checklist:
            assert item["score"] == day21["dimensions"][item["dimension"]][
                "score"]


class TestFullyCoveredPrompt:
    @pytest.fixture
    def readiness(self, service):
        return service.validate_prompt(FULL)["readiness"]

    def test_status_ready(self, readiness):
        assert readiness["status"] == "ready"

    def test_required_coverage_100(self, readiness):
        cov = readiness["coverage"]
        assert cov["required_total"] == 7
        assert cov["required_present"] == 7
        assert cov["required_missing"] == 0
        assert cov["required_weak"] == 0
        assert cov["required_coverage_percentage"] == 100

    def test_supporting_present(self, readiness):
        cov = readiness["coverage"]
        assert cov["supporting_present"] == 2
        assert cov["supporting_missing"] == 0
        assert cov["supporting_weak"] == 0
        assert cov["supporting_coverage_percentage"] == 100

    def test_no_missing_or_weak(self, readiness):
        assert readiness["missing_dimensions"] == []
        assert readiness["weak_dimensions"] == []
        assert readiness["suggestions"] == []

    def test_all_checklist_present(self, readiness):
        labels = {"visual_style": "Visual style"}
        for item in readiness["checklist"]:
            assert item["status"] == "present"
            assert item["present"] is True
            label = labels.get(item["dimension"],
                               item["dimension"].capitalize())
            assert item["message"] == f"{label} information detected."


class TestRequiredDimensionsMissing:
    @pytest.fixture
    def readiness(self, service):
        return service.validate_prompt(CITY)["readiness"]

    def test_status_needs_attention(self, readiness):
        assert readiness["status"] == "needs_attention"

    def test_missing_and_weak_lists(self, readiness):
        assert readiness["weak_dimensions"] == ["subject"]
        assert readiness["missing_dimensions"] == [
            "action", "camera", "lighting", "visual_style", "color",
            "composition", "audio",
        ]

    def test_no_invented_camera_or_lighting(self, readiness):
        by_dim = {c["dimension"]: c for c in readiness["checklist"]}
        for dim in ("camera", "lighting", "visual_style", "composition",
                    "color", "audio"):
            assert by_dim[dim]["status"] == "missing", dim
            assert by_dim[dim]["score"] == 0

    def test_coverage_counts(self, readiness):
        cov = readiness["coverage"]
        assert cov["required_present"] == 1
        assert cov["required_weak"] == 1
        assert cov["required_missing"] == 5
        assert cov["required_coverage_percentage"] == 14

    def test_suggestions_exact(self, readiness):
        assert readiness["suggestions"] == [
            "Expand subject information if known.",
            "Specify action information if known.",
            "Specify camera information if known.",
            "Specify lighting information if known.",
            "Specify visual style information if known.",
            "Specify color information if known.",
            "Specify composition information if known.",
            "Specify audio information if known.",
        ]


class TestSupportingDimensionsMissing:
    @pytest.fixture
    def readiness(self, service):
        return service.validate_prompt(REQ_ONLY)["readiness"]

    def test_status_stays_ready(self, readiness):
        assert readiness["status"] == "ready", \
            "missing supporting dims must not block ready"

    def test_required_coverage_100(self, readiness):
        cov = readiness["coverage"]
        assert cov["required_present"] == 7
        assert cov["required_missing"] == 0
        assert cov["required_weak"] == 0
        assert cov["required_coverage_percentage"] == 100

    def test_color_audio_reported_missing(self, readiness):
        assert "color" in readiness["missing_dimensions"]
        assert "audio" in readiness["missing_dimensions"]
        cov = readiness["coverage"]
        assert cov["supporting_present"] == 0
        assert cov["supporting_missing"] == 2

    def test_supporting_suggestions_still_neutral(self, readiness):
        assert readiness["suggestions"] == [
            "Specify color information if known.",
            "Specify audio information if known.",
        ]


class TestWeakDimension:
    @pytest.fixture
    def readiness(self, service):
        return service.validate_prompt(WEAK_CAM)["readiness"]

    def test_camera_weak_in_checklist(self, readiness):
        camera = next(c for c in readiness["checklist"]
                      if c["dimension"] == "camera")
        assert camera["status"] == "weak"
        assert camera["score"] == 40
        assert camera["present"] is False
        assert camera["message"] == (
            "Camera information is present but may need more detail."
        )

    def test_weak_blocks_ready(self, readiness):
        assert readiness["status"] == "needs_attention"
        assert readiness["weak_dimensions"] == ["camera"]
        assert readiness["missing_dimensions"] == []

    def test_weak_suggestion(self, readiness):
        assert readiness["suggestions"] == [
            "Expand camera information if known.",
        ]

    def test_weak_does_not_count_as_present(self, readiness):
        cov = readiness["coverage"]
        assert cov["required_present"] == 6, "weak camera excluded"
        assert cov["required_weak"] == 1
        assert cov["required_coverage_percentage"] == 86


class TestCoverage:
    def test_spec_example_counts_and_rounding(self, service):
        cov = service.validate_prompt(COV71)["readiness"]["coverage"]
        assert cov["required_total"] == 7
        assert cov["required_present"] == 5
        assert cov["required_missing"] == 1
        assert cov["required_weak"] == 1
        assert cov["required_coverage_percentage"] == 71, "round(5/7*100)"

    @pytest.mark.parametrize("prompt,expected", [
        (FULL, 100),      # 7/7
        (WEAK_CAM, 86),   # 6/7 -> round(85.71) = 86
        (COV71, 71),      # 5/7 -> round(71.43) = 71
        (CITY, 14),       # 1/7 -> round(14.28) = 14
        (MINIMAL, 0),     # 0/7
    ])
    def test_percentage_values(self, service, prompt, expected):
        cov = service.validate_prompt(prompt)["readiness"]["coverage"]
        assert cov["required_coverage_percentage"] == expected

    @pytest.mark.parametrize("prompt", [FULL, REQ_ONLY, CITY, WEAK_CAM,
                                        COV71, MINIMAL])
    def test_bounds_0_100(self, service, prompt):
        cov = service.validate_prompt(prompt)["readiness"]["coverage"]
        assert 0 <= cov["required_coverage_percentage"] <= 100
        assert 0 <= cov["supporting_coverage_percentage"] <= 100

    @pytest.mark.parametrize("prompt", [FULL, REQ_ONLY, CITY, WEAK_CAM,
                                        COV71, MINIMAL])
    def test_counts_are_consistent(self, service, prompt):
        cov = service.validate_prompt(prompt)["readiness"]["coverage"]
        for prefix, total in (("required", 7), ("supporting", 2)):
            assert cov[f"{prefix}_total"] == total
            assert (cov[f"{prefix}_present"] + cov[f"{prefix}_missing"]
                    + cov[f"{prefix}_weak"]) == total

    def test_all_missing_prompt_is_zero(self, service):
        cov = service.validate_prompt(MINIMAL)["readiness"]["coverage"]
        assert cov["required_present"] == 0
        assert cov["required_missing"] == 7
        assert cov["required_coverage_percentage"] == 0
        assert cov["supporting_coverage_percentage"] == 0

    def test_percentage_is_int(self, service):
        cov = service.validate_prompt(COV71)["readiness"]["coverage"]
        assert type(cov["required_coverage_percentage"]) is int


class TestMessages:
    @pytest.mark.parametrize("dim,label", [
        ("subject", "Subject"), ("action", "Action"),
        ("environment", "Environment"), ("camera", "Camera"),
        ("lighting", "Lighting"), ("visual_style", "Visual style"),
        ("color", "Color"), ("composition", "Composition"),
        ("audio", "Audio"),
    ])
    def test_all_three_messages_per_dimension(self, dim, label):
        for score, suffix in ((100, "information detected."),
                              (40, "information is present but may need "
                                  "more detail."),
                              (0, "information is not detected.")):
            scores = {d: 100 for d in DIMENSIONS}
            scores[dim] = score
            checklist = service_with(scores).validate_prompt(FULL)[
                "readiness"]["checklist"]
            item = next(c for c in checklist if c["dimension"] == dim)
            assert item["message"] == f"{label} {suffix}"

    def test_score_70_message_is_present(self):
        scores = {d: 100 for d in DIMENSIONS}
        scores["camera"] = 70
        checklist = service_with(scores).validate_prompt(FULL)[
            "readiness"]["checklist"]
        camera = next(c for c in checklist if c["dimension"] == "camera")
        assert camera["message"] == "Camera information detected."


class TestSuggestions:
    @pytest.mark.parametrize("dim", list(DIMENSIONS))
    def test_missing_and_weak_suggestions_only(self, dim):
        scores = {d: 100 for d in DIMENSIONS}
        scores[dim] = 0
        readiness = service_with(scores).validate_prompt(FULL)["readiness"]
        assert readiness["suggestions"] == [
            f"Specify {dim.replace('_', ' ')} information if known."
        ]
        scores[dim] = 40
        readiness = service_with(scores).validate_prompt(FULL)["readiness"]
        assert readiness["suggestions"] == [
            f"Expand {dim.replace('_', ' ')} information if known."
        ]
        scores[dim] = 70
        readiness = service_with(scores).validate_prompt(FULL)["readiness"]
        assert readiness["suggestions"] == [], "present gets no suggestion"

    def test_suggestions_match_weak_and_missing_exactly(self, service):
        readiness = service.validate_prompt(COV71)["readiness"]
        flagged = [d for d in DIMENSIONS
                   if d in set(readiness["missing_dimensions"])
                   | set(readiness["weak_dimensions"])]
        assert len(readiness["suggestions"]) == len(flagged)
        for dim, suggestion in zip(flagged, readiness["suggestions"]):
            assert dim.replace("_", " ") in suggestion

    def test_ready_prompt_has_no_suggestions(self, service):
        assert service.validate_prompt(FULL)["readiness"][
            "suggestions"] == []


class TestDeterminism:
    def test_repeated_calls_identical(self, service):
        first = service.validate_prompt(COV71)
        second = service.validate_prompt(COV71)
        third = service.validate_prompt(COV71)
        assert first == second == third

    def test_case_insensitive_consistent_with_day21(self, service):
        lower = service.validate_prompt(CITY)
        upper = service.validate_prompt(CITY.upper())
        assert (lower["readiness"]["status"]
                == upper["readiness"]["status"])
        assert (lower["readiness"]["coverage"]
                == upper["readiness"]["coverage"])
        assert (lower["readiness"]["checklist"]
                == upper["readiness"]["checklist"])
        assert upper["prompt"] == CITY.upper(), "case preserved in echo"

    def test_prompt_echoed_exactly(self, service):
        odd = "  Mixed   CASE with  spacing  "
        result = service.validate_prompt(odd)
        assert result["prompt"] == odd

    def test_no_random_or_time_values(self, service):
        import re
        text = str(service.validate_prompt(COV71))
        for pat in (r"\d{4}-\d{2}-\d{2}", r"\d{2}:\d{2}"):
            assert not re.search(pat, text)
        for token in ("uuid", "random", "timestamp", "datetime"):
            assert token not in text.lower(), token

    def test_json_serializable(self, service):
        json.dumps(service.validate_prompt(FULL))


class TestReadOnlyAndSecurity:
    def test_quality_service_report_not_modified(self, service):
        qs = PromptQualityService()
        svc = PromptReadinessService(qs)
        before = qs.analyze_prompt(CITY)
        svc.validate_prompt(CITY)
        after = qs.analyze_prompt(CITY)
        assert before == after, "Day21 output untouched"

    def test_no_history_or_org_dependencies(self):
        import app.services.prompt_readiness_service as mod
        source = inspect.getsource(mod)
        for token in ("prompt_history_service", "organization_service",
                      "search_service", "export_service",
                      "package_service", "create_version",
                      "delete_version", "get_version"):
            assert token not in source, token

    def test_module_no_network_or_filesystem_access(self):
        import app.services.prompt_readiness_service as mod
        source = inspect.getsource(mod)
        for forbidden in ("requests", "urllib", "socket", "http.client",
                          "subprocess", "open(", "os.path", "Path(",
                          "httpx", "aiohttp", "import random",
                          "import datetime", "datetime.now"):
            assert forbidden not in source, forbidden

    def test_no_absolute_paths_in_result(self, service):
        text = str(service.validate_prompt(FULL))
        for bad in ("C:\\", "C:/", "/home", "/Users", "/var/"):
            assert bad not in text

    def test_no_internal_objects_or_secrets(self, service):
        text = str(service.validate_prompt(CITY))
        for token in ("_storage", "PromptReadinessService",
                      "PromptQualityService", "PromptHistoryService",
                      "Traceback", "secret", "api_key", "password",
                      "os.environ"):
            assert token not in text, token

    def test_no_fabricated_words_added_to_prompt(self, service):
        prompt = "A person walks through a city street."
        result = service.validate_prompt(prompt)
        assert result["prompt"] == prompt
        text = str(result["readiness"])
        for word in ("sunset", "neon", "tokyo", "ferrari", "woman",
                     "rain", "dusk", "luxury", "drone"):
            assert word not in text.lower(), f"fabricated: {word}"

    def test_no_forbidden_ranking_language(self, service):
        for prompt in (FULL, CITY, COV71, REQ_ONLY):
            text = str(service.validate_prompt(prompt)["readiness"]).lower()
            for word in ("best", "worst", "winner", "perfect",
                         "guaranteed", "objectively good",
                         "objectively bad", "superior", "inferior"):
                assert word not in text, f"{word} in {prompt[:30]}"


class TestReadyStatusRules:
    @pytest.mark.parametrize("scores,expected", [
        ({d: 100 for d in DIMENSIONS}, "ready"),
        ({d: 70 for d in DIMENSIONS}, "ready"),
    ])
    def test_all_required_present_is_ready(self, scores, expected):
        readiness = service_with(scores).validate_prompt(FULL)["readiness"]
        assert readiness["status"] == expected

    @pytest.mark.parametrize("weak_dim", list(REQUIRED_DIMENSIONS))
    def test_any_weak_required_blocks_ready(self, weak_dim):
        scores = {d: 100 for d in DIMENSIONS}
        scores[weak_dim] = 40
        readiness = service_with(scores).validate_prompt(FULL)["readiness"]
        assert readiness["status"] == "needs_attention"
        assert weak_dim in readiness["weak_dimensions"]

    @pytest.mark.parametrize("missing_dim", list(REQUIRED_DIMENSIONS))
    def test_any_missing_required_blocks_ready(self, missing_dim):
        scores = {d: 100 for d in DIMENSIONS}
        scores[missing_dim] = 0
        readiness = service_with(scores).validate_prompt(FULL)["readiness"]
        assert readiness["status"] == "needs_attention"
        assert missing_dim in readiness["missing_dimensions"]

    @pytest.mark.parametrize("support_dim", list(SUPPORTING_DIMENSIONS))
    def test_missing_supporting_never_blocks_ready(self, support_dim):
        scores = {d: 100 for d in DIMENSIONS}
        scores[support_dim] = 0
        readiness = service_with(scores).validate_prompt(FULL)["readiness"]
        assert readiness["status"] == "ready"
        assert support_dim in readiness["missing_dimensions"]
        assert readiness["suggestions"] == [
            f"Specify {support_dim.replace('_', ' ')} information if known."
        ]

    @pytest.mark.parametrize("support_dim", list(SUPPORTING_DIMENSIONS))
    def test_weak_supporting_never_blocks_ready(self, support_dim):
        scores = {d: 100 for d in DIMENSIONS}
        scores[support_dim] = 40
        readiness = service_with(scores).validate_prompt(FULL)["readiness"]
        assert readiness["status"] == "ready"
        assert support_dim in readiness["weak_dimensions"]
