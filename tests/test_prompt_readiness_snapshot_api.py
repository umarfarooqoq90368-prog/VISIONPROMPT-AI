"""API tests for the prompt readiness snapshot endpoint (Day 28)."""
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

DAY26_TOP_KEYS = {
    "video_filename", "version_a", "version_b", "dimensions",
    "changed_dimensions", "dimensions_changed", "dimensions_unchanged",
    "required_changes", "supporting_changes", "transitions",
    "transition_summary", "required_coverage",
}

DAY27_TOP_KEYS = {
    "video_filename", "versions_analyzed", "steps", "timeline", "summary",
}

DAY25_TOP_KEYS = {
    "video_filename", "versions_analyzed", "results", "summary",
    "dimension_summary",
}


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


def _snapshot(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness/snapshot",
        params=params,
    )


def _change(stored, a, b):
    return client.get(
        f"/api/videos/{stored}/prompt/history/compare/{a}/{b}/readiness"
    )


def _analyze(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness", params=params
    )


def _timeline(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness/timeline",
        params=params,
    )


def _quality(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/quality",
                       json={"prompt": prompt})


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


class TestEndpointBasics:
    def test_valid_snapshot_returns_200(self):
        stored = _versions()
        assert _snapshot(stored).status_code == 200

    def test_top_level_keys_exact(self):
        stored = _versions()
        assert set(_snapshot(stored).json().keys()) == TOP_KEYS

    def test_video_filename_echo(self):
        stored = _versions()
        assert _snapshot(stored).json()["video_filename"] == stored

    def test_versions_analyzed_all_five(self):
        stored = _versions()
        assert _snapshot(stored).json()["versions_analyzed"] == [1, 2, 3, 4, 5]

    def test_snapshots_order_matches(self):
        stored = _versions()
        data = _snapshot(stored).json()
        assert len(data["snapshots"]) == 5
        assert [s["version"] for s in data["snapshots"]] == \
            data["versions_analyzed"]

    def test_summary_keys_exact(self):
        stored = _versions()
        summary = _snapshot(stored).json()["summary"]
        assert set(summary.keys()) == SUMMARY_KEYS

    def test_snapshot_keys_exact(self):
        stored = _versions()
        for snapshot in _snapshot(stored).json()["snapshots"]:
            assert set(snapshot.keys()) == SNAPSHOT_KEYS, \
                list(snapshot.keys())

    def test_readiness_keys_and_orders(self):
        stored = _versions()
        for snapshot in _snapshot(stored).json()["snapshots"]:
            block = snapshot["readiness"]
            assert set(block.keys()) == READINESS_KEYS
            assert list(block["required"].keys()) == REQUIRED_KEYS
            assert list(block["supporting"].keys()) == SUPPORTING_KEYS

    def test_dimensions_in_day21_order_everywhere(self):
        stored = _versions()
        data = _snapshot(stored).json()
        assert [row["dimension"] for row in
                data["summary"]["dimension_summary"]] == list(DIMENSIONS)
        for snapshot in data["snapshots"]:
            for key in ("missing_dimensions", "weak_dimensions"):
                dims = snapshot["readiness"][key]
                assert dims == [d for d in DIMENSIONS if d in set(dims)]
        for snapshot in data["snapshots"]:
            for key in ("missing_dimensions", "weak_dimensions"):
                dims = snapshot["readiness"][key]
                assert dims == [d for d in DIMENSIONS if d in set(dims)]


class TestSnapshotMatchesExistingEndpoints:
    def test_each_snapshot_matches_day24_endpoint(self):
        stored = _versions()
        for snapshot in _snapshot(stored).json()["snapshots"]:
            version = snapshot["version"]
            day24 = _hreadiness(stored, version).json()["readiness"]
            block = snapshot["readiness"]
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

    def test_favorite_and_tags_match_day17_endpoint(self):
        stored = _marked()
        for snapshot in _snapshot(stored).json()["snapshots"]:
            org = _org(stored, snapshot["version"]).json()
            assert snapshot["favorite"] == org["favorite"]
            assert snapshot["tags"] == org["tags"]

    def test_aggregate_matches_day25_endpoint(self):
        stored = _versions()
        summary = _snapshot(stored).json()["summary"]
        day25 = _analyze(stored).json()
        assert summary["versions_analyzed"] == \
            len(day25["versions_analyzed"]) == 5
        assert summary["ready_count"] == day25["summary"]["ready_count"] == 1
        assert summary["needs_attention_count"] == \
            day25["summary"]["needs_attention_count"] == 4
        assert summary["required"]["total"] == \
            day25["summary"]["required_dimensions_total"] == 35
        assert summary["required"]["present"] == \
            day25["summary"]["required_dimensions_present"] == 20
        assert summary["required"]["weak"] == \
            day25["summary"]["required_dimensions_weak"] == 2
        assert summary["required"]["missing"] == \
            day25["summary"]["required_dimensions_missing"] == 13
        assert summary["required"]["coverage_percentage"] == \
            day25["summary"]["required_coverage_percentage"] == 57
        assert summary["supporting"]["present"] == \
            day25["summary"]["supporting_dimensions_present"] == 6
        assert summary["supporting"]["missing"] == \
            day25["summary"]["supporting_dimensions_missing"] == 4
        for ours, theirs in zip(summary["dimension_summary"],
                                day25["dimension_summary"]):
            assert ours == {
                "dimension": theirs["dimension"],
                "present": theirs["present_count"],
                "weak": theirs["weak_count"],
                "missing": theirs["missing_count"],
            }

    def test_status_and_coverage_values(self):
        stored = _versions()
        snapshots = {s["version"]: s
                     for s in _snapshot(stored).json()["snapshots"]}
        assert snapshots[1]["readiness"]["status"] == "ready"
        assert snapshots[1]["readiness"]["required_coverage_percentage"] == 100
        assert snapshots[2]["readiness"]["status"] == "needs_attention"
        assert snapshots[2]["readiness"]["required_coverage_percentage"] == 86
        assert snapshots[2]["readiness"]["weak_dimensions"] == ["camera"]
        assert snapshots[3]["readiness"]["missing_dimensions"] == ["camera"]
        assert snapshots[4]["readiness"]["required_coverage_percentage"] == 14
        assert snapshots[5]["readiness"]["required_coverage_percentage"] == 0
        assert snapshots[5]["readiness"]["missing_dimensions"] == list(DIMENSIONS)

    def test_raw_scores_are_day21_values(self):
        stored = _versions()
        snapshots = {s["version"]: s
                     for s in _snapshot(stored).json()["snapshots"]}
        assert snapshots[2]["readiness"]["required"]["camera"] == {
            "status": "weak", "score": 40}
        assert snapshots[4]["readiness"]["required"]["subject"] == {
            "status": "weak", "score": 40}
        assert snapshots[4]["readiness"]["required"]["environment"] == {
            "status": "present", "score": 70}
        assert snapshots[1]["readiness"]["required"]["subject"] == {
            "status": "present", "score": 100}

    def test_created_at_is_stored_metadata(self):
        stored = _versions()
        for snapshot in _snapshot(stored).json()["snapshots"]:
            record = client.get(
                f"/api/videos/{stored}/prompt/history/"
                f"{snapshot['version']}"
            ).json()
            assert snapshot["created_at"] == record["created_at"]


class TestSelection:
    def test_versions_subset(self):
        stored = _versions()
        data = _snapshot(stored, "1,3").json()
        assert data["versions_analyzed"] == [1, 3]
        assert [s["version"] for s in data["snapshots"]] == [1, 3]
        assert data["summary"]["versions_analyzed"] == 2

    def test_reverse_order_preserved(self):
        stored = _versions()
        data = _snapshot(stored, "3,1").json()
        assert data["versions_analyzed"] == [3, 1]
        assert [s["version"] for s in data["snapshots"]] == [3, 1]

    def test_arbitrary_order_not_sorted(self):
        stored = _versions()
        data = _snapshot(stored, "5,2,1").json()
        assert data["versions_analyzed"] == [5, 2, 1]

    def test_repeated_query_params(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/readiness/snapshot",
            params=[("versions", "1"), ("versions", "3")],
        )
        assert response.status_code == 200
        assert response.json()["versions_analyzed"] == [1, 3]

    def test_whitespace_tolerated(self):
        stored = _versions()
        data = _snapshot(stored, "1 , 3").json()
        assert data["versions_analyzed"] == [1, 3]

    def test_single_version_selection(self):
        stored = _versions()
        data = _snapshot(stored, "5").json()
        assert data["versions_analyzed"] == [5]
        assert len(data["snapshots"]) == 1
        summary = data["summary"]
        assert summary["versions_analyzed"] == 1
        assert summary["ready_count"] == 0
        assert summary["needs_attention_count"] == 1
        assert summary["required"] == {
            "total": 7, "present": 0, "weak": 0, "missing": 7,
            "coverage_percentage": 0}
        assert summary["supporting"] == {
            "total": 2, "present": 0, "weak": 0, "missing": 2}

    def test_selection_changes_aggregate(self):
        stored = _marked()
        full = _snapshot(stored).json()["summary"]
        subset = _snapshot(stored, "1,3").json()["summary"]
        assert full["required"]["present"] == 20
        assert subset["required"]["present"] == 13
        assert subset["organization"]["favorite_count"] == 1
        assert subset["organization"]["tag_counts"] == {
            "ai": 1, "cinematic": 1, "final": 1}
        assert full["organization"]["favorite_count"] == 1

    def test_step_count_pattern_for_snapshots(self):
        stored = _versions()
        for query, count in (("1,2,3,4,5", 5), ("5,1", 2), ("3", 1)):
            data = _snapshot(stored, query).json()
            assert len(data["snapshots"]) == count, query
            assert data["summary"]["versions_analyzed"] == count


class TestValidation:
    @pytest.mark.parametrize("query", [
        "", "0", "-1", "abc", "1,,2", "1,1", "1.5", ",", "1;2", "+2",
        " ", "1 2", "2,2", "0,1", "-1,2", "1,1.5", "3,1,3",
    ])
    def test_malformed_versions_is_422(self, query):
        stored = _versions()
        assert _snapshot(stored, query).status_code == 422

    def test_repeated_duplicate_params_is_422(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/readiness/snapshot",
            params=[("versions", "1"), ("versions", "1")],
        )
        assert response.status_code == 422

    def test_error_detail_is_plain_string(self):
        stored = _versions()
        detail = _snapshot(stored, "1,99").json()["detail"]
        assert isinstance(detail, str)

    def test_nonexistent_version_is_404(self):
        stored = _versions()
        assert _snapshot(stored, "1,99").status_code == 404

    def test_deleted_version_is_404(self):
        stored = _versions()
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/2"
        ).status_code == 200
        assert _snapshot(stored, "1,2").status_code == 404
        assert _snapshot(stored, "2").status_code == 404

    def test_default_after_deletion_skips_deleted_version(self):
        stored = _versions()
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/3"
        ).status_code == 200
        data = _snapshot(stored).json()
        assert data["versions_analyzed"] == [1, 2, 4, 5]
        assert data["summary"]["versions_analyzed"] == 4

    def test_nonexistent_video_is_404(self):
        assert _snapshot("missing.mp4").status_code == 404

    def test_invalid_extension_is_400(self):
        assert _snapshot("clip.txt").status_code == 400

    def test_path_traversal_is_404(self):
        response = client.get(
            "/api/videos/../../../etc/passwd/prompt/history/readiness/"
            "snapshot"
        )
        assert response.status_code == 404

    def test_missing_version_never_silently_replaced(self):
        stored = _versions()
        listing_before = client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content
        _snapshot(stored, "1,99")
        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content == listing_before

    def test_404_detail_matches_day16_message(self):
        stored = _versions()
        detail = _snapshot(stored, "99").json()["detail"]
        assert detail == f"Version 99 not found for video '{stored}'."


class TestEmptyAndSingle:
    def test_empty_video_returns_empty_snapshot_200(self):
        stored = _upload()
        response = _snapshot(stored)
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == TOP_KEYS
        assert data["versions_analyzed"] == []
        assert data["snapshots"] == []
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
        assert _snapshot(stored, "1").status_code == 404

    def test_single_version_video(self):
        stored = _upload()
        _save(stored, FULL)
        assert client.post(
            f"/api/videos/{stored}/prompt/history/1/favorite"
        ).status_code == 200
        data = _snapshot(stored).json()
        assert data["versions_analyzed"] == [1]
        assert len(data["snapshots"]) == 1
        summary = data["summary"]
        assert summary["versions_analyzed"] == 1
        assert summary["ready_count"] == 1
        assert summary["needs_attention_count"] == 0
        assert summary["required"] == {
            "total": 7, "present": 7, "weak": 0, "missing": 0,
            "coverage_percentage": 100}
        assert summary["supporting"] == {
            "total": 2, "present": 2, "weak": 0, "missing": 0}
        assert len(summary["dimension_summary"]) == 9
        for row in summary["dimension_summary"]:
            assert row["present"] + row["weak"] + row["missing"] == 1
        assert summary["organization"] == {
            "favorite_count": 1, "tag_counts": {}}
        snapshot = data["snapshots"][0]
        assert snapshot["favorite"] is True
        assert snapshot["tags"] == []
        assert snapshot["readiness"]["status"] == "ready"

    def test_single_version_snapshot_equals_full_entry(self):
        stored = _versions()
        full = {s["version"]: s
                for s in _snapshot(stored).json()["snapshots"]}
        single = _snapshot(stored, "4").json()["snapshots"][0]
        assert single == full[4]


class TestDeterminism:
    def test_repeated_requests_identical(self):
        stored = _versions()
        assert _snapshot(stored).json() == _snapshot(stored).json()

    def test_byte_equivalent_text(self):
        stored = _versions()
        assert _snapshot(stored).text == _snapshot(stored).text

    def test_subset_selection_deterministic(self):
        stored = _versions()
        assert _snapshot(stored, "1,4").text == \
            _snapshot(stored, "1,4").text

    def test_no_uuids_or_random_ids(self):
        stored = _versions()
        data = _snapshot(stored).json()
        assert data["video_filename"] == stored
        text = str({k: v for k, v in data.items()
                    if k != "video_filename"})
        assert "uuid" not in text.lower()
        assert not re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            text)


class TestIntegrity:
    def test_history_listing_unchanged(self):
        stored = _versions()
        before = client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content
        _snapshot(stored)
        _snapshot(stored, "1,4")
        _snapshot(stored, "5,2")
        _snapshot(stored, "1,99")
        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content == before, "snapshot never creates/deletes versions"

    def test_prompts_unchanged(self):
        stored = _versions()
        before = [client.get(
            f"/api/videos/{stored}/prompt/history/{v}"
        ).content for v in range(1, 6)]
        _snapshot(stored, "1,5")
        after = [client.get(
            f"/api/videos/{stored}/prompt/history/{v}"
        ).content for v in range(1, 6)]
        assert before == after

    def test_favorites_tags_org_unchanged(self):
        stored = _marked()
        assert client.post(
            f"/api/videos/{stored}/prompt/history/1/favorite"
        ).status_code == 200
        org_before = {
            v: _org(stored, v).content
            for v in range(1, 6)
        }
        _snapshot(stored)
        _snapshot(stored, "5,1")
        for v, blob in org_before.items():
            assert _org(stored, v).content == blob

    def test_export_and_quality_unchanged(self):
        stored = _versions()
        export_before = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).content
        quality_before = _quality(stored, PROMPT).json()
        _snapshot(stored, "1,4")
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).content == export_before
        assert _quality(stored, PROMPT).json() == quality_before


class TestRouteCollision:
    def test_day16_token_compare_unchanged(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2"
        )
        assert response.status_code == 200
        assert "common_tokens" in response.json()
        assert "snapshots" not in response.json()

    def test_day23_detailed_compare_unchanged(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2/detailed"
        )
        assert response.status_code == 200
        assert "comparison" in response.json()
        assert "snapshots" not in response.json()

    def test_day24_routes_distinct(self):
        stored = _versions()
        post = _readiness(stored, FULL)
        per_version = _hreadiness(stored, 1)
        snap = _snapshot(stored)
        assert post.status_code == per_version.status_code == \
            snap.status_code == 200
        assert "readiness" in post.json()
        assert "readiness" in per_version.json()
        assert "snapshots" not in per_version.json()
        assert set(snap.json().keys()) == TOP_KEYS
        assert "prompt" not in snap.json()

    def test_day25_and_day28_routes_distinct(self):
        stored = _versions()
        day25 = _analyze(stored)
        day28 = _snapshot(stored)
        assert day25.status_code == day28.status_code == 200
        assert set(day25.json().keys()) == DAY25_TOP_KEYS
        assert set(day28.json().keys()) == TOP_KEYS
        assert set(day25.json().keys()) != set(day28.json().keys())

    def test_day26_and_day27_routes_distinct(self):
        stored = _versions()
        day26 = _change(stored, 1, 2)
        day27 = _timeline(stored)
        day28 = _snapshot(stored)
        assert day26.status_code == day27.status_code == \
            day28.status_code == 200
        assert set(day26.json().keys()) == DAY26_TOP_KEYS
        assert set(day27.json().keys()) == DAY27_TOP_KEYS
        assert set(day28.json().keys()) == TOP_KEYS
        assert set(day26.json().keys()) != set(day28.json().keys())
        assert set(day27.json().keys()) != set(day28.json().keys())

    def test_numeric_route_not_captured_by_snapshot_static(self):
        stored = _versions()
        numeric = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        )
        snap = _snapshot(stored)
        assert numeric.status_code == 200
        assert "prompt" in numeric.json()
        assert "prompt" not in snap.json()
        assert snap.json()["versions_analyzed"] == [1, 2, 3, 4, 5]

    def test_all_readiness_static_routes_resolve(self):
        stored = _versions()
        assert _snapshot(stored).status_code == 200
        assert _snapshot(stored, "1").status_code == 200
        assert _analyze(stored).status_code == 200
        assert _timeline(stored).status_code == 200
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
        hv = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/quality"
        )
        assert hv.status_code == 200

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
        assert set(change.json().keys()) == DAY26_TOP_KEYS
        assert change.json()["version_a"]["version"] == 1
        assert _change(stored, 2, 1).status_code == 200
        assert _change(stored, 1, 1).json()["dimensions_changed"] == 0

        # Day 27 readiness timeline
        timeline = _timeline(stored)
        assert timeline.status_code == 200
        tl = timeline.json()
        assert set(tl.keys()) == DAY27_TOP_KEYS
        assert tl["versions_analyzed"] == [1, 2]
        assert tl["steps"] == 1
        assert tl["timeline"][0] == _change(stored, 1, 2).json()
        assert _timeline(stored, "1").json()["steps"] == 0
        assert _timeline(stored, "2,1").json()["versions_analyzed"] == [2, 1]

        # Day 28 readiness snapshot
        snap = _snapshot(stored)
        assert snap.status_code == 200
        data = snap.json()
        assert set(data.keys()) == TOP_KEYS
        assert data["versions_analyzed"] == [1, 2]
        assert len(data["snapshots"]) == 2
        for entry in data["snapshots"]:
            assert set(entry.keys()) == SNAPSHOT_KEYS
            day24 = _hreadiness(stored, entry["version"]).json()["readiness"]
            assert entry["readiness"]["status"] == day24["status"]
            assert entry["readiness"]["missing_dimensions"] == \
                day24["missing_dimensions"]
            org_entry = _org(stored, entry["version"]).json()
            assert entry["favorite"] == org_entry["favorite"]
            assert entry["tags"] == org_entry["tags"]
        assert set(data["summary"].keys()) == SUMMARY_KEYS
        assert data["summary"]["versions_analyzed"] == 2
        assert data["summary"]["ready_count"] + \
            data["summary"]["needs_attention_count"] == 2
        assert _snapshot(stored, "1").json()["summary"][
            "versions_analyzed"] == 1
        assert _snapshot(stored, "2,1").json()["versions_analyzed"] == [2, 1]
        assert _snapshot(stored, "3").status_code == 404
        assert set(data["summary"]["dimension_summary"][0].keys()) == {
            "dimension", "present", "weak", "missing"}

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
            text = _snapshot(stored, query).text
            for bad in ("C:\\", "C:/", "/home", "/Users", "/var/"):
                assert bad not in text, bad
            for internal in ("_storage", "PromptReadinessSnapshotService",
                             "PromptReadinessHistoryService",
                             "PromptReadinessChangeService",
                             "PromptReadinessTimelineService",
                             "PromptReadinessService",
                             "PromptOrganizationService",
                             "PromptHistoryService",
                             "PromptQualityService",
                             "readiness_snapshot_service",
                             "history_service", "organization_service",
                             "Traceback", "os.environ", "api_key",
                             "password", "secret"):
                assert internal not in text, internal

    def test_no_ranking_or_evaluative_language(self):
        stored = _marked()
        text = _snapshot(stored, "1,5").text.lower()
        for word in ("best", "worst", "winner", "perfect", "guaranteed",
                     "superior", "inferior", "rank", "recommended",
                     "better", "worse", "improved", "improvement",
                     "gain"):
            assert word not in text, word

    def test_prompt_and_negative_prompt_not_echoed(self):
        stored = _versions()
        text = _snapshot(stored).text
        assert "film grain style portrait" not in text
        assert FULL not in text
        assert PROMPT not in text
        assert NEGATIVE not in text
        assert "blurry, low quality" not in text

    def test_prompt_not_modified_by_snapshot(self):
        stored = _versions()
        before = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        ).json()["prompt"]
        _snapshot(stored, "1,4")
        after = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        ).json()["prompt"]
        assert before == after == FULL
