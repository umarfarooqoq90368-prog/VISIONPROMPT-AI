"""API tests for the prompt readiness timeline endpoint (Day 27)."""
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

DAY26_TOP_KEYS = {
    "video_filename", "version_a", "version_b", "dimensions",
    "changed_dimensions", "dimensions_changed", "dimensions_unchanged",
    "required_changes", "supporting_changes", "transitions",
    "transition_summary", "required_coverage",
}

DAY25_TOP_KEYS = {
    "video_filename", "versions_analyzed", "results", "summary",
    "dimension_summary",
}

TRANSITION_KEYS = {
    "missing_to_weak", "missing_to_present", "weak_to_missing",
    "weak_to_present", "present_to_missing", "present_to_weak",
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


def _change(stored, a, b):
    return client.get(
        f"/api/videos/{stored}/prompt/history/compare/{a}/{b}/readiness"
    )


def _quality(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/quality",
                       json={"prompt": prompt})


def _readiness(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/readiness",
                       json={"prompt": prompt})


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


class TestEndpointBasics:
    def test_valid_timeline_returns_200(self):
        stored = _versions()
        assert _timeline(stored).status_code == 200

    def test_top_level_keys_exact(self):
        stored = _versions()
        assert set(_timeline(stored).json().keys()) == TOP_KEYS

    def test_video_filename_echo(self):
        stored = _versions()
        assert _timeline(stored).json()["video_filename"] == stored

    def test_versions_analyzed_all_five(self):
        stored = _versions()
        assert _timeline(stored).json()["versions_analyzed"] == [1, 2, 3, 4, 5]

    def test_steps_and_timeline_length(self):
        stored = _versions()
        data = _timeline(stored).json()
        assert data["steps"] == 4
        assert len(data["timeline"]) == 4
        assert data["steps"] == len(data["versions_analyzed"]) - 1

    def test_summary_keys_exact(self):
        stored = _versions()
        summary = _timeline(stored).json()["summary"]
        assert set(summary.keys()) == SUMMARY_KEYS

    def test_every_step_has_exact_day26_keys(self):
        stored = _versions()
        for step in _timeline(stored).json()["timeline"]:
            assert set(step.keys()) == DAY26_TOP_KEYS

    def test_dimensions_in_day21_order_in_every_step(self):
        stored = _versions()
        for step in _timeline(stored).json()["timeline"]:
            dims = [item["dimension"] for item in step["dimensions"]]
            assert dims == list(DIMENSIONS)
            assert len(dims) == 9

    def test_transition_summary_six_keys_in_steps_and_summary(self):
        stored = _versions()
        data = _timeline(stored).json()
        assert set(data["summary"]["transition_summary"].keys()) == \
            TRANSITION_KEYS
        for step in data["timeline"]:
            assert set(step["transition_summary"].keys()) == TRANSITION_KEYS


class TestChainMatchesDay26:
    def test_pairs_are_consecutive_versions(self):
        stored = _versions()
        pairs = [(step["version_a"]["version"], step["version_b"]["version"])
                 for step in _timeline(stored).json()["timeline"]]
        assert pairs == [(1, 2), (2, 3), (3, 4), (4, 5)]

    @pytest.mark.parametrize("a,b", [(1, 2), (2, 3), (3, 4), (4, 5)])
    def test_step_byte_equals_direct_day26_endpoint(self, a, b):
        stored = _versions()
        step = _timeline(stored, f"{a},{b}").json()["timeline"][0]
        direct = _change(stored, a, b).json()
        assert step == direct

    def test_all_steps_equal_direct_day26_endpoints(self):
        stored = _versions()
        for step in _timeline(stored).json()["timeline"]:
            direct = _change(stored, step["version_a"]["version"],
                             step["version_b"]["version"]).json()
            assert step == direct

    def test_summary_totals_match_day26_summation(self):
        stored = _versions()
        summary = _timeline(stored).json()["summary"]
        directs = [_change(stored, a, b).json()
                   for a, b in ((1, 2), (2, 3), (3, 4), (4, 5))]
        assert summary["dimensions_changed_total"] == sum(
            d["dimensions_changed"] for d in directs) == 11
        assert summary["dimensions_unchanged_total"] == sum(
            d["dimensions_unchanged"] for d in directs) == 25
        assert summary["required_changes_total"] == sum(
            len(d["required_changes"]) for d in directs) == 9
        assert summary["supporting_changes_total"] == sum(
            len(d["supporting_changes"]) for d in directs) == 2

    def test_summary_transition_totals_match_day26(self):
        stored = _versions()
        summary = _timeline(stored).json()["summary"]
        assert summary["transition_summary"] == {
            "missing_to_weak": 0, "missing_to_present": 0,
            "weak_to_missing": 2, "weak_to_present": 0,
            "present_to_missing": 7, "present_to_weak": 2,
        }

    def test_summary_first_last_and_delta(self):
        stored = _versions()
        summary = _timeline(stored).json()["summary"]
        assert summary["first_version"] == 1
        assert summary["last_version"] == 5
        assert summary["first_required_coverage_percentage"] == 100
        assert summary["last_required_coverage_percentage"] == 0
        assert summary["required_coverage_delta"] == -100

    def test_delta_telescopes_over_steps(self):
        stored = _versions()
        data = _timeline(stored).json()
        total = sum(step["required_coverage"]["delta"]
                    for step in data["timeline"])
        assert total == data["summary"]["required_coverage_delta"]

    def test_invariants_hold(self):
        stored = _versions()
        summary = _timeline(stored).json()["summary"]
        assert (summary["dimensions_changed_total"]
                + summary["dimensions_unchanged_total"]) == \
            summary["steps"] * len(DIMENSIONS)
        assert (summary["required_changes_total"]
                + summary["supporting_changes_total"]) == \
            summary["dimensions_changed_total"]
        assert sum(summary["transition_summary"].values()) == \
            summary["dimensions_changed_total"]


class TestSelectionQuery:
    def test_versions_subset(self):
        stored = _versions()
        data = _timeline(stored, "1,3,5").json()
        assert data["versions_analyzed"] == [1, 3, 5]
        assert data["steps"] == 2
        pairs = [(step["version_a"]["version"], step["version_b"]["version"])
                 for step in data["timeline"]]
        assert pairs == [(1, 3), (3, 5)]

    def test_repeated_query_params(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/readiness/timeline",
            params=[("versions", "1"), ("versions", "3")],
        )
        assert response.status_code == 200
        assert response.json()["versions_analyzed"] == [1, 3]
        assert response.json()["steps"] == 1

    def test_whitespace_tolerated(self):
        stored = _versions()
        data = _timeline(stored, "1 , 3").json()
        assert data["versions_analyzed"] == [1, 3]

    def test_single_version_selection(self):
        stored = _versions()
        data = _timeline(stored, "5").json()
        assert data["versions_analyzed"] == [5]
        assert data["steps"] == 0
        assert data["timeline"] == []
        assert data["summary"]["first_version"] == 5
        assert data["summary"]["last_version"] == 5
        assert data["summary"]["first_required_coverage_percentage"] == 0
        assert data["summary"]["last_required_coverage_percentage"] == 0
        assert data["summary"]["required_coverage_delta"] == 0

    def test_requested_order_preserved(self):
        stored = _versions()
        data = _timeline(stored, "4,2").json()
        assert data["versions_analyzed"] == [4, 2]
        assert data["steps"] == 1
        assert data["summary"]["first_version"] == 4
        assert data["summary"]["last_version"] == 2
        assert data["summary"]["required_coverage_delta"] == 72

    def test_summary_selection_matches_query(self):
        stored = _versions()
        data = _timeline(stored, "2,4,5").json()
        assert data["summary"]["versions_analyzed"] == 3
        assert data["summary"]["steps"] == 2
        assert data["summary"]["first_version"] == 2
        assert data["summary"]["last_version"] == 5

    def test_empty_video_returns_empty_timeline_200(self):
        stored = _upload()
        response = _timeline(stored)
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == TOP_KEYS
        assert data["versions_analyzed"] == []
        assert data["steps"] == 0
        assert data["timeline"] == []
        assert data["summary"]["versions_analyzed"] == 0
        assert data["summary"]["first_version"] is None
        assert data["summary"]["last_version"] is None
        assert data["summary"]["first_required_coverage_percentage"] is None
        assert data["summary"]["last_required_coverage_percentage"] is None
        assert data["summary"]["required_coverage_delta"] == 0

    def test_empty_video_with_single_version_query_404(self):
        stored = _upload()
        assert _timeline(stored, "1").status_code == 404

    @pytest.mark.parametrize("query,expected_steps", [
        ("1,2,3,4,5", 4), ("1,4", 1), ("2,3,4", 2), ("3", 0),
    ])
    def test_step_count_always_one_fewer_than_selection(
            self, query, expected_steps):
        stored = _versions()
        data = _timeline(stored, query).json()
        assert data["steps"] == expected_steps
        assert len(data["timeline"]) == expected_steps


class TestValidation:
    @pytest.mark.parametrize("query", [
        "", "0", "-1", "abc", "1,,2", "1,1", "1.5", ",", "1;2", "+2",
        " ", "1 2", "2,2", "0,1", "-1,2", "1,1.5", "3,1,3",
    ])
    def test_malformed_versions_is_422(self, query):
        stored = _versions()
        assert _timeline(stored, query).status_code == 422

    def test_repeated_duplicate_params_is_422(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/readiness/timeline",
            params=[("versions", "1"), ("versions", "1")],
        )
        assert response.status_code == 422

    def test_error_detail_is_plain_string(self):
        stored = _versions()
        detail = _timeline(stored, "1,99").json()["detail"]
        assert isinstance(detail, str)

    def test_nonexistent_version_is_404(self):
        stored = _versions()
        assert _timeline(stored, "1,99").status_code == 404

    def test_deleted_version_is_404(self):
        stored = _versions()
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/2"
        ).status_code == 200
        assert _timeline(stored, "1,2").status_code == 404
        assert _timeline(stored, "2").status_code == 404

    def test_default_after_deletion_skips_deleted_version(self):
        stored = _versions()
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/3"
        ).status_code == 200
        data = _timeline(stored).json()
        assert data["versions_analyzed"] == [1, 2, 4, 5]
        assert data["steps"] == 3

    def test_nonexistent_video_is_404(self):
        assert _timeline("missing.mp4").status_code == 404

    def test_invalid_extension_is_400(self):
        assert _timeline("clip.txt").status_code == 400

    def test_path_traversal_is_404(self):
        response = client.get(
            "/api/videos/../../../etc/passwd/prompt/history/readiness/"
            "timeline"
        )
        assert response.status_code == 404

    def test_missing_version_never_silently_replaced(self):
        stored = _versions()
        listing_before = client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content
        _timeline(stored, "1,99")
        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content == listing_before

    def test_404_detail_matches_day16_message(self):
        stored = _versions()
        detail = _timeline(stored, "99").json()["detail"]
        assert detail == f"Version 99 not found for video '{stored}'."


class TestDeterminism:
    def test_repeated_requests_identical(self):
        stored = _versions()
        assert _timeline(stored).json() == _timeline(stored).json()

    def test_no_timestamps_or_uuids(self):
        stored = _versions()
        text = _timeline(stored).text
        for pat in (r"\d{4}-\d{2}-\d{2}", r"\d{2}:\d{2}"):
            assert not re.search(pat, text)
        assert "uuid" not in text.lower()

    def test_byte_equivalent_text(self):
        stored = _versions()
        assert _timeline(stored).text == _timeline(stored).text

    def test_subset_selection_deterministic(self):
        stored = _versions()
        assert _timeline(stored, "1,3,5").text == \
            _timeline(stored, "1,3,5").text


class TestIntegrity:
    def test_history_listing_unchanged(self):
        stored = _versions()
        before = client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content
        _timeline(stored)
        _timeline(stored, "1,5")
        _timeline(stored, "4,2")
        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content == before, "timeline never creates/deletes versions"

    def test_prompts_unchanged(self):
        stored = _versions()
        before = [client.get(
            f"/api/videos/{stored}/prompt/history/{v}"
        ).content for v in range(1, 6)]
        _timeline(stored, "1,4")
        after = [client.get(
            f"/api/videos/{stored}/prompt/history/{v}"
        ).content for v in range(1, 6)]
        assert before == after

    def test_favorites_tags_org_unchanged(self):
        stored = _versions()
        assert client.post(
            f"/api/videos/{stored}/prompt/history/1/favorite"
        ).status_code == 200
        assert client.post(
            f"/api/videos/{stored}/prompt/history/3/tags",
            json={"tags": ["draft"]},
        ).status_code == 200
        org_before = {
            v: client.get(
                f"/api/videos/{stored}/prompt/history/{v}/organization"
            ).content
            for v in range(1, 6)
        }
        _timeline(stored)
        _timeline(stored, "5,1")
        for v, blob in org_before.items():
            assert client.get(
                f"/api/videos/{stored}/prompt/history/{v}/organization"
            ).content == blob

    def test_export_and_quality_unchanged(self):
        stored = _versions()
        export_before = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).content
        quality_before = _quality(stored, PROMPT).json()
        _timeline(stored, "1,4")
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
        assert "timeline" not in response.json()

    def test_day23_detailed_compare_unchanged(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2/detailed"
        )
        assert response.status_code == 200
        assert "comparison" in response.json()
        assert "timeline" not in response.json()

    def test_day25_and_day27_routes_distinct(self):
        stored = _versions()
        day25 = _analyze(stored)
        day27 = _timeline(stored)
        assert day25.status_code == day27.status_code == 200
        assert set(day25.json().keys()) == DAY25_TOP_KEYS
        assert set(day27.json().keys()) == TOP_KEYS
        assert set(day25.json().keys()) != set(day27.json().keys())

    def test_day26_and_day27_routes_distinct(self):
        stored = _versions()
        day26 = _change(stored, 1, 2)
        day27 = _timeline(stored)
        assert day26.status_code == day27.status_code == 200
        assert set(day26.json().keys()) == DAY26_TOP_KEYS
        assert set(day27.json().keys()) == TOP_KEYS
        assert set(day26.json().keys()) != set(day27.json().keys())

    def test_numeric_route_not_captured_by_timeline_static(self):
        stored = _versions()
        numeric = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        )
        timeline = _timeline(stored)
        assert numeric.status_code == 200
        assert "prompt" in numeric.json()
        assert "prompt" not in timeline.json()
        assert timeline.json()["steps"] == 4

    def test_timeline_static_route_not_captured_by_numeric(self):
        stored = _versions()
        assert _timeline(stored).status_code == 200
        assert _timeline(stored, "1").status_code == 200
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
        assert _readiness(stored, CITY).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/readiness"
        ).status_code == 200


class TestDay16To27Regression:
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
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/readiness"
        ).status_code == 200

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
        data = timeline.json()
        assert set(data.keys()) == TOP_KEYS
        assert data["versions_analyzed"] == [1, 2]
        assert data["steps"] == 1
        assert set(data["timeline"][0].keys()) == DAY26_TOP_KEYS
        assert data["timeline"][0] == _change(stored, 1, 2).json()
        assert set(data["summary"].keys()) == SUMMARY_KEYS
        assert _timeline(stored, "1").json()["steps"] == 0
        assert _timeline(stored, "2,1").json()["versions_analyzed"] == [2, 1]

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
        stored = _versions()
        for query in (None, "1,4", "4,1"):
            text = _timeline(stored, query).text
            for bad in ("C:\\", "C:/", "/home", "/Users", "/var/"):
                assert bad not in text, bad
            for internal in ("_storage", "PromptReadinessTimelineService",
                             "PromptReadinessChangeService",
                             "PromptReadinessService",
                             "PromptQualityService",
                             "PromptHistoryService",
                             "readiness_timeline_service", "Traceback",
                             "os.environ", "api_key", "password",
                             "secret"):
                assert internal not in text, internal

    def test_no_ranking_or_evaluative_language(self):
        stored = _versions()
        text = _timeline(stored, "1,5").text.lower()
        for word in ("best", "worst", "winner", "perfect", "guaranteed",
                     "superior", "inferior", "rank", "recommended",
                     "better", "worse", "improved", "improvement",
                     "gain"):
            assert word not in text, word

    def test_prompt_not_echoed_or_modified(self):
        stored = _versions()
        before = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        ).json()["prompt"]
        text = _timeline(stored, "1,4").text
        assert "film grain style portrait" not in text
        assert before == FULL
        after = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        ).json()["prompt"]
        assert before == after == FULL
