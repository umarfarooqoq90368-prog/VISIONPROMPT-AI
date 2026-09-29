"""API tests for the detailed prompt version comparison endpoint (Day 23)."""
import os

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import DIMENSIONS

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets",
                               "test_video.mp4")

PROMPT = "Cinematic wide shot of the subject, golden hour lighting, slow dolly in."
NEGATIVE = "blurry, low quality, distorted anatomy, unwanted text, watermark"
SPEC_A = "A person walks through a road."
SPEC_B = "A person walks through a road. Medium shot with natural lighting."


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


def _compare(stored, version_a, version_b):
    return client.get(
        f"/api/videos/{stored}/prompt/history/compare/"
        f"{version_a}/{version_b}/detailed"
    )


def _quality(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/quality",
                       json={"prompt": prompt})


def _hquality(stored, version):
    return client.get(f"/api/videos/{stored}/prompt/history/{version}/quality")


def _improve(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/improve",
                       json={"prompt": prompt})


def _himprove(stored, version):
    return client.get(f"/api/videos/{stored}/prompt/history/{version}/improve")


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)


class TestDetailedCompareValidation:
    def test_valid_request_200(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        assert _compare(stored, 1, 2).status_code == 200

    def test_same_version_200_identical(self):
        stored = _upload()
        _save(stored, PROMPT)
        response = _compare(stored, 1, 1)
        assert response.status_code == 200
        assert response.json()["comparison"]["identical"] is True

    @pytest.mark.parametrize("bad", [0, -1])
    def test_version_a_below_one_is_422(self, bad):
        stored = _upload()
        _save(stored, PROMPT)
        assert _compare(stored, bad, 1).status_code == 422

    @pytest.mark.parametrize("bad", [0, -1])
    def test_version_b_below_one_is_422(self, bad):
        stored = _upload()
        _save(stored, PROMPT)
        assert _compare(stored, 1, bad).status_code == 422

    def test_non_integer_version_is_422(self):
        stored = _upload()
        _save(stored, PROMPT)
        response = client.get(
            f"/api/videos/{stored}/prompt/history/compare/abc/1/detailed"
        )
        assert response.status_code == 422

    def test_nonexistent_video_is_404(self):
        assert _compare("does_not_exist.mp4", 1, 2).status_code == 404

    def test_invalid_extension_is_400(self):
        assert _compare("notavideo.txt", 1, 2).status_code == 400

    def test_nonexistent_version_a_is_404(self):
        stored = _upload()
        _save(stored, PROMPT)
        assert _compare(stored, 99, 1).status_code == 404

    def test_nonexistent_version_b_is_404(self):
        stored = _upload()
        _save(stored, PROMPT)
        assert _compare(stored, 1, 99).status_code == 404

    def test_deleted_version_is_404(self):
        stored = _upload()
        _save(stored, "first version prompt")
        _save(stored, "second version prompt")
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/1"
        ).status_code == 200
        assert _compare(stored, 1, 2).status_code == 404

    def test_traversal_is_404(self):
        response = client.get(
            "/api/videos/../secret.mp4/prompt/history/compare/1/1/detailed"
        )
        assert response.status_code == 404


class TestDetailedCompareResults:
    def test_full_schema(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        data = _compare(stored, 1, 2).json()
        assert set(data.keys()) == {
            "video_filename", "version_a", "version_b", "comparison",
        }
        assert data["video_filename"] == stored
        for key in ("version_a", "version_b"):
            assert set(data[key].keys()) == {
                "version", "version_id", "source", "operation",
                "prompt", "quality",
            }
        assert set(data["comparison"].keys()) == {
            "identical", "changed", "added_text", "removed_text",
            "common_text", "quality_score_delta", "quality_score_change",
            "completeness_delta", "completeness_change",
            "changed_dimensions",
        }

    def test_version_order_preserved(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        data = _compare(stored, 2, 1).json()
        assert data["version_a"]["version"] == 2
        assert data["version_b"]["version"] == 1
        assert data["version_a"]["prompt"] == SPEC_B
        assert data["version_b"]["prompt"] == SPEC_A

    def test_diff_text_matches_saved_prompts(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        comp = _compare(stored, 1, 2).json()["comparison"]
        assert comp["changed"] is True
        assert comp["removed_text"] == ""
        assert comp["common_text"] == SPEC_A
        assert comp["added_text"] in SPEC_B

    def test_quality_deltas_match_direct_day21_endpoints(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        qa = _quality(stored, SPEC_A).json()["quality"]
        qb = _quality(stored, SPEC_B).json()["quality"]
        comp = _compare(stored, 1, 2).json()["comparison"]
        assert (comp["quality_score_delta"]
                == qb["overall_score"] - qa["overall_score"])
        assert (comp["completeness_delta"]
                == qb["completeness_percentage"]
                - qa["completeness_percentage"])
        assert comp["quality_score_change"] == "increased"
        assert comp["completeness_change"] == "increased"

    def test_changed_dimensions_match_direct_quality_analysis(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        qa = _quality(stored, SPEC_A).json()["quality"]
        qb = _quality(stored, SPEC_B).json()["quality"]
        expected = []
        for dim in DIMENSIONS:
            if qa["dimensions"][dim] != qb["dimensions"][dim]:
                expected.append({
                    "dimension": dim,
                    "before_present": qa["dimensions"][dim]["present"],
                    "after_present": qb["dimensions"][dim]["present"],
                    "before_score": qa["dimensions"][dim]["score"],
                    "after_score": qb["dimensions"][dim]["score"],
                })
        comp = _compare(stored, 1, 2).json()["comparison"]
        assert comp["changed_dimensions"] == expected
        assert [c["dimension"] for c in comp["changed_dimensions"]] == [
            "camera", "lighting",
        ]

    def test_summaries_embed_direct_quality_reports(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        data = _compare(stored, 1, 2).json()
        assert (data["version_a"]["quality"]
                == _hquality(stored, 1).json()["quality"])
        assert (data["version_b"]["quality"]
                == _hquality(stored, 2).json()["quality"])

    def test_identical_versions_have_zero_deltas(self):
        stored = _upload()
        _save(stored, PROMPT)
        comp = _compare(stored, 1, 1).json()["comparison"]
        assert comp["identical"] is True
        assert comp["changed"] is False
        assert comp["quality_score_delta"] == 0
        assert comp["completeness_delta"] == 0
        assert comp["changed_dimensions"] == []

    def test_metadata_preserved_in_summaries(self):
        stored = _upload()
        _save(stored, SPEC_A, source="refinement", operation="cinematic")
        _save(stored, SPEC_B)
        data = _compare(stored, 1, 2).json()
        assert data["version_a"]["source"] == "refinement"
        assert data["version_a"]["operation"] == "cinematic"
        assert (data["version_a"]["version_id"]
                == f"{stored}:1")


class TestDeterminism:
    def test_repeated_requests_identical(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        first = _compare(stored, 1, 2).json()
        second = _compare(stored, 1, 2).json()
        third = _compare(stored, 1, 2).json()
        assert first == second == third

    def test_no_timestamps_in_response(self):
        import re
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        text = str(_compare(stored, 1, 2).json())
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", text)
        assert "uuid" not in text.lower()


class TestReadOnly:
    def test_history_and_organization_unchanged(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        assert client.post(
            f"/api/videos/{stored}/prompt/history/1/favorite"
        ).status_code == 200
        assert client.post(
            f"/api/videos/{stored}/prompt/history/2/tags",
            json={"tags": ["review"]},
        ).json()["tags"] == ["review"]

        listing_before = client.get(
            f"/api/videos/{stored}/prompt/history"
        ).json()
        org1_before = client.get(
            f"/api/videos/{stored}/prompt/history/1/organization"
        ).json()
        export_before = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).content

        _compare(stored, 1, 2)
        _compare(stored, 2, 1)
        _compare(stored, 1, 1)

        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).json() == listing_before
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/organization"
        ).json() == org1_before
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).content == export_before

    def test_comparison_does_not_create_versions(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        _compare(stored, 1, 2)
        _compare(stored, 2, 1)
        versions = client.get(
            f"/api/videos/{stored}/prompt/history"
        ).json()["versions"]
        assert [v["version"] for v in versions] == [1, 2]


class TestRouteCollision:
    def test_day16_compare_route_unchanged(self):
        stored = _upload()
        _save(stored, SPEC_A)
        _save(stored, SPEC_B)
        old = client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2"
        )
        assert old.status_code == 200
        data = old.json()
        assert "added_tokens" in data
        assert "removed_tokens" in data
        assert "comparison" not in data
        # detailed route is a different response
        new = _compare(stored, 1, 2)
        assert new.status_code == 200
        assert "comparison" in new.json()

    def test_numeric_version_route_still_resolves(self):
        stored = _upload()
        created = _save(stored, PROMPT)
        version = created["version"]
        response = client.get(
            f"/api/videos/{stored}/prompt/history/{version}"
        )
        assert response.status_code == 200
        assert response.json()["prompt"] == PROMPT

    def test_other_history_routes_still_resolve(self):
        stored = _upload()
        created = _save(stored, PROMPT)
        version = created["version"]
        assert client.post(
            f"/api/videos/{stored}/prompt/history/{version}/favorite"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/organization"
        ).status_code == 200
        assert _hquality(stored, version).status_code == 200
        assert _himprove(stored, version).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "json"},
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/package"
        ).status_code == 200


class TestDay16To22Regression:
    def test_all_previous_features_still_work(self):
        stored = _upload()
        created = _save(stored)
        version = created["version"]
        _save(stored, SPEC_B)

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
        hv = _hquality(stored, version)
        assert hv.status_code == 200

        # Day 22 improve
        assert _improve(stored, PROMPT).status_code == 200
        assert _himprove(stored, version).status_code == 200

        # Day 23 detailed comparison
        detailed = _compare(stored, 1, 2)
        assert detailed.status_code == 200
        assert detailed.json()["comparison"]["changed"] is True

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
