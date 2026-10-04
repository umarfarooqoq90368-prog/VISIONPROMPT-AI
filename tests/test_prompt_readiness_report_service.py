"""Tests for the prompt readiness report service (Day 29)."""
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
from app.services.prompt_readiness_history_service import (
    PromptReadinessHistoryService,
)
from app.services.prompt_readiness_change_service import (
    PromptReadinessChangeService,
    TRANSITION_KEYS,
)
from app.services.prompt_readiness_timeline_service import (
    PromptReadinessTimelineService,
)
from app.services.prompt_readiness_snapshot_service import (
    PromptReadinessSnapshotService,
)
from app.services.prompt_readiness_report_service import (
    PromptReadinessReportService,
)

# --- Fixture prompts (Day 21/24/26/27/28 verified) --------------------------
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
    "video_filename", "versions_analyzed", "report", "timeline", "summary",
}

REPORT_KEYS = {
    "type", "version_count", "first_version", "last_version",
    "selection_order", "snapshots",
}

TIMELINE_KEYS = {
    "steps", "changed_dimensions", "unchanged_dimensions",
    "required_changes", "supporting_changes", "transition_summary",
    "required_coverage_delta",
}

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

FORBIDDEN_WORDS = [
    "best", "worst", "winner", "loser", "superior", "inferior",
    "better", "worse", "improved", "degraded", "recommended",
    "preferred", "optimal",
]

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

SELECTIONS = [
    None, [1], [6], [1, 3, 5], [5, 3, 1], [4, 2], [8, 7, 6, 5, 4, 3, 2, 1],
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
def readiness():
    return PromptReadinessService(PromptQualityService())


@pytest.fixture
def organization(history):
    return PromptOrganizationService(history)


@pytest.fixture
def change(history, readiness):
    return PromptReadinessChangeService(history, readiness)


@pytest.fixture
def timeline_service(history, change):
    return PromptReadinessTimelineService(history, change)


@pytest.fixture
def snapshot_service(history, readiness, organization):
    return PromptReadinessSnapshotService(history, readiness, organization)


@pytest.fixture
def service(timeline_service, snapshot_service):
    return PromptReadinessReportService(timeline_service, snapshot_service)


@pytest.fixture
def result(service):
    return service.generate_report(VIDEO)


@pytest.fixture
def marked(history, organization):
    """Standard history with probe-verified favorites and tags."""
    organization.favorite_version(VIDEO, 1)
    organization.favorite_version(VIDEO, 7)
    organization.add_tags(VIDEO, 1, [" Cinematic ", "ai"])
    organization.add_tags(VIDEO, 4, ["final"])
    organization.add_tags(VIDEO, 7, ["cinematic", "draft", "cinematic"])
    return history


def _entries(report):
    return report["report"]["snapshots"]


def _pairs(report):
    return [(step["version_a"]["version"], step["version_b"]["version"])
            for step in report["timeline"]["steps"]]


class TestWiring:
    def test_constructor_state_only_two_dependencies(
            self, timeline_service, snapshot_service):
        svc = PromptReadinessReportService(timeline_service, snapshot_service)
        assert set(vars(svc).keys()) == {
            "readiness_timeline_service", "readiness_snapshot_service"}

    def test_holds_given_services(self, timeline_service, snapshot_service):
        svc = PromptReadinessReportService(timeline_service, snapshot_service)
        assert svc.readiness_timeline_service is timeline_service
        assert svc.readiness_snapshot_service is snapshot_service

    def test_snapshot_service_reuses_day16_day24_day17(
            self, service, history, readiness, organization):
        snap = service.readiness_snapshot_service
        assert isinstance(snap, PromptReadinessSnapshotService)
        assert snap.history_service is history
        assert snap.readiness_service is readiness
        assert snap.organization_service is organization

    def test_timeline_service_reuses_day16_day26(
            self, service, history, change):
        tl = service.readiness_timeline_service
        assert isinstance(tl, PromptReadinessTimelineService)
        assert tl.history_service is history
        assert tl.readiness_change_service is change

    def test_change_service_reuses_day16_day24(
            self, service, history, readiness):
        change_service = service.readiness_timeline_service.\
            readiness_change_service
        assert isinstance(change_service, PromptReadinessChangeService)
        assert change_service.history_service is history
        assert change_service.readiness_service is readiness

    def test_single_shared_history_store(self, service, history):
        assert service.readiness_timeline_service.history_service is \
            service.readiness_snapshot_service.history_service is history

    def test_no_day25_day26_day27_day28_direct_dependency(self, service):
        assert not isinstance(service, PromptReadinessHistoryService)
        assert not isinstance(service, PromptReadinessChangeService)
        assert not isinstance(service, PromptReadinessTimelineService)
        assert not isinstance(service, PromptReadinessSnapshotService)


class TestResponseStructure:
    def test_top_level_keys_exact(self, result):
        assert set(result.keys()) == TOP_KEYS

    def test_video_filename_echo(self, result):
        assert result["video_filename"] == VIDEO

    def test_report_metadata_keys_and_order(self, result):
        assert list(result["report"].keys()) == [
            "type", "version_count", "first_version", "last_version",
            "selection_order", "snapshots"]

    def test_report_metadata_values(self, result):
        meta = result["report"]
        assert meta["type"] == "prompt_readiness_report"
        assert meta["version_count"] == 8
        assert meta["first_version"] == 1
        assert meta["last_version"] == 8
        assert meta["selection_order"] == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_versions_analyzed_matches_selection_order(self, result):
        assert result["versions_analyzed"] == [1, 2, 3, 4, 5, 6, 7, 8]
        assert result["versions_analyzed"] == result["report"][
            "selection_order"]

    def test_timeline_keys_exact(self, result):
        assert set(result["timeline"].keys()) == TIMELINE_KEYS

    def test_summary_keys_exact(self, result):
        assert set(result["summary"].keys()) == SUMMARY_KEYS

    def test_snapshot_entry_keys_exact(self, result):
        for entry in _entries(result):
            assert set(entry.keys()) == SNAPSHOT_KEYS, list(entry.keys())

    def test_readiness_keys_and_day21_orders(self, result):
        for entry in _entries(result):
            block = entry["readiness"]
            assert set(block.keys()) == READINESS_KEYS
            assert list(block["required"].keys()) == REQUIRED_KEYS
            assert list(block["supporting"].keys()) == SUPPORTING_KEYS
            for key in ("missing_dimensions", "weak_dimensions"):
                dims = block[key]
                assert dims == [d for d in DIMENSIONS if d in set(dims)]

    def test_dimension_summary_day21_order(self, result):
        rows = result["summary"]["dimension_summary"]
        assert [row["dimension"] for row in rows] == list(DIMENSIONS)
        assert len(rows) == 9

    def test_transition_summary_keys(self, result):
        assert set(result["timeline"]["transition_summary"].keys()) == \
            set(TRANSITION_KEYS)

    def test_no_prompt_text_in_report(self, result):
        text = json.dumps(result)
        for prompt in (FULL, WEAK_CAM, W_CAMLESS, CITY, CITY_ENV100,
                       MINIMAL, REQ_ONLY, SUBJ70):
            assert prompt not in text


class TestFullReport:
    def test_default_selection_ascending(self, result):
        assert result["versions_analyzed"] == [1, 2, 3, 4, 5, 6, 7, 8]
        assert [e["version"] for e in _entries(result)] == \
            [1, 2, 3, 4, 5, 6, 7, 8]

    def test_per_version_readiness_equals_day24(
            self, service, history, readiness):
        report = service.generate_report(VIDEO)
        for entry in _entries(report):
            record = history.get_version(VIDEO, entry["version"])
            day24 = readiness.validate_prompt(record["prompt"])["readiness"]
            block = entry["readiness"]
            assert block["status"] == day24["status"]
            assert block["required_coverage_percentage"] == \
                day24["coverage"]["required_coverage_percentage"]
            assert block["missing_dimensions"] == day24["missing_dimensions"]
            assert block["weak_dimensions"] == day24["weak_dimensions"]
            checks = {item["dimension"]: item
                      for item in day24["checklist"]}
            for dim in REQUIRED_DIMENSIONS:
                assert block["required"][dim] == {
                    "status": checks[dim]["status"],
                    "score": checks[dim]["score"]}
            for dim in SUPPORTING_DIMENSIONS:
                assert block["supporting"][dim] == {
                    "status": checks[dim]["status"],
                    "score": checks[dim]["score"]}

    def test_per_version_metadata_equals_day16_records(
            self, service, history):
        report = service.generate_report(VIDEO)
        for entry in _entries(report):
            record = history.get_version(VIDEO, entry["version"])
            assert entry["source"] == record["source"]
            assert entry["operation"] == record["operation"]
            assert entry["created_at"] == record["created_at"]

    def test_per_version_org_equals_day17(
            self, service, organization):
        service.generate_report(VIDEO)  # no marks yet
        organization.favorite_version(VIDEO, 1)
        organization.add_tags(VIDEO, 1, ["ai"])
        report = service.generate_report(VIDEO)
        for entry in _entries(report):
            org = organization.get_organization(VIDEO, entry["version"])
            assert entry["favorite"] == org["favorite"]
            assert entry["tags"] == org["tags"]
        assert _entries(report)[0]["favorite"] is True
        assert _entries(report)[0]["tags"] == ["ai"]

    def test_readiness_statuses_and_coverages(self, result):
        entries = {e["version"]: e["readiness"] for e in _entries(result)}
        assert (entries[1]["status"],
                entries[1]["required_coverage_percentage"]) == ("ready", 100)
        assert (entries[2]["status"],
                entries[2]["required_coverage_percentage"]) == \
            ("needs_attention", 86)
        assert entries[2]["weak_dimensions"] == ["camera"]
        assert entries[3]["missing_dimensions"] == ["camera"]
        assert (entries[4]["status"],
                entries[4]["required_coverage_percentage"]) == \
            ("needs_attention", 14)
        assert entries[4]["weak_dimensions"] == ["subject"]
        assert entries[5]["required_coverage_percentage"] == 14
        assert entries[6]["required_coverage_percentage"] == 0
        assert entries[6]["missing_dimensions"] == list(DIMENSIONS)
        assert (entries[7]["status"],
                entries[7]["missing_dimensions"]) == \
            ("ready", ["color", "audio"])
        assert entries[8]["weak_dimensions"] == ["action"]

    def test_raw_scores_spot_checks(self, result):
        entries = {e["version"]: e["readiness"] for e in _entries(result)}
        assert entries[1]["required"]["subject"] == {
            "status": "present", "score": 100}
        assert entries[2]["required"]["camera"] == {
            "status": "weak", "score": 40}
        assert entries[4]["required"]["subject"] == {
            "status": "weak", "score": 40}
        assert entries[4]["required"]["environment"] == {
            "status": "present", "score": 70}
        assert entries[7]["supporting"]["color"] == {
            "status": "missing", "score": 0}

    def test_steps_equal_day27_timeline(self, service, timeline_service):
        report = service.generate_report(VIDEO)
        day27 = timeline_service.build_timeline(VIDEO)
        assert report["timeline"]["steps"] == day27["timeline"]
        assert len(report["timeline"]["steps"]) == 7

    def test_steps_equal_day26_compares(self, service, change, result):
        for step in result["timeline"]["steps"]:
            direct = change.compare_versions(
                VIDEO, step["version_a"]["version"],
                step["version_b"]["version"])
            assert step == direct

    def test_timeline_pairs_consecutive_ascending(self, result):
        assert _pairs(result) == [
            (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8)]

    def test_timeline_totals_probe_values(self, result):
        tl = result["timeline"]
        assert tl["changed_dimensions"] == 21
        assert tl["unchanged_dimensions"] == 42
        assert tl["required_changes"] == 17
        assert tl["supporting_changes"] == 4
        assert tl["transition_summary"] == {
            "missing_to_weak": 0, "missing_to_present": 9,
            "weak_to_missing": 2, "weak_to_present": 0,
            "present_to_missing": 7, "present_to_weak": 3}
        assert tl["required_coverage_delta"] == -14

    def test_summary_probe_values(self, result):
        summary = result["summary"]
        assert summary["versions_analyzed"] == 8
        assert summary["ready_count"] == 2
        assert summary["needs_attention_count"] == 6
        assert summary["required"] == {
            "total": 56, "present": 34, "weak": 4, "missing": 18,
            "coverage_percentage": 61}
        assert summary["supporting"] == {
            "total": 16, "present": 8, "weak": 0, "missing": 8}

    def test_dimension_summary_probe_values(self, result):
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

    def test_organization_summary_probe_values(self, marked, service):
        summary = service.generate_report(VIDEO)["summary"]
        assert summary["organization"] == {
            "favorite_count": 2,
            "tag_counts": {"ai": 1, "cinematic": 2, "draft": 1,
                           "final": 1}}

    def test_step_deltas_telescope(self, result):
        deltas = [step["required_coverage"]["delta"]
                  for step in result["timeline"]["steps"]]
        assert deltas == [-14, 0, -72, 0, -14, 100, -14]
        assert sum(deltas) == result["timeline"]["required_coverage_delta"]


class TestSelectedReport:
    def test_subset_1_3_5(self, service):
        report = service.generate_report(VIDEO, [1, 3, 5])
        assert report["versions_analyzed"] == [1, 3, 5]
        assert report["report"]["selection_order"] == [1, 3, 5]
        assert report["report"]["version_count"] == 3
        assert report["report"]["first_version"] == 1
        assert report["report"]["last_version"] == 5
        assert [e["version"] for e in _entries(report)] == [1, 3, 5]
        assert _pairs(report) == [(1, 3), (3, 5)]
        assert report["summary"]["required"] == {
            "total": 21, "present": 14, "weak": 1, "missing": 6,
            "coverage_percentage": 67}
        assert report["timeline"]["required_coverage_delta"] == -86

    def test_reverse_5_3_1(self, service):
        report = service.generate_report(VIDEO, [5, 3, 1])
        assert report["versions_analyzed"] == [5, 3, 1]
        assert report["report"]["selection_order"] == [5, 3, 1]
        assert [e["version"] for e in _entries(report)] == [5, 3, 1]
        assert _pairs(report) == [(5, 3), (3, 1)], "never resorted"
        assert report["report"]["first_version"] == 5
        assert report["report"]["last_version"] == 1

    def test_reverse_3_1_timeline_delta(self, service):
        report = service.generate_report(VIDEO, [3, 1])
        tl = report["timeline"]
        assert _pairs(report) == [(3, 1)]
        assert tl["steps"][0]["required_coverage"]["delta"] == 14
        assert tl["required_coverage_delta"] == 14
        assert report["summary"]["required"] == {
            "total": 14, "present": 13, "weak": 0, "missing": 1,
            "coverage_percentage": 93}

    def test_order_preserved_not_sorted(self, service):
        report = service.generate_report(VIDEO, [4, 2, 5])
        assert report["versions_analyzed"] == [4, 2, 5]
        assert report["report"]["selection_order"] == [4, 2, 5]
        assert [e["version"] for e in _entries(report)] == [4, 2, 5]
        assert _pairs(report) == [(4, 2), (2, 5)]

    def test_explicit_full_list_matches_default(self, service):
        explicit = service.generate_report(
            VIDEO, [1, 2, 3, 4, 5, 6, 7, 8])
        default = service.generate_report(VIDEO)
        assert explicit == default

    def test_selection_changes_aggregate(self, service):
        full = service.generate_report(VIDEO)["summary"]
        subset = service.generate_report(VIDEO, [1, 3])["summary"]
        assert full["required"]["present"] == 34
        assert subset["required"]["present"] == 13
        assert subset["versions_analyzed"] == 2

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_selection_list_matches_everywhere(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        expected = ([1, 2, 3, 4, 5, 6, 7, 8]
                    if versions is None else versions)
        assert report["versions_analyzed"] == expected
        assert report["report"]["selection_order"] == expected
        assert [e["version"] for e in _entries(report)] == expected
        assert report["report"]["version_count"] == len(expected)


class TestTimelineIntegration:
    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_steps_byte_equal_day27(
            self, service, timeline_service, versions):
        report = service.generate_report(VIDEO, versions)
        day27 = timeline_service.build_timeline(VIDEO, versions)
        assert report["timeline"]["steps"] == day27["timeline"]
        assert report["versions_analyzed"] == day27["versions_analyzed"]

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_timeline_totals_equal_day27_summary(
            self, service, timeline_service, versions):
        report = service.generate_report(VIDEO, versions)
        day27 = timeline_service.build_timeline(VIDEO, versions)
        tl = report["timeline"]
        assert tl["changed_dimensions"] == \
            day27["summary"]["dimensions_changed_total"]
        assert tl["unchanged_dimensions"] == \
            day27["summary"]["dimensions_unchanged_total"]
        assert tl["required_changes"] == \
            day27["summary"]["required_changes_total"]
        assert tl["supporting_changes"] == \
            day27["summary"]["supporting_changes_total"]
        assert tl["transition_summary"] == \
            day27["summary"]["transition_summary"]

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_delta_mapping_day27(
            self, service, timeline_service, versions):
        report = service.generate_report(VIDEO, versions)
        day27 = timeline_service.build_timeline(VIDEO, versions)
        if report["versions_analyzed"]:
            assert report["timeline"]["required_coverage_delta"] == \
                day27["summary"]["required_coverage_delta"]
        else:
            assert report["timeline"]["required_coverage_delta"] is None

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_invariants(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        n = len(report["versions_analyzed"])
        steps = len(report["timeline"]["steps"])
        tl = report["timeline"]
        assert tl["changed_dimensions"] + tl["unchanged_dimensions"] == \
            steps * 9
        assert tl["required_changes"] + tl["supporting_changes"] == \
            tl["changed_dimensions"]
        assert sum(tl["transition_summary"].values()) == \
            tl["changed_dimensions"]

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_step_deltas_sum_to_report_delta(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        deltas = [step["required_coverage"]["delta"]
                  for step in report["timeline"]["steps"]]
        assert sum(deltas) == report["timeline"]["required_coverage_delta"]

    @pytest.mark.parametrize("versions", [
        [1, 3, 5], [5, 3, 1], [4, 2, 5], [2, 1], [8, 1],
    ])
    def test_telescoping_equals_last_minus_first(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        coverages = [e["readiness"]["required_coverage_percentage"]
                     for e in _entries(report)]
        assert report["timeline"]["required_coverage_delta"] == \
            coverages[-1] - coverages[0]

    @pytest.mark.parametrize("versions", [
        [1, 3, 5], [5, 3, 1], [4, 2, 5], [2, 1],
    ])
    def test_step_pairs_follow_selection_order(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        expected = list(zip(versions, versions[1:]))
        assert _pairs(report) == expected


class TestSummaryIntegration:
    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_summary_byte_equal_day28(
            self, service, snapshot_service, versions):
        report = service.generate_report(VIDEO, versions)
        day28 = snapshot_service.create_snapshot(VIDEO, versions)
        assert report["summary"] == day28["summary"]
        assert report["report"]["snapshots"] == day28["snapshots"]
        assert report["versions_analyzed"] == day28["versions_analyzed"]

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_totals_are_n_times_dimensions(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        n = len(report["versions_analyzed"])
        assert report["summary"]["required"]["total"] == n * 7
        assert report["summary"]["supporting"]["total"] == n * 2

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_each_dimension_sums_to_n(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        n = len(report["versions_analyzed"])
        for row in report["summary"]["dimension_summary"]:
            assert row["present"] + row["weak"] + row["missing"] == n, row

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_required_and_supporting_sums(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        n = len(report["versions_analyzed"])
        required = report["summary"]["required"]
        supporting = report["summary"]["supporting"]
        assert required["present"] + required["weak"] + required[
            "missing"] == n * 7
        assert supporting["present"] + supporting["weak"] + supporting[
            "missing"] == n * 2

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_ready_plus_attention_equals_n(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        summary = report["summary"]
        n = len(report["versions_analyzed"])
        assert summary["ready_count"] + summary["needs_attention_count"] == n
        assert summary["versions_analyzed"] == n

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_coverage_percentage_rounding(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        required = report["summary"]["required"]
        if required["total"]:
            assert required["coverage_percentage"] == round(
                required["present"] / required["total"] * 100)
        else:
            assert required["coverage_percentage"] is None

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_dimension_summary_present_keys(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        for row in report["summary"]["dimension_summary"]:
            assert set(row.keys()) == {"dimension", "present", "weak",
                                       "missing"}


class TestOrganization:
    def test_default_counts_zero(self, result):
        assert result["summary"]["organization"] == {
            "favorite_count": 0, "tag_counts": {}}

    def test_favorite_count(self, marked, service):
        org = service.generate_report(VIDEO)["summary"]["organization"]
        assert org["favorite_count"] == 2

    def test_tag_counts_exact_and_once_per_version(
            self, marked, service):
        org = service.generate_report(VIDEO)["summary"]["organization"]
        assert org["tag_counts"] == {
            "ai": 1, "cinematic": 2, "draft": 1, "final": 1}

    def test_tags_alphabetical_order(self, marked, service):
        tags = service.generate_report(VIDEO)["summary"]["organization"][
            "tag_counts"]
        assert list(tags.keys()) == sorted(tags.keys())

    def test_normalized_tags_counted(self, marked, service):
        tags = service.generate_report(VIDEO)["summary"]["organization"][
            "tag_counts"]
        assert " Cinematic " not in tags
        assert "cinematic" in tags

    def test_scoped_selection_counts(self, marked, service):
        org = service.generate_report(VIDEO, [4])["summary"]["organization"]
        assert org == {"favorite_count": 0,
                       "tag_counts": {"final": 1}}
        org2 = service.generate_report(VIDEO, [1, 7])[
            "summary"]["organization"]
        assert org2["favorite_count"] == 2
        assert org2["tag_counts"] == {"ai": 1, "cinematic": 2, "draft": 1}


class TestEmptyHistory:
    @pytest.fixture
    def empty_service(self):
        history = PromptHistoryService()
        readiness = PromptReadinessService(PromptQualityService())
        organization = PromptOrganizationService(history)
        change = PromptReadinessChangeService(history, readiness)
        timeline = PromptReadinessTimelineService(history, change)
        snapshot = PromptReadinessSnapshotService(
            history, readiness, organization)
        return PromptReadinessReportService(timeline, snapshot)

    def test_empty_report_exact_schema(self, empty_service):
        report = empty_service.generate_report("none.mp4")
        assert set(report.keys()) == TOP_KEYS
        assert report["video_filename"] == "none.mp4"
        assert report["versions_analyzed"] == []
        assert report["report"] == {
            "type": "prompt_readiness_report",
            "version_count": 0,
            "first_version": None,
            "last_version": None,
            "selection_order": [],
            "snapshots": [],
        }
        assert report["timeline"] == {
            "steps": [],
            "changed_dimensions": 0,
            "unchanged_dimensions": 0,
            "required_changes": 0,
            "supporting_changes": 0,
            "transition_summary": {
                "missing_to_weak": 0, "missing_to_present": 0,
                "weak_to_missing": 0, "weak_to_present": 0,
                "present_to_missing": 0, "present_to_weak": 0},
            "required_coverage_delta": None,
        }
        assert report["summary"] == {
            "versions_analyzed": 0,
            "ready_count": 0,
            "needs_attention_count": 0,
            "required": {"total": 0, "present": 0, "weak": 0,
                         "missing": 0, "coverage_percentage": None},
            "supporting": {"total": 0, "present": 0, "weak": 0,
                           "missing": 0},
            "dimension_summary": [],
            "organization": {"favorite_count": 0, "tag_counts": {}},
        }

    def test_empty_with_version_query_raises(self, empty_service):
        with pytest.raises(ValueError) as exc:
            empty_service.generate_report("none.mp4", [1])
        assert str(exc.value) == \
            "Version 1 not found for video 'none.mp4'."


class TestSingleVersion:
    @pytest.mark.parametrize("version", [1, 6, 8])
    def test_single_version_semantics(self, service, version):
        report = service.generate_report(VIDEO, [version])
        assert report["report"]["version_count"] == 1
        assert report["report"]["first_version"] == version
        assert report["report"]["last_version"] == version
        assert report["report"]["selection_order"] == [version]
        assert report["versions_analyzed"] == [version]
        assert len(_entries(report)) == 1
        tl = report["timeline"]
        assert tl["steps"] == []
        assert tl["changed_dimensions"] == 0
        assert tl["unchanged_dimensions"] == 0
        assert tl["required_changes"] == 0
        assert tl["supporting_changes"] == 0
        assert set(tl["transition_summary"].values()) == {0}
        assert tl["required_coverage_delta"] == 0

    @pytest.mark.parametrize("version", [1, 6, 8])
    def test_single_summary_matches_version(self, service, snapshot_service,
                                            version):
        report = service.generate_report(VIDEO, [version])
        day28 = snapshot_service.create_snapshot(VIDEO, [version])
        assert report["summary"] == day28["summary"]
        assert report["summary"]["required"]["total"] == 7
        assert report["summary"]["supporting"]["total"] == 2
        for row in report["summary"]["dimension_summary"]:
            assert row["present"] + row["weak"] + row["missing"] == 1

    def test_single_snapshot_equals_full_entry(self, service):
        full = {e["version"]: e for e in _entries(
            service.generate_report(VIDEO))}
        single = _entries(service.generate_report(VIDEO, [4]))[0]
        assert single == full[4]


class TestValidation:
    @pytest.mark.parametrize("versions, message", [
        ([], "versions must be a non-empty list of positive integers."),
        (["1"], "versions must contain positive integers."),
        ([0], "versions must contain positive integers."),
        ([-1], "versions must contain positive integers."),
        ([1.5], "versions must contain positive integers."),
        ([True], "versions must contain positive integers."),
        ([None], "versions must contain positive integers."),
        ([1, 1], "duplicate versions are not allowed."),
        ([2, 1, 2], "duplicate versions are not allowed."),
        ("1,3", "versions must be a non-empty list of positive integers."),
        ({"1"}, "versions must be a non-empty list of positive integers."),
    ])
    def test_invalid_selection_messages(self, service, versions, message):
        with pytest.raises(ValueError) as exc:
            service.generate_report(VIDEO, versions)
        assert str(exc.value) == message

    @pytest.mark.parametrize("version", [9, 99, 1000])
    def test_missing_version_day16_message(self, service, version):
        with pytest.raises(ValueError) as exc:
            service.generate_report(VIDEO, [version])
        assert str(exc.value) == \
            f"Version {version} not found for video '{VIDEO}'."

    def test_deleted_version_raises_day16_message(self, service, history):
        history.delete_version(VIDEO, 3)
        with pytest.raises(ValueError) as exc:
            service.generate_report(VIDEO, [3])
        assert str(exc.value) == \
            f"Version 3 not found for video '{VIDEO}'."

    def test_default_after_deletion_skips_gap(self, service, history):
        history.delete_version(VIDEO, 3)
        report = service.generate_report(VIDEO)
        assert report["versions_analyzed"] == [1, 2, 4, 5, 6, 7, 8]
        assert report["report"]["selection_order"] == [1, 2, 4, 5, 6, 7, 8]

    def test_missing_version_never_creates_or_deletes(
            self, service, history):
        listing_before = history.list_versions(VIDEO)
        with pytest.raises(ValueError):
            service.generate_report(VIDEO, [1, 99])
        assert history.list_versions(VIDEO) == listing_before


class TestDeterminism:
    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_repeated_reports_identical(self, service, versions):
        first = service.generate_report(VIDEO, versions)
        second = service.generate_report(VIDEO, versions)
        assert json.dumps(first) == json.dumps(second)

    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_no_generated_ids_or_timestamps(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        text = json.dumps(report)
        assert "uuid" not in text.lower()
        import re
        assert not re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            text)

    def test_created_at_values_are_stored_metadata(
            self, service, history):
        report = service.generate_report(VIDEO)
        for entry in _entries(report):
            record = history.get_version(VIDEO, entry["version"])
            assert entry["created_at"] == record["created_at"]

    def test_interleaved_selections_stable(self, service):
        a = service.generate_report(VIDEO, [5, 1])
        service.generate_report(VIDEO, [2, 8])
        service.generate_report(VIDEO, [3])
        b = service.generate_report(VIDEO, [5, 1])
        assert json.dumps(a) == json.dumps(b)


class TestReadOnlyIntegrity:
    def test_history_listing_unchanged(self, service, history):
        before = history.list_versions(VIDEO)
        service.generate_report(VIDEO)
        service.generate_report(VIDEO, [1, 5])
        service.generate_report(VIDEO, [8, 2])
        with pytest.raises(ValueError):
            service.generate_report(VIDEO, [99])
        assert history.list_versions(VIDEO) == before

    def test_records_unchanged(self, service, history):
        before = [history.get_version(VIDEO, v)
                  for v in range(1, 9)]
        service.generate_report(VIDEO, [1, 4])
        after = [history.get_version(VIDEO, v) for v in range(1, 9)]
        assert before == after

    def test_prompts_untouched(self, service, history):
        service.generate_report(VIDEO)
        assert history.get_version(VIDEO, 1)["prompt"] == FULL
        assert history.get_version(VIDEO, 4)["prompt"] == CITY

    def test_favorites_and_tags_unchanged(
            self, service, marked, organization):
        before = [organization.get_organization(VIDEO, v)
                  for v in range(1, 9)]
        service.generate_report(VIDEO)
        service.generate_report(VIDEO, [1, 7])
        after = [organization.get_organization(VIDEO, v)
                 for v in range(1, 9)]
        assert before == after

    def test_report_never_creates_versions(
            self, service, marked, organization, history):
        listing_before = history.list_versions(VIDEO)
        org_before = [organization.get_organization(VIDEO, v["version"])
                      for v in listing_before]
        service.generate_report(VIDEO)
        assert history.list_versions(VIDEO) == listing_before
        assert [organization.get_organization(VIDEO, v["version"])
                for v in listing_before] == org_before


class TestNoRankingLanguage:
    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_forbidden_words_absent(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        low = json.dumps(report).lower()
        for word in FORBIDDEN_WORDS:
            assert word not in low, word

    def test_no_prompt_or_negative_text(self, service, result):
        text = json.dumps(result)
        assert "film grain style portrait" not in text
        assert "blurry, low quality" not in text


class TestNoLeaks:
    @pytest.mark.parametrize("versions", SELECTIONS, ids=lambda v: str(v))
    def test_no_internal_objects_or_paths(self, service, versions):
        report = service.generate_report(VIDEO, versions)
        text = json.dumps(report)
        for bad in ("C:\\", "C:/", "/home", "/Users", "/var/",
                    "_storage", "storage/uploads", "BytesIO",
                    "Traceback", "os.environ"):
            assert bad not in text, bad
        for internal in (
                "PromptReadinessReportService",
                "PromptReadinessTimelineService",
                "PromptReadinessSnapshotService",
                "PromptReadinessChangeService",
                "PromptReadinessHistoryService",
                "PromptReadinessService", "PromptOrganizationService",
                "PromptHistoryService", "PromptQualityService",
                "readiness_report_service", "readiness_timeline_service",
                "readiness_snapshot_service", "history_service",
                "organization_service", "change_service"):
            assert internal not in text, internal

    def test_service_class_names_not_in_output(self, service):
        text = json.dumps(service.generate_report(VIDEO))
        assert "Service" not in text


class TestSourceContract:
    def test_sources_and_operations_match_records(
            self, service, history):
        report = service.generate_report(VIDEO)
        for entry in _entries(report):
            record = history.get_version(VIDEO, entry["version"])
            assert entry["source"] == record["source"]
            assert entry["operation"] == record["operation"]
            assert entry["source"] in {
                "advanced_prompt", "custom", "template", "refinement"}

    def test_standard_sources_cover_all_versions(self, service):
        report = service.generate_report(VIDEO)
        sources = [e["source"] for e in _entries(report)]
        assert sources == ["advanced_prompt", "custom", "template",
                           "refinement", "custom", "template",
                           "refinement", "custom"]
        operations = [e["operation"] for e in _entries(report)]
        assert operations == ["generate", "", "cinematic", "expand",
                              "tweak", "shorten", "expand", "draft"]
