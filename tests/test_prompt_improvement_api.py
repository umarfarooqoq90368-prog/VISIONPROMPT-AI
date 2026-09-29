"""API tests for the prompt improvement endpoints (Day 22)."""
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
SOURCE = "A person walks down a road."


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


def _improve(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/improve",
                       json={"prompt": prompt})


def _himprove(stored, version):
    return client.get(
        f"/api/videos/{stored}/prompt/history/{version}/improve"
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


class TestImproveEndpointValidation:
    def test_missing_body_is_422(self):
        stored = _upload()
        assert client.post(
            f"/api/videos/{stored}/prompt/improve"
        ).status_code == 422

    def test_missing_prompt_field_is_422(self):
        stored = _upload()
        assert client.post(f"/api/videos/{stored}/prompt/improve",
                           json={}).status_code == 422

    @pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
    def test_empty_or_whitespace_prompt_is_422(self, bad):
        stored = _upload()
        assert _improve(stored, bad).status_code == 422

    @pytest.mark.parametrize("bad", [None, 42, ["a"], {"a": 1}, True])
    def test_non_string_prompt_is_422(self, bad):
        stored = _upload()
        assert _improve(stored, bad).status_code == 422

    def test_nonexistent_video_is_404(self):
        assert _improve("does_not_exist.mp4",
                        SOURCE).status_code == 404

    def test_invalid_extension_is_400(self):
        assert _improve("notavideo.txt", SOURCE).status_code == 400

    def test_traversal_is_404(self):
        response = client.post("/api/videos/../secret.mp4/prompt/improve",
                               json={"prompt": SOURCE})
        assert response.status_code == 404


class TestImproveEndpointResults:
    def test_valid_request_200_full_schema(self):
        stored = _upload()
        response = _improve(stored, SOURCE)
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {
            "video_filename",
            "source_prompt",
            "improved_prompt",
            "quality_before",
            "quality_after",
            "improvements",
            "improvement_applied",
            "preserved_information",
            "guidance_added",
            "guided_dimensions",
        }
        assert data["video_filename"] == stored
        assert data["source_prompt"] == SOURCE
        assert data["improved_prompt"].startswith(SOURCE)
        assert data["improvement_applied"] is True
        assert data["preserved_information"] is True
        assert data["guidance_added"] is True
        for dim in data["guided_dimensions"]:
            assert dim in DIMENSIONS
        for item in data["improvements"]:
            assert set(item.keys()) == {"dimension", "reason", "guidance"}
            assert item["dimension"] in DIMENSIONS
            assert item["reason"] in ("missing", "weak")

    def test_source_prompt_unchanged_in_response(self):
        stored = _upload()
        messy = "  Mixed   CASE\ntext  "
        data = _improve(stored, messy).json()
        assert data["source_prompt"] == messy
        assert data["improved_prompt"].startswith(messy)

    def test_quality_before_equals_direct_quality_analysis(self):
        stored = _upload()
        improve_data = _improve(stored, SOURCE).json()
        quality_data = _quality(stored, SOURCE).json()
        assert improve_data["quality_before"] == quality_data["quality"]

    def test_quality_after_matches_improved_prompt_analysis(self):
        stored = _upload()
        improve_data = _improve(stored, SOURCE).json()
        after = _quality(stored, improve_data["improved_prompt"]).json()
        assert improve_data["quality_after"] == after["quality"]

    def test_no_fabrication_in_improved_prompt(self):
        stored = _upload()
        data = _improve(stored, SOURCE).json()
        added = data["improved_prompt"][len(SOURCE):]
        assert added.startswith("\n\nEnhancement Guidance:\n")
        guidance_lines = [ln for ln in added.splitlines() if ln.startswith("[")]
        assert guidance_lines == [
            i["guidance"] for i in data["improvements"]
        ]
        for word in ("sunset", "rain", "neon", "beautiful", "sarah",
                     "tokyo", "ferrari", "luxury", "woman", "cinematic"):
            assert word not in data["improved_prompt"].lower(), word

    def test_deterministic_repeated_requests(self):
        stored = _upload()
        first = _improve(stored, SOURCE).json()
        second = _improve(stored, SOURCE).json()
        assert first == second

    def test_fully_covered_prompt_no_improvement(self):
        stored = _upload()
        detailed = (
            "Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, camera tracking with shallow depth of field, soft "
            "lighting with rim light and golden hour glow, vibrant teal "
            "and orange palette with warm tones, layered foreground and "
            "rule of thirds composition, ambient sound with quiet music "
            "score."
        )
        data = _improve(stored, detailed).json()
        assert data["improvement_applied"] is False
        assert data["improved_prompt"] == detailed
        assert data["improvements"] == []
        assert data["guidance_added"] is False

    def test_improve_does_not_require_history(self):
        stored = _upload()
        assert _improve(stored, SOURCE).status_code == 200

    def test_improve_does_not_save_to_history(self):
        stored = _upload()
        _save(stored)
        before = client.get(f"/api/videos/{stored}/prompt/history").json()
        _improve(stored, "another different prompt about things")
        after = client.get(f"/api/videos/{stored}/prompt/history").json()
        assert before == after
        assert len(after["versions"]) == 1

    def test_response_has_no_internal_details(self):
        stored = _upload()
        text = _improve(stored, SOURCE).text
        for forbidden in ("PromptImprovementService", "PromptQualityService",
                          "_quality_service", "Traceback",
                          "Internal Server", "_storage"):
            assert forbidden not in text

    def test_response_no_absolute_paths_or_env(self):
        stored = _upload()
        text = _improve(stored, SOURCE).text
        for bad in ("C:\\", "C:/", "/home", "/Users", "/var/",
                    "os.environ", "APPDATA", "PYTHONPATH"):
            assert bad not in text, bad


class TestHistoryImproveEndpoint:
    def test_existing_version_200(self):
        stored = _upload()
        created = _save(stored)
        response = _himprove(stored, created["version"])
        assert response.status_code == 200
        data = response.json()
        assert data["video_filename"] == stored
        assert data["source_prompt"] == PROMPT
        assert data["improved_prompt"].startswith(PROMPT)
        assert set(data["quality_before"].keys()) == {
            "overall_score",
            "completeness_percentage",
            "dimensions",
            "missing_dimensions",
            "suggestions",
        }

    def test_nonexistent_version_404(self):
        stored = _upload()
        assert _himprove(stored, 99).status_code == 404

    def test_deleted_version_404(self):
        stored = _upload()
        created = _save(stored)
        delete = client.delete(
            f"/api/videos/{stored}/prompt/history/{created['version']}"
        )
        assert delete.status_code == 200
        assert _himprove(stored, created["version"]).status_code == 404

    def test_version_zero_is_422(self):
        stored = _upload()
        assert _himprove(stored, 0).status_code == 422

    def test_missing_video_404(self):
        assert _himprove("missing_video.mp4", 1).status_code == 404

    def test_history_never_modified_by_improvement(self):
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
        _improve(stored, SOURCE)
        _himprove(stored, version)
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

    def test_history_improve_matches_post_improve(self):
        stored = _upload()
        created = _save(stored, SOURCE)
        hist = _himprove(stored, created["version"]).json()
        post = _improve(stored, SOURCE).json()
        for key in ("source_prompt", "improved_prompt", "quality_before",
                    "quality_after", "improvements", "improvement_applied",
                    "preserved_information"):
            assert hist[key] == post[key]


class TestDay16To21Regression:
    def test_all_previous_features_still_work(self):
        stored = _upload()
        created = _save(stored)
        version = created["version"]

        # Day 16 history
        listing = client.get(f"/api/videos/{stored}/prompt/history")
        assert listing.status_code == 200
        assert len(listing.json()["versions"]) == 1
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
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "xml"},
        ).status_code == 422

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

        # Day 22 improve does not break any of the above
        assert _improve(stored, PROMPT).status_code == 200
        assert _himprove(stored, version).status_code == 200

        export_after = client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "json"},
        )
        assert export_after.status_code == 200
        assert export_after.content == export_json_before

        # Day 21 quality unchanged after improvement calls
        quality_after = _quality(stored, PROMPT)
        assert quality_after.json() == quality.json()

        # history untouched
        final = client.get(f"/api/videos/{stored}/prompt/history/{version}")
        assert final.json()["prompt"] == PROMPT

    def test_version_routes_still_resolve_after_improve_routes(self):
        stored = _upload()
        created = _save(stored)
        version = created["version"]
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/improve"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/quality"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/export",
            params={"format": "json"},
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/{version}/package"
        ).status_code == 200
