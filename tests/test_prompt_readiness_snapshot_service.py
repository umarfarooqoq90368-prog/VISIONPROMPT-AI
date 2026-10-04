"""Tests for the prompt readiness snapshot service (Day 28)."""
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
from app.services.prompt_readiness_snapshot_service import (
    PromptReadinessSnapshotService,
)

# --- Fixture prompts (Day 21/24/26/27 verified) ----------------------------
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

TOP_KEYS = {"video_filename", "versions_analyzed", "snapshots", "summary"}

SUMMARY_KEYS = {
    "versions_analyzed", "ready_count", "needs_attention_count",
    "required", "supporting", "dimension_summary", "organization",
}

SNAPSHOT_KEYS = {
    "version", "source", "operation", "created_at", "favorite", "tags",
    "readiness",
}

READINESS_KEYS = {
    "status", "required_coverage_percentage", "required", "supporting",
    "missing_dimensions", "weak_dimensions",
}

REQUIRED_KEYS = [
    "subject", "action", "environment", "camera", "lighting",
    "visual_style", "composition",
]
SUPPORTING_KEYS = ["color", "audio"]

# standard 8-version history (probe-verified):
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
    organization = PromptOrganizationService(history)
    return PromptReadinessSnapshotService(history, readiness, organization)


@pytest.fixture
def history():
    return _build_history()


@pytest.fixture
def organization(history):
    return PromptOrganizationService(history)


@pytest.fixture
def readiness():
    return PromptReadinessService(PromptQualityService())


@pytest.fixture
def service(history, readiness, organization):
    return PromptReadinessSnapshotService(history, readiness, organization)


@pytest.fixture
def result(service):
    return service.create_snapshot(VIDEO)


@pytest.fixture
def marked(history, organization):
    """Standard history with probe-verified favorites and tags."""
    organization.favorite_version(VIDEO, 1)
    organization.favorite_version(VIDEO, 7)
    organization.add_tags(VIDEO, 1, [" Cinematic ", "ai"])
    organization.add_tags(VIDEO, 4, ["final"])
    organization.add_tags(VIDEO, 7, ["cinematic", "draft", "cinematic"])
    return history


class TestWiring:
    def test_constructor_state_only_three_dependencies(
            self, history, readiness, organization):
        svc = PromptReadinessSnapshotService(
            history, readiness, organization)
        assert set(vars(svc).keys()) == {
            "history_service", "readiness_service",
            "organization_service"}
        assert svc.history_service is history
        assert svc.readiness_service is readiness
        assert svc.organization_service is organization

    def test_readiness_is_day24_instance(self, service):
        assert isinstance(service.readiness_service, PromptReadinessService)

    def test_organization_is_day17_instance(self, service):
        assert isinstance(service.organization_service,
                          PromptOrganizationService)

    def test_reuses_same_history_store(self, service, history):
        assert service.history_service is history

    def test_no_fourth_store_or_services(self, service):
        for name in ("quality_service", "change_service",
                     "timeline_service", "search_service",
                     "export_service", "package_service"):
            assert not hasattr(service, name), name

    def test_no_second_store_created(self, service):
        for name in ("_storage", "_versions", "_snapshots", "_cache"):
            assert not hasattr(service, name), name


class TestResponseStructure:
    def test_top_level_keys_exact(self, result):
        assert set(result.keys()) == TOP_KEYS

    def test_video_filename_echo(self, result):
        assert result["video_filename"] == VIDEO

    def test_versions_analyzed_all_eight_ascending(self, result):
        assert result["versions_analyzed"] == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_snapshots_count_and_order(self, result):
        assert len(result["snapshots"]) == 8
        assert [s["version"] for s in result["snapshots"]] == \
            result["versions_analyzed"]

    def test_summary_keys_exact(self, result):
        assert set(result["summary"].keys()) == SUMMARY_KEYS

    def test_snapshot_keys_exact(self, result):
        for snapshot in result["snapshots"]:
            assert set(snapshot.keys()) == SNAPSHOT_KEYS, \
                list(snapshot.keys())

    def test_readiness_keys_exact(self, result):
        for snapshot in result["snapshots"]:
            assert set(snapshot["readiness"].keys()) == READINESS_KEYS, \
                list(snapshot["readiness"].keys())

    def test_required_keys_in_day21_required_order(self, result):
        for snapshot in result["snapshots"]:
            assert list(snapshot["readiness"]["required"].keys()) == \
                REQUIRED_KEYS

    def test_supporting_keys_in_day21_supporting_order(self, result):
        for snapshot in result["snapshots"]:
            assert list(snapshot["readiness"]["supporting"].keys()) == \
                SUPPORTING_KEYS

    def test_value_types(self, result):
        for snapshot in result["snapshots"]:
            assert type(snapshot["version"]) is int
            assert isinstance(snapshot["source"], str)
            assert isinstance(snapshot["operation"], str)
            assert isinstance(snapshot["created_at"], str)
            assert type(snapshot["favorite"]) is bool
            assert isinstance(snapshot["tags"], list)
            assert all(isinstance(tag, str) for tag in snapshot["tags"])
            assert snapshot["readiness"]["status"] in (
                "ready", "needs_attention")
            assert type(
                snapshot["readiness"]["required_coverage_percentage"]) is int

    def test_no_prompt_fields_in_snapshots(self, result):
        for snapshot in result["snapshots"]:
            assert "prompt" not in snapshot
            assert "negative_prompt" not in snapshot
            text = json.dumps(snapshot)
            assert FULL[:40] not in text


class TestSnapshotContent:
    @pytest.fixture
    def by_version(self, result):
        return {s["version"]: s for s in result["snapshots"]}

    def test_every_snapshot_matches_day24_exactly(
            self, service, history, by_version):
        for version, snapshot in by_version.items():
            record = history.get_version(VIDEO, version)
            readiness = service.readiness_service.validate_prompt(
                record["prompt"])["readiness"]
            block = snapshot["readiness"]
            assert block["status"] == readiness["status"]
            assert block["required_coverage_percentage"] == \
                readiness["coverage"]["required_coverage_percentage"]
            assert block["missing_dimensions"] == \
                readiness["missing_dimensions"]
            assert block["weak_dimensions"] == readiness["weak_dimensions"]
            checks = {item["dimension"]: item
                      for item in readiness["checklist"]}
            for dim in REQUIRED_DIMENSIONS:
                assert block["required"][dim] == {
                    "status": checks[dim]["status"],
                    "score": checks[dim]["score"],
                }
            for dim in SUPPORTING_DIMENSIONS:
                assert block["supporting"][dim] == {
                    "status": checks[dim]["status"],
                    "score": checks[dim]["score"],
                }

    def test_source_operation_metadata_passed_through(self, by_version):
        expected = [(source, operation)
                    for _, source, operation in STANDARD]
        actual = [(by_version[v]["source"], by_version[v]["operation"])
                  for v in range(1, 9)]
        assert actual == expected

    def test_created_at_comes_from_stored_record(
            self, history, by_version):
        for version, snapshot in by_version.items():
            record = history.get_version(VIDEO, version)
            assert snapshot["created_at"] == record["created_at"]

    def test_full_version_ready(self, by_version):
        block = by_version[1]["readiness"]
        assert block["status"] == "ready"
        assert block["required_coverage_percentage"] == 100
        assert block["missing_dimensions"] == []
        assert block["weak_dimensions"] == []

    def test_weak_camera_version(self, by_version):
        block = by_version[2]["readiness"]
        assert block["status"] == "needs_attention"
        assert block["required_coverage_percentage"] == 86
        assert block["missing_dimensions"] == []
        assert block["weak_dimensions"] == ["camera"]
        assert block["required"]["camera"] == {"status": "weak", "score": 40}

    def test_cameraless_version(self, by_version):
        block = by_version[3]["readiness"]
        assert block["required_coverage_percentage"] == 86
        assert block["missing_dimensions"] == ["camera"]
        assert block["weak_dimensions"] == []
        assert block["required"]["camera"] == {
            "status": "missing", "score": 0}

    def test_city_version_raw_scores(self, by_version):
        block = by_version[4]["readiness"]
        assert block["status"] == "needs_attention"
        assert block["required_coverage_percentage"] == 14
        assert block["required"]["subject"] == {"status": "weak", "score": 40}
        assert block["required"]["environment"] == {
            "status": "present", "score": 70}
        assert block["required"]["camera"] == {
            "status": "missing", "score": 0}
        assert block["supporting"]["color"] == {
            "status": "missing", "score": 0}
        assert block["supporting"]["audio"] == {
            "status": "missing", "score": 0}
        assert block["missing_dimensions"] == [
            "action", "camera", "lighting", "visual_style", "color",
            "composition", "audio"]
        assert block["weak_dimensions"] == ["subject"]

    def test_score_only_difference_between_v4_and_v5(self, by_version):
        b4 = by_version[4]["readiness"]
        b5 = by_version[5]["readiness"]
        assert b4["status"] == b5["status"]
        assert b4["missing_dimensions"] == b5["missing_dimensions"]
        assert b4["weak_dimensions"] == b5["weak_dimensions"]
        assert b4["required_coverage_percentage"] == \
            b5["required_coverage_percentage"] == 14
        assert b5["required"]["environment"] == {
            "status": "present", "score": 100}
        assert b4["required"]["environment"] == {
            "status": "present", "score": 70}

    def test_minimal_version_all_missing(self, by_version):
        block = by_version[6]["readiness"]
        assert block["status"] == "needs_attention"
        assert block["required_coverage_percentage"] == 0
        assert block["missing_dimensions"] == list(DIMENSIONS)
        assert block["weak_dimensions"] == []

    def test_required_only_version_ready_with_missing_supporting(
            self, by_version):
        block = by_version[7]["readiness"]
        assert block["status"] == "ready"
        assert block["required_coverage_percentage"] == 100
        assert block["missing_dimensions"] == ["color", "audio"]
        assert block["weak_dimensions"] == []
        assert block["supporting"]["color"] == {
            "status": "missing", "score": 0}
        assert block["supporting"]["audio"] == {
            "status": "missing", "score": 0}

    def test_subject70_version(self, by_version):
        block = by_version[8]["readiness"]
        assert block["status"] == "needs_attention"
        assert block["required_coverage_percentage"] == 86
        assert block["missing_dimensions"] == []
        assert block["weak_dimensions"] == ["action"]
        assert block["required"]["action"] == {"status": "weak", "score": 40}
        assert block["required"]["subject"] == {
            "status": "present", "score": 70}

    def test_missing_and_weak_lists_in_day21_order(self, by_version):
        for snapshot in by_version.values():
            block = snapshot["readiness"]
            for key in ("missing_dimensions", "weak_dimensions"):
                dims = block[key]
                assert dims == [d for d in DIMENSIONS if d in set(dims)], \
                    f"{key} must follow Day21 order"


class TestSelectedVersions:
    def test_subset_1_3(self, service):
        data = service.create_snapshot(VIDEO, [1, 3])
        assert data["versions_analyzed"] == [1, 3]
        assert [s["version"] for s in data["snapshots"]] == [1, 3]
        assert data["summary"]["versions_analyzed"] == 2

    def test_reverse_order_3_1_preserved(self, service):
        data = service.create_snapshot(VIDEO, [3, 1])
        assert data["versions_analyzed"] == [3, 1]
        assert [s["version"] for s in data["snapshots"]] == [3, 1]

    def test_reverse_order_not_sorted(self, service):
        data = service.create_snapshot(VIDEO, [8, 4, 1])
        assert data["versions_analyzed"] == [8, 4, 1]

    def test_no_substitution_nonexistent_raises(self, service):
        with pytest.raises(ValueError,
                           match="Version 99 not found for video 'sample"
                                 "\\.mp4'\\."):
            service.create_snapshot(VIDEO, [1, 99])

    def test_single_version(self, service):
        data = service.create_snapshot(VIDEO, [7])
        assert data["versions_analyzed"] == [7]
        assert len(data["snapshots"]) == 1
        assert data["snapshots"][0]["version"] == 7
        assert data["summary"]["versions_analyzed"] == 1

    def test_tuple_selection_accepted(self, service):
        data = service.create_snapshot(VIDEO, (2, 5))
        assert data["versions_analyzed"] == [2, 5]

    def test_default_after_deletion_skips_gap(self, history, service):
        history.delete_version(VIDEO, 3)
        data = service.create_snapshot(VIDEO)
        assert data["versions_analyzed"] == [1, 2, 4, 5, 6, 7, 8]
        assert len(data["snapshots"]) == 7
        assert data["summary"]["versions_analyzed"] == 7

    def test_selected_deleted_version_raises(self, history, service):
        history.delete_version(VIDEO, 3)
        with pytest.raises(ValueError,
                           match="Version 3 not found for video 'sample"
                                 "\\.mp4'\\."):
            service.create_snapshot(VIDEO, [3])

    def test_selection_changes_aggregate(self, service):
        full = service.create_snapshot(VIDEO)["summary"]
        subset = service.create_snapshot(VIDEO, [1, 7])["summary"]
        assert full["versions_analyzed"] == 8
        assert subset["versions_analyzed"] == 2
        assert subset["required"]["total"] == 14
        assert subset["required"]["present"] == 14
        assert subset["required"]["coverage_percentage"] == 100
        assert full["required"]["present"] == 34

    def test_snapshots_never_reordered_forward_only(self, service):
        data = service.create_snapshot(VIDEO, [7, 6, 5])
        versions = [s["version"] for s in data["snapshots"]]
        assert versions == [7, 6, 5]
        assert versions != sorted(versions)


class TestValidation:
    def test_empty_list_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must be a non-empty list of "
                                 "positive integers\\."):
            service.create_snapshot(VIDEO, [])

    def test_non_list_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must be a non-empty list of "
                                 "positive integers\\."):
            service.create_snapshot(VIDEO, 1)

    def test_string_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must be a non-empty list of "
                                 "positive integers\\."):
            service.create_snapshot(VIDEO, "1,2")

    def test_zero_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.create_snapshot(VIDEO, [0])

    def test_negative_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.create_snapshot(VIDEO, [-1])

    def test_bool_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.create_snapshot(VIDEO, [True])

    def test_float_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.create_snapshot(VIDEO, [1.5])

    def test_numeric_string_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.create_snapshot(VIDEO, ["2"])

    def test_none_element_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.create_snapshot(VIDEO, [None])

    def test_duplicates_rejected(self, service):
        with pytest.raises(ValueError,
                           match="duplicate versions are not allowed\\."):
            service.create_snapshot(VIDEO, [1, 1])

    def test_duplicates_later_in_list_rejected(self, service):
        with pytest.raises(ValueError,
                           match="duplicate versions are not allowed\\."):
            service.create_snapshot(VIDEO, [2, 3, 2])

    def test_invalid_element_checked_before_lookup(self, service):
        with pytest.raises(ValueError,
                           match="versions must contain positive integers\\."):
            service.create_snapshot(VIDEO, [0, 99])


SELECTIONS = (None, [1, 3, 5], [4, 2], [6], [1, 7], [2, 3, 4, 5, 6])


def _count(data, selection):
    return 8 if selection is None else len(selection)


class TestAggregate:
    def test_default_counts(self, result):
        summary = result["summary"]
        assert summary["versions_analyzed"] == 8
        assert summary["ready_count"] == 2
        assert summary["needs_attention_count"] == 6

    def test_default_required_totals(self, result):
        assert result["summary"]["required"] == {
            "total": 56, "present": 34, "weak": 4, "missing": 18,
            "coverage_percentage": 61}

    def test_default_supporting_totals(self, result):
        assert result["summary"]["supporting"] == {
            "total": 16, "present": 8, "weak": 0, "missing": 8}

    def test_default_dimension_summary_exact(self, result):
        assert result["summary"]["dimension_summary"] == [
            {"dimension": "subject", "present": 5, "weak": 2, "missing": 1},
            {"dimension": "action", "present": 4, "weak": 1, "missing": 3},
            {"dimension": "environment", "present": 7, "weak": 0,
             "missing": 1},
            {"dimension": "camera", "present": 3, "weak": 1, "missing": 4},
            {"dimension": "lighting", "present": 5, "weak": 0, "missing": 3},
            {"dimension": "visual_style", "present": 5, "weak": 0,
             "missing": 3},
            {"dimension": "color", "present": 4, "weak": 0, "missing": 4},
            {"dimension": "composition", "present": 5, "weak": 0,
             "missing": 3},
            {"dimension": "audio", "present": 4, "weak": 0, "missing": 4},
        ]

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_required_total_is_n_times_7(self, service, selection):
        summary = service.create_snapshot(VIDEO, selection)["summary"]
        assert summary["required"]["total"] == \
            summary["versions_analyzed"] * 7

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_supporting_total_is_n_times_2(self, service, selection):
        summary = service.create_snapshot(VIDEO, selection)["summary"]
        assert summary["supporting"]["total"] == \
            summary["versions_analyzed"] * 2

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_required_partition_sums_to_total(self, service, selection):
        required = service.create_snapshot(VIDEO, selection)["summary"][
            "required"]
        assert required["present"] + required["weak"] + required["missing"] \
            == required["total"]

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_supporting_partition_sums_to_total(self, service, selection):
        supporting = service.create_snapshot(VIDEO, selection)["summary"][
            "supporting"]
        assert (supporting["present"] + supporting["weak"]
                + supporting["missing"]) == supporting["total"]

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_every_dimension_sums_to_n(self, service, selection):
        summary = service.create_snapshot(VIDEO, selection)["summary"]
        n = summary["versions_analyzed"]
        if n == 0:
            return
        assert len(summary["dimension_summary"]) == 9
        for row in summary["dimension_summary"]:
            assert row["present"] + row["weak"] + row["missing"] == n, row

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_dimension_summary_day21_order(self, service, selection):
        summary = service.create_snapshot(VIDEO, selection)["summary"]
        if summary["versions_analyzed"] == 0:
            assert summary["dimension_summary"] == []
            return
        assert [row["dimension"] for row in summary["dimension_summary"]] == \
            list(DIMENSIONS)

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_ready_plus_needs_attention_equals_n(self, service, selection):
        summary = service.create_snapshot(VIDEO, selection)["summary"]
        assert summary["ready_count"] + summary["needs_attention_count"] == \
            summary["versions_analyzed"]

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_required_coverage_rounding(self, service, selection):
        required = service.create_snapshot(VIDEO, selection)["summary"][
            "required"]
        if required["total"] == 0:
            assert required["coverage_percentage"] is None
            return
        assert required["coverage_percentage"] == round(
            required["present"] / required["total"] * 100)

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_aggregate_matches_per_snapshot_states(self, service, selection):
        data = service.create_snapshot(VIDEO, selection)
        summary = data["summary"]
        required_present = sum(
            1 for snap in data["snapshots"]
            for dim in REQUIRED_DIMENSIONS
            if snap["readiness"]["required"][dim]["status"] == "present")
        required_weak = sum(
            1 for snap in data["snapshots"]
            for dim in REQUIRED_DIMENSIONS
            if snap["readiness"]["required"][dim]["status"] == "weak")
        supporting_present = sum(
            1 for snap in data["snapshots"]
            for dim in SUPPORTING_DIMENSIONS
            if snap["readiness"]["supporting"][dim]["status"] == "present")
        assert summary["required"]["present"] == required_present
        assert summary["required"]["weak"] == required_weak
        assert summary["supporting"]["present"] == supporting_present

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_ready_count_matches_snapshot_statuses(self, service, selection):
        data = service.create_snapshot(VIDEO, selection)
        ready = sum(1 for snap in data["snapshots"]
                    if snap["readiness"]["status"] == "ready")
        assert data["summary"]["ready_count"] == ready

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_version_counts_match(self, service, selection):
        data = service.create_snapshot(VIDEO, selection)
        assert data["summary"]["versions_analyzed"] == len(data["snapshots"])
        expected = _count(data, selection)
        assert data["summary"]["versions_analyzed"] == expected


class TestOrganization:
    def test_default_favorite_count(self, marked, readiness, organization):
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        summary = service.create_snapshot(VIDEO)["summary"]
        assert summary["organization"]["favorite_count"] == 2

    def test_default_tag_counts_exact(self, marked, readiness, organization):
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        summary = service.create_snapshot(VIDEO)["summary"]
        assert summary["organization"]["tag_counts"] == {
            "ai": 1, "cinematic": 2, "draft": 1, "final": 1}

    def test_tag_counts_alphabetical_order(self, marked, readiness,
                                           organization):
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        tag_counts = service.create_snapshot(VIDEO)["summary"][
            "organization"]["tag_counts"]
        assert list(tag_counts.keys()) == sorted(tag_counts.keys())

    def test_snapshot_tags_normalized(self, marked, readiness, organization):
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        snapshots = {s["version"]: s
                     for s in service.create_snapshot(VIDEO)["snapshots"]}
        assert snapshots[1]["tags"] == ["ai", "cinematic"]
        assert snapshots[4]["tags"] == ["final"]
        assert snapshots[7]["tags"] == ["cinematic", "draft"]

    def test_duplicate_tag_counted_once_per_version(
            self, marked, readiness, organization):
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        snapshots = {s["version"]: s
                     for s in service.create_snapshot(VIDEO)["snapshots"]}
        assert snapshots[7]["tags"].count("cinematic") == 1
        tag_counts = service.create_snapshot(VIDEO)["summary"][
            "organization"]["tag_counts"]
        assert tag_counts["cinematic"] == 2, "v1 + v7, not double-counted"

    def test_version_without_org_metadata_defaults(self, result):
        snapshots = {s["version"]: s for s in result["snapshots"]}
        assert snapshots[2]["favorite"] is False
        assert snapshots[2]["tags"] == []
        assert snapshots[3]["favorite"] is False
        assert snapshots[3]["tags"] == []

    def test_no_marks_gives_zero_organization(self, result):
        organization = result["summary"]["organization"]
        assert organization["favorite_count"] == 0
        assert organization["tag_counts"] == {}

    def test_selection_limits_organization_counts(
            self, marked, readiness, organization):
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        summary = service.create_snapshot(VIDEO, [1, 4])["summary"]
        assert summary["organization"]["favorite_count"] == 1
        assert summary["organization"]["tag_counts"] == {
            "ai": 1, "cinematic": 1, "final": 1}

    def test_unselected_versions_not_counted(self, marked, readiness,
                                              organization):
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        summary = service.create_snapshot(VIDEO, [3])["summary"]
        assert summary["organization"]["favorite_count"] == 0
        assert summary["organization"]["tag_counts"] == {}

    def test_favorite_is_boolean_type(self, result):
        for snapshot in result["snapshots"]:
            assert type(snapshot["favorite"]) is bool

    def test_favorite_count_never_exceeds_versions(self, marked, readiness,
                                                   organization):
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        summary = service.create_snapshot(VIDEO)["summary"]
        assert summary["organization"]["favorite_count"] <= \
            summary["versions_analyzed"]


class TestEmptyAndSingle:
    @pytest.fixture
    def empty(self, service):
        return service.create_snapshot("none.mp4")

    def test_empty_exact_result(self, empty):
        assert empty == {
            "video_filename": "none.mp4",
            "versions_analyzed": [],
            "snapshots": [],
            "summary": {
                "versions_analyzed": 0,
                "ready_count": 0,
                "needs_attention_count": 0,
                "required": {
                    "total": 0,
                    "present": 0,
                    "weak": 0,
                    "missing": 0,
                    "coverage_percentage": None,
                },
                "supporting": {
                    "total": 0,
                    "present": 0,
                    "weak": 0,
                    "missing": 0,
                },
                "dimension_summary": [],
                "organization": {
                    "favorite_count": 0,
                    "tag_counts": {},
                },
            },
        }

    def test_empty_selection_rejected(self, service):
        with pytest.raises(ValueError,
                           match="versions must be a non-empty list of "
                                 "positive integers\\."):
            service.create_snapshot("none.mp4", [])

    def test_empty_version_lookup_404(self, service):
        with pytest.raises(ValueError, match="Version 1 not found"):
            service.create_snapshot("none.mp4", [1])

    def test_single_version_aggregates(self, service):
        summary = service.create_snapshot(VIDEO, [6])["summary"]
        assert summary["versions_analyzed"] == 1
        assert summary["ready_count"] == 0
        assert summary["needs_attention_count"] == 1
        assert summary["required"] == {
            "total": 7, "present": 0, "weak": 0, "missing": 7,
            "coverage_percentage": 0}
        assert summary["supporting"] == {
            "total": 2, "present": 0, "weak": 0, "missing": 2}

    def test_single_version_ready_aggregates(self, service):
        summary = service.create_snapshot(VIDEO, [1])["summary"]
        assert summary["ready_count"] == 1
        assert summary["needs_attention_count"] == 0
        assert summary["required"] == {
            "total": 7, "present": 7, "weak": 0, "missing": 0,
            "coverage_percentage": 100}
        assert summary["supporting"] == {
            "total": 2, "present": 2, "weak": 0, "missing": 0}

    def test_single_version_dimension_rows_sum_to_one(self, service):
        summary = service.create_snapshot(VIDEO, [6])["summary"]
        assert len(summary["dimension_summary"]) == 9
        for row in summary["dimension_summary"]:
            assert row["present"] + row["weak"] + row["missing"] == 1

    def test_single_version_matches_full_snapshot_entry(self, service):
        full = {s["version"]: s
                for s in service.create_snapshot(VIDEO)["snapshots"]}
        single = service.create_snapshot(VIDEO, [4])["snapshots"][0]
        assert json.dumps(single, sort_keys=True) == \
            json.dumps(full[4], sort_keys=True)


class TestDeterminism:
    def test_repeated_calls_identical(self, service):
        first = json.dumps(service.create_snapshot(VIDEO), sort_keys=True)
        second = json.dumps(service.create_snapshot(VIDEO), sort_keys=True)
        assert first == second

    def test_two_service_instances_identical(self, marked):
        first = json.dumps(
            _build_service(marked).create_snapshot(VIDEO), sort_keys=True)
        second = json.dumps(
            _build_service(marked).create_snapshot(VIDEO), sort_keys=True)
        assert first == second

    def test_no_generated_timestamps_beyond_stored_created_at(
            self, history, result):
        import re
        text = json.dumps(result)
        for record in history.list_versions(VIDEO):
            text = text.replace(record["created_at"], "")
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", text)

    def test_no_uuids_or_random_ids(self, result):
        import re
        text = json.dumps(result)
        assert not re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            text)

    def test_result_is_json_serializable(self, result):
        assert json.loads(json.dumps(result)) == result

    def test_subset_selection_deterministic(self, service):
        first = json.dumps(service.create_snapshot(VIDEO, [1, 4, 6]),
                           sort_keys=True)
        second = json.dumps(service.create_snapshot(VIDEO, [1, 4, 6]),
                            sort_keys=True)
        assert first == second


class TestReadOnlyIntegrity:
    def _snapshot(self, history):
        return json.dumps(
            [record for record in
             sorted(history.list_versions(VIDEO),
                    key=lambda record: record["version"])],
            sort_keys=True)

    def test_history_records_unchanged(self, history, service):
        before = self._snapshot(history)
        service.create_snapshot(VIDEO)
        assert self._snapshot(history) == before

    def test_version_count_unchanged(self, history, service):
        service.create_snapshot(VIDEO)
        assert len(history.list_versions(VIDEO)) == 8

    def test_prompt_text_unchanged(self, history, service):
        service.create_snapshot(VIDEO, [1, 5, 8])
        assert history.get_version(VIDEO, 1)["prompt"] == FULL
        assert history.get_version(VIDEO, 5)["prompt"] == CITY_ENV100
        assert history.get_version(VIDEO, 8)["prompt"] == SUBJ70

    def test_source_metadata_unchanged(self, history, service):
        service.create_snapshot(VIDEO)
        record = history.get_version(VIDEO, 2)
        assert record["source"] == "custom"
        assert record["operation"] == ""

    def test_favorites_unchanged(self, marked, readiness, organization):
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        before = json.dumps(organization.list_favorites(VIDEO),
                            sort_keys=True)
        service.create_snapshot(VIDEO)
        assert json.dumps(organization.list_favorites(VIDEO),
                          sort_keys=True) == before

    def test_tags_unchanged(self, marked, readiness, organization):
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        before = {
            v: json.dumps(organization.get_organization(VIDEO, v),
                          sort_keys=True)
            for v in range(1, 9)
        }
        service.create_snapshot(VIDEO)
        for v, blob in before.items():
            assert json.dumps(
                organization.get_organization(VIDEO, v),
                sort_keys=True) == blob

    def test_organization_metadata_not_created_for_unmarked(
            self, history, organization, service):
        before = json.dumps(
            organization.get_organization(VIDEO, 2), sort_keys=True)
        service.create_snapshot(VIDEO)
        assert json.dumps(
            organization.get_organization(VIDEO, 2),
            sort_keys=True) == before

    def test_no_versions_created_or_deleted(self, history, service):
        before = [record["version"] for record in
                  history.list_versions(VIDEO)]
        service.create_snapshot(VIDEO, [4, 1])
        after = [record["version"] for record in
                 history.list_versions(VIDEO)]
        assert after == before == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_failed_selection_never_mutates(self, history, service):
        before = self._snapshot(history)
        with pytest.raises(ValueError):
            service.create_snapshot(VIDEO, [1, 99])
        assert self._snapshot(history) == before


class TestNoRankingLanguage:
    RANKING_WORDS = (
        "best", "worst", "winner", "winning", "rank", "ranking", "ranked",
        "superior", "inferior", "better", "worse", "perfect", "guaranteed",
        "recommended", "recommendation", "ideal", "outperforms",
        "improvement", "improved", "improves", "gain",
    )

    def _text(self, result):
        return json.dumps(result).lower()

    def test_no_ranking_words_in_full_snapshot(self, marked, readiness,
                                                organization):
        import re
        service = PromptReadinessSnapshotService(
            marked, readiness, organization)
        text = self._text(service.create_snapshot(VIDEO))
        for word in self.RANKING_WORDS:
            assert not re.search(rf"\b{word}\b", text), word

    def test_no_ranking_words_in_subset(self, service):
        import re
        text = self._text(service.create_snapshot(VIDEO, [1, 6]))
        for word in self.RANKING_WORDS:
            assert not re.search(rf"\b{word}\b", text), word

    def test_no_comparison_prose(self, result):
        text = self._text(result)
        for phrase in ("more ready", "less ready", "more consistent",
                       "readiness improved", "readiness declined",
                       "should use", "prefer version"):
            assert phrase not in text

    def test_no_winner_or_selection_keys(self, result):
        import re
        text = json.dumps(result)
        assert not re.search(
            r"\"(winner|best_version|recommended_version|rankings)\"", text)

    def test_counts_are_plain_integers(self, result):
        summary = result["summary"]
        assert type(summary["ready_count"]) is int
        assert type(summary["needs_attention_count"]) is int
        assert type(summary["required"]["coverage_percentage"]) in (int, type(None))


class TestNoLeaks:
    def test_no_absolute_paths(self, result):
        import re
        text = json.dumps(result)
        assert not re.search(r"[A-Za-z]:\\", text)
        assert "/home/" not in text
        assert "/Users/" not in text

    def test_no_internal_names(self, result):
        text = json.dumps(result)
        for name in ("PromptReadinessSnapshotService",
                     "PromptReadinessHistoryService",
                     "PromptReadinessChangeService",
                     "PromptReadinessTimelineService",
                     "PromptReadinessService", "PromptQualityService",
                     "PromptOrganizationService", "PromptHistoryService",
                     "prompt_readiness_snapshot_service",
                     "readiness_snapshot_service", "history_service",
                     "readiness_service", "organization_service"):
            assert name not in text, name

    def test_no_prompt_text_echoed(self, service):
        text = json.dumps(service.create_snapshot(VIDEO))
        for fragment in ("film grain style portrait", "quiet city street",
                         "nothing specific at all", "blurry, low quality"):
            assert fragment not in text

    def test_no_traceback_or_debug_artifacts(self, result):
        text = json.dumps(result)
        assert "Traceback" not in text
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
        from app.services import prompt_readiness_snapshot_service as module
        return inspect.getsource(module)

    def test_imports_only_expected_modules(self, source):
        for forbidden in ("import socket", "import requests",
                          "import urllib", "import http", "import sqlite3",
                          "import pathlib", "from pathlib",
                          "import os", "import random", "import uuid",
                          "import time", "import datetime", "import openai"):
            assert forbidden not in source, forbidden

    def test_does_not_import_other_day_services(self, source):
        for forbidden in ("prompt_readiness_history_service",
                          "prompt_readiness_change_service",
                          "prompt_readiness_timeline_service",
                          "prompt_search_service", "prompt_export_service",
                          "prompt_comparison_service"):
            assert forbidden not in source, forbidden

    def test_no_filesystem_or_network_calls(self, source):
        for forbidden in ("open(", "os.environ", "os.path",
                          "requests.get", "requests.post",
                          "urlopen", "sqlite3.connect"):
            assert forbidden not in source, forbidden

    def test_uses_history_read_methods(self, source):
        assert "list_versions" in source
        assert "get_version" in source

    def test_uses_day24_and_day17_exactly(self, source):
        assert "validate_prompt" in source
        assert "get_organization" in source

    def test_never_mutates_history_or_organization(self, source):
        for forbidden in ("create_version(", "delete_version(",
                          "save_advanced_prompt(", "save_refinement(",
                          "save_template(", "favorite_version(",
                          "unfavorite_version(", "add_tags(",
                          "remove_tags("):
            assert forbidden not in source, forbidden

    def test_defined_methods_exact(self):
        import inspect
        from app.services.prompt_readiness_snapshot_service import (
            PromptReadinessSnapshotService,
        )
        names = [
            name for name, _
            in inspect.getmembers(PromptReadinessSnapshotService,
                                  inspect.isfunction)
            if name != "__init__"
        ]
        assert sorted(names) == ["_select", "create_snapshot"]

    def test_no_store_attributes_in_source(self, source):
        for forbidden in ("self._storage", "self._versions",
                          "self._snapshots", "self._cache", "self._store"):
            assert forbidden not in source, forbidden
