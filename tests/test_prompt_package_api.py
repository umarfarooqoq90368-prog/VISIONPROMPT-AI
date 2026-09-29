"""API tests for the prompt package endpoint (Day 20)."""
import io
import os
import re
import zipfile

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets", "test_video.mp4")

PROMPT = "Cinematic wide shot of the subject, golden hour lighting, slow dolly in."
NEGATIVE = "blurry, low quality, distorted anatomy, unwanted text, watermark"

PACKAGE_FILES = ["prompt.json", "prompt.md", "prompt.txt", "package_metadata.json"]
METADATA_KEYS = ["video_filename", "version", "version_id", "source",
                 "operation", "created_at", "favorite", "tags"]


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


def _package(stored, version):
    return client.get(f"/api/videos/{stored}/prompt/history/{version}/package")


def _favorite(stored, version):
    return client.post(f"/api/videos/{stored}/prompt/history/{version}/favorite")


def _add_tags(stored, version, tags):
    return client.post(
        f"/api/videos/{stored}/prompt/history/{version}/tags", json={"tags": tags}
    )


def _read_files(response):
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return {name: zf.read(name).decode("utf-8") for name in zf.namelist()}


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)


class TestPackageResponse:
    def test_valid_version_200(self):
        stored = _upload()
        _save(stored)
        response = _package(stored, 1)
        assert response.status_code == 200
        assert response.content[:2] == b"PK"

    def test_content_type_application_zip(self):
        stored = _upload()
        _save(stored)
        assert _package(stored, 1).headers["content-type"].startswith(
            "application/zip"
        )

    def test_safe_deterministic_filename_no_uuid(self):
        stored = _upload()
        _save(stored)
        cd = _package(stored, 1).headers["content-disposition"]
        assert cd == 'attachment; filename="visionprompt_video_v1.zip"'
        stem = os.path.splitext(stored)[0]
        assert stem not in cd
        assert "a15cca2a" not in cd
        assert re.fullmatch(
            r'attachment; filename="visionprompt_video_v\d+\.zip"', cd
        )

    def test_zip_contains_exactly_four_files(self):
        stored = _upload()
        _save(stored, metadata={"style": "film"})
        files = _read_files(_package(stored, 1))
        assert list(files.keys()) == PACKAGE_FILES

    def test_prompt_json_exact_preservation(self):
        stored = _upload()
        _save(stored, prompt=PROMPT, negative=NEGATIVE, source="refinement",
              operation="cinematic", metadata={"style": "film"})
        import json
        data = json.loads(_read_files(_package(stored, 1))["prompt.json"])
        assert data["prompt"] == PROMPT
        assert data["negative_prompt"] == NEGATIVE
        assert data["source"] == "refinement"
        assert data["operation"] == "cinematic"
        assert data["metadata"] == {"style": "film"}
        assert data["version"] == 1
        assert data["version_id"] == f"{stored}:1"
        assert data["favorite"] is False
        assert data["tags"] == []

    def test_prompt_md_exact_preservation(self):
        stored = _upload()
        _save(stored, prompt=PROMPT, negative=NEGATIVE)
        files = _read_files(_package(stored, 1))
        assert f"## Prompt\n\n{PROMPT}" in files["prompt.md"]
        assert f"## Negative Prompt\n\n{NEGATIVE}" in files["prompt.md"]
        assert files["prompt.md"].startswith("# VisionPrompt AI Prompt")

    def test_prompt_txt_exact_preservation(self):
        stored = _upload()
        _save(stored, prompt=PROMPT, negative=NEGATIVE)
        files = _read_files(_package(stored, 1))
        assert f"## PROMPT\n\n{PROMPT}" in files["prompt.txt"]
        assert f"## NEGATIVE PROMPT\n\n{NEGATIVE}" in files["prompt.txt"]
        assert files["prompt.txt"].startswith("# VISIONPROMPT AI PROMPT")

    def test_package_metadata_fields(self):
        stored = _upload()
        record = _save(stored, source="template", operation="ai_video")
        _favorite(stored, 1)
        _add_tags(stored, 1, ["Cinematic", "ai"])
        import json
        meta = json.loads(
            _read_files(_package(stored, 1))["package_metadata.json"]
        )
        assert list(meta.keys()) == METADATA_KEYS
        assert meta["video_filename"] == stored
        assert meta["version"] == 1
        assert meta["version_id"] == f"{stored}:1"
        assert meta["source"] == "template"
        assert meta["operation"] == "ai_video"
        assert meta["created_at"] == record["created_at"]
        assert meta["favorite"] is True
        assert meta["tags"] == ["ai", "cinematic"]

    def test_package_matches_day19_export_files(self):
        stored = _upload()
        _save(stored, metadata={"style": "film"})
        _favorite(stored, 1)
        _add_tags(stored, 1, ["ai"])
        files = _read_files(_package(stored, 1))
        export_json = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        ).text
        export_md = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "markdown"},
        ).text
        export_txt = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "txt"},
        ).text
        assert files["prompt.json"] == export_json
        assert files["prompt.md"] == export_md
        assert files["prompt.txt"] == export_txt

    def test_favorite_and_tag_changes_reflected(self):
        stored = _upload()
        _save(stored)
        import json
        before = json.loads(
            _read_files(_package(stored, 1))["package_metadata.json"]
        )
        assert before["favorite"] is False and before["tags"] == []
        _favorite(stored, 1)
        _add_tags(stored, 1, ["ai", "zeta"])
        after = json.loads(
            _read_files(_package(stored, 1))["package_metadata.json"]
        )
        assert after["favorite"] is True
        assert after["tags"] == ["ai", "zeta"]

    def test_empty_fields(self):
        stored = _upload()
        _save(stored, negative="", operation="", metadata={})
        files = _read_files(_package(stored, 1))
        import json
        data = json.loads(files["prompt.json"])
        assert data["negative_prompt"] == ""
        assert data["operation"] == ""
        assert data["metadata"] == {}
        assert "## Negative Prompt\n\n(empty)" in files["prompt.md"]
        assert "## NEGATIVE PROMPT\n\n(empty)" in files["prompt.txt"]


class TestValidation:
    def test_nonexistent_video_404(self):
        response = client.get("/api/videos/nope.mp4/prompt/history/1/package")
        assert response.status_code == 404

    def test_nonexistent_version_404(self):
        stored = _upload()
        _save(stored)
        assert _package(stored, 99).status_code == 404

    def test_deleted_version_404(self):
        stored = _upload()
        _save(stored, prompt="one")
        _save(stored, prompt="two")
        assert client.delete(f"/api/videos/{stored}/prompt/history/1").status_code == 200
        assert _package(stored, 1).status_code == 404
        assert _package(stored, 2).status_code == 200

    def test_version_created_after_deletion_packagable(self):
        stored = _upload()
        _save(stored, prompt="one")
        _save(stored, prompt="two")
        _save(stored, prompt="three")
        assert client.delete(f"/api/videos/{stored}/prompt/history/2").status_code == 200
        created = _save(stored, prompt="four after delete")
        assert created["version"] == 4
        files = _read_files(_package(stored, 4))
        import json
        assert json.loads(files["prompt.json"])["prompt"] == "four after delete"
        assert _package(stored, 2).status_code == 404

    def test_version_zero_422(self):
        stored = _upload()
        _save(stored)
        assert _package(stored, 0).status_code == 422

    def test_negative_version_422(self):
        stored = _upload()
        _save(stored)
        assert _package(stored, -1).status_code == 422

    def test_path_traversal_404(self):
        response = client.get(
            "/api/videos/../../../etc/passwd/prompt/history/1/package"
        )
        assert response.status_code == 404
        response = client.get(
            "/api/videos/..%2F..%2Fetc%2Fpasswd.mp4/prompt/history/1/package"
        )
        assert response.status_code in (400, 404)

    def test_zip_names_safe(self):
        stored = _upload()
        _save(stored)
        response = _package(stored, 1)
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            for name in zf.namelist():
                assert "/" not in name and "\\" not in name and ".." not in name
            assert zf.testzip() is None


class TestMultipleVersionsAndVideos:
    def test_multiple_versions(self):
        stored = _upload()
        _save(stored, prompt="first prompt")
        _save(stored, prompt="second prompt")
        _save(stored, prompt="third prompt")
        import json
        for version, prompt in [(1, "first prompt"), (2, "second prompt"),
                                (3, "third prompt")]:
            files = _read_files(_package(stored, version))
            data = json.loads(files["prompt.json"])
            assert data["prompt"] == prompt
            assert data["version"] == version

    def test_multiple_videos_isolated(self):
        stored_a = _upload()
        stored_b = _upload()
        _save(stored_a, prompt="video A prompt")
        _save(stored_b, prompt="video B prompt")
        _favorite(stored_b, 1)
        _add_tags(stored_b, 1, ["b-only"])
        import json
        files_a = _read_files(_package(stored_a, 1))
        files_b = _read_files(_package(stored_b, 1))
        assert json.loads(files_a["prompt.json"])["prompt"] == "video A prompt"
        assert json.loads(files_b["prompt.json"])["prompt"] == "video B prompt"
        assert "video B prompt" not in files_a["prompt.json"]
        assert "video A prompt" not in files_b["prompt.json"]
        meta_a = json.loads(files_a["package_metadata.json"])
        meta_b = json.loads(files_b["package_metadata.json"])
        assert meta_a["video_filename"] == stored_a
        assert meta_b["video_filename"] == stored_b
        assert meta_a["favorite"] is False and meta_a["tags"] == []
        assert meta_b["favorite"] is True and meta_b["tags"] == ["b-only"]


class TestRouteCollision:
    def test_package_route_resolves_as_package(self):
        stored = _upload()
        _save(stored)
        response = _package(stored, 1)
        assert response.status_code == 200
        assert response.content[:2] == b"PK"

    def test_numeric_version_route_still_works(self):
        stored = _upload()
        _save(stored)
        response = client.get(f"/api/videos/{stored}/prompt/history/1")
        assert response.status_code == 200
        assert response.json()["prompt"] == PROMPT
        assert response.content[:2] != b"PK"

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


class TestReadOnlyDeterminismSecurity:
    def test_original_history_unchanged_after_packaging(self):
        stored = _upload()
        _save(stored, prompt="original", metadata={"k": "v"})
        _favorite(stored, 1)
        _add_tags(stored, 1, ["ai"])
        history_before = client.get(f"/api/videos/{stored}/prompt/history").json()
        version_before = client.get(f"/api/videos/{stored}/prompt/history/1").json()
        org_before = client.get(
            f"/api/videos/{stored}/prompt/history/1/organization"
        ).json()
        assert _package(stored, 1).status_code == 200
        assert _package(stored, 1).status_code == 200
        assert client.get(f"/api/videos/{stored}/prompt/history").json() == history_before
        assert client.get(f"/api/videos/{stored}/prompt/history/1").json() == version_before
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/organization"
        ).json() == org_before

    def test_repeated_generation_identical(self):
        stored = _upload()
        _save(stored, metadata={"k": "v"})
        _favorite(stored, 1)
        _add_tags(stored, 1, ["ai"])
        first = _package(stored, 1)
        second = _package(stored, 1)
        assert first.status_code == second.status_code == 200
        assert first.content == second.content
        assert first.headers["content-disposition"] == second.headers["content-disposition"]
        assert first.headers["content-type"] == second.headers["content-type"]

    def test_no_absolute_paths_anywhere(self):
        stored = _upload()
        _save(stored, metadata={"path": "relative/entry"})
        files = _read_files(_package(stored, 1))
        for content in files.values():
            for bad in ["C:/", "C:\\", "/home", "/Users", "/var/"]:
                assert bad not in content, f"absolute path {bad}"

    def test_no_fabricated_information(self):
        stored = _upload()
        _save(stored, prompt="alpha beta gamma", negative="noise watermark")
        combined = " ".join(_read_files(_package(stored, 1)).values()).lower()
        for word in ["person", "character", "dialogue", "walking", "park",
                     "city", "sunset", "voiceover"]:
            assert word not in combined, f"fabricated {word}"

    def test_no_internal_service_information(self):
        stored = _upload()
        _save(stored)
        combined = " ".join(_read_files(_package(stored, 1)).values())
        for internal in ["_storage", "_org", "PromptHistoryService",
                         "PromptPackageService", "storage/uploads", "BytesIO"]:
            assert internal not in combined, f"internal leak {internal}"


class TestDay16To19Regression:
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
        assert _package(stored, 1).status_code == 200
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/2"
        ).status_code == 200
        after = client.get(f"/api/videos/{stored}/prompt/history").json()
        assert [v["version"] for v in after["versions"]] == [1]

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
        assert client.request(
            "DELETE", f"/api/videos/{stored}/prompt/history/1/tags",
            json={"tags": ["cinematic"]},
        ).json()["tags"] == ["ai"]
        org_after_remove = client.get(
            f"/api/videos/{stored}/prompt/history/1/organization"
        ).json()
        assert org_after_remove == {"video_filename": stored, "version": 1,
                                    "favorite": True, "tags": ["ai"]}
        assert _package(stored, 1).status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/organization"
        ).json() == org_after_remove

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
        assert client.get(
            f"/api/videos/{stored}/prompt/search",
            params={"source": "custom"},
        ).json()["results"][0]["version"] == 2
        assert _package(stored, 1).status_code == 200
        search_again = client.get(
            f"/api/videos/{stored}/prompt/search",
            params={"query": "cinematic", "favorite": "true"},
        )
        assert search_again.json() == search.json()

    def test_day19_export_endpoints_still_work(self):
        stored = _upload()
        _save(stored, metadata={"style": "film"})
        export_json = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "json"},
        )
        assert export_json.status_code == 200
        assert export_json.headers["content-type"].startswith("application/json")
        export_md = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "markdown"},
        )
        assert export_md.status_code == 200
        assert export_md.headers["content-type"].startswith("text/markdown")
        export_txt = client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "txt"},
        )
        assert export_txt.status_code == 200
        assert export_txt.headers["content-type"].startswith("text/plain")
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/export"
        ).status_code == 422
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/export",
            params={"format": "xml"},
        ).status_code == 422
        pkg = _package(stored, 1)
        files = _read_files(pkg)
        assert files["prompt.json"] == export_json.text
        assert files["prompt.md"] == export_md.text
        assert files["prompt.txt"] == export_txt.text
