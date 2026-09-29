"""API tests for the prompt export endpoint (Day 19)."""
import os

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets", "test_video.mp4")

PROMPT = "Cinematic wide shot of the subject, golden hour lighting, slow dolly in."
NEGATIVE = "blurry, low quality, distorted anatomy, unwanted text, watermark"


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
        upload = client.post("/api/videos/upload", files={"file": ("test.mp4", f, "video/mp4")})
    assert upload.status_code == 200
    stored = upload.json()["video"]["stored_filename"]
    response = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds=1")
    assert response.status_code == 200
    return stored


def _save(stored, prompt=PROMPT, negative=NEGATIVE, source="custom", operation="",
          metadata=None):
    body = {"prompt": prompt, "negative_prompt": negative,
            "source": source, "operation": operation}
    if metadata is not None:
        body["metadata"] = metadata
    response = client.post(f"/api/videos/{stored}/prompt/history", json=body)
    assert response.status_code == 200
    return response.json()


def _export(stored, version, format):
    return client.get(
        f"/api/videos/{stored}/prompt/history/{version}/export",
        params={"format": format},
    )


def _favorite(stored, version):
    return client.post(f"/api/videos/{stored}/prompt/history/{version}/favorite")


def _add_tags(stored, version, tags):
    return client.post(
        f"/api/videos/{stored}/prompt/history/{version}/tags", json={"tags": tags}
    )


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)


class TestExportFormats:
    def test_json_export_200(self):
        stored = _upload()
        _save(stored)
        response = _export(stored, 1, "json")
        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] == PROMPT

    def test_markdown_export_200(self):
        stored = _upload()
        _save(stored)
        response = _export(stored, 1, "markdown")
        assert response.status_code == 200
        assert response.text.startswith("# VisionPrompt AI Prompt")
        assert PROMPT in response.text

    def test_txt_export_200(self):
        stored = _upload()
        _save(stored)
        response = _export(stored, 1, "txt")
        assert response.status_code == 200
        assert response.text.startswith("# VISIONPROMPT AI PROMPT")
        assert PROMPT in response.text

    def test_content_types(self):
        stored = _upload()
        _save(stored)
        assert _export(stored, 1, "json").headers["content-type"].startswith(
            "application/json"
        )
        assert _export(stored, 1, "markdown").headers["content-type"].startswith(
            "text/markdown"
        )
        assert _export(stored, 1, "txt").headers["content-type"].startswith(
            "text/plain"
        )

    def test_content_disposition_filenames(self):
        stored = _upload()
        _save(stored)
        stem = os.path.splitext(stored)[0]
        assert _export(stored, 1, "json").headers["content-disposition"] == \
            f'attachment; filename="visionprompt_{stem}_v1.json"'
        assert _export(stored, 1, "markdown").headers["content-disposition"] == \
            f'attachment; filename="visionprompt_{stem}_v1.md"'
        assert _export(stored, 1, "txt").headers["content-disposition"] == \
            f'attachment; filename="visionprompt_{stem}_v1.txt"'

    def test_json_structure(self):
        stored = _upload()
        _save(stored, source="refinement", operation="cinematic",
              metadata={"style": "film"})
        data = _export(stored, 1, "json").json()
        assert list(data.keys()) == [
            "video_filename", "version", "version_id", "source",
            "operation", "prompt", "negative_prompt", "created_at",
            "metadata", "favorite", "tags",
        ]
        assert data["video_filename"] == stored
        assert data["version"] == 1
        assert data["version_id"] == f"{stored}:1"
        assert data["source"] == "refinement"
        assert data["operation"] == "cinematic"
        assert data["metadata"] == {"style": "film"}
        assert data["favorite"] is False
        assert data["tags"] == []

    def test_exact_prompt_and_negative_preserved_all_formats(self):
        stored = _upload()
        prompt = 'Exact "quoted" line one.\nLine two with 100% symbols.'
        negative = 'avoid "text" overlays, watermark'
        _save(stored, prompt=prompt, negative=negative)
        data = _export(stored, 1, "json").json()
        assert data["prompt"] == prompt
        assert data["negative_prompt"] == negative
        md = _export(stored, 1, "markdown").text
        assert prompt in md
        assert negative in md
        txt = _export(stored, 1, "txt").text
        assert prompt in txt
        assert negative in txt

    def test_favorite_and_tags_included(self):
        stored = _upload()
        _save(stored)
        _favorite(stored, 1)
        _add_tags(stored, 1, ["Cinematic", "ai", " zeta"])
        data = _export(stored, 1, "json").json()
        assert data["favorite"] is True
        assert data["tags"] == ["ai", "cinematic", "zeta"]
        md = _export(stored, 1, "markdown").text
        assert "## Favorite\n\ntrue" in md
        assert "* ai\n* cinematic\n* zeta" in md
        txt = _export(stored, 1, "txt").text
        assert "Favorite: true" in txt
        assert "Tags: ai, cinematic, zeta" in txt

    def test_no_absolute_paths_in_exports(self):
        stored = _upload()
        _save(stored, metadata={"path": "relative/entry"})
        for fmt in ("json", "markdown", "txt"):
            content = _export(stored, 1, fmt).text
            for bad in ["C:/", "C:\\", "/home", "/Users", "/var/", "/etc/"]:
                assert bad not in content, f"{bad} leaked in {fmt}"

    def test_no_fabricated_information(self):
        stored = _upload()
        _save(stored, prompt="alpha beta gamma", negative="noise watermark")
        for fmt in ("json", "markdown", "txt"):
            content = _export(stored, 1, fmt).text.lower()
            for word in ["person", "character", "dialogue", "walking",
                         "park", "city", "sunset", "voiceover"]:
                assert word not in content, f"fabricated {word} in {fmt}"

    def test_deterministic_exports(self):
        stored = _upload()
        _save(stored, metadata={"k": "v"})
        _favorite(stored, 1)
        _add_tags(stored, 1, ["ai"])
        for fmt in ("json", "markdown", "txt"):
            first = _export(stored, 1, fmt)
            second = _export(stored, 1, fmt)
            assert first.status_code == second.status_code == 200
            assert first.content == second.content
            assert first.headers["content-disposition"] == \
                second.headers["content-disposition"]


class TestValidation:
    def test_nonexistent_video_404(self):
        response = client.get(
            "/api/videos/nonexistent.mp4/prompt/history/1/export",
            params={"format": "json"},
        )
        assert response.status_code == 404

    def test_nonexistent_version_404(self):
        stored = _upload()
        _save(stored)
        assert _export(stored, 99, "json").status_code == 404
        assert _export(stored, 99, "markdown").status_code == 404
        assert _export(stored, 99, "txt").status_code == 404

    def test_deleted_version_404(self):
        stored = _upload()
        _save(stored, prompt="one")
        _save(stored, prompt="two")
        delete = client.delete(f"/api/videos/{stored}/prompt/history/1")
        assert delete.status_code == 200
        for fmt in ("json", "markdown", "txt"):
            assert _export(stored, 1, fmt).status_code == 404
        assert _export(stored, 2, "json").status_code == 200

    def test_path_traversal_404(self):
        response = client.get(
            "/api/videos/../../../etc/passwd/prompt/history/1/export",
            params={"format": "json"},
        )
        assert response.status_code == 404
        response = client.get(
            "/api/videos/..%2F..%2Fetc%2Fpasswd.mp4/prompt/history/1/export",
            params={"format": "json"},
        )
        assert response.status_code in (400, 404)

    def test_version_zero_422(self):
        stored = _upload()
        _save(stored)
        assert _export(stored, 0, "json").status_code == 422

    def test_negative_version_422(self):
        stored = _upload()
        _save(stored)
        assert _export(stored, -1, "json").status_code == 422

    def test_missing_format_422(self):
        stored = _upload()
        _save(stored)
        response = client.get(f"/api/videos/{stored}/prompt/history/1/export")
        assert response.status_code == 422

    @pytest.mark.parametrize("fmt", ["xml", "html", "Json", "TXT", "json ", ""])
    def test_invalid_format_422(self, fmt):
        stored = _upload()
        _save(stored)
        assert _export(stored, 1, fmt).status_code == 422


class TestRouteCollision:
    def test_export_route_resolves_as_export(self):
        stored = _upload()
        _save(stored)
        response = _export(stored, 1, "json")
        assert response.status_code == 200
        assert response.json()["version_id"] == f"{stored}:1"

    def test_numeric_version_route_still_works(self):
        stored = _upload()
        _save(stored)
        response = client.get(f"/api/videos/{stored}/prompt/history/1")
        assert response.status_code == 200
        assert response.json()["prompt"] == PROMPT
        assert "version_id" in response.json()

    def test_static_history_routes_still_work(self):
        stored = _upload()
        _save(stored)
        _favorite(stored, 1)
        _add_tags(stored, 1, ["ai"])
        _save(stored, prompt="second")
        assert client.get(f"/api/videos/{stored}/prompt/history").status_code == 200
        assert client.get(f"/api/videos/{stored}/prompt/history/favorites").status_code == 200
        assert client.get(f"/api/videos/{stored}/prompt/history/tag/ai").status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2"
        ).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/organization"
        ).status_code == 200

    def test_search_route_still_works(self):
        stored = _upload()
        _save(stored)
        response = client.get(f"/api/videos/{stored}/prompt/search")
        assert response.status_code == 200
        assert response.json()["count"] == 1


class TestMultipleVersionsAndVideos:
    def test_multiple_versions_export_distinctly(self):
        stored = _upload()
        _save(stored, prompt="first prompt")
        _save(stored, prompt="second prompt")
        first = _export(stored, 1, "json").json()
        second = _export(stored, 2, "json").json()
        assert first["prompt"] == "first prompt"
        assert second["prompt"] == "second prompt"
        assert first["version_id"] != second["version_id"]
        md1 = _export(stored, 1, "markdown").text
        md2 = _export(stored, 2, "markdown").text
        assert "first prompt" in md1 and "second prompt" not in md1
        assert "second prompt" in md2 and "first prompt" not in md2

    def test_multiple_videos_isolated(self):
        stored_a = _upload()
        stored_b = _upload()
        _save(stored_a, prompt="video A prompt")
        _save(stored_b, prompt="video B prompt")
        _favorite(stored_b, 1)
        a = _export(stored_a, 1, "json").json()
        b = _export(stored_b, 1, "json").json()
        assert a["video_filename"] == stored_a
        assert b["video_filename"] == stored_b
        assert a["prompt"] == "video A prompt"
        assert b["prompt"] == "video B prompt"
        assert a["favorite"] is False
        assert b["favorite"] is True

    def test_favorites_and_tags_do_not_leak_between_videos(self):
        stored_a = _upload()
        stored_b = _upload()
        _save(stored_a, prompt="video A")
        _save(stored_b, prompt="video B")
        _favorite(stored_b, 1)
        _add_tags(stored_b, 1, ["only-b"])
        a = _export(stored_a, 1, "json").json()
        assert a["favorite"] is False
        assert a["tags"] == []


class TestReadOnlyAndRegression:
    def test_original_history_unchanged_after_export(self):
        stored = _upload()
        _save(stored, prompt="original", metadata={"k": "v"})
        _favorite(stored, 1)
        _add_tags(stored, 1, ["ai"])
        history_before = client.get(f"/api/videos/{stored}/prompt/history").json()
        org_before = client.get(
            f"/api/videos/{stored}/prompt/history/1/organization"
        ).json()
        for fmt in ("json", "markdown", "txt"):
            assert _export(stored, 1, fmt).status_code == 200
        history_after = client.get(f"/api/videos/{stored}/prompt/history").json()
        org_after = client.get(
            f"/api/videos/{stored}/prompt/history/1/organization"
        ).json()
        assert history_before == history_after
        assert org_before == org_after

    def test_day16_history_endpoints_still_work(self):
        stored = _upload()
        created = _save(stored, prompt="day16 check")
        assert created["version"] == 1
        listing = client.get(f"/api/videos/{stored}/prompt/history")
        assert listing.status_code == 200
        assert len(listing.json()["versions"]) == 1
        single = client.get(f"/api/videos/{stored}/prompt/history/1")
        assert single.status_code == 200
        assert single.json()["prompt"] == "day16 check"
        _save(stored, prompt="second")
        compare = client.get(f"/api/videos/{stored}/prompt/history/compare/1/2")
        assert compare.status_code == 200
        assert "common_tokens" in compare.json()
        # export in between must not disturb history
        assert _export(stored, 1, "json").status_code == 200
        listing_after = client.get(f"/api/videos/{stored}/prompt/history")
        assert listing_after.status_code == 200
        assert [v["prompt"] for v in listing_after.json()["versions"]] == [
            "day16 check", "second"
        ]

    def test_day17_organization_endpoints_still_work(self):
        stored = _upload()
        _save(stored)
        assert _favorite(stored, 1).status_code == 200
        assert _add_tags(stored, 1, ["ai", "cinematic"]).status_code == 200
        org = client.get(f"/api/videos/{stored}/prompt/history/1/organization")
        assert org.status_code == 200
        assert org.json()["favorite"] is True
        assert org.json()["tags"] == ["ai", "cinematic"]
        favorites = client.get(f"/api/videos/{stored}/prompt/history/favorites")
        assert favorites.status_code == 200
        assert [x["version"] for x in favorites.json()["favorites"]] == [1]
        by_tag = client.get(f"/api/videos/{stored}/prompt/history/tag/ai")
        assert by_tag.status_code == 200
        assert [x["version"] for x in by_tag.json()["versions"]] == [1]
        assert _export(stored, 1, "txt").status_code == 200
        org_after = client.get(f"/api/videos/{stored}/prompt/history/1/organization")
        assert org_after.json() == org.json()

    def test_day18_search_endpoint_still_works(self):
        stored = _upload()
        _save(stored, prompt="cinematic alpha", source="refinement")
        _save(stored, prompt="documentary beta", source="custom")
        _favorite(stored, 1)
        search = client.get(
            f"/api/videos/{stored}/prompt/search",
            params={"query": "cinematic", "favorite": "true"},
        )
        assert search.status_code == 200
        assert search.json()["count"] == 1
        assert search.json()["results"][0]["version"] == 1
        search_all = client.get(f"/api/videos/{stored}/prompt/search")
        assert search_all.json()["count"] == 2
        assert _export(stored, 1, "json").status_code == 200
        search_again = client.get(
            f"/api/videos/{stored}/prompt/search",
            params={"query": "cinematic", "favorite": "true"},
        )
        assert search_again.json() == search.json()

    def test_export_does_not_modify_history_or_org(self):
        stored = _upload()
        _save(stored, prompt="stable", metadata={"k": "v"})
        _favorite(stored, 1)
        _add_tags(stored, 1, ["ai"])
        version_before = client.get(f"/api/videos/{stored}/prompt/history/1").json()
        for fmt in ("json", "markdown", "txt"):
            _export(stored, 1, fmt)
        version_after = client.get(f"/api/videos/{stored}/prompt/history/1").json()
        assert version_before == version_after
        assert version_after["prompt"] == "stable"
