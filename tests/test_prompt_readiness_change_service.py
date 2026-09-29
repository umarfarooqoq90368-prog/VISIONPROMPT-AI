"""Tests for the prompt readiness change tracking service (Day 26)."""
import inspect
import json

import pytest

from app.services.prompt_quality_service import (
    PromptQualityService,
    DIMENSIONS,
)
from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService
from app.services.prompt_readiness_service import (
    PromptReadinessService,
    REQUIRED_DIMENSIONS,
    SUPPORTING_DIMENSIONS,
)
from app.services.prompt_readiness_change_service import (
    PromptReadinessChangeService,
    TRANSITION_KEYS,
)

# --- Fixture prompts (Day 21/24 verified via probe) -------------------------
FULL = ("Cinematic film grain style portrait of a person, the subject "
        "walking, looking around and gesturing in an outdoor forest "
        "street, camera tracking with shallow depth of field, soft "
        "lighting with rim light and golden hour glow, vibrant teal and "
        "orange palette with warm tones, layered foreground and rule of "
        "thirds composition, ambient sound with quiet music score.")
WEAK_CAM = ("Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, tracking only, soft lighting with rim light and "
            "golden hour glow, vibrant teal and orange palette with warm "
            "tones, layered foreground and rule of thirds composition, "
            "ambient sound with quiet music score.")
W_CAMLESS = ("Cinematic film grain style portrait of a person, the subject "
             "walking, looking around and gesturing in an outdoor forest "
             "street, soft lighting with rim light and golden hour glow, "
             "vibrant teal and orange palette with warm tones, layered "
             "foreground and rule of thirds composition, ambient sound "
             "with quiet music score.")
CITY = "A person walks through a city street."
CITY_ENV100 = "A person walks through a quiet city street near the forest park."
MINIMAL = "nothing specific at all"
REQ_ONLY = ("Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, camera tracking with shallow depth of field, soft "
            "lighting with rim light and golden hour glow, layered "
            "foreground and rule of thirds composition.")
SUBJ70 = ("Cinematic film grain style portrait of a person, "
          "walking through an outdoor forest street, camera tracking "
          "with shallow depth of field, soft lighting with rim light "
          "and golden hour glow, vibrant teal and orange palette with "
          "warm tones, layered foreground and rule of thirds "
          "composition, ambient sound with quiet music score.")

VIDEO = "sample.mp4"

TOP_KEYS = {
    "video_filename", "version_a", "version_b", "dimensions",
    "changed_dimensions", "dimensions_changed", "dimensions_unchanged",
    "required_changes", "supporting_changes", "transitions",
    "transition_summary", "required_coverage",
}

VERSION_BLOCK_KEYS = {
    "version", "source", "operation", "readiness_status",
    "required_coverage_percentage",
}

DIMENSION_ENTRY_KEYS = {
    "dimension", "version_a", "version_b", "changed",
}

# standard 8-version history:
# 1 FULL, 2 WEAK_CAM, 3 W_CAMLESS, 4 CITY, 5 CITY_ENV100,
# 6 MINIMAL, 7 REQ_ONLY, 8 SUBJ70
STANDARD = [
    (FULL, "advanced_prompt", "generate"),
    (WEAK_CAM, "custom", ""),
    (W_CAMLESS, "template", "cinematic"),
    (CITY, "refinement", "expand"),
    (CITY_ENV100, "custom", "tweak"),
    (MINIMAL, "template", "shorten"),
    (REQ_ONLY, "refinement", "expand"),
    (SUBJ70, "custom", "draft"),
]


def _build_history(specs=None):
    history = PromptHistoryService()
    for prompt, source, operation in (specs or STANDARD):
        history.create_version(VIDEO, prompt, source=source,
                               operation=operation)
    return history


@pytest.fixture
def history():
    return _build_history()


@pytest.fixture
def service(history):
    return PromptReadinessChangeService(
        history, PromptReadinessService(PromptQualityService())
    )


def summary_with(**counts):
    summary = {key: 0 for key in TRANSITION_KEYS}
    summary.update(counts)
    return summary


def entry(result, dimension):
    return next(d for d in result["dimensions"]
                if d["dimension"] == dimension)


class TestWiring:
    def test_constructor_state_only_two_dependencies(self, history):
        readiness = PromptReadinessService(PromptQualityService())
        svc = PromptReadinessChangeService(history, readiness)
        assert set(vars(svc).keys()) == {"history_service",
                                         "readiness_service"}
        assert svc.history_service is history
        assert svc.readiness_service is readiness

    def test_no_third_store_or_services(self, history):
        svc = PromptReadinessChangeService(
            history, PromptReadinessService(PromptQualityService())
        )
        for name in ("quality_service", "organization_service",
                     "search_service", "export_service",
                     "package_service"):
            assert not hasattr(svc, name), name

    def test_no_second_store_created(self, service):
        assert service.history_service is not None
        assert not hasattr(service, "_storage")
        assert not hasattr(service, "_versions")


class TestResponseStructure:
    @pytest.fixture
    def result(self, service):
        return service.compare_versions(VIDEO, 1, 2)

    def test_top_level_keys_exact(self, result):
        assert set(result.keys()) == TOP_KEYS

    def test_video_filename_echo(self, result):
        assert result["video_filename"] == VIDEO

    def test_version_block_keys(self, result):
        assert set(result["version_a"].keys()) == VERSION_BLOCK_KEYS
        assert set(result["version_b"].keys()) == VERSION_BLOCK_KEYS

    def test_version_blocks_preserve_requested_direction(self, result):
        assert result["version_a"]["version"] == 1
        assert result["version_b"]["version"] == 2
        assert result["version_a"]["source"] == "advanced_prompt"
        assert result["version_a"]["operation"] == "generate"
        assert result["version_b"]["source"] == "custom"
        assert result["version_b"]["operation"] == ""

    def test_version_block_statuses_and_coverage(self, result):
        assert result["version_a"]["readiness_status"] == "ready"
        assert result["version_a"]["required_coverage_percentage"] == 100
        assert result["version_b"]["readiness_status"] == "needs_attention"
        assert result["version_b"]["required_coverage_percentage"] == 86

    def test_dimensions_nine_in_day21_order(self, result):
        assert [d["dimension"] for d in result["dimensions"]] == \
            list(DIMENSIONS)

    def test_dimension_entry_keys(self, result):
        for item in result["dimensions"]:
            assert set(item.keys()) == DIMENSION_ENTRY_KEYS
            assert set(item["version_a"].keys()) == {"status", "score"}
            assert set(item["version_b"].keys()) == {"status", "score"}
            assert item["version_a"]["status"] in (
                "present", "weak", "missing")
            assert item["version_b"]["status"] in (
                "present", "weak", "missing")
            assert type(item["changed"]) is bool

    def test_changed_flags_match_status_difference(self, result):
        for item in result["dimensions"]:
            expected = (item["version_a"]["status"]
                        != item["version_b"]["status"])
            assert item["changed"] is expected

    def test_transition_summary_has_exactly_six_keys(self, result):
        assert set(result["transition_summary"].keys()) == set(
            TRANSITION_KEYS)
        assert len(result["transition_summary"]) == 6
        assert all(type(v) is int
                   for v in result["transition_summary"].values())

    def test_transition_entries_shape(self, result):
        for t in result["transitions"]:
            assert set(t.keys()) == {"dimension", "from", "to"}
            assert t["from"] != t["to"]

    def test_required_coverage_block_shape(self, result):
        cov = result["required_coverage"]
        assert set(cov.keys()) == {"version_a", "version_b", "delta"}
        for value in cov.values():
            assert type(value) is int


class TestIdenticalVersions:
    def test_all_nine_dimensions_unchanged(self, service):
        result = service.compare_versions(VIDEO, 1, 1)
        assert len(result["dimensions"]) == 9
        assert all(d["changed"] is False for d in result["dimensions"])

    def test_changed_dimensions_empty(self, service):
        result = service.compare_versions(VIDEO, 1, 1)
        assert result["changed_dimensions"] == []
        assert result["dimensions_changed"] == 0
        assert result["dimensions_unchanged"] == 9
        assert result["required_changes"] == []
        assert result["supporting_changes"] == []
        assert result["transitions"] == []

    def test_all_transition_counts_zero(self, service):
        result = service.compare_versions(VIDEO, 1, 1)
        assert result["transition_summary"] == summary_with()

    def test_coverage_delta_zero_and_same_status(self, service):
        result = service.compare_versions(VIDEO, 1, 1)
        assert result["required_coverage"] == {
            "version_a": 100, "version_b": 100, "delta": 0}
        assert result["version_a"] == result["version_b"]

    def test_identical_prompt_text_in_two_versions(self):
        history = PromptHistoryService()
        history.create_version(VIDEO, FULL, source="custom", operation="")
        history.create_version(VIDEO, FULL, source="custom", operation="")
        svc = PromptReadinessChangeService(
            history, PromptReadinessService(PromptQualityService())
        )
        result = svc.compare_versions(VIDEO, 1, 2)
        assert result["dimensions_changed"] == 0
        assert result["dimensions_unchanged"] == 9
        assert result["transition_summary"] == summary_with()
        assert result["required_coverage"]["delta"] == 0

    @pytest.mark.parametrize("version", [2, 4, 6, 7])
    def test_self_comparison_zero_for_other_versions(
        self, service, version
    ):
        result = service.compare_versions(VIDEO, version, version)
        assert result["dimensions_changed"] == 0
        assert result["dimensions_unchanged"] == 9
        assert result["transition_summary"] == summary_with()


class TestSixTransitionsIndependently:
    """Each directional transition verified alone (exact summary)."""

    def test_present_to_weak_camera_only(self, service):
        result = service.compare_versions(VIDEO, 1, 2)
        assert result["changed_dimensions"] == ["camera"]
        assert result["transition_summary"] == summary_with(
            present_to_weak=1)
        assert result["transitions"] == [
            {"dimension": "camera", "from": "present", "to": "weak"}]

    def test_weak_to_present_camera_only(self, service):
        result = service.compare_versions(VIDEO, 2, 1)
        assert result["changed_dimensions"] == ["camera"]
        assert result["transition_summary"] == summary_with(
            weak_to_present=1)
        assert result["transitions"] == [
            {"dimension": "camera", "from": "weak", "to": "present"}]

    def test_missing_to_weak_camera_only(self, service):
        result = service.compare_versions(VIDEO, 3, 2)
        assert result["changed_dimensions"] == ["camera"]
        assert result["transition_summary"] == summary_with(
            missing_to_weak=1)
        assert entry(result, "camera")["version_a"] == {
            "status": "missing", "score": 0}
        assert entry(result, "camera")["version_b"] == {
            "status": "weak", "score": 40}

    def test_weak_to_missing_camera_only(self, service):
        result = service.compare_versions(VIDEO, 2, 3)
        assert result["changed_dimensions"] == ["camera"]
        assert result["transition_summary"] == summary_with(
            weak_to_missing=1)
        assert result["transitions"] == [
            {"dimension": "camera", "from": "weak", "to": "missing"}]

    def test_present_to_missing_all_nine(self, service):
        result = service.compare_versions(VIDEO, 1, 6)
        assert result["changed_dimensions"] == list(DIMENSIONS)
        assert result["transition_summary"] == summary_with(
            present_to_missing=9)
        assert result["dimensions_changed"] == 9
        assert result["dimensions_unchanged"] == 0

    def test_missing_to_present_all_nine(self, service):
        result = service.compare_versions(VIDEO, 6, 1)
        assert result["changed_dimensions"] == list(DIMENSIONS)
        assert result["transition_summary"] == summary_with(
            missing_to_present=9)
        assert result["dimensions_changed"] == 9

    def test_transition_summary_never_counts_same_state(self, service):
        for a, b in ((1, 2), (2, 1), (3, 2), (2, 3), (1, 6), (6, 1)):
            summary = service.compare_versions(
                VIDEO, a, b)["transition_summary"]
            assert "present_to_present" not in summary
            assert "weak_to_weak" not in summary
            assert "missing_to_missing" not in summary
            assert sum(summary.values()) == service.compare_versions(
                VIDEO, a, b)["dimensions_changed"]


class TestPresentScoreChangeNotStateChange:
    def test_70_to_100_stays_present_and_unchanged(self, service):
        result = service.compare_versions(VIDEO, 4, 5)
        env = entry(result, "environment")
        assert env["version_a"] == {"status": "present", "score": 70}
        assert env["version_b"] == {"status": "present", "score": 100}
        assert env["changed"] is False

    def test_score_only_pair_has_zero_changed_dimensions(self, service):
        result = service.compare_versions(VIDEO, 4, 5)
        assert result["changed_dimensions"] == []
        assert result["dimensions_changed"] == 0
        assert result["dimensions_unchanged"] == 9
        assert result["transition_summary"] == summary_with()
        assert result["required_changes"] == []
        assert result["supporting_changes"] == []
        assert result["transitions"] == []

    def test_raw_scores_returned_exactly_as_day21(self, service):
        from app.services.prompt_quality_service import PromptQualityService
        day21 = PromptQualityService().analyze_prompt(
            CITY_ENV100)["quality"]["dimensions"]
        result = service.compare_versions(VIDEO, 4, 5)
        for item in result["dimensions"]:
            dim = item["dimension"]
            assert item["version_a"]["score"] == \
                PromptQualityService().analyze_prompt(
                    CITY)["quality"]["dimensions"][dim]["score"]
            assert item["version_b"]["score"] == day21[dim]["score"]

    def test_score_change_within_present_does_not_count(self, service):
        # FULL(1) vs SUBJ70(8): subject 100 -> 70 stays present;
        # only action 100 -> 40 is a real state change.
        result = service.compare_versions(VIDEO, 1, 8)
        subject = entry(result, "subject")
        assert subject["version_a"] == {"status": "present", "score": 100}
        assert subject["version_b"] == {"status": "present", "score": 70}
        assert subject["changed"] is False
        assert result["changed_dimensions"] == ["action"]
        assert result["dimensions_changed"] == 1
        assert result["transition_summary"] == summary_with(
            present_to_weak=1)


class TestMultipleChanges:
    @pytest.fixture
    def full_to_city(self, service):
        return service.compare_versions(VIDEO, 1, 4)

    def test_changed_dimensions_in_day21_order(self, full_to_city):
        assert full_to_city["changed_dimensions"] == [
            "subject", "action", "camera", "lighting", "visual_style",
            "color", "composition", "audio",
        ]

    def test_counts(self, full_to_city):
        assert full_to_city["dimensions_changed"] == 8
        assert full_to_city["dimensions_unchanged"] == 1

    def test_environment_unchanged_despite_score_100_vs_70(
        self, full_to_city
    ):
        env = entry(full_to_city, "environment")
        assert env["version_a"]["score"] == 100
        assert env["version_b"]["score"] == 70
        assert env["version_a"]["status"] == "present"
        assert env["version_b"]["status"] == "present"
        assert env["changed"] is False

    def test_exact_transition_counts(self, full_to_city):
        assert full_to_city["transition_summary"] == summary_with(
            present_to_weak=1, present_to_missing=7)

    def test_required_and_supporting_categorization(self, full_to_city):
        assert full_to_city["required_changes"] == [
            "subject", "action", "camera", "lighting", "visual_style",
            "composition",
        ]
        assert full_to_city["supporting_changes"] == ["color", "audio"]

    def test_required_plus_supporting_equals_changed(
        self, full_to_city
    ):
        combined = (full_to_city["required_changes"]
                    + full_to_city["supporting_changes"])
        assert set(combined) == set(full_to_city["changed_dimensions"])
        order = {dim: i for i, dim in enumerate(DIMENSIONS)}
        for group in (full_to_city["required_changes"],
                      full_to_city["supporting_changes"]):
            assert group == sorted(group, key=order.get), \
                "each group stays in Day21 order"

    def test_transitions_list_day21_order_with_from_to(
        self, full_to_city
    ):
        assert full_to_city["transitions"] == [
            {"dimension": "subject", "from": "present", "to": "weak"},
            {"dimension": "action", "from": "present", "to": "missing"},
            {"dimension": "camera", "from": "present", "to": "missing"},
            {"dimension": "lighting", "from": "present", "to": "missing"},
            {"dimension": "visual_style", "from": "present",
             "to": "missing"},
            {"dimension": "color", "from": "present", "to": "missing"},
            {"dimension": "composition", "from": "present",
             "to": "missing"},
            {"dimension": "audio", "from": "present", "to": "missing"},
        ]

    def test_city_to_req_only_mixed_transitions(self, service):
        result = service.compare_versions(VIDEO, 4, 7)
        assert result["changed_dimensions"] == [
            "subject", "action", "camera", "lighting", "visual_style",
            "composition",
        ]
        assert result["dimensions_changed"] == 6
        assert result["dimensions_unchanged"] == 3
        assert result["transition_summary"] == summary_with(
            weak_to_present=1, missing_to_present=5)
        assert result["required_changes"] == [
            "subject", "action", "camera", "lighting", "visual_style",
            "composition",
        ]
        assert result["supporting_changes"] == []

    def test_minimal_to_full_changes_all(self, service):
        result = service.compare_versions(VIDEO, 6, 1)
        assert result["required_changes"] == list(REQUIRED_DIMENSIONS)
        assert result["supporting_changes"] == list(SUPPORTING_DIMENSIONS)


class TestReverseComparison:
    def test_reverse_mirrors_single_transition(self, service):
        fwd = service.compare_versions(VIDEO, 1, 2)
        rev = service.compare_versions(VIDEO, 2, 1)
        assert fwd["transition_summary"] == summary_with(
            present_to_weak=1)
        assert rev["transition_summary"] == summary_with(
            weak_to_present=1)
        assert fwd["changed_dimensions"] == rev["changed_dimensions"]
        assert fwd["dimensions_changed"] == rev["dimensions_changed"]

    def test_reverse_mirrors_all_nine(self, service):
        fwd = service.compare_versions(VIDEO, 1, 6)
        rev = service.compare_versions(VIDEO, 6, 1)
        assert fwd["transition_summary"] == summary_with(
            present_to_missing=9)
        assert rev["transition_summary"] == summary_with(
            missing_to_present=9)

    def test_version_labels_never_swapped(self, service):
        rev = service.compare_versions(VIDEO, 2, 1)
        assert rev["version_a"]["version"] == 2
        assert rev["version_b"]["version"] == 1
        assert rev["version_a"]["readiness_status"] == "needs_attention"
        assert rev["version_b"]["readiness_status"] == "ready"
        assert rev["required_coverage"] == {
            "version_a": 86, "version_b": 100, "delta": 14}

    def test_transition_entries_mirror_from_to(self, service):
        fwd = service.compare_versions(VIDEO, 3, 2)
        rev = service.compare_versions(VIDEO, 2, 3)
        assert fwd["transitions"] == [
            {"dimension": "camera", "from": "missing", "to": "weak"}]
        assert rev["transitions"] == [
            {"dimension": "camera", "from": "weak", "to": "missing"}]

    def test_coverage_delta_negates_on_reverse(self, service):
        fwd = service.compare_versions(VIDEO, 1, 6)
        rev = service.compare_versions(VIDEO, 6, 1)
        assert fwd["required_coverage"]["delta"] == -100
        assert rev["required_coverage"]["delta"] == 100

    @pytest.mark.parametrize("a,b", [(1, 2), (1, 4), (4, 7), (1, 7)])
    def test_reverse_dimension_entries_swapped(self, service, a, b):
        fwd = service.compare_versions(VIDEO, a, b)
        rev = service.compare_versions(VIDEO, b, a)
        for f_item, r_item in zip(fwd["dimensions"], rev["dimensions"]):
            assert f_item["dimension"] == r_item["dimension"]
            assert f_item["version_a"] == r_item["version_b"]
            assert f_item["version_b"] == r_item["version_a"]
            assert f_item["changed"] == r_item["changed"]


class TestCoverage:
    @pytest.mark.parametrize("a,b,va,vb,delta", [
        (1, 2, 100, 86, -14),
        (2, 1, 86, 100, 14),
        (3, 2, 86, 86, 0),
        (1, 6, 100, 0, -100),
        (6, 1, 0, 100, 100),
        (4, 5, 14, 14, 0),
        (4, 7, 14, 100, 86),
        (7, 1, 100, 100, 0),
        (1, 8, 100, 86, -14),
        (1, 1, 100, 100, 0),
    ])
    def test_exact_coverage_and_delta(self, service, a, b, va, vb, delta):
        result = service.compare_versions(VIDEO, a, b)
        assert result["required_coverage"] == {
            "version_a": va, "version_b": vb, "delta": delta}

    def test_delta_is_plain_arithmetic_b_minus_a(self, service):
        for a in range(1, 9):
            for b in range(1, 9):
                cov = service.compare_versions(VIDEO, a, b)[
                    "required_coverage"]
                assert cov["delta"] == cov["version_b"] - cov["version_a"]

    def test_coverage_percentages_bounded_ints(self, service):
        cov = service.compare_versions(VIDEO, 1, 6)["required_coverage"]
        assert 0 <= cov["version_a"] <= 100
        assert 0 <= cov["version_b"] <= 100
        assert type(cov["delta"]) is int

    def test_version_status_and_coverage_match_day24(self, service):
        readiness = PromptReadinessService(PromptQualityService())
        result = service.compare_versions(VIDEO, 7, 4)
        assert result["version_a"]["readiness_status"] == \
            readiness.validate_prompt(REQ_ONLY)["readiness"]["status"]
        assert result["version_b"]["readiness_status"] == \
            readiness.validate_prompt(CITY)["readiness"]["status"]
        assert result["version_a"]["required_coverage_percentage"] == \
            readiness.validate_prompt(REQ_ONLY)["readiness"]["coverage"][
                "required_coverage_percentage"]
        assert result["version_b"]["required_coverage_percentage"] == 14


class TestRequiredSupportingCategorization:
    def test_supporting_only_changes(self, service):
        result = service.compare_versions(VIDEO, 7, 1)
        assert result["changed_dimensions"] == ["color", "audio"]
        assert result["required_changes"] == []
        assert result["supporting_changes"] == ["color", "audio"]
        assert result["transition_summary"] == summary_with(
            missing_to_present=2)
        assert result["dimensions_changed"] == 2
        assert result["dimensions_unchanged"] == 7

    def test_partition_of_changed_dimensions(self, service):
        for a, b in ((1, 4), (4, 7), (7, 1), (1, 6), (6, 1)):
            result = service.compare_versions(VIDEO, a, b)
            combined = (result["required_changes"]
                        + result["supporting_changes"])
            assert set(combined) == set(result["changed_dimensions"])
            assert set(result["required_changes"]).isdisjoint(
                result["supporting_changes"])

    def test_categorization_follows_day24_groups(self, service):
        result = service.compare_versions(VIDEO, 6, 1)
        assert set(result["required_changes"]) == set(REQUIRED_DIMENSIONS)
        assert set(result["supporting_changes"]) == set(
            SUPPORTING_DIMENSIONS)

    def test_supporting_changes_not_ranked_or_labeled(self, service):
        result = service.compare_versions(VIDEO, 7, 1)
        assert isinstance(result["supporting_changes"], list)
        assert all(isinstance(d, str) for d in
                   result["supporting_changes"])


class TestValidation:
    @pytest.mark.parametrize("bad_a", [0, -1, -5, "1", 1.5, None, True,
                                       False, {}, []])
    def test_invalid_version_a_raises(self, service, bad_a):
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, bad_a, 1)

    @pytest.mark.parametrize("bad_b", [0, -1, "2", 2.5, None, True])
    def test_invalid_version_b_raises(self, service, bad_b):
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, 1, bad_b)

    def test_nonexistent_version_raises_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.compare_versions(VIDEO, 1, 99)

    def test_nonexistent_version_a_raises_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.compare_versions(VIDEO, 99, 1)

    def test_deleted_version_raises_not_found(self, history, service):
        history.delete_version(VIDEO, 2)
        with pytest.raises(ValueError, match="not found"):
            service.compare_versions(VIDEO, 1, 2)

    def test_nonexistent_video_raises_not_found(self, service):
        with pytest.raises(ValueError):
            service.compare_versions("gone.mp4", 1, 2)

    def test_error_message_names_missing_version(self, service):
        with pytest.raises(ValueError, match="Version 99 not found"):
            service.compare_versions(VIDEO, 99, 1)

    def test_missing_version_never_silently_replaced(self, history,
                                                     service):
        before = [r["version"] for r in history.list_versions(VIDEO)]
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, 1, 99)
        after = [r["version"] for r in history.list_versions(VIDEO)]
        assert before == after


class TestDeterminism:
    def test_repeated_calls_identical(self, service):
        assert (service.compare_versions(VIDEO, 1, 4)
                == service.compare_versions(VIDEO, 1, 4))

    def test_json_byte_equivalent(self, service):
        first = json.dumps(service.compare_versions(VIDEO, 1, 4),
                           sort_keys=True)
        second = json.dumps(service.compare_versions(VIDEO, 1, 4),
                            sort_keys=True)
        assert first == second

    def test_json_serializable(self, service):
        text = json.dumps(service.compare_versions(VIDEO, 1, 4))
        assert json.loads(text)["dimensions_changed"] == 8

    def test_no_timestamps_uuids_or_random_values(self, service):
        text = json.dumps(service.compare_versions(VIDEO, 1, 4))
        for token in ("created_at", "uuid", "timestamp", "datetime",
                      "random"):
            assert token not in text, token

    def test_no_network_or_time_patterns(self, service):
        import re
        text = json.dumps(service.compare_versions(VIDEO, 1, 6))
        for pat in (r"\d{4}-\d{2}-\d{2}", r"\d{2}:\d{2}", "http://",
                    "https://"):
            assert not re.search(pat, text), pat

    def test_pure_function_of_stored_prompts(self):
        first = PromptReadinessChangeService(
            _build_history(),
            PromptReadinessService(PromptQualityService()),
        ).compare_versions(VIDEO, 1, 4)
        second = PromptReadinessChangeService(
            _build_history(),
            PromptReadinessService(PromptQualityService()),
        ).compare_versions(VIDEO, 1, 4)
        assert first == second


class TestReadOnlyAndIntegrity:
    def test_history_listing_unchanged(self, service, history):
        before = json.dumps(history.list_versions(VIDEO))
        service.compare_versions(VIDEO, 1, 4)
        service.compare_versions(VIDEO, 4, 1)
        assert json.dumps(history.list_versions(VIDEO)) == before

    def test_history_record_keys_unchanged(self, service, history):
        before = {v: set(history.get_version(VIDEO, v).keys())
                  for v in range(1, 9)}
        service.compare_versions(VIDEO, 1, 4)
        for version in range(1, 9):
            assert set(history.get_version(VIDEO, version).keys()) == \
                before[version]

    def test_prompts_unchanged_exactly(self, service, history):
        prompts = {v: history.get_version(VIDEO, v)["prompt"]
                   for v in range(1, 9)}
        service.compare_versions(VIDEO, 1, 6)
        for version, prompt in prompts.items():
            assert history.get_version(VIDEO, version)["prompt"] == prompt

    def test_metadata_unchanged(self, history, service):
        history.create_version(VIDEO, "extra", source="custom",
                               operation="", metadata={"k": "v"})
        before = history.get_version(VIDEO, 9)["metadata"]
        service.compare_versions(VIDEO, 1, 4)
        assert history.get_version(VIDEO, 9)["metadata"] == before

    def test_favorites_and_tags_unchanged(self, history, service):
        org = PromptOrganizationService(history)
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 4, ["city"])
        before_favorites = org.list_favorites(VIDEO)
        before_org = {v: org.get_organization(VIDEO, v)
                      for v in range(1, 9)}
        service.compare_versions(VIDEO, 1, 4)
        assert org.list_favorites(VIDEO) == before_favorites
        for version, entry_value in before_org.items():
            assert org.get_organization(VIDEO, version) == entry_value

    def test_day21_quality_report_unchanged(self, history, service):
        quality = PromptQualityService()
        before = quality.analyze_prompt(CITY)
        service.compare_versions(VIDEO, 1, 4)
        assert quality.analyze_prompt(CITY) == before

    def test_no_versions_created_or_deleted(self, history, service):
        count_before = len(history.list_versions(VIDEO))
        service.compare_versions(VIDEO, 1, 4)
        service.compare_versions(VIDEO, 6, 6)
        assert len(history.list_versions(VIDEO)) == count_before

    def test_day24_readiness_reused_not_altered(self, service):
        readiness = PromptReadinessService(PromptQualityService())
        result = service.compare_versions(VIDEO, 4, 7)
        a_checks = {i["dimension"]: i for i in
                    readiness.validate_prompt(CITY)["readiness"][
                        "checklist"]}
        b_checks = {i["dimension"]: i for i in
                    readiness.validate_prompt(REQ_ONLY)["readiness"][
                        "checklist"]}
        for item in result["dimensions"]:
            dim = item["dimension"]
            assert item["version_a"]["status"] == a_checks[dim]["status"]
            assert item["version_a"]["score"] == a_checks[dim]["score"]
            assert item["version_b"]["status"] == b_checks[dim]["status"]
            assert item["version_b"]["score"] == b_checks[dim]["score"]


class TestNoLeaksAndNoRanking:
    def test_no_absolute_paths_in_output(self, service):
        text = str(service.compare_versions(VIDEO, 1, 4))
        for bad in ("C:\\", "C:/", "/home", "/Users", "/var/"):
            assert bad not in text, bad

    def test_no_internal_objects_or_secrets(self, service):
        text = str(service.compare_versions(VIDEO, 1, 4))
        for token in ("_storage", "PromptReadinessChangeService",
                      "PromptReadinessService", "PromptQualityService",
                      "PromptHistoryService", "Traceback", "secret",
                      "api_key", "password", "os.environ"):
            assert token not in text, token

    def test_no_forbidden_ranking_language(self, service):
        text = str(service.compare_versions(VIDEO, 1, 4)).lower()
        for word in ("best", "worst", "winner", "perfect", "guaranteed",
                     "superior", "inferior", "rank", "recommended",
                     "better", "worse", "improved", "improvement",
                     "gain", "upgrade"):
            assert word not in text, word

    def test_no_forbidden_language_on_reverse_and_same(self, service):
        for a, b in ((4, 1), (1, 1), (7, 4)):
            text = str(service.compare_versions(VIDEO, a, b)).lower()
            for word in ("best", "winner", "superior", "better",
                         "worse", "improved", "improvement", "gain"):
                assert word not in text, f"{word} in {a}->{b}"

    def test_delta_never_labeled_evaluatively(self, service):
        text = json.dumps(service.compare_versions(VIDEO, 6, 1))
        for word in ("improvement", "improved", "gain", "increase",
                     "quality increase", "superior", "better"):
            assert word not in text.lower(), word

    def test_no_prompt_text_leak_in_change_report(self, service):
        text = str(service.compare_versions(VIDEO, 1, 4))
        for fragment in ("Cinematic film grain", "city street",
                         "nothing specific"):
            assert fragment not in text, fragment


class TestSourceContract:
    def test_module_has_no_network_or_filesystem_access(self):
        import app.services.prompt_readiness_change_service as mod
        source = inspect.getsource(mod)
        for forbidden in ("requests", "urllib", "socket", "http.client",
                          "subprocess", "open(", "os.path", "Path(",
                          "httpx", "aiohttp", "import random",
                          "import datetime", "datetime.now", "import uuid"):
            assert forbidden not in source, forbidden

    def test_module_never_writes_to_history(self):
        import app.services.prompt_readiness_change_service as mod
        source = inspect.getsource(mod)
        for forbidden in ("create_version", "delete_version",
                          "favorite_version", "unfavorite_version",
                          "add_tags", "remove_tags", "save_advanced_prompt",
                          "_storage["):
            assert forbidden not in source, forbidden

    def test_module_uses_only_read_paths(self):
        import app.services.prompt_readiness_change_service as mod
        source = inspect.getsource(mod)
        assert "get_version" in source
        assert "validate_prompt" in source
        assert "list_versions" not in source, "no bulk listing needed"
        assert "delete_version" not in source

    def test_no_llm_or_remote_calls(self):
        import app.services.prompt_readiness_change_service as mod
        source = inspect.getsource(mod)
        for forbidden in ("openai", "anthropic", "completion", "api_key"):
            assert forbidden not in source, forbidden

    def test_transition_keys_are_exactly_six(self):
        assert len(TRANSITION_KEYS) == 6
        assert set(TRANSITION_KEYS) == {
            "missing_to_weak", "missing_to_present",
            "weak_to_missing", "weak_to_present",
            "present_to_missing", "present_to_weak",
        }
