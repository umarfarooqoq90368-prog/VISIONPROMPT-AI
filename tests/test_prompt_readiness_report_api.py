"""API tests for the prompt readiness report endpoint (Day 29)."""
import os
import re

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import DIMENSIONS

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets",
                               "test_video.mp4")

PROMPT = "Cinematic wide shot of the subject, golden hour lighting, slow dolly in."
NEGATIVE = "blurry, low quality, distorted anatomy, unwanted text, watermark"

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
MINIMAL = "nothing specific at all"

REPORT_TOP = {
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

DAY26_TOP = {
    "video_filename", "version_a", "version_b", "dimensions",
    "changed_dimensions", "dimensions_changed", "dimensions_unchanged",
    "required_changes", "supporting_changes", "transitions",
    "transition_summary", "required_coverage",
}

DAY27_TOP = {
    "video_filename", "versions_analyzed", "steps", "timeline", "summary",
}

DAY25_TOP = {
    "video_filename", "versions_analyzed", "results", "summary",
    "dimension_summary",
}

DAY28_TOP = {
    "video_filename", "versions_analyzed", "snapshots", "summary",
}

FORBIDDEN_WORDS = [
    "best", "worst", "winner", "loser", "superior", "inferior",
    "better", "worse", "improved", "degraded", "recommended",
    "preferred", "optimal",
]


def _create_real_mp4(path: str):
    import imageio_ffmpeg
    import subprocess
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=3", "-y", path],
            capture_output=True, timeout=10,
        )
        return os.path.exists(path) and os.path.getsize(path) > 0
    except Exception:
        return False


def _upload():
    if not os.path.exists(TEST_VIDEO_PATH):
        _create_real_mp4(TEST_VIDEO_PATH)
    with open(TEST_VIDEO_PATH, "rb") as f:
        upload = client.post("/api/videos/upload",
                             files={"file": ("test.mp4", f, "video/mp4")})
    assert upload.status_code == 200
    stored = upload.json()["video"]["stored_filename"]
    response = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds=1")
    assert response.status_code == 200
    return stored


def _save(stored, prompt=PROMPT, source="custom", operation="", metadata=None):
    body = {"prompt": prompt, "negative_prompt": NEGATIVE,
            "source": source, "operation": operation}
    if metadata is not None:
        body["metadata"] = metadata
    response = client.post(f"/api/videos/{stored}/prompt/history", json=body)
    assert response.status_code == 200
    return response.json()


def _report(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness/report",
        params=params,
    )


def _snapshot(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness/snapshot",
        params=params,
    )


def _timeline(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness/timeline",
        params=params,
    )


def _analyze(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness", params=params,
    )


def _change(stored, a, b):
    return client.get(
        f"/api/videos/{stored}/prompt/history/compare/{a}/{b}/readiness"
    )


def _readiness(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/readiness",
                       json={"prompt": prompt})


def _hreadiness(stored, version):
    return client.get(
        f"/api/videos/{stored}/prompt/history/{version}/readiness"
    )


def _org(stored, version):
    return client.get(
        f"/api/videos/{stored}/prompt/history/{version}/organization"
    )


def _quality(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/quality",
                       json={"prompt": prompt})


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)


def _versions(stored=None):
    """Upload and save the standard 5-version set."""
    stored = stored or _upload()
    for prompt in (FULL, WEAK_CAM, W_CAMLESS, CITY, MINIMAL):
        _save(stored, prompt)
    return stored


def _marked(stored=None):
    """Standard 5-version set with probe-verified favorites and tags."""
    stored = _versions(stored)
    assert client.post(
        f"/api/videos/{stored}/prompt/history/1/favorite").status_code == 200
    assert client.post(
        f"/api/videos/{stored}/prompt/history/1/tags",
        json={"tags": [" Cinematic ", "ai"]},
    ).json()["tags"] == ["ai", "cinematic"]
    assert client.post(
        f"/api/videos/{stored}/prompt/history/3/tags",
        json={"tags": ["final"]},
    ).json()["tags"] == ["final"]
    return stored


def _entries(data):
    return data["report"]["snapshots"]


def _pairs(data):
    return [(step["version_a"]["version"], step["version_b"]["version"])
            for step in data["timeline"]["steps"]]


class TestEndpointBasics:
    def test_valid_report_returns_200(self):
        stored = _versions()
        assert _report(stored).status_code == 200

    def test_top_level_keys_exact(self):
        stored = _versions()
        assert set(_report(stored).json().keys()) == REPORT_TOP
        assert len(_report(stored).json().keys()) == 5

    def test_video_filename_echo(self):
        stored = _versions()
        assert _report(stored).json()["video_filename"] == stored

    def test_versions_analyzed_all_five(self):
        stored = _versions()
        assert _report(stored).json()["versions_analyzed"] == [1, 2, 3, 4, 5]

    def test_report_metadata_keys_and_values(self):
        stored = _versions()
        meta = _report(stored).json()["report"]
        assert list(meta.keys()) == [
            "type", "version_count", "first_version", "last_version",
            "selection_order", "snapshots"]
        assert meta["type"] == "prompt_readiness_report"
        assert meta["version_count"] == 5
        assert meta["first_version"] == 1
        assert meta["last_version"] == 5
        assert meta["selection_order"] == [1, 2, 3, 4, 5]

    def test_timeline_keys_exact(self):
        stored = _versions()
        assert set(_report(stored).json()["timeline"].keys()) == TIMELINE_KEYS

    def test_summary_keys_exact(self):
        stored = _versions()
        assert set(_report(stored).json()["summary"].keys()) == SUMMARY_KEYS

    def test_snapshot_entry_keys_exact(self):
        stored = _versions()
        for entry in _entries(_report(stored).json()):
            assert set(entry.keys()) == SNAPSHOT_KEYS, list(entry.keys())

    def test_readiness_keys_and_orders(self):
        stored = _versions()
        for entry in _entries(_report(stored).json()):
            block = entry["readiness"]
            assert set(block.keys()) == READINESS_KEYS
            assert list(block["required"].keys()) == REQUIRED_KEYS
            assert list(block["supporting"].keys()) == SUPPORTING_KEYS

    def test_dimension_summary_day21_order(self):
        stored = _versions()
        rows = _report(stored).json()["summary"]["dimension_summary"]
        assert [row["dimension"] for row in rows] == list(DIMENSIONS)
        assert len(rows) == 9


class TestDay24Equivalence:
    def test_every_entry_matches_day24_endpoint(self):
        stored = _versions()
        for entry in _entries(_report(stored).json()):
            day24 = _hreadiness(stored, entry["version"]).json()["readiness"]
            block = entry["readiness"]
            assert block["status"] == day24["status"]
            assert block["required_coverage_percentage"] == \
                day24["coverage"]["required_coverage_percentage"]
            assert block["missing_dimensions"] == day24["missing_dimensions"]
            assert block["weak_dimensions"] == day24["weak_dimensions"]
            checks = {item["dimension"]: item
                      for item in day24["checklist"]}
            for dim in REQUIRED_KEYS:
                assert block["required"][dim] == {
                    "status": checks[dim]["status"],
                    "score": checks[dim]["score"]}
            for dim in SUPPORTING_KEYS:
                assert block["supporting"][dim] == {
                    "status": checks[dim]["status"],
                    "score": checks[dim]["score"]}

    def test_entry_metadata_matches_day16_records(self):
        stored = _versions()
        for entry in _entries(_report(stored).json()):
            record = client.get(
                f"/api/videos/{stored}/prompt/history/"
                f"{entry['version']}"
            ).json()
            assert entry["source"] == record["source"]
            assert entry["operation"] == record["operation"]
            assert entry["created_at"] == record["created_at"]

    def test_entry_org_matches_day17_endpoint(self):
        stored = _marked()
        for entry in _entries(_report(stored).json()):
            org = _org(stored, entry["version"]).json()
            assert entry["favorite"] == org["favorite"]
            assert entry["tags"] == org["tags"]


class TestDay28Equivalence:
    def test_summary_byte_equal_snapshot_endpoint(self):
        stored = _versions()
        assert _report(stored).json()["summary"] == \
            _snapshot(stored).json()["summary"]

    def test_snapshots_byte_equal_snapshot_endpoint(self):
        stored = _versions()
        assert _report(stored).json()["report"]["snapshots"] == \
            _snapshot(stored).json()["snapshots"]

    def test_selection_list_equal_snapshot_endpoint(self):
        stored = _versions()
        data = _report(stored, "3,1").json()
        snap = _snapshot(stored, "3,1").json()
        assert data["versions_analyzed"] == snap["versions_analyzed"] == [3, 1]
        assert data["video_filename"] == snap["video_filename"]
        assert data["summary"] == snap["summary"]
        assert data["report"]["snapshots"] == snap["snapshots"]

    def test_selected_aggregates_match_snapshot(self):
        stored = _marked()
        for query in (None, "1,3", "5,2", "4"):
            assert _report(stored, query).json()["summary"] == \
                _snapshot(stored, query).json()["summary"]

    def test_probe_aggregate_values(self):
        stored = _versions()
        summary = _report(stored).json()["summary"]
        assert summary["versions_analyzed"] == 5
        assert summary["ready_count"] == 1
        assert summary["needs_attention_count"] == 4
        assert summary["required"] == {
            "total": 35, "present": 20, "weak": 2, "missing": 13,
            "coverage_percentage": 57}
        assert summary["supporting"] == {
            "total": 10, "present": 6, "weak": 0, "missing": 4}
        assert summary["dimension_summary"] == [
            {"dimension": "subject", "present": 3, "weak": 1, "missing": 1},
            {"dimension": "action", "present": 3, "weak": 0, "missing": 2},
            {"dimension": "environment", "present": 4, "weak": 0,
             "missing": 1},
            {"dimension": "camera", "present": 1, "weak": 1, "missing": 3},
            {"dimension": "lighting", "present": 3, "weak": 0, "missing": 2},
            {"dimension": "visual_style", "present": 3, "weak": 0,
             "missing": 2},
            {"dimension": "color", "present": 3, "weak": 0, "missing": 2},
            {"dimension": "composition", "present": 3, "weak": 0,
             "missing": 2},
            {"dimension": "audio", "present": 3, "weak": 0, "missing": 2},
        ]


class TestDay27Equivalence:
    def test_steps_byte_equal_timeline_endpoint(self):
        stored = _versions()
        data = _report(stored).json()
        assert data["timeline"]["steps"] == _timeline(stored).json()["timeline"]

    def test_totals_equal_timeline_summary(self):
        stored = _versions()
        tl = _report(stored).json()["timeline"]
        day27 = _timeline(stored).json()["summary"]
        assert tl["changed_dimensions"] == day27["dimensions_changed_total"]
        assert tl["unchanged_dimensions"] == day27["dimensions_unchanged_total"]
        assert tl["required_changes"] == day27["required_changes_total"]
        assert tl["supporting_changes"] == day27["supporting_changes_total"]
        assert tl["transition_summary"] == day27["transition_summary"]
        assert tl["required_coverage_delta"] == \
            day27["required_coverage_delta"]

    def test_selected_steps_byte_equal_timeline_endpoint(self):
        stored = _versions()
        for query in ("1,3", "5,1", "4,2,5", "2"):
            assert _report(stored, query).json()["timeline"]["steps"] == \
                _timeline(stored, query).json()["timeline"]

    def test_delta_telescopes_over_steps(self):
        stored = _versions()
        tl = _report(stored).json()["timeline"]
        deltas = [step["required_coverage"]["delta"] for step in tl["steps"]]
        assert len(deltas) == 4
        assert deltas == [-14, 0, -72, -14]
        assert sum(deltas) == tl["required_coverage_delta"] == -100

    def test_each_step_matches_day26_endpoint(self):
        stored = _versions()
        for step in _report(stored).json()["timeline"]["steps"]:
            direct = _change(stored, step["version_a"]["version"],
                             step["version_b"]["version"])
            assert direct.status_code == 200
            assert step == direct.json()

    def test_delta_equals_last_minus_first_coverage(self):
        stored = _versions()
        data = _report(stored, "5,1").json()
        coverages = [e["readiness"]["required_coverage_percentage"]
                     for e in _entries(data)]
        assert coverages == [0, 100]
        assert data["timeline"]["required_coverage_delta"] == \
            coverages[-1] - coverages[0] == 100


class TestSelection:
    def test_versions_subset(self):
        stored = _versions()
        data = _report(stored, "1,3").json()
        assert data["versions_analyzed"] == [1, 3]
        assert data["report"]["selection_order"] == [1, 3]
        assert data["report"]["version_count"] == 2
        assert data["report"]["first_version"] == 1
        assert data["report"]["last_version"] == 3
        assert [e["version"] for e in _entries(data)] == [1, 3]
        assert _pairs(data) == [(1, 3)]

    def test_reverse_order_preserved(self):
        stored = _versions()
        data = _report(stored, "3,1").json()
        assert data["versions_analyzed"] == [3, 1]
        assert data["report"]["selection_order"] == [3, 1]
        assert [e["version"] for e in _entries(data)] == [3, 1]
        assert _pairs(data) == [(3, 1)], "never resorted"
        assert data["report"]["first_version"] == 3
        assert data["report"]["last_version"] == 1

    def test_reverse_not_sorted_to_ascending(self):
        stored = _versions()
        data = _report(stored, "5,2,1").json()
        assert data["versions_analyzed"] == [5, 2, 1]
        assert _pairs(data) == [(5, 2), (2, 1)]

    def test_repeated_query_params(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/readiness/report",
            params=[("versions", "1"), ("versions", "3")],
        )
        assert response.status_code == 200
        assert response.json()["versions_analyzed"] == [1, 3]

    def test_whitespace_tolerated(self):
        stored = _versions()
        data = _report(stored, "1 , 3").json()
        assert data["versions_analyzed"] == [1, 3]
        assert _pairs(data) == [(1, 3)]

    def test_single_version_selection(self):
        stored = _versions()
        data = _report(stored, "5").json()
        assert data["versions_analyzed"] == [5]
        assert data["report"]["version_count"] == 1
        assert data["report"]["first_version"] == 5
        assert data["report"]["last_version"] == 5
        assert data["report"]["selection_order"] == [5]
        assert len(data["report"]["snapshots"]) == 1
        assert data["timeline"]["steps"] == []
        assert data["timeline"]["required_coverage_delta"] == 0
        assert data["timeline"]["changed_dimensions"] == 0
        assert set(data["timeline"]["transition_summary"].values()) == {0}
        summary = data["summary"]
        assert summary["versions_analyzed"] == 1
        assert summary["ready_count"] == 0
        assert summary["needs_attention_count"] == 1
        assert summary["required"] == {
            "total": 7, "present": 0, "weak": 0, "missing": 7,
            "coverage_percentage": 0}
        assert summary["supporting"] == {
            "total": 2, "present": 0, "weak": 0, "missing": 2}

    def test_selection_changes_aggregates(self):
        stored = _marked()
        full = _report(stored).json()["summary"]
        subset = _report(stored, "1,3").json()["summary"]
        assert full["required"]["present"] == 20
        assert subset["required"]["present"] == 13
        assert subset["organization"] == {
            "favorite_count": 1,
            "tag_counts": {"ai": 1, "cinematic": 1, "final": 1}}

    def test_step_count_pattern(self):
        stored = _versions()
        for query, count in (("1,2,3,4,5", 4), ("5,1", 1), ("3", 0),
                             ("1,3,5", 2)):
            data = _report(stored, query).json()
            assert len(data["timeline"]["steps"]) == count, query


class TestValidation:
    @pytest.mark.parametrize("query", [
        "", "0", "-1", "abc", "1,,2", "1,1", "1.5", ",", "1;2", "+2",
        " ", "1 2", "2,2", "0,1", "-1,2", "1,1.5", "3,1,3",
    ])
    def test_malformed_versions_is_422(self, query):
        stored = _versions()
        assert _report(stored, query).status_code == 422

    def test_repeated_duplicate_params_is_422(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/readiness/report",
            params=[("versions", "1"), ("versions", "1")],
        )
        assert response.status_code == 422

    def test_error_detail_is_plain_string(self):
        stored = _versions()
        detail = _report(stored, "1,99").json()["detail"]
        assert isinstance(detail, str)

    def test_nonexistent_version_is_404(self):
        stored = _versions()
        assert _report(stored, "1,99").status_code == 404

    def test_deleted_version_is_404(self):
        stored = _versions()
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/2"
        ).status_code == 200
        assert _report(stored, "1,2").status_code == 404
        assert _report(stored, "2").status_code == 404

    def test_default_after_deletion_skips_gap(self):
        stored = _versions()
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/3"
        ).status_code == 200
        data = _report(stored).json()
        assert data["versions_analyzed"] == [1, 2, 4, 5]
        assert data["report"]["selection_order"] == [1, 2, 4, 5]
        assert data["summary"]["versions_analyzed"] == 4

    def test_nonexistent_video_is_404(self):
        assert _report("missing.mp4").status_code == 404

    def test_invalid_extension_is_400(self):
        assert _report("clip.txt").status_code == 400

    def test_path_traversal_is_404(self):
        response = client.get(
            "/api/videos/../../../etc/passwd/prompt/history/readiness/"
            "report"
        )
        assert response.status_code == 404

    def test_missing_version_never_silently_replaced(self):
        stored = _versions()
        listing_before = client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content
        _report(stored, "1,99")
        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content == listing_before

    def test_404_detail_matches_day16_message(self):
        stored = _versions()
        detail = _report(stored, "99").json()["detail"]
        assert detail == f"Version 99 not found for video '{stored}'."


class TestEmptyAndSingle:
    def test_empty_video_returns_empty_report_200(self):
        stored = _upload()
        response = _report(stored)
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == REPORT_TOP
        assert data["versions_analyzed"] == []
        assert data["report"] == {
            "type": "prompt_readiness_report",
            "version_count": 0,
            "first_version": None,
            "last_version": None,
            "selection_order": [],
            "snapshots": [],
        }
        assert data["timeline"] == {
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
        summary = data["summary"]
        assert set(summary.keys()) == SUMMARY_KEYS
        assert summary["versions_analyzed"] == 0
        assert summary["ready_count"] == 0
        assert summary["needs_attention_count"] == 0
        assert summary["required"] == {
            "total": 0, "present": 0, "weak": 0, "missing": 0,
            "coverage_percentage": None}
        assert summary["supporting"] == {
            "total": 0, "present": 0, "weak": 0, "missing": 0}
        assert summary["dimension_summary"] == []
        assert summary["organization"] == {
            "favorite_count": 0, "tag_counts": {}}

    def test_empty_video_with_version_query_404(self):
        stored = _upload()
        assert _report(stored, "1").status_code == 404

    def test_single_version_video(self):
        stored = _upload()
        _save(stored, FULL)
        assert client.post(
            f"/api/videos/{stored}/prompt/history/1/favorite"
        ).status_code == 200
        data = _report(stored).json()
        assert data["versions_analyzed"] == [1]
        assert data["report"]["version_count"] == 1
        assert data["report"]["first_version"] == 1
        assert data["report"]["last_version"] == 1
        assert data["timeline"]["steps"] == []
        assert data["timeline"]["required_coverage_delta"] == 0
        summary = data["summary"]
        assert summary["versions_analyzed"] == 1
        assert summary["ready_count"] == 1
        assert summary["needs_attention_count"] == 0
        assert summary["required"] == {
            "total": 7, "present": 7, "weak": 0, "missing": 0,
            "coverage_percentage": 100}
        assert summary["supporting"] == {
            "total": 2, "present": 2, "weak": 0, "missing": 0}
        assert summary["organization"] == {
            "favorite_count": 1, "tag_counts": {}}
        entry = data["report"]["snapshots"][0]
        assert entry["favorite"] is True
        assert entry["tags"] == []
        assert entry["readiness"]["status"] == "ready"

    def test_single_snapshot_equals_full_entry(self):
        stored = _versions()
        full = {e["version"]: e
                for e in _entries(_report(stored).json())}
        single = _entries(_report(stored, "4").json())[0]
        assert single == full[4]

    def test_single_summary_matches_snapshot_single(self):
        stored = _versions()
        assert _report(stored, "4").json()["summary"] == \
            _snapshot(stored, "4").json()["summary"]


class TestDeterminism:
    def test_repeated_requests_identical(self):
        stored = _versions()
        assert _report(stored).json() == _report(stored).json()

    def test_byte_equivalent_text(self):
        stored = _versions()
        assert _report(stored).text == _report(stored).text

    def test_subset_selection_deterministic(self):
        stored = _versions()
        assert _report(stored, "1,4").text == _report(stored, "1,4").text
        assert _report(stored, "4,1").text == _report(stored, "4,1").text

    def test_no_generated_ids_outside_video_filename(self):
        stored = _versions()
        data = _report(stored).json()
        assert data["video_filename"] == stored
        text = str({k: v for k, v in data.items()
                    if k != "video_filename"})
        text = text.replace(stored, "")
        assert "uuid" not in text.lower()
        assert not re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            text)

    def test_created_at_are_stored_values(self):
        stored = _versions()
        for entry in _entries(_report(stored).json()):
            record = client.get(
                f"/api/videos/{stored}/prompt/history/"
                f"{entry['version']}"
            ).json()
            assert entry["created_at"] == record["created_at"]


class TestIntegrity:
    def test_history_listing_unchanged(self):
        stored = _versions()
        before = client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content
        _report(stored)
        _report(stored, "1,4")
        _report(stored, "5,2")
        _report(stored, "1,99")
        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content == before, "report never creates/deletes versions"

    def test_prompts_unchanged(self):
        stored = _versions()
        before = [client.get(
            f"/api/videos/{stored}/prompt/history/{v}"
        ).content for v in range(1, 6)]
        _report(stored, "1,5")
        after = [client.get(
            f"/api/videos/{stored}/prompt/history/{v}"
        ).content for v in range(1, 6)]
        assert before == after

    def test_favorites_tags_org_unchanged(self):
        stored = _marked()
        org_before = {v: _org(stored, v).content for v in range(1, 6)}
        _report(stored)
        _report(stored, "5,1")
        for v, blob in org_before.items():
            assert _org(stored, v).content == blob

    def test_export_and_quality_unchanged(self):
        stored = _versions()
        export_before = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).content
        quality_before = _quality(stored, PROMPT).json()
        _report(stored, "1,4")
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).content == export_before
        assert _quality(stored, PROMPT).json() == quality_before


class TestRouteCollision:
    def test_report_distinct_from_all_readiness_endpoints(self):
        stored = _versions()
        report = _report(stored)
        snap = _snapshot(stored)
        tline = _timeline(stored)
        analyze = _analyze(stored)
        change = _change(stored, 1, 2)
        assert report.status_code == snap.status_code == tline.status_code == \
            analyze.status_code == change.status_code == 200
        key_sets = [
            set(report.json().keys()), set(snap.json().keys()),
            set(tline.json().keys()), set(analyze.json().keys()),
            set(change.json().keys()),
        ]
        assert key_sets[0] == REPORT_TOP
        assert key_sets[1] == DAY28_TOP
        assert key_sets[2] == DAY27_TOP
        assert key_sets[3] == DAY25_TOP
        assert key_sets[4] == DAY26_TOP
        for i in range(len(key_sets)):
            for j in range(i + 1, len(key_sets)):
                assert key_sets[i] != key_sets[j], (i, j)

    def test_day16_token_compare_unchanged(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2"
        )
        assert response.status_code == 200
        assert "common_tokens" in response.json()
        assert "report" not in response.json()

    def test_day23_detailed_compare_unchanged(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2/detailed"
        )
        assert response.status_code == 200
        assert "comparison" in response.json()
        assert "report" not in response.json()

    def test_day24_routes_distinct(self):
        stored = _versions()
        post = _readiness(stored, FULL)
        per_version = _hreadiness(stored, 1)
        report = _report(stored)
        assert post.status_code == per_version.status_code == \
            report.status_code == 200
        assert "readiness" in per_version.json()
        assert "snapshots" not in per_version.json()
        assert set(per_version.json().keys()) == {
            "video_filename", "prompt", "readiness"}
        assert set(report.json().keys()) == REPORT_TOP
        assert "prompt" not in report.json()

    def test_numeric_route_not_captured_by_report_static(self):
        stored = _versions()
        numeric = client.get(f"/api/videos/{stored}/prompt/history/1")
        report = _report(stored)
        assert numeric.status_code == 200
        assert "prompt" in numeric.json()
        assert "prompt" not in report.json()
        assert report.json()["versions_analyzed"] == [1, 2, 3, 4, 5]

    def test_all_readiness_static_routes_resolve(self):
        stored = _versions()
        assert _report(stored).status_code == 200
        assert _report(stored, "1").status_code == 200
        assert _snapshot(stored).status_code == 200
        assert _timeline(stored).status_code == 200
        assert _analyze(stored).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/readiness"
        ).status_code == 200

    def test_static_and_post_routes_still_resolve(self):
        stored = _versions()
        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/favorites"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/tag/ai"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/search"
        ).status_code == 200
        assert _quality(stored, PROMPT).status_code == 200
        assert client.post(
            f"/api/videos/{stored}/prompt/improve",
            json={"prompt": PROMPT},
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/package"
        ).status_code == 200


class TestDay16To28Regression:
    def test_all_previous_features_still_work(self):
        stored = _upload()
        created = _save(stored, PROMPT)
        version = created["version"]
        _save(stored, CITY)

        # Day 16 history
        listing = client.get(f"/api/videos/{stored}/prompt/history")
        assert listing.status_code == 200
        assert len(listing.json()["versions"]) == 2
        single = client.get(f"/api/videos/{stored}/prompt/history/{version}")
        assert single.status_code == 200 and single.json()["prompt"] == PROMPT
        assert client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/1"
        ).status_code == 200

        # Day 17 favorites/tags
        assert client.post(
            f"/api/videos/{stored}/prompt/history/{version}/favorite"
        ).status_code == 200
        assert client.post(
            f"/api/videos/{stored}/prompt/history/{version}/tags",
            json={"tags": ["ai"]},
        ).json()["tags"] == ["ai"]
        org = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/organization"
        )
        assert org.status_code == 200 and org.json()["favorite"] is True

        # Day 18 search
        search = client.get(f"/api/videos/{stored}/prompt/search",
                            params={"query": "cinematic"})
        assert search.status_code == 200
        assert search.json()["count"] >= 1

        # Day 19 export
        for fmt in ("json", "markdown", "txt"):
            assert client.get(
                f"/api/videos/{stored}/prompt/history/{version}/export",
                params={"format": fmt},
            ).status_code == 200, fmt
        export_json_before = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "json"},
        ).content

        # Day 20 package
        package = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/package"
        )
        assert package.status_code == 200
        assert package.content[:2] == b"PK"

        # Day 21 quality
        quality = _quality(stored, PROMPT)
        assert quality.status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/quality"
        ).status_code == 200

        # Day 22 improve
        assert client.post(
            f"/api/videos/{stored}/prompt/improve",
            json={"prompt": PROMPT},
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/improve"
        ).status_code == 200

        # Day 23 detailed comparison
        detailed = client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2/detailed"
        )
        assert detailed.status_code == 200
        assert detailed.json()["comparison"]["changed"] is True

        # Day 24 readiness
        ready = _readiness(stored, FULL)
        assert ready.status_code == 200
        assert ready.json()["readiness"]["status"] == "ready"
        assert _hreadiness(stored, version).status_code == 200

        # Day 25 readiness history
        analysis = _analyze(stored)
        assert analysis.status_code == 200
        assert analysis.json()["versions_analyzed"] == [1, 2]
        assert _analyze(stored, "2,1").json()[
            "versions_analyzed"] == [2, 1]

        # Day 26 readiness change tracking
        change = _change(stored, 1, 2)
        assert change.status_code == 200
        assert set(change.json().keys()) == DAY26_TOP
        assert change.json()["version_a"]["version"] == 1
        assert _change(stored, 2, 1).status_code == 200
        assert _change(stored, 1, 1).json()["dimensions_changed"] == 0

        # Day 27 readiness timeline
        timeline = _timeline(stored)
        assert timeline.status_code == 200
        tl = timeline.json()
        assert set(tl.keys()) == DAY27_TOP
        assert tl["versions_analyzed"] == [1, 2]
        assert tl["steps"] == 1
        assert tl["timeline"][0] == _change(stored, 1, 2).json()
        assert _timeline(stored, "1").json()["steps"] == 0
        assert _timeline(stored, "2,1").json()["versions_analyzed"] == [2, 1]

        # Day 28 readiness snapshot
        snap = _snapshot(stored)
        assert snap.status_code == 200
        snap_data = snap.json()
        assert set(snap_data.keys()) == DAY28_TOP
        assert snap_data["versions_analyzed"] == [1, 2]
        assert len(snap_data["snapshots"]) == 2
        for entry in snap_data["snapshots"]:
            assert set(entry.keys()) == SNAPSHOT_KEYS
            day24 = _hreadiness(stored, entry["version"]).json()["readiness"]
            assert entry["readiness"]["status"] == day24["status"]
            assert entry["readiness"]["missing_dimensions"] == \
                day24["missing_dimensions"]
            org_entry = _org(stored, entry["version"]).json()
            assert entry["favorite"] == org_entry["favorite"]
            assert entry["tags"] == org_entry["tags"]
        assert set(snap_data["summary"].keys()) == SUMMARY_KEYS

        # Day 29 readiness report
        report = _report(stored)
        assert report.status_code == 200
        data = report.json()
        assert set(data.keys()) == REPORT_TOP
        assert data["versions_analyzed"] == [1, 2]
        meta = data["report"]
        assert meta["type"] == "prompt_readiness_report"
        assert meta["version_count"] == 2
        assert meta["first_version"] == 1
        assert meta["last_version"] == 2
        assert meta["selection_order"] == [1, 2]
        assert data["summary"] == snap_data["summary"]
        assert meta["snapshots"] == snap_data["snapshots"]
        assert data["timeline"]["steps"] == tl["timeline"]
        assert data["timeline"]["transition_summary"] == \
            tl["summary"]["transition_summary"]
        assert data["timeline"]["required_coverage_delta"] == \
            tl["summary"]["required_coverage_delta"]
        assert _report(stored, "1").json()["report"]["version_count"] == 1
        assert _report(stored, "1").json()["timeline"]["steps"] == []
        assert _report(stored, "2,1").json()["versions_analyzed"] == [2, 1]
        assert _report(stored, "3").status_code == 404

        # nothing above changed history, org, export, or quality
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "json"},
        ).content == export_json_before
        assert _quality(stored, PROMPT).json() == quality.json()
        final = client.get(f"/api/videos/{stored}/prompt/history/{version}")
        assert final.json()["prompt"] == PROMPT
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/organization"
        ).json() == org.json()


class TestNoLeaks:
    def test_response_has_no_absolute_paths_or_internals(self):
        stored = _marked()
        for query in (None, "1,4", "4,1"):
            text = _report(stored, query).text
            for bad in ("C:\\", "C:/", "/home", "/Users", "/var/"):
                assert bad not in text, bad
            for internal in ("_storage", "PromptReadinessReportService",
                             "PromptReadinessSnapshotService",
                             "PromptReadinessTimelineService",
                             "PromptReadinessChangeService",
                             "PromptReadinessHistoryService",
                             "PromptReadinessService",
                             "PromptOrganizationService",
                             "PromptHistoryService",
                             "PromptQualityService",
                             "readiness_report_service",
                             "readiness_snapshot_service",
                             "readiness_timeline_service",
                             "history_service", "organization_service",
                             "Traceback", "os.environ", "api_key",
                             "password", "secret"):
                assert internal not in text, internal

    def test_no_ranking_or_evaluative_language(self):
        stored = _marked()
        text = _report(stored, "1,5").text.lower()
        for word in FORBIDDEN_WORDS:
            assert word not in text, word

    def test_prompt_and_negative_prompt_not_echoed(self):
        stored = _versions()
        text = _report(stored).text
        assert "film grain style portrait" not in text
        assert FULL not in text
        assert PROMPT not in text
        assert NEGATIVE not in text
        assert "blurry, low quality" not in text

    def test_prompt_not_modified_by_report(self):
        stored = _versions()
        before = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        ).json()["prompt"]
        _report(stored, "1,4")
        after = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        ).json()["prompt"]
        assert before == after == FULL
