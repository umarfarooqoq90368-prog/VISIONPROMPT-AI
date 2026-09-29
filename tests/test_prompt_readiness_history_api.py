"""API tests for the prompt readiness history analysis endpoint (Day 25)."""
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
REQ_ONLY = ("Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, camera tracking with shallow depth of field, soft "
            "lighting with rim light and golden hour glow, layered "
            "foreground and rule of thirds composition.")
CITY = "A person walks through a city street."
WEAK_CAM = ("Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, tracking only, soft lighting with rim light and "
            "golden hour glow, vibrant teal and orange palette with warm "
            "tones, layered foreground and rule of thirds composition, "
            "ambient sound with quiet music score.")


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


def _analyze(stored, params=None):
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness", params=params
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


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)


def _four_versions(stored=None):
    """Upload a video and save the standard 4-version set."""
    stored = stored or _upload()
    for prompt in (FULL, CITY, REQ_ONLY, WEAK_CAM):
        _save(stored, prompt)
    return stored


class TestEndpointBasics:
    def test_no_query_analyzes_all_versions(self):
        stored = _four_versions()
        response = _analyze(stored)
        assert response.status_code == 200
        assert response.json()["versions_analyzed"] == [1, 2, 3, 4]

    def test_top_level_keys(self):
        stored = _four_versions()
        assert set(_analyze(stored).json().keys()) == {
            "video_filename", "versions_analyzed", "results", "summary",
            "dimension_summary",
        }

    def test_video_filename_echo(self):
        stored = _four_versions()
        assert _analyze(stored).json()["video_filename"] == stored

    def test_results_count_matches_versions(self):
        stored = _four_versions()
        data = _analyze(stored).json()
        assert len(data["results"]) == len(data["versions_analyzed"])
        assert len(data["results"]) == 4

    def test_video_without_versions_returns_empty_200(self):
        stored = _upload()
        response = _analyze(stored)
        assert response.status_code == 200
        data = response.json()
        assert data["versions_analyzed"] == []
        assert data["results"] == []
        assert data["summary"]["versions_analyzed"] == 0
        assert data["summary"]["required_coverage_percentage"] == 0
        assert len(data["dimension_summary"]) == len(DIMENSIONS)

    def test_each_result_keys(self):
        stored = _four_versions()
        for item in _analyze(stored).json()["results"]:
            assert set(item.keys()) == {
                "version", "version_id", "source", "operation", "readiness",
            }
            assert item["version_id"] == f"{stored}:{item['version']}"


class TestVersionsQuery:
    def test_selected_versions_comma_separated(self):
        stored = _four_versions()
        data = _analyze(stored, {"versions": "1,3"}).json()
        assert data["versions_analyzed"] == [1, 3]

    def test_single_version(self):
        stored = _four_versions()
        assert _analyze(stored, {"versions": "2"}).json()[
            "versions_analyzed"] == [2]

    def test_whitespace_tolerated_between_parts(self):
        stored = _four_versions()
        assert _analyze(stored, {"versions": " 1 , 3 "}).json()[
            "versions_analyzed"] == [1, 3]

    def test_repeated_query_params_supported(self):
        stored = _four_versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/readiness",
            params=[("versions", "1"), ("versions", "3")],
        )
        assert response.status_code == 200
        assert response.json()["versions_analyzed"] == [1, 3]

    def test_requested_order_preserved(self):
        stored = _four_versions()
        assert _analyze(stored, {"versions": "4,2"}).json()[
            "versions_analyzed"] == [4, 2]

    @pytest.mark.parametrize("bad", [
        "", "0", "-1", "abc", "1,,2", "1,1", "1.5", ",", "2,2",
        " ", "0,1", "1;2", "+2",
    ])
    def test_invalid_versions_query_is_422(self, bad):
        stored = _four_versions()
        response = _analyze(stored, {"versions": bad})
        assert response.status_code == 422, bad

    def test_selected_version_results_equal_all_results(self):
        stored = _four_versions()
        everything = {r["version"]: r
                      for r in _analyze(stored).json()["results"]}
        chosen = _analyze(stored, {"versions": "4,2"}).json()["results"]
        assert chosen == [everything[4], everything[2]]


class TestErrorCases:
    def test_nonexistent_video_is_404(self):
        assert _analyze("missing.mp4").status_code == 404

    def test_invalid_extension_is_400(self):
        assert _analyze("clip.txt").status_code == 400

    def test_path_traversal_is_404(self):
        assert _analyze("..%2Fsecret.mp4").status_code == 404

    def test_nonexistent_version_is_404(self):
        stored = _four_versions()
        assert _analyze(stored, {"versions": "99"}).status_code == 404

    def test_deleted_version_is_404(self):
        stored = _four_versions()
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/2"
        ).status_code == 200
        assert _analyze(stored, {"versions": "2"}).status_code == 404

    def test_deleted_version_still_analyzed_for_remaining(self):
        stored = _four_versions()
        client.delete(f"/api/videos/{stored}/prompt/history/2")
        data = _analyze(stored).json()
        assert data["versions_analyzed"] == [1, 3, 4]
        assert data["summary"]["versions_analyzed"] == 3

    def test_error_detail_is_plain_string(self):
        stored = _four_versions()
        detail = _analyze(stored, {"versions": "99"}).json()["detail"]
        assert isinstance(detail, str)


class TestAnalysisResults:
    @pytest.mark.parametrize("version,expected", [
        (1, "ready"), (2, "needs_attention"), (3, "ready"),
        (4, "needs_attention"),
    ])
    def test_status_per_version(self, version, expected):
        stored = _four_versions()
        data = _analyze(stored, {"versions": str(version)}).json()
        assert data["results"][0]["readiness"]["status"] == expected

    @pytest.mark.parametrize("index,prompt", [
        (1, FULL), (2, CITY), (3, REQ_ONLY), (4, WEAK_CAM),
    ])
    def test_result_readiness_equals_post_readiness(
        self, index, prompt
    ):
        stored = _four_versions()
        analyzed = _analyze(stored, {"versions": str(index)}).json()
        direct = _readiness(stored, prompt).json()["readiness"]
        assert analyzed["results"][0]["readiness"] == direct

    @pytest.mark.parametrize("version", [1, 2, 3, 4])
    def test_result_readiness_equals_day24_history_readiness(
        self, version
    ):
        stored = _four_versions()
        analyzed = _analyze(stored, {"versions": str(version)}).json()
        assert (analyzed["results"][0]["readiness"]
                == _hreadiness(stored, version).json()["readiness"])

    def test_summary_counts(self):
        stored = _four_versions()
        summary = _analyze(stored).json()["summary"]
        assert summary["versions_analyzed"] == 4
        assert summary["ready_count"] == 2
        assert summary["needs_attention_count"] == 2

    def test_summary_aggregate_numbers(self):
        stored = _four_versions()
        summary = _analyze(stored).json()["summary"]
        assert summary["required_dimensions_total"] == 28
        assert summary["required_dimensions_present"] == 21
        assert summary["required_dimensions_weak"] == 2
        assert summary["required_dimensions_missing"] == 5
        assert summary["required_coverage_percentage"] == round(
            21 / 28 * 100
        )
        assert summary["supporting_dimensions_total"] == 8
        assert summary["supporting_dimensions_present"] == 4
        assert summary["supporting_dimensions_missing"] == 4

    def test_summary_counts_sum_consistently(self):
        stored = _four_versions()
        summary = _analyze(stored).json()["summary"]
        assert (summary["required_dimensions_present"]
                + summary["required_dimensions_weak"]
                + summary["required_dimensions_missing"]) == 28
        assert (summary["ready_count"]
                + summary["needs_attention_count"]) == 4

    def test_dimension_summary_order_and_sums(self):
        stored = _four_versions()
        dims = _analyze(stored).json()["dimension_summary"]
        assert [d["dimension"] for d in dims] == list(DIMENSIONS)
        for entry in dims:
            assert (entry["present_count"] + entry["weak_count"]
                    + entry["missing_count"]) == 4

    def test_dimension_summary_camera_counts(self):
        stored = _four_versions()
        dims = _analyze(stored).json()["dimension_summary"]
        camera = next(d for d in dims if d["dimension"] == "camera")
        assert (camera["present_count"], camera["weak_count"],
                camera["missing_count"]) == (2, 1, 1)

    def test_selected_subset_changes_summary(self):
        stored = _four_versions()
        summary = _analyze(stored, {"versions": "1,2"}).json()["summary"]
        assert summary["versions_analyzed"] == 2
        assert summary["ready_count"] == 1
        assert summary["required_dimensions_total"] == 14
        assert summary["required_dimensions_present"] == 8

    def test_supporting_missing_version_still_ready(self):
        stored = _four_versions()
        data = _analyze(stored, {"versions": "3"}).json()
        assert data["results"][0]["readiness"]["status"] == "ready"
        assert data["summary"]["ready_count"] == 1

    def test_response_contains_no_prompt_text(self):
        stored = _four_versions()
        text = _analyze(stored).text
        for fragment in ("Cinematic film grain", "city street"):
            assert fragment not in text, fragment


class TestDeterminism:
    def test_repeated_requests_identical(self):
        stored = _four_versions()
        first = _analyze(stored).json()
        second = _analyze(stored).json()
        third = _analyze(stored, {"versions": "1,3"}).json()
        assert first == second
        assert third == _analyze(stored, {"versions": "1,3"}).json()

    def test_case_insensitive_status_consistent(self):
        stored = _upload()
        _save(stored, CITY)
        _save(stored, CITY.upper())
        first = _analyze(stored, {"versions": "1"}).json()
        second = _analyze(stored, {"versions": "2"}).json()
        assert (first["results"][0]["readiness"]["status"]
                == second["results"][0]["readiness"]["status"])
        assert (first["results"][0]["readiness"]["coverage"]
                == second["results"][0]["readiness"]["coverage"])

    def test_no_timestamps_or_uuids(self):
        stored = _four_versions()
        text = _analyze(stored).text
        for pat in (r"\d{4}-\d{2}-\d{2}", r"\d{2}:\d{2}"):
            assert not re.search(pat, text)
        assert "uuid" not in text.lower()


class TestReadOnlyIntegrity:
    def test_history_listing_unchanged(self):
        stored = _four_versions()
        before = client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content
        _analyze(stored)
        _analyze(stored, {"versions": "2,4"})
        assert (client.get(
            f"/api/videos/{stored}/prompt/history"
        ).content == before)

    def test_export_content_unchanged(self):
        stored = _four_versions()
        export_before = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).content
        _analyze(stored)
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).content == export_before

    def test_favorites_and_tags_unchanged(self):
        stored = _four_versions()
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
            for v in (1, 2, 3, 4)
        }

        _analyze(stored)

        for v, blob in org_before.items():
            assert client.get(
                f"/api/videos/{stored}/prompt/history/{v}/organization"
            ).content == blob

    def test_prompt_text_unchanged(self):
        stored = _four_versions()
        before = client.get(
            f"/api/videos/{stored}/prompt/history/2"
        ).json()["prompt"]
        _analyze(stored, {"versions": "2"})
        after = client.get(
            f"/api/videos/{stored}/prompt/history/2"
        ).json()["prompt"]
        assert before == after == CITY

    def test_quality_report_unchanged(self):
        stored = _four_versions()
        quality_before = _quality(stored, PROMPT).json()
        _analyze(stored)
        assert _quality(stored, PROMPT).json() == quality_before


class TestRouteCollision:
    def test_numeric_version_route_still_resolves(self):
        stored = _four_versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        )
        assert response.status_code == 200
        assert response.json()["prompt"] == FULL

    def test_numeric_delete_route_still_resolves(self):
        stored = _four_versions()
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/4"
        ).status_code == 200

    def test_day24_history_readiness_route_still_resolves(self):
        stored = _four_versions()
        assert _hreadiness(stored, 1).status_code == 200
        assert _readiness(stored, CITY).status_code == 200

    def test_other_history_routes_still_resolve(self):
        stored = _four_versions()
        assert client.post(
            f"/api/videos/{stored}/prompt/history/1/favorite"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/organization"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/quality"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/improve"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/package"
        ).status_code == 200

    def test_static_history_routes_still_resolve(self):
        stored = _four_versions()
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
            f"/api/videos/{stored}/prompt/history/compare/1/2"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2/detailed"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/search"
        ).status_code == 200

    def test_post_routes_still_resolve(self):
        stored = _four_versions()
        assert _quality(stored, PROMPT).status_code == 200
        assert client.post(
            f"/api/videos/{stored}/prompt/improve",
            json={"prompt": PROMPT},
        ).status_code == 200
        assert client.post(
            f"/api/videos/{stored}/prompt/readiness",
            json={"prompt": CITY},
        ).status_code == 200


class TestDay16To24Regression:
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
        compare = client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/1"
        )
        assert compare.status_code == 200

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
            export = client.get(
                f"/api/videos/{stored}/prompt/history/{version}/export",
                params={"format": fmt},
            )
            assert export.status_code == 200, fmt
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
        assert set(quality.json()["quality"].keys()) == {
            "overall_score", "completeness_percentage", "dimensions",
            "missing_dimensions", "suggestions",
        }
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

        # Day 25 readiness history analysis
        analysis = _analyze(stored)
        assert analysis.status_code == 200
        assert analysis.json()["versions_analyzed"] == [1, 2]
        selected = _analyze(stored, {"versions": "2,1"})
        assert selected.status_code == 200
        assert selected.json()["versions_analyzed"] == [2, 1]
        assert selected.json()["summary"]["versions_analyzed"] == 2

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
        stored = _four_versions()
        text = _analyze(stored).text
        for bad in ("C:\\", "C:/", "/home", "/Users", "/var/"):
            assert bad not in text, bad
        for internal in ("_storage", "PromptReadinessHistoryService",
                         "PromptReadinessService", "PromptQualityService",
                         "PromptHistoryService", "Traceback",
                         "os.environ", "api_key", "password", "secret"):
            assert internal not in text, internal

    def test_no_ranking_language(self):
        stored = _four_versions()
        text = _analyze(stored).text.lower()
        for word in ("best", "worst", "winner", "perfect", "guaranteed",
                     "superior", "inferior", "rank", "recommended"):
            assert word not in text, word

    def test_prompt_not_modified_by_analysis(self):
        stored = _four_versions()
        before = client.get(
            f"/api/videos/{stored}/prompt/history/3"
        ).json()["prompt"]
        _analyze(stored, {"versions": "3"})
        after = client.get(
            f"/api/videos/{stored}/prompt/history/3"
        ).json()["prompt"]
        assert before == after == REQ_ONLY
