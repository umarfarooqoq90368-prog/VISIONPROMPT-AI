"""Tests for the prompt readiness timeline service (Day 27)."""
import json

import pytest

from app.services.prompt_quality_service import (
    PromptQualityService,
    DIMENSIONS,
)
from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService
from app.services.prompt_readiness_service import PromptReadinessService
from app.services.prompt_readiness_change_service import (
    PromptReadinessChangeService,
    TRANSITION_KEYS,
)
from app.services.prompt_readiness_timeline_service import (
    PromptReadinessTimelineService,
)

# --- Fixture prompts (Day 21/24 verified) ----------------------------------
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
    "video_filename", "versions_analyzed", "steps", "timeline", "summary",
}

SUMMARY_KEYS = {
    "versions_analyzed", "steps", "dimensions_changed_total",
    "dimensions_unchanged_total", "required_changes_total",
    "supporting_changes_total", "transition_summary", "first_version",
    "last_version", "first_required_coverage_percentage",
    "last_required_coverage_percentage", "required_coverage_delta",
}

DAY26_STEP_KEYS = {
    "video_filename", "version_a", "version_b", "dimensions",
    "changed_dimensions", "dimensions_changed", "dimensions_unchanged",
    "required_changes", "supporting_changes", "transitions",
    "transition_summary", "required_coverage",
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


def _build_service(history):
    readiness = PromptReadinessService(PromptQualityService())
    change = PromptReadinessChangeService(history, readiness)
    return PromptReadinessTimelineService(history, change)


@pytest.fixture
def history():
    return _build_history()


@pytest.fixture
def change(history):
    return PromptReadinessChangeService(
        history, PromptReadinessService(PromptQualityService())
    )


@pytest.fixture
def service(history, change):
    return PromptReadinessTimelineService(history, change)


@pytest.fixture
def result(service):
    return service.build_timeline(VIDEO)


def pairs(timeline):
    return [(step["version_a"]["version"], step["version_b"]["version"])
            for step in timeline]


class TestWiring:
    def test_constructor_state_only_two_dependencies(self, history, change):
        svc = PromptReadinessTimelineService(history, change)
        assert set(vars(svc).keys()) == {"history_service",
                                         "readiness_change_service"}
        assert svc.history_service is history
        assert svc.readiness_change_service is change

    def test_change_service_is_day26_instance(self, service):
        assert isinstance(service.readiness_change_service,
                          PromptReadinessChangeService)

    def test_reuses_same_history_store(self, service, history):
        assert service.history_service is history

    def test_no_third_store_or_services(self, service):
        for name in ("quality_service", "readiness_service",
                     "organization_service", "search_service",
                     "export_service", "package_service"):
            assert not hasattr(service, name), name

    def test_no_second_store_created(self, service):
        assert not hasattr(service, "_storage")
        assert not hasattr(service, "_versions")
        assert not hasattr(service, "_timeline")

    def test_change_service_not_duplicated(self, history, change):
        svc = PromptReadinessTimelineService(history, change)
        assert svc.readiness_change_service is change


class TestResponseStructure:
    @pytest.fixture
    def keys(self, result):
        return set(result.keys())

    def test_top_level_keys_exact(self, keys):
        assert keys == TOP_KEYS

    def test_video_filename_echo(self, result):
        assert result["video_filename"] == VIDEO

    def test_versions_analyzed_ascending(self, result):
        assert result["versions_analyzed"] == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_steps_equals_pairs(self, result):
        assert result["steps"] == 7
        assert result["steps"] == len(result["timeline"])
        assert result["steps"] == len(result["versions_analyzed"]) - 1

    def test_summary_keys_exact(self, result):
        assert set(result["summary"].keys()) == SUMMARY_KEYS

    def test_summary_counts_match_top_level(self, result):
        assert result["summary"]["versions_analyzed"] == 8
        assert result["summary"]["steps"] == result["steps"]

    def test_every_step_has_exact_day26_keys(self, result):
        for step in result["timeline"]:
            assert set(step.keys()) == DAY26_STEP_KEYS

    def test_every_step_is_exact_day26_output(self, service, result):
        for step in result["timeline"]:
            direct = service.readiness_change_service.compare_versions(
                VIDEO,
                step["version_a"]["version"],
                step["version_b"]["version"],
            )
            assert json.dumps(step, sort_keys=True) == \
                json.dumps(direct, sort_keys=True)

    def test_transition_summary_six_keys_everywhere(self, result):
        assert set(result["summary"]["transition_summary"].keys()) == \
            set(TRANSITION_KEYS)
        for step in result["timeline"]:
            assert set(step["transition_summary"].keys()) == \
                set(TRANSITION_KEYS)

    def test_summary_value_types(self, result):
        summary = result["summary"]
        for key in ("versions_analyzed", "steps",
                    "dimensions_changed_total", "dimensions_unchanged_total",
                    "required_changes_total", "supporting_changes_total",
                    "required_coverage_delta"):
            assert type(summary[key]) is int, key
        for key in ("first_version", "last_version",
                    "first_required_coverage_percentage",
                    "last_required_coverage_percentage"):
            assert summary[key] is None or type(summary[key]) is int, key
        for value in summary["transition_summary"].values():
            assert type(value) is int

    def test_steps_is_int(self, result):
        assert type(result["steps"]) is int


class TestFullChain:
    def test_step_count_and_pairs(self, result):
        assert pairs(result["timeline"]) == [
            (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8)]

    def test_step1_camera_present_to_weak(self, result):
        step = result["timeline"][0]
        assert step["version_a"]["version"] == 1
        assert step["version_b"]["version"] == 2
        assert step["changed_dimensions"] == ["camera"]
        assert step["transitions"] == [
            {"dimension": "camera", "from": "present", "to": "weak"}]
        assert step["transition_summary"]["present_to_weak"] == 1
        assert step["required_changes"] == ["camera"]
        assert step["supporting_changes"] == []
        assert step["required_coverage"] == {"version_a": 100,
                                             "version_b": 86, "delta": -14}

    def test_step2_camera_weak_to_missing(self, result):
        step = result["timeline"][1]
        assert (step["version_a"]["version"], step["version_b"]["version"]) \
            == (2, 3)
        assert step["changed_dimensions"] == ["camera"]
        assert step["transition_summary"]["weak_to_missing"] == 1
        assert step["required_coverage"] == {"version_a": 86,
                                             "version_b": 86, "delta": 0}

    def test_step3_multi_dimension_diff(self, result):
        step = result["timeline"][2]
        assert step["changed_dimensions"] == [
            "subject", "action", "lighting", "visual_style",
            "color", "composition", "audio"]
        assert step["dimensions_changed"] == 7
        assert step["transition_summary"]["present_to_missing"] == 6
        assert step["transition_summary"]["present_to_weak"] == 1
        assert step["required_changes"] == [
            "subject", "action", "lighting", "visual_style", "composition"]
        assert step["supporting_changes"] == ["color", "audio"]
        assert step["required_coverage"] == {"version_a": 86,
                                             "version_b": 14, "delta": -72}

    def test_step4_score_only_no_state_change(self, result):
        step = result["timeline"][3]
        assert (step["version_a"]["version"], step["version_b"]["version"]) \
            == (4, 5)
        assert step["changed_dimensions"] == []
        assert step["dimensions_changed"] == 0
        assert step["transitions"] == []
        assert set(step["transition_summary"].values()) == {0}
        assert step["required_coverage"] == {"version_a": 14,
                                             "version_b": 14, "delta": 0}
        env = next(d for d in step["dimensions"]
                   if d["dimension"] == "environment")
        assert env["version_a"] == {"status": "present", "score": 70}
        assert env["version_b"] == {"status": "present", "score": 100}
        assert env["changed"] is False

    def test_step5_two_required_changes(self, result):
        step = result["timeline"][4]
        assert step["changed_dimensions"] == ["subject", "environment"]
        assert step["transition_summary"]["weak_to_missing"] == 1
        assert step["transition_summary"]["present_to_missing"] == 1
        assert step["required_changes"] == ["subject", "environment"]
        assert step["required_coverage"] == {"version_a": 14,
                                             "version_b": 0, "delta": -14}

    def test_step6_all_required_missing_to_present(self, result):
        step = result["timeline"][5]
        assert step["changed_dimensions"] == [
            "subject", "action", "environment", "camera", "lighting",
            "visual_style", "composition"]
        assert step["transition_summary"]["missing_to_present"] == 7
        assert sum(step["transition_summary"].values()) == 7
        assert len(step["required_changes"]) == 7
        assert step["supporting_changes"] == []
        assert step["required_coverage"] == {"version_a": 0,
                                             "version_b": 100, "delta": 100}
        assert step["version_b"]["readiness_status"] == "ready"

    def test_step7_required_plus_supporting(self, result):
        step = result["timeline"][6]
        assert step["changed_dimensions"] == ["action", "color", "audio"]
        assert step["transition_summary"]["missing_to_present"] == 2
        assert step["transition_summary"]["present_to_weak"] == 1
        assert step["required_changes"] == ["action"]
        assert step["supporting_changes"] == ["color", "audio"]
        assert step["required_coverage"] == {"version_a": 100,
                                             "version_b": 86, "delta": -14}

    def test_summary_totals(self, result):
        summary = result["summary"]
        assert summary["dimensions_changed_total"] == 21
        assert summary["dimensions_unchanged_total"] == 42
        assert summary["required_changes_total"] == 17
        assert summary["supporting_changes_total"] == 4

    def test_summary_transition_totals(self, result):
        assert result["summary"]["transition_summary"] == {
            "missing_to_weak": 0, "missing_to_present": 9,
            "weak_to_missing": 2, "weak_to_present": 0,
            "present_to_missing": 7, "present_to_weak": 3}

    def test_summary_first_last_coverage(self, result):
        summary = result["summary"]
        assert summary["first_version"] == 1
        assert summary["last_version"] == 8
        assert summary["first_required_coverage_percentage"] == 100
        assert summary["last_required_coverage_percentage"] == 86
        assert summary["required_coverage_delta"] == -14

    def test_adjacent_steps_chain(self, result):
        timeline = result["timeline"]
        for previous, following in zip(timeline, timeline[1:]):
            assert previous["version_b"]["version"] == \
                following["version_a"]["version"]

    def test_coverage_delta_telescopes(self, result):
        total = sum(step["required_coverage"]["delta"]
                    for step in result["timeline"])
        assert total == result["summary"]["required_coverage_delta"]

    def test_changed_plus_unchanged_is_all_dimension_slots(self, result):
        summary = result["summary"]
        assert (summary["dimensions_changed_total"]
                + summary["dimensions_unchanged_total"]) == \
            summary["steps"] * len(DIMENSIONS)

    def test_required_plus_supporting_equals_changed(self, result):
        summary = result["summary"]
        assert (summary["required_changes_total"]
                + summary["supporting_changes_total"]) == \
            summary["dimensions_changed_total"]

    def test_transition_sum_equals_changed(self, result):
        total = sum(result["summary"]["transition_summary"].values())
        assert total == result["summary"]["dimensions_changed_total"]


class TestSelection:
    def test_default_selects_every_version_ascending(self, result):
        assert result["versions_analyzed"] == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_subset_selection_pairs(self, service):
        result = service.build_timeline(VIDEO, [1, 3, 5])
        assert pairs(result["timeline"]) == [(1, 3), (3, 5)]
        assert result["steps"] == 2

    def test_subset_selection_summary(self, service):
        summary = service.build_timeline(VIDEO, [1, 3, 5])["summary"]
        assert summary["versions_analyzed"] == 3
        assert summary["steps"] == 2
        assert summary["dimensions_changed_total"] == 8
        assert summary["dimensions_unchanged_total"] == 10
        assert summary["required_changes_total"] == 6
        assert summary["supporting_changes_total"] == 2
        assert summary["transition_summary"] == {
            "missing_to_weak": 0, "missing_to_present": 0,
            "weak_to_missing": 0, "weak_to_present": 0,
            "present_to_missing": 7, "present_to_weak": 1}
        assert summary["first_version"] == 1
        assert summary["last_version"] == 5
        assert summary["first_required_coverage_percentage"] == 100
        assert summary["last_required_coverage_percentage"] == 14
        assert summary["required_coverage_delta"] == -86

    def test_single_selected_version(self, service):
        result = service.build_timeline(VIDEO, [7])
        assert result["versions_analyzed"] == [7]
        assert result["steps"] == 0
        assert result["timeline"] == []
        assert result["summary"]["versions_analyzed"] == 1
        assert result["summary"]["first_version"] == 7
        assert result["summary"]["last_version"] == 7
        assert result["summary"]["first_required_coverage_percentage"] == 100
        assert result["summary"]["last_required_coverage_percentage"] == 100
        assert result["summary"]["required_coverage_delta"] == 0

    def test_single_selected_version_uses_same_version_day26(self, service):
        result = service.build_timeline(VIDEO, [2])
        same = service.readiness_change_service.compare_versions(VIDEO, 2, 2)
        assert result["summary"]["first_required_coverage_percentage"] == \
            same["version_a"]["required_coverage_percentage"] == 86
        assert result["summary"]["last_required_coverage_percentage"] == 86

    def test_two_versions_produce_one_step(self, service):
        result = service.build_timeline(VIDEO, [1, 2])
        assert result["steps"] == 1
        assert pairs(result["timeline"]) == [(1, 2)]

    def test_requested_order_preserved_not_resorted(self, service):
        result = service.build_timeline(VIDEO, [4, 2])
        assert result["versions_analyzed"] == [4, 2]
        assert pairs(result["timeline"]) == [(4, 2)]
        assert result["summary"]["first_version"] == 4
        assert result["summary"]["last_version"] == 2

    def test_reverse_pair_coverage_flips_sign(self, service):
        forward = service.build_timeline(VIDEO, [4, 2])
        assert forward["summary"]["required_coverage_delta"] == 72
        assert forward["timeline"][0]["required_coverage"] == {
            "version_a": 14, "version_b": 86, "delta": 72}

    def test_pair_order_2_1(self, service):
        result = service.build_timeline(VIDEO, [2, 1])
        assert pairs(result["timeline"]) == [(2, 1)]
        assert result["summary"]["required_coverage_delta"] == 14

    def test_selection_order_not_normalized(self, service):
        result = service.build_timeline(VIDEO, [5, 4])
        assert result["versions_analyzed"] == [5, 4]
        assert pairs(result["timeline"]) == [(5, 4)]

    def test_default_after_deletion_skips_gap(self, history, service):
        history.delete_version(VIDEO, 3)
        result = service.build_timeline(VIDEO)
        assert result["versions_analyzed"] == [1, 2, 4, 5, 6, 7, 8]
        assert pairs(result["timeline"]) == [
            (1, 2), (2, 4), (4, 5), (5, 6), (6, 7), (7, 8)]
        assert result["steps"] == 6

    def test_selected_deleted_version_raises(self, history, service):
        history.delete_version(VIDEO, 3)
        with pytest.raises(ValueError,
                           match="Version 3 not found for video 'sample"
                                 "\\.mp4'\\."):
            service.build_timeline(VIDEO, [3])

    def test_nonexistent_version_raises_day16_message(self, service):
        with pytest.raises(ValueError,
                           match="Version 99 not found for video 'sample"
                                 "\\.mp4'\\."):
            service.build_timeline(VIDEO, [1, 99])

    def test_tuple_selection_accepted(self, service):
        result = service.build_timeline(VIDEO, (1, 2))
        assert result["steps"] == 1
        assert pairs(result["timeline"]) == [(1, 2)]


class TestValidation:
    def test_empty_list_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must be a non-empty list of "
                                 "positive integers\\."):
            service.build_timeline(VIDEO, [])

    def test_non_list_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must be a non-empty list of "
                                 "positive integers\\."):
            service.build_timeline(VIDEO, 1)

    def test_string_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must be a non-empty list of "
                                 "positive integers\\."):
            service.build_timeline(VIDEO, "1,2")

    def test_zero_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.build_timeline(VIDEO, [0])

    def test_negative_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.build_timeline(VIDEO, [-1])

    def test_bool_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.build_timeline(VIDEO, [True])

    def test_float_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.build_timeline(VIDEO, [1.5])

    def test_numeric_string_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.build_timeline(VIDEO, ["2"])

    def test_none_element_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.build_timeline(VIDEO, [None])

    def test_duplicates_rejected(self, service):
        with pytest.raises(ValueError,
                           match="duplicate versions are not allowed\\."):
            service.build_timeline(VIDEO, [1, 1])

    def test_duplicates_later_in_list_rejected(self, service):
        with pytest.raises(ValueError,
                           match="duplicate versions are not allowed\\."):
            service.build_timeline(VIDEO, [1, 2, 1])

    def test_invalid_element_checked_before_lookup(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.build_timeline(VIDEO, [0, 99])


class TestEmptyAndSingle:
    @pytest.fixture
    def empty(self, service):
        return service.build_timeline("none.mp4")

    def test_empty_top_level_keys(self, empty):
        assert set(empty.keys()) == TOP_KEYS

    def test_empty_exact_result(self, empty):
        assert empty == {
            "video_filename": "none.mp4",
            "versions_analyzed": [],
            "steps": 0,
            "timeline": [],
            "summary": {
                "versions_analyzed": 0,
                "steps": 0,
                "dimensions_changed_total": 0,
                "dimensions_unchanged_total": 0,
                "required_changes_total": 0,
                "supporting_changes_total": 0,
                "transition_summary": {
                    "missing_to_weak": 0, "missing_to_present": 0,
                    "weak_to_missing": 0, "weak_to_present": 0,
                    "present_to_missing": 0, "present_to_weak": 0},
                "first_version": None,
                "last_version": None,
                "first_required_coverage_percentage": None,
                "last_required_coverage_percentage": None,
                "required_coverage_delta": 0,
            },
        }

    def test_empty_selection_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must be a non-empty list of "
                                 "positive integers\\."):
            service.build_timeline("none.mp4", [])

    def test_single_version_history(self, history):
        service = _build_service(history)
        history.delete_version(VIDEO, 2)
        history.delete_version(VIDEO, 3)
        for version in (4, 5, 6, 7, 8):
            history.delete_version(VIDEO, version)
        result = service.build_timeline(VIDEO)
        assert result["versions_analyzed"] == [1]
        assert result["steps"] == 0
        assert result["timeline"] == []
        assert result["summary"]["versions_analyzed"] == 1
        assert result["summary"]["first_version"] == 1
        assert result["summary"]["last_version"] == 1
        assert result["summary"]["first_required_coverage_percentage"] == 100
        assert result["summary"]["last_required_coverage_percentage"] == 100
        assert result["summary"]["required_coverage_delta"] == 0

    def test_single_version_in_validation_error_path(self, service):
        with pytest.raises(ValueError, match="Version 99 not found"):
            service.build_timeline("none.mp4", [99])


class TestDeterminism:
    def test_repeated_calls_identical(self, service):
        first = json.dumps(service.build_timeline(VIDEO), sort_keys=True)
        second = json.dumps(service.build_timeline(VIDEO), sort_keys=True)
        assert first == second

    def test_two_service_instances_identical(self, history, change):
        import re
        first = json.dumps(
            PromptReadinessTimelineService(history, change)
            .build_timeline(VIDEO), sort_keys=True)
        second = json.dumps(
            PromptReadinessTimelineService(history, change)
            .build_timeline(VIDEO), sort_keys=True)
        assert first == second
        assert not re.search(r"\d{4}-\d{2}-\d{2}", first)

    def test_no_timestamps_or_dates(self, service):
        import re
        text = json.dumps(service.build_timeline(VIDEO))
        assert not re.search(r"\d{4}-\d{2}-\d{2}", text)
        assert not re.search(r"\d{2}:\d{2}:\d{2}", text)

    def test_no_uuids_or_random_ids(self, service):
        import re
        text = json.dumps(service.build_timeline(VIDEO))
        assert not re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            text)

    def test_result_is_json_serializable(self, result):
        assert json.loads(json.dumps(result)) == result

    def test_subset_selection_deterministic(self, service):
        first = service.build_timeline(VIDEO, [1, 3, 5])
        second = service.build_timeline(VIDEO, [1, 3, 5])
        assert json.dumps(first, sort_keys=True) == \
            json.dumps(second, sort_keys=True)


class TestReadOnlyIntegrity:
    def _snapshot(self, history):
        return json.dumps(
            [record for record in
             sorted(history.list_versions(VIDEO),
                    key=lambda record: record["version"])],
            sort_keys=True)

    def test_history_records_unchanged(self, history, service):
        before = self._snapshot(history)
        service.build_timeline(VIDEO)
        assert self._snapshot(history) == before

    def test_version_count_unchanged(self, history, service):
        service.build_timeline(VIDEO)
        assert len(history.list_versions(VIDEO)) == 8

    def test_prompt_text_unchanged(self, history, service):
        service.build_timeline(VIDEO, [1, 5, 8])
        assert history.get_version(VIDEO, 1)["prompt"] == FULL
        assert history.get_version(VIDEO, 5)["prompt"] == CITY_ENV100
        assert history.get_version(VIDEO, 8)["prompt"] == SUBJ70

    def test_source_metadata_unchanged(self, history, service):
        service.build_timeline(VIDEO)
        record = history.get_version(VIDEO, 2)
        assert record["source"] == "custom"
        assert record["operation"] == ""

    def test_favorites_unchanged(self, history, service):
        org = PromptOrganizationService(history)
        org.favorite_version(VIDEO, 1)
        service.build_timeline(VIDEO)
        assert org.list_favorites(VIDEO) == [
            {"version": 1, "favorite": True, "tags": []}]

    def test_tags_unchanged(self, history, service):
        org = PromptOrganizationService(history)
        org.add_tags(VIDEO, 4, ["keep", "review"])
        service.build_timeline(VIDEO)
        entry = org.get_organization(VIDEO, 4)
        assert entry["tags"] == ["keep", "review"]

    def test_no_versions_created_or_deleted(self, history, service):
        before = [record["version"] for record in
                  history.list_versions(VIDEO)]
        service.build_timeline(VIDEO, [4, 1])
        after = [record["version"] for record in
                 history.list_versions(VIDEO)]
        assert after == before == [1, 2, 3, 4, 5, 6, 7, 8]


class TestNoRankingLanguage:
    RANKING_WORDS = (
        "best", "worst", "winner", "winning", "rank", "ranking", "ranked",
        "superior", "inferior", "better", "worse", "perfect", "guaranteed",
        "recommended", "recommendation", "ideal", "outperforms",
        "improvement", "improved", "improves", "gain",
    )

    def _text(self, result):
        return json.dumps(result).lower()

    def test_no_ranking_words_in_full_chain(self, result):
        import re
        text = self._text(result)
        for word in self.RANKING_WORDS:
            assert not re.search(rf"\b{word}\b", text), word

    def test_no_ranking_words_in_subset(self, service):
        import re
        text = self._text(service.build_timeline(VIDEO, [1, 3, 5]))
        for word in self.RANKING_WORDS:
            assert not re.search(rf"\b{word}\b", text), word

    def test_no_comparison_prose(self, service):
        text = self._text(service.build_timeline(VIDEO))
        for phrase in ("more ready", "less ready", "more consistent",
                       "readiness improved", "readiness declined"):
            assert phrase not in text

    def test_no_winner_or_selection_keys(self, result):
        import re
        text = json.dumps(result)
        assert not re.search(
            r"\"(winner|best_version|recommended_version|rankings)\"", text)

    def test_delta_is_plain_integer_not_language(self, result):
        summary = result["summary"]
        assert type(summary["required_coverage_delta"]) is int
        assert not isinstance(summary["required_coverage_delta"], bool)


class TestNoLeaks:
    def test_no_absolute_paths(self, result):
        import re
        text = json.dumps(result)
        assert not re.search(r"[A-Za-z]:\\", text)
        assert "/home/" not in text
        assert "/Users/" not in text

    def test_no_internal_names(self, result):
        text = json.dumps(result)
        for name in ("PromptReadinessTimelineService",
                     "PromptReadinessChangeService",
                     "PromptHistoryService",
                     "prompt_readiness_timeline_service",
                     "prompt_readiness_change_service",
                     "readiness_change_service",
                     "history_service"):
            assert name not in text, name

    def test_no_prompt_text_echoed(self, service):
        text = json.dumps(service.build_timeline(VIDEO))
        for fragment in ("film grain style portrait", "quiet city street",
                         "nothing specific at all"):
            assert fragment not in text

    def test_no_traceback_or_debug_artifacts(self, result):
        text = json.dumps(result)
        assert "Traceback" not in text
        assert "File \\\"" not in text
        assert "NoneType" not in text

    def test_no_secrets_or_environment(self, result):
        text = json.dumps(result).upper()
        for token in ("SECRET", "PASSWORD", "API_KEY", "TOKEN",
                      "OS.ENVIRON"):
            assert token not in text, token


class TestSourceContract:
    @pytest.fixture
    def source(self):
        import inspect
        from app.services import prompt_readiness_timeline_service as module
        return inspect.getsource(module)

    def test_imports_only_expected_modules(self, source):
        for forbidden in ("import socket", "import requests",
                          "import urllib", "import http", "import sqlite3",
                          "import pathlib", "from pathlib",
                          "import os", "import random", "import uuid",
                          "import time", "import datetime", "import openai"):
            assert forbidden not in source, forbidden

    def test_no_filesystem_or_network_calls(self, source):
        for forbidden in ("open(", "os.environ", "os.path",
                          "requests.get", "requests.post",
                          "urlopen", "sqlite3.connect"):
            assert forbidden not in source, forbidden

    def test_uses_history_read_methods(self, source):
        assert "list_versions" in source
        assert "get_version" in source

    def test_uses_day26_compare(self, source):
        assert "compare_versions" in source

    def test_never_mutates_history(self, source):
        for forbidden in ("create_version(", "delete_version(",
                          "save_advanced_prompt(", "save_refinement(",
                          "save_template(", "favorite_version(",
                          "add_tags("):
            assert forbidden not in source, forbidden

    def test_defined_methods_exact(self):
        import inspect
        from app.services.prompt_readiness_timeline_service import \
            PromptReadinessTimelineService
        names = [
            name for name, _
            in inspect.getmembers(PromptReadinessTimelineService,
                                  inspect.isfunction)
            if name != "__init__"
        ]
        assert sorted(names) == ["_select", "build_timeline"]

    def test_no_store_attributes_in_source(self, source):
        for forbidden in ("self._storage", "self._versions",
                          "self._timeline", "self._store"):
            assert forbidden not in source, forbidden


SELECTIONS = (None, [1, 3, 5], [4, 2], [2, 6], [1, 2], [7], [3, 4, 5, 6])


class TestAggregationInvariants:
    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_changed_plus_unchanged_slots(self, service, selection):
        result = service.build_timeline(VIDEO, selection)
        summary = result["summary"]
        assert (summary["dimensions_changed_total"]
                + summary["dimensions_unchanged_total"]) == \
            summary["steps"] * len(DIMENSIONS)

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_required_plus_supporting_equals_changed(
            self, service, selection):
        summary = service.build_timeline(VIDEO, selection)["summary"]
        assert (summary["required_changes_total"]
                + summary["supporting_changes_total"]) == \
            summary["dimensions_changed_total"]

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_transition_totals_equal_changed(self, service, selection):
        summary = service.build_timeline(VIDEO, selection)["summary"]
        assert sum(summary["transition_summary"].values()) == \
            summary["dimensions_changed_total"]

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_delta_equals_sum_of_step_deltas(self, service, selection):
        result = service.build_timeline(VIDEO, selection)
        total = sum(step["required_coverage"]["delta"]
                    for step in result["timeline"])
        if result["steps"] == 0:
            total = result["summary"]["required_coverage_delta"]
        assert total == result["summary"]["required_coverage_delta"]

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_delta_equals_last_minus_first(self, service, selection):
        summary = service.build_timeline(VIDEO, selection)["summary"]
        expected = (summary["last_required_coverage_percentage"]
                    - summary["first_required_coverage_percentage"])
        assert summary["required_coverage_delta"] == expected

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_step_totals_match_timeline(self, service, selection):
        result = service.build_timeline(VIDEO, selection)
        changed = sum(step["dimensions_changed"]
                      for step in result["timeline"])
        required = sum(len(step["required_changes"])
                       for step in result["timeline"])
        assert changed == result["summary"]["dimensions_changed_total"]
        assert required == result["summary"]["required_changes_total"]

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_versions_analyzed_matches_selection_order(
            self, service, selection):
        result = service.build_timeline(VIDEO, selection)
        expected = selection if selection is not None else \
            [1, 2, 3, 4, 5, 6, 7, 8]
        assert result["versions_analyzed"] == expected

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_steps_count_matches_selection(self, service, selection):
        result = service.build_timeline(VIDEO, selection)
        count = 8 if selection is None else len(selection)
        assert result["steps"] == max(0, count - 1)


class TestChainingProperties:
    @pytest.mark.parametrize("selection", (None, [1, 3, 5], [4, 2],
                                           [2, 6, 7]))
    def test_adjacent_steps_chain(self, service, selection):
        timeline = service.build_timeline(VIDEO, selection)["timeline"]
        for previous, following in zip(timeline, timeline[1:]):
            assert previous["version_b"]["version"] == \
                following["version_a"]["version"]

    @pytest.mark.parametrize("selection", (None, [1, 3, 5], [4, 2],
                                           [2, 6, 7]))
    def test_timeline_length_is_pairs(self, service, selection):
        result = service.build_timeline(VIDEO, selection)
        count = 8 if selection is None else len(selection)
        assert len(result["timeline"]) == max(0, count - 1)

    @pytest.mark.parametrize("pair", ((1, 3), (3, 5), (4, 2), (7, 8)))
    def test_each_step_byte_equals_direct_day26(
            self, service, pair):
        result = service.build_timeline(VIDEO, list(pair))
        direct = service.readiness_change_service.compare_versions(
            VIDEO, pair[0], pair[1])
        assert json.dumps(result["timeline"][0], sort_keys=True) == \
            json.dumps(direct, sort_keys=True)

    def test_subset_steps_all_equal_direct_day26(self, service):
        result = service.build_timeline(VIDEO, [1, 4, 6, 8])
        for step in result["timeline"]:
            direct = service.readiness_change_service.compare_versions(
                VIDEO, step["version_a"]["version"],
                step["version_b"]["version"])
            assert json.dumps(step, sort_keys=True) == \
                json.dumps(direct, sort_keys=True)

    def test_step_order_follows_selection_order(self, service):
        result = service.build_timeline(VIDEO, [6, 4, 2])
        assert pairs(result["timeline"]) == [(6, 4), (4, 2)]

    def test_deleted_version_gaps_are_not_compared(self, history, service):
        history.delete_version(VIDEO, 4)
        result = service.build_timeline(VIDEO, [1, 2, 5])
        assert pairs(result["timeline"]) == [(1, 2), (2, 5)]


class TestSummaryCoverage:
    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_first_coverage_matches_first_step(
            self, service, selection):
        result = service.build_timeline(VIDEO, selection)
        if not result["timeline"]:
            return
        assert result["summary"]["first_required_coverage_percentage"] == \
            result["timeline"][0]["required_coverage"]["version_a"]

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_last_coverage_matches_last_step(self, service, selection):
        result = service.build_timeline(VIDEO, selection)
        if not result["timeline"]:
            return
        assert result["summary"]["last_required_coverage_percentage"] == \
            result["timeline"][-1]["required_coverage"]["version_b"]

    @pytest.mark.parametrize("selection", ([1], [2], [7], [8]))
    def test_single_version_coverage_from_day26_same_version(
            self, service, selection):
        result = service.build_timeline(VIDEO, selection)
        same = service.readiness_change_service.compare_versions(
            VIDEO, selection[0], selection[0])
        expected = same["version_a"]["required_coverage_percentage"]
        summary = result["summary"]
        assert summary["first_required_coverage_percentage"] == expected
        assert summary["last_required_coverage_percentage"] == expected
        assert summary["required_coverage_delta"] == 0

    @pytest.mark.parametrize("selection", (None, [1, 3, 5], [4, 2]))
    def test_coverage_values_come_from_steps(self, service, selection):
        result = service.build_timeline(VIDEO, selection)
        if not result["timeline"]:
            return
        summary = result["summary"]
        assert summary["first_required_coverage_percentage"] in (
            step["required_coverage"]["version_a"]
            for step in result["timeline"])
        assert summary["last_required_coverage_percentage"] in (
            step["required_coverage"]["version_b"]
            for step in result["timeline"])

    def test_default_first_and_last_coverage(self, result):
        summary = result["summary"]
        assert summary["first_required_coverage_percentage"] == 100
        assert summary["last_required_coverage_percentage"] == 86
        assert summary["required_coverage_delta"] == -14

    def test_empty_coverage_is_none_not_zero(self, service):
        summary = service.build_timeline("none.mp4")["summary"]
        assert summary["first_required_coverage_percentage"] is None
        assert summary["last_required_coverage_percentage"] is None
        assert summary["first_version"] is None
        assert summary["last_version"] is None
        assert summary["required_coverage_delta"] == 0

    @pytest.mark.parametrize("selection", ([2, 1], [4, 2], [6, 7]))
    def test_positive_delta_arithmetic(self, service, selection):
        summary = service.build_timeline(VIDEO, selection)["summary"]
        assert summary["required_coverage_delta"] == \
            summary["last_required_coverage_percentage"] - \
            summary["first_required_coverage_percentage"]
        assert summary["required_coverage_delta"] > 0
