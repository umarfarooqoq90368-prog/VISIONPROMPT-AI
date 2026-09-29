"""API tests for the prompt history endpoints (Day 16)."""
import json
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets", "test_video.mp4")


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


def _save(stored, prompt="Scene progression across 1 scenes.", negative="",
          source="custom", operation="", metadata=None):
    body = {"prompt": prompt, "negative_prompt": negative, "source": source,
            "operation": operation}
    if metadata is not None:
        body["metadata"] = metadata
    return client.post(f"/api/videos/{stored}/prompt/history", json=body)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)


def test_create_version_returns_200():
    stored = _upload()
    response = _save(stored, metadata={"note": "first"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["version"] == 1
    assert data["video_filename"] == stored
    assert data["source"] == "custom"
    assert data["metadata"] == {"note": "first"}


def test_create_version_preserves_prompt_exactly():
    stored = _upload()
    weird = '  Subject: "a person"  \nAction: walking... 42%  '
    response = _save(stored, prompt=weird, negative="blurry, low quality")
    assert response.status_code == 200
    assert response.json()["prompt"] == weird
    assert response.json()["negative_prompt"] == "blurry, low quality"


def test_sequential_versions_via_api():
    stored = _upload()
    assert _save(stored, prompt="one two three").json()["version"] == 1
    assert _save(stored, prompt="one two four").json()["version"] == 2
    assert _save(stored, prompt="one two five").json()["version"] == 3


def test_list_history_returns_200():
    stored = _upload()
    _save(stored, prompt="alpha beta")
    _save(stored, prompt="alpha gamma")
    response = client.get(f"/api/videos/{stored}/prompt/history")
    assert response.status_code == 200
    data = response.json()
    assert data["video_filename"] == stored
    assert [v["version"] for v in data["versions"]] == [1, 2]
    assert data["versions"][0]["prompt"] == "alpha beta"


def test_empty_history():
    stored = _upload()
    response = client.get(f"/api/videos/{stored}/prompt/history")
    assert response.status_code == 200
    assert response.json() == {"video_filename": stored, "versions": []}


def test_get_version_returns_200():
    stored = _upload()
    saved = _save(stored, prompt="hello world prompt")
    version = saved.json()["version"]
    response = client.get(f"/api/videos/{stored}/prompt/history/{version}")
    assert response.status_code == 200
    assert response.json() == saved.json()


def test_delete_version_returns_200():
    stored = _upload()
    _save(stored, prompt="one")
    response = client.delete(f"/api/videos/{stored}/prompt/history/1")
    assert response.status_code == 200
    assert response.json() == {
        "deleted": True,
        "video_filename": stored,
        "version": 1,
    }
    remaining = client.get(f"/api/videos/{stored}/prompt/history").json()["versions"]
    assert remaining == []


def test_deleted_versions_not_renumbered():
    stored = _upload()
    _save(stored, prompt="one one")
    _save(stored, prompt="two two")
    _save(stored, prompt="three three")
    client.delete(f"/api/videos/{stored}/prompt/history/2")
    versions = [
        v["version"]
        for v in client.get(f"/api/videos/{stored}/prompt/history").json()["versions"]
    ]
    assert versions == [1, 3]
    created = _save(stored, prompt="four four")
    assert created.json()["version"] == 4


def test_compare_versions_returns_200():
    stored = _upload()
    _save(stored, prompt="alpha beta gamma")
    _save(stored, prompt="alpha beta delta")
    response = client.get(
        f"/api/videos/{stored}/prompt/history/compare/1/2"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["video_filename"] == stored
    assert data["version_a"] == 1
    assert data["version_b"] == 2
    assert data["prompt_a"] == "alpha beta gamma"
    assert data["prompt_b"] == "alpha beta delta"
    assert data["negative_prompt_a"] == ""
    assert data["negative_prompt_b"] == ""
    assert data["added_tokens"] == ["delta"]
    assert data["removed_tokens"] == ["gamma"]
    assert set(data["common_tokens"]) == {"alpha", "beta"}
    assert data["changed"] is True


def test_compare_route_not_captured_by_version_route():
    """The static compare route must win over /history/{version}."""
    stored = _upload()
    _save(stored, prompt="alpha beta")
    _save(stored, prompt="alpha gamma")
    response = client.get(f"/api/videos/{stored}/prompt/history/compare/1/2")
    assert response.status_code == 200
    data = response.json()
    assert "added_tokens" in data and "common_tokens" in data
    assert "version_id" not in data
    numeric = client.get(f"/api/videos/{stored}/prompt/history/1")
    assert numeric.status_code == 200
    assert numeric.json()["version_id"]


def test_missing_version_returns_404():
    stored = _upload()
    response = client.get(f"/api/videos/{stored}/prompt/history/99")
    assert response.status_code == 404
    response = client.delete(f"/api/videos/{stored}/prompt/history/99")
    assert response.status_code == 404


def test_compare_missing_version_returns_404():
    stored = _upload()
    _save(stored, prompt="alpha beta")
    response = client.get(f"/api/videos/{stored}/prompt/history/compare/1/2")
    assert response.status_code == 404


@pytest.mark.parametrize("bad_version", ["0", "-1"])
def test_invalid_version_returns_422(bad_version):
    stored = _upload()
    response = client.get(f"/api/videos/{stored}/prompt/history/{bad_version}")
    assert response.status_code == 422


def test_non_integer_version_returns_422():
    stored = _upload()
    response = client.get(f"/api/videos/{stored}/prompt/history/abc")
    assert response.status_code == 422


def test_invalid_compare_version_returns_422():
    stored = _upload()
    response = client.get(f"/api/videos/{stored}/prompt/history/compare/0/1")
    assert response.status_code == 422


def test_invalid_source_returns_422():
    stored = _upload()
    response = _save(stored, source="database")
    assert response.status_code == 422


def test_empty_prompt_returns_422():
    stored = _upload()
    response = _save(stored, prompt="")
    assert response.status_code == 422


def test_whitespace_prompt_returns_422():
    stored = _upload()
    response = _save(stored, prompt="   ")
    assert response.status_code == 422


def test_missing_prompt_returns_422():
    stored = _upload()
    response = client.post(
        f"/api/videos/{stored}/prompt/history", json={"source": "custom"}
    )
    assert response.status_code == 422


def test_missing_body_returns_422():
    stored = _upload()
    response = client.post(f"/api/videos/{stored}/prompt/history")
    assert response.status_code == 422


def test_nonexistent_video_returns_404():
    response = client.post(
        "/api/videos/nonexistent.mp4/prompt/history",
        json={"prompt": "alpha beta"},
    )
    assert response.status_code == 404
    response = client.get("/api/videos/nonexistent.mp4/prompt/history")
    assert response.status_code == 404


def test_path_traversal_returns_404():
    response = client.get("/api/videos/../../../etc/passwd/prompt/history")
    assert response.status_code in (400, 404)
    response = client.post(
        "/api/videos/../../../etc/passwd/prompt/history",
        json={"prompt": "alpha beta"},
    )
    assert response.status_code in (400, 404)


def test_no_absolute_paths():
    stored = _upload()
    created = _save(stored, prompt="alpha beta", metadata={"k": "v"})
    versions = client.get(f"/api/videos/{stored}/prompt/history").json()["versions"]
    single = client.get(f"/api/videos/{stored}/prompt/history/1")
    compare = None
    _save(stored, prompt="alpha gamma")
    compare = client.get(f"/api/videos/{stored}/prompt/history/compare/1/2")
    for payload in [created.json(), versions, single.json()]:
        serialized = json.dumps(payload)
        assert "C:/" not in serialized
        assert "C:\\" not in serialized
        assert "/home" not in serialized
        assert "/Users" not in serialized
        assert "/var" not in serialized
    serialized = json.dumps(compare.json())
    assert "C:/" not in serialized
    assert "C:\\" not in serialized


def test_history_does_not_fabricate_information():
    stored = _upload()
    _save(stored, prompt="Scene progression across 1 scenes.")
    _save(stored, prompt="Scene progression across 1 scenes, cinematic composition.")
    versions = client.get(f"/api/videos/{stored}/prompt/history").json()["versions"]
    compare = client.get(
        f"/api/videos/{stored}/prompt/history/compare/1/2"
    ).json()
    text = (json.dumps(versions) + json.dumps(compare)).lower()
    for word in ["person", "character", "dialogue", "walking", "park",
                 "city", "sunset", "brand", "product", "voiceover"]:
        assert word not in text, f"fabricated: {word}"


def test_metadata_preserved_via_api():
    stored = _upload()
    meta = {"tags": ["draft"], "note": "manual save"}
    response = _save(stored, metadata=meta)
    assert response.status_code == 200
    assert response.json()["metadata"] == meta


def test_multiple_videos_isolated_via_api():
    stored_a = _upload()
    stored_b = _upload()
    _save(stored_a, prompt="alpha beta")
    assert client.get(f"/api/videos/{stored_b}/prompt/history").json()["versions"] == []
    assert _save(stored_b, prompt="alpha gamma").json()["version"] == 1


def test_invalid_source_enum_values_only():
    stored = _upload()
    for bad in ["advanced", "template ", "Custom", "day13"]:
        assert _save(stored, source=bad).status_code == 422


def test_previous_endpoints_unaffected():
    """Day 1-15 endpoints should still work after adding history."""
    stored = _upload()
    assert client.get("/api/health").status_code == 200
    assert client.get(f"/api/videos/{stored}/metadata").status_code == 200
    assert client.post(f"/api/videos/{stored}/prompt?style=cinematic").status_code == 200
    assert client.post(
        f"/api/videos/{stored}/advanced-prompt?style=cinematic"
    ).status_code == 200
    assert client.post(
        f"/api/videos/{stored}/prompt/refine", json={"operation": "refine"}
    ).status_code == 200
    assert client.post(
        f"/api/videos/{stored}/prompt/template",
        json={"template": "ai_video"},
    ).status_code == 200
    assert _save(stored).status_code == 200
