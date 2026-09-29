"""API tests for the production readiness validator endpoints (Day 24)."""
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


def _readiness(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/readiness",
                       json={"prompt": prompt})


def _hreadiness(stored, version):
    return client.get(
        f"/api/videos/{stored}/prompt/history/{version}/readiness"
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


class TestReadinessValidation:
    def test_missing_body_is_422(self):
        stored = _upload()
        assert client.post(
            f"/api/videos/{stored}/prompt/readiness"
        ).status_code == 422

    def test_missing_prompt_field_is_422(self):
        stored = _upload()
        assert client.post(f"/api/videos/{stored}/prompt/readiness",
                           json={}).status_code == 422

    @pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
    def test_empty_or_whitespace_prompt_is_422(self, bad):
        stored = _upload()
        assert _readiness(stored, bad).status_code == 422

    @pytest.mark.parametrize("bad", [None, 42, ["a"], {"a": 1}, True])
    def test_non_string_prompt_is_422(self, bad):
        stored = _upload()
        assert _readiness(stored, bad).status_code == 422

    def test_nonexistent_video_is_404(self):
        assert _readiness("does_not_exist.mp4", CITY).status_code == 404

    def test_invalid_extension_is_400(self):
        assert _readiness("notavideo.txt", CITY).status_code == 400

    def test_traversal_is_404(self):
        response = client.post("/api/videos/../secret.mp4/prompt/readiness",
                               json={"prompt": CITY})
        assert response.status_code == 404


class TestHistoryReadinessValidation:
    @pytest.mark.parametrize("bad", [0, -1])
    def test_version_below_one_is_422(self, bad):
        stored = _upload()
        _save(stored, CITY)
        assert _hreadiness(stored, bad).status_code == 422

    def test_non_integer_version_is_422(self):
        stored = _upload()
        _save(stored, CITY)
        response = client.get(
            f"/api/videos/{stored}/prompt/history/abc/readiness"
        )
        assert response.status_code == 422

    def test_nonexistent_version_is_404(self):
        stored = _upload()
        _save(stored, CITY)
        assert _hreadiness(stored, 99).status_code == 404

    def test_deleted_version_is_404(self):
        stored = _upload()
        _save(stored, "first version prompt")
        _save(stored, "second version prompt")
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/1"
        ).status_code == 200
        assert _hreadiness(stored, 1).status_code == 404

    def test_nonexistent_video_is_404(self):
        assert _hreadiness("missing_video.mp4", 1).status_code == 404

    def test_traversal_is_404(self):
        response = client.get(
            "/api/videos/../secret.mp4/prompt/history/1/readiness"
        )
        assert response.status_code == 404


class TestReadinessResults:
    def test_full_response_schema(self):
        stored = _upload()
        response = _readiness(stored, FULL)
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"video_filename", "prompt", "readiness"}
        assert data["video_filename"] == stored
        assert data["prompt"] == FULL, "prompt echoed exactly"
        readiness = data["readiness"]
        assert set(readiness.keys()) == {
            "status", "required_dimensions", "supporting_dimensions",
            "checklist", "coverage", "missing_dimensions",
            "weak_dimensions", "suggestions",
        }

    def test_fully_covered_prompt_is_ready(self):
        stored = _upload()
        readiness = _readiness(stored, FULL).json()["readiness"]
        assert readiness["status"] == "ready"
        cov = readiness["coverage"]
        assert cov["required_present"] == 7
        assert cov["required_coverage_percentage"] == 100
        assert readiness["missing_dimensions"] == []
        assert readiness["weak_dimensions"] == []
        assert readiness["suggestions"] == []

    def test_city_prompt_needs_attention(self):
        stored = _upload()
        readiness = _readiness(stored, CITY).json()["readiness"]
        assert readiness["status"] == "needs_attention"
        assert readiness["weak_dimensions"] == ["subject"]
        assert readiness["coverage"]["required_coverage_percentage"] == 14

    def test_supporting_missing_stays_ready(self):
        stored = _upload()
        readiness = _readiness(stored, REQ_ONLY).json()["readiness"]
        assert readiness["status"] == "ready"
        cov = readiness["coverage"]
        assert cov["required_coverage_percentage"] == 100
        assert cov["supporting_missing"] == 2
        assert "color" in readiness["missing_dimensions"]
        assert "audio" in readiness["missing_dimensions"]

    def test_required_and_supporting_lists(self):
        stored = _upload()
        readiness = _readiness(stored, CITY).json()["readiness"]
        assert readiness["required_dimensions"] == [
            "subject", "action", "environment", "camera", "lighting",
            "visual_style", "composition",
        ]
        assert readiness["supporting_dimensions"] == ["color", "audio"]

    def test_checklist_covers_all_dimensions_in_day21_order(self):
        stored = _upload()
        readiness = _readiness(stored, CITY).json()["readiness"]
        assert [c["dimension"] for c in readiness["checklist"]] == \
            list(DIMENSIONS)
        for item in readiness["checklist"]:
            assert set(item.keys()) == {
                "dimension", "status", "present", "score", "message",
            }
            assert item["status"] in ("present", "weak", "missing")

    def test_coverage_matches_direct_day21_analysis(self):
        stored = _upload()
        readiness = _readiness(stored, CITY).json()["readiness"]
        day21 = _quality(stored, CITY).json()["quality"]
        required = readiness["required_dimensions"]
        present = sum(
            1 for dim in required
            if day21["dimensions"][dim]["score"] >= 70
        )
        weak = sum(
            1 for dim in required
            if day21["dimensions"][dim]["score"] == 40
        )
        missing = sum(
            1 for dim in required
            if day21["dimensions"][dim]["score"] == 0
        )
        cov = readiness["coverage"]
        assert cov["required_present"] == present
        assert cov["required_weak"] == weak
        assert cov["required_missing"] == missing
        assert cov["required_coverage_percentage"] == round(
            present / 7 * 100
        )
        for item in readiness["checklist"]:
            assert item["score"] == day21["dimensions"][
                item["dimension"]]["score"]

    def test_suggestions_exact_for_city(self):
        stored = _upload()
        readiness = _readiness(stored, CITY).json()["readiness"]
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

    def test_does_not_require_history(self):
        stored = _upload()
        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).json()["versions"] == []
        assert _readiness(stored, CITY).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).json()["versions"] == [], "readiness never saves into history"


class TestHistoryReadinessEndpoint:
    def test_valid_version_200(self):
        stored = _upload()
        created = _save(stored, CITY)
        response = _hreadiness(stored, created["version"])
        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] == CITY
        assert data["readiness"]["status"] == "needs_attention"
        assert data["video_filename"] == stored

    def test_history_readiness_matches_post_readiness(self):
        stored = _upload()
        created = _save(stored, CITY)
        via_history = _hreadiness(stored, created["version"]).json()
        via_post = _readiness(stored, CITY).json()
        assert via_history == via_post, "same report for same prompt"

    def test_history_unchanged_before_and_after(self):
        stored = _upload()
        created = _save(stored, CITY)
        version = created["version"]
        record_before = client.get(
            f"/api/videos/{stored}/prompt/history/{version}"
        ).json()
        listing_before = client.get(
            f"/api/videos/{stored}/prompt/history"
        ).json()
        org_before = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/organization"
        ).json()
        export_before = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "json"},
        ).content

        _hreadiness(stored, version)
        _readiness(stored, CITY)
        _readiness(stored, FULL)

        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}"
        ).json() == record_before
        assert client.get(
            f"/api/videos/{stored}/prompt/history"
        ).json() == listing_before
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/organization"
        ).json() == org_before
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "json"},
        ).content == export_before


class TestDeterminism:
    def test_repeated_requests_identical(self):
        stored = _upload()
        first = _readiness(stored, CITY).json()
        second = _readiness(stored, CITY).json()
        third = _readiness(stored, CITY).json()
        assert first == second == third

    def test_repeated_history_requests_identical(self):
        stored = _upload()
        _save(stored, CITY)
        first = _hreadiness(stored, 1).json()
        second = _hreadiness(stored, 1).json()
        assert first == second

    def test_case_insensitive_status_consistent(self):
        stored = _upload()
        lower = _readiness(stored, CITY).json()["readiness"]
        upper = _readiness(stored, CITY.upper()).json()["readiness"]
        assert lower["status"] == upper["status"]
        assert lower["coverage"] == upper["coverage"]
        assert lower["checklist"] == upper["checklist"]

    def test_no_timestamps_or_uuids(self):
        import re
        stored = _upload()
        text = str(_readiness(stored, FULL).json())
        for pat in (r"\d{4}-\d{2}-\d{2}", r"\d{2}:\d{2}"):
            assert not re.search(pat, text)
        assert "uuid" not in text.lower()


class TestRouteCollision:
    def test_numeric_version_route_still_resolves(self):
        stored = _upload()
        created = _save(stored, PROMPT)
        response = client.get(
            f"/api/videos/{stored}/prompt/history/{created['version']}"
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
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/quality"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/improve"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "json"},
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/package"
        ).status_code == 200

    def test_post_routes_still_resolve(self):
        stored = _upload()
        _save(stored, PROMPT)
        assert _quality(stored, PROMPT).status_code == 200
        assert client.post(
            f"/api/videos/{stored}/prompt/improve",
            json={"prompt": PROMPT},
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/search"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/1"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/1/detailed"
        ).status_code == 200
        assert client.post(
            f"/api/videos/{stored}/prompt/readiness",
            json={"prompt": CITY},
        ).status_code == 200


class TestDay16To23Regression:
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
        stored = _upload()
        _save(stored, CITY)
        blobs = [
            _readiness(stored, FULL).text,
            _readiness(stored, CITY).text,
            _hreadiness(stored, 1).text,
        ]
        for blob in blobs:
            for bad in ("C:\\", "C:/", "/home", "/Users", "/var/"):
                assert bad not in blob, bad
            for internal in ("_storage", "PromptReadinessService",
                             "PromptQualityService",
                             "PromptHistoryService", "Traceback",
                             "os.environ", "api_key", "password",
                             "secret"):
                assert internal not in blob, internal

    def test_prompt_not_modified_by_readiness_call(self):
        stored = _upload()
        _save(stored, CITY)
        before = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        ).json()["prompt"]
        _hreadiness(stored, 1)
        after = client.get(
            f"/api/videos/{stored}/prompt/history/1"
        ).json()["prompt"]
        assert before == after == CITY
