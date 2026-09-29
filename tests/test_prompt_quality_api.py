"""API tests for the prompt quality analyzer endpoints (Day 21)."""
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

DETAILED = (
    "Cinematic film grain style portrait of a person, the subject "
    "walking, looking around and gesturing in an outdoor forest street, "
    "camera tracking with shallow depth of field, soft lighting with rim "
    "light and golden hour glow, vibrant teal and orange palette with "
    "warm tones, layered foreground and rule of thirds composition, "
    "ambient sound with quiet music score."
)


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


def _quality(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/quality",
                       json={"prompt": prompt})


def _version_quality(stored, version):
    return client.get(
        f"/api/videos/{stored}/prompt/history/{version}/quality"
    )


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)


class TestQualityEndpointValidation:
    def test_missing_body_is_422(self):
        stored = _upload()
        response = client.post(f"/api/videos/{stored}/prompt/quality")
        assert response.status_code == 422

    def test_missing_prompt_field_is_422(self):
        stored = _upload()
        response = client.post(f"/api/videos/{stored}/prompt/quality", json={})
        assert response.status_code == 422

    @pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
    def test_empty_or_whitespace_prompt_is_422(self, bad):
        stored = _upload()
        response = _quality(stored, bad)
        assert response.status_code == 422

    @pytest.mark.parametrize("bad", [None, 42, ["a"], {"a": 1}, True])
    def test_non_string_prompt_is_422(self, bad):
        stored = _upload()
        response = _quality(stored, bad)
        assert response.status_code == 422

    def test_nonexistent_video_is_404(self):
        response = _quality("does_not_exist.mp4", "a portrait of a person")
        assert response.status_code == 404

    def test_invalid_extension_is_400(self):
        response = _quality("notavideo.txt", "a portrait of a person")
        assert response.status_code == 400

    def test_traversal_is_404(self):
        response = client.post("/api/videos/../secret.mp4/prompt/quality",
                               json={"prompt": "a portrait"})
        assert response.status_code == 404


class TestQualityEndpointResults:
    def test_detailed_prompt_200_full_structure(self):
        stored = _upload()
        response = _quality(stored, DETAILED)
        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] == DETAILED
        quality = data["quality"]
        assert set(quality.keys()) == {
            "overall_score",
            "completeness_percentage",
            "dimensions",
            "missing_dimensions",
            "suggestions",
        }
        assert list(quality["dimensions"].keys()) == list(DIMENSIONS)
        for dim in DIMENSIONS:
            entry = quality["dimensions"][dim]
            assert type(entry["present"]) is bool
            assert type(entry["score"]) is int
            assert 0 <= entry["score"] <= 100
        assert quality["missing_dimensions"] == []
        assert quality["suggestions"] == []
        assert quality["overall_score"] == 100
        assert quality["completeness_percentage"] == 100

    def test_short_prompt_200_all_missing(self):
        stored = _upload()
        data = _quality(stored, "Hello world.").json()
        quality = data["quality"]
        assert quality["missing_dimensions"] == list(DIMENSIONS)
        assert quality["overall_score"] == 0
        assert quality["completeness_percentage"] == 0
        assert len(quality["suggestions"]) == len(DIMENSIONS)

    def test_quality_does_not_require_history(self):
        stored = _upload()
        response = _quality(stored, "a portrait of a person")
        assert response.status_code == 200

    def test_deterministic_across_calls(self):
        stored = _upload()
        first = _quality(stored, DETAILED).json()
        second = _quality(stored, DETAILED).json()
        assert first == second

    def test_response_echoes_prompt_exactly(self):
        stored = _upload()
        original = "  Mixed   CASE\ntext  "
        data = _quality(stored, original).json()
        assert data["prompt"] == original

    def test_response_has_no_internal_details(self):
        stored = _upload()
        text = _quality(stored, DETAILED).text
        for forbidden in ("PromptQualityService", "Traceback",
                          "Internal Server", "_storage"):
            assert forbidden not in text


class TestHistoryQualityEndpoint:
    def test_existing_version_200_same_structure(self):
        stored = _upload()
        created = _save(stored)
        response = _version_quality(stored, created["version"])
        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] == PROMPT
        assert set(data["quality"].keys()) == {
            "overall_score",
            "completeness_percentage",
            "dimensions",
            "missing_dimensions",
            "suggestions",
        }
        assert list(data["quality"]["dimensions"].keys()) == list(DIMENSIONS)

    def test_nonexistent_version_404(self):
        stored = _upload()
        assert _version_quality(stored, 99).status_code == 404

    def test_deleted_version_404(self):
        stored = _upload()
        created = _save(stored)
        delete = client.delete(
            f"/api/videos/{stored}/prompt/history/{created['version']}"
        )
        assert delete.status_code == 200
        assert _version_quality(stored, created["version"]).status_code == 404

    def test_version_zero_is_422(self):
        stored = _upload()
        assert _version_quality(stored, 0).status_code == 422

    def test_missing_video_404(self):
        assert _version_quality("missing_video.mp4", 1).status_code == 404

    def test_quality_analysis_does_not_modify_history(self):
        stored = _upload()
        created = _save(stored)
        version = created["version"]

        favorite = client.post(
            f"/api/videos/{stored}/prompt/history/{version}/favorite"
        )
        assert favorite.status_code == 200

        before = client.get(
            f"/api/videos/{stored}/prompt/history/{version}"
        ).json()
        _quality(stored, DETAILED)
        _version_quality(stored, version)
        after = client.get(
            f"/api/videos/{stored}/prompt/history/{version}"
        ).json()
        assert before == after

        versions = client.get(f"/api/videos/{stored}/prompt/history").json()
        assert len(versions["versions"]) == 1

        org = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/organization"
        ).json()
        assert org["favorite"] is True


class TestDay16To20Regression:
    def test_history_org_search_export_package_still_work(self):
        stored = _upload()
        created = _save(stored)
        version = created["version"]

        # Day 16 history
        listing = client.get(f"/api/videos/{stored}/prompt/history")
        assert listing.status_code == 200
        assert len(listing.json()["versions"]) == 1

        # Day 17 organization
        org = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/organization"
        )
        assert org.status_code == 200
        assert org.json()["favorite"] is False

        # Day 18 search
        search = client.get(f"/api/videos/{stored}/prompt/search",
                            params={"query": "cinematic"})
        assert search.status_code == 200
        assert search.json()["count"] >= 1

        # Day 19 export
        export = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "json"},
        )
        assert export.status_code == 200

        # Day 20 package
        package = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/package"
        )
        assert package.status_code == 200
        assert package.headers["content-type"] == "application/zip"

        # Day 21 quality does not break any of the above
        assert _quality(stored, PROMPT).status_code == 200
        assert _version_quality(stored, version).status_code == 200

        export_again = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "json"},
        )
        assert export_again.status_code == 200
        assert export_again.content == export.content

    def test_version_routes_still_resolve_after_quality_routes(self):
        stored = _upload()
        created = _save(stored)
        version = created["version"]
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/quality"
        ).status_code == 200
