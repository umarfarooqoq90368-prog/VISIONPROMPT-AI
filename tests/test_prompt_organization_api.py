"""API tests for the prompt favorites & tags endpoints (Day 17)."""
import json
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets", "test_video.mp4")

PROMPT = "Scene progression across 3 scenes, cinematic composition."
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


def _save(stored, prompt=PROMPT, negative=NEGATIVE, source="custom"):
    response = client.post(
        f"/api/videos/{stored}/prompt/history",
        json={"prompt": prompt, "negative_prompt": negative, "source": source},
    )
    assert response.status_code == 200
    return response.json()


def _favorite(stored, version):
    return client.post(f"/api/videos/{stored}/prompt/history/{version}/favorite")


def _unfavorite(stored, version):
    return client.delete(f"/api/videos/{stored}/prompt/history/{version}/favorite")


def _add_tags(stored, version, tags):
    return client.post(
        f"/api/videos/{stored}/prompt/history/{version}/tags", json={"tags": tags}
    )


def _remove_tags(stored, version, tags):
    return client.request(
        "DELETE",
        f"/api/videos/{stored}/prompt/history/{version}/tags",
        json={"tags": tags},
    )


def _organization(stored, version):
    return client.get(f"/api/videos/{stored}/prompt/history/{version}/organization")


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)


def test_favorite_returns_200():
    stored = _upload()
    _save(stored)
    response = _favorite(stored, 1)
    assert response.status_code == 200
    assert response.json() == {
        "video_filename": stored, "version": 1, "favorite": True,
    }


def test_favorite_idempotent():
    stored = _upload()
    _save(stored)
    assert _favorite(stored, 1).status_code == 200
    second = _favorite(stored, 1)
    assert second.status_code == 200
    assert second.json()["favorite"] is True


def test_unfavorite_returns_200():
    stored = _upload()
    _save(stored)
    _favorite(stored, 1)
    response = _unfavorite(stored, 1)
    assert response.status_code == 200
    assert response.json() == {
        "video_filename": stored, "version": 1, "favorite": False,
    }


def test_unfavorite_idempotent():
    stored = _upload()
    _save(stored)
    assert _unfavorite(stored, 1).status_code == 200
    assert _unfavorite(stored, 1).status_code == 200


def test_add_tags_returns_200():
    stored = _upload()
    _save(stored)
    response = _add_tags(stored, 1, [" Cinematic ", "AI", "cinematic", ""])
    assert response.status_code == 200
    assert response.json() == {
        "video_filename": stored, "version": 1, "tags": ["ai", "cinematic"],
    }


def test_remove_tags_returns_200():
    stored = _upload()
    _save(stored)
    _add_tags(stored, 1, ["ai", "cinematic"])
    response = _remove_tags(stored, 1, ["ai"])
    assert response.status_code == 200
    assert response.json() == {
        "video_filename": stored, "version": 1, "tags": ["cinematic"],
    }


def test_get_organization_returns_200():
    stored = _upload()
    _save(stored)
    _favorite(stored, 1)
    _add_tags(stored, 1, ["ai"])
    response = _organization(stored, 1)
    assert response.status_code == 200
    assert response.json() == {
        "video_filename": stored,
        "version": 1,
        "favorite": True,
        "tags": ["ai"],
    }


def test_list_favorites_returns_200():
    stored = _upload()
    _save(stored)
    _save(stored, prompt=PROMPT + " more")
    _favorite(stored, 2)
    response = client.get(f"/api/videos/{stored}/prompt/history/favorites")
    assert response.status_code == 200
    data = response.json()
    assert data["video_filename"] == stored
    assert data["favorites"] == [
        {"version": 2, "favorite": True, "tags": []}
    ]


def test_list_favorites_empty():
    stored = _upload()
    _save(stored)
    response = client.get(f"/api/videos/{stored}/prompt/history/favorites")
    assert response.status_code == 200
    assert response.json()["favorites"] == []


def test_tag_filter_returns_200():
    stored = _upload()
    _save(stored)
    _save(stored, prompt=PROMPT + " two")
    _add_tags(stored, 1, ["ai", "cinematic"])
    _add_tags(stored, 2, ["commercial"])
    response = client.get(f"/api/videos/{stored}/prompt/history/tag/ai")
    assert response.status_code == 200
    data = response.json()
    assert data["video_filename"] == stored
    assert data["tag"] == "ai"
    assert len(data["versions"]) == 1
    assert data["versions"][0]["version"] == 1
    assert data["versions"][0]["favorite"] is False
    assert data["versions"][0]["tags"] == ["ai", "cinematic"]


def test_tag_filter_missing_tag_empty():
    stored = _upload()
    _save(stored)
    response = client.get(f"/api/videos/{stored}/prompt/history/tag/missing")
    assert response.status_code == 200
    assert response.json()["versions"] == []


def test_tag_filter_no_substring_matching():
    stored = _upload()
    _save(stored)
    _add_tags(stored, 1, ["cinematic"])
    response = client.get(f"/api/videos/{stored}/prompt/history/tag/cine")
    assert response.status_code == 200
    assert response.json()["versions"] == []


def test_deleted_version_disappears_from_history_lists():
    stored = _upload()
    for i in range(3):
        _save(stored, prompt=f"{PROMPT} {i}")
    for v in (1, 2, 3):
        _favorite(stored, v)
        _add_tags(stored, v, ["ai"])
    delete = client.delete(f"/api/videos/{stored}/prompt/history/2")
    assert delete.status_code == 200
    favorites = client.get(
        f"/api/videos/{stored}/prompt/history/favorites"
    ).json()["favorites"]
    assert [f["version"] for f in favorites] == [1, 3]
    tagged = client.get(
        f"/api/videos/{stored}/prompt/history/tag/ai"
    ).json()["versions"]
    assert [t["version"] for t in tagged] == [1, 3]
    assert _organization(stored, 2).status_code == 404


def test_nonexistent_video_returns_404():
    assert _favorite("nonexistent.mp4", 1).status_code == 404
    assert _organization("nonexistent.mp4", 1).status_code == 404
    response = client.get("/api/videos/nonexistent.mp4/prompt/history/favorites")
    assert response.status_code == 404
    response = client.get("/api/videos/nonexistent.mp4/prompt/history/tag/ai")
    assert response.status_code == 404


def test_nonexistent_version_returns_404():
    stored = _upload()
    _save(stored)
    assert _favorite(stored, 99).status_code == 404
    assert _unfavorite(stored, 99).status_code == 404
    assert _add_tags(stored, 99, ["ai"]).status_code == 404
    assert _remove_tags(stored, 99, ["ai"]).status_code == 404
    assert _organization(stored, 99).status_code == 404


@pytest.mark.parametrize("bad_version", ["0", "-1"])
def test_invalid_version_returns_422(bad_version):
    stored = _upload()
    _save(stored)
    assert _favorite(stored, bad_version).status_code == 422
    assert _organization(stored, bad_version).status_code == 422
    assert _add_tags(stored, bad_version, ["ai"]).status_code == 422


def test_non_integer_version_returns_422():
    stored = _upload()
    _save(stored)
    assert _favorite(stored, "abc").status_code == 422


def test_invalid_tag_payload_returns_422():
    stored = _upload()
    _save(stored)
    response = client.post(
        f"/api/videos/{stored}/prompt/history/1/tags", json={}
    )
    assert response.status_code == 422
    response = client.post(
        f"/api/videos/{stored}/prompt/history/1/tags",
        json={"tags": "ai"},
    )
    assert response.status_code == 422
    response = client.post(
        f"/api/videos/{stored}/prompt/history/1/tags"
    )
    assert response.status_code == 422


def test_invalid_tag_item_returns_422():
    stored = _upload()
    _save(stored)
    response = _add_tags(stored, 1, ["ai", 42])
    assert response.status_code == 422
    response = _add_tags(stored, 1, [{"nested": "tag"}])
    assert response.status_code == 422


def test_empty_and_whitespace_tags_ignored():
    stored = _upload()
    _save(stored)
    response = _add_tags(stored, 1, ["", "   ", "ai"])
    assert response.status_code == 200
    assert response.json()["tags"] == ["ai"]


def test_tag_max_length_returns_422():
    stored = _upload()
    _save(stored)
    response = _add_tags(stored, 1, ["x" * 51])
    assert response.status_code == 422


def test_path_traversal_returns_404():
    response = client.post(
        "/api/videos/../../../etc/passwd/prompt/history/1/favorite"
    )
    assert response.status_code in (400, 404)
    response = client.get(
        "/api/videos/../../../etc/passwd/prompt/history/favorites"
    )
    assert response.status_code in (400, 404)
    response = client.get(
        "/api/videos/../../../etc/passwd/prompt/history/tag/ai"
    )
    assert response.status_code in (400, 404)


def test_route_collision_favorites_not_captured_by_version():
    """GET /history/favorites must not be captured by /history/{version}."""
    stored = _upload()
    _save(stored)
    response = client.get(f"/api/videos/{stored}/prompt/history/favorites")
    assert response.status_code == 200
    data = response.json()
    assert "favorites" in data
    assert "version_id" not in data


def test_route_collision_tag_not_captured_by_version():
    """GET /history/tag/{tag} must not be captured by /history/{version}."""
    stored = _upload()
    _save(stored)
    _add_tags(stored, 1, ["ai"])
    response = client.get(f"/api/videos/{stored}/prompt/history/tag/ai")
    assert response.status_code == 200
    data = response.json()
    assert "versions" in data and "tag" in data
    assert "version_id" not in data


def test_numeric_version_route_still_works():
    stored = _upload()
    _save(stored)
    response = client.get(f"/api/videos/{stored}/prompt/history/1")
    assert response.status_code == 200
    assert "version_id" in response.json()
    org = _organization(stored, 1)
    assert org.status_code == 200
    assert "version_id" not in org.json()


def test_no_absolute_paths():
    stored = _upload()
    _save(stored)
    _favorite(stored, 1)
    _add_tags(stored, 1, ["ai"])
    payloads = [
        _organization(stored, 1).json(),
        client.get(f"/api/videos/{stored}/prompt/history/favorites").json(),
        client.get(f"/api/videos/{stored}/prompt/history/tag/ai").json(),
        _favorite(stored, 1).json(),
        _add_tags(stored, 1, ["meta"]).json(),
    ]
    for payload in payloads:
        serialized = json.dumps(payload)
        assert "C:/" not in serialized
        assert "C:\\" not in serialized
        assert "/home" not in serialized
        assert "/Users" not in serialized
        assert "/var" not in serialized


def test_no_fabricated_information():
    """Organization metadata must contain only user-provided tags."""
    stored = _upload()
    _save(stored)
    _favorite(stored, 1)
    _add_tags(stored, 1, ["mytag"])
    org = _organization(stored, 1).json()
    assert org["tags"] == ["mytag"]
    text = json.dumps(org).lower()
    for word in ["person", "character", "dialogue", "walking", "park",
                 "city", "sunset", "brand", "product", "voiceover",
                 "cinematic", "scene", "camera"]:
        assert word not in text, f"fabricated: {word}"


def test_multi_video_isolation():
    stored_a = _upload()
    stored_b = _upload()
    _save(stored_a)
    _save(stored_b)
    _favorite(stored_a, 1)
    _add_tags(stored_a, 1, ["ai"])
    _add_tags(stored_b, 1, ["commercial"])
    org_a = _organization(stored_a, 1).json()
    org_b = _organization(stored_b, 1).json()
    assert org_a == {"video_filename": stored_a, "version": 1,
                     "favorite": True, "tags": ["ai"]}
    assert org_b == {"video_filename": stored_b, "version": 1,
                     "favorite": False, "tags": ["commercial"]}
    favs_b = client.get(
        f"/api/videos/{stored_b}/prompt/history/favorites"
    ).json()["favorites"]
    assert favs_b == []


def test_day16_history_endpoints_still_work():
    """Day 16 history endpoints must remain functional after Day 17."""
    stored = _upload()
    first = _save(stored, prompt="alpha beta gamma")
    _save(stored, prompt="alpha beta delta")
    listing = client.get(f"/api/videos/{stored}/prompt/history")
    assert listing.status_code == 200
    assert [v["version"] for v in listing.json()["versions"]] == [1, 2]
    single = client.get(f"/api/videos/{stored}/prompt/history/1")
    assert single.status_code == 200
    assert single.json()["prompt"] == first["prompt"]
    compare = client.get(
        f"/api/videos/{stored}/prompt/history/compare/1/2"
    )
    assert compare.status_code == 200
    assert compare.json()["changed"] is True
    deleted = client.delete(f"/api/videos/{stored}/prompt/history/2")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_day1_15_endpoints_still_work():
    """Day 1-15 endpoints must remain functional after Day 17."""
    stored = _upload()
    assert client.get("/api/health").status_code == 200
    assert client.get(f"/api/videos/{stored}/metadata").status_code == 200
    assert client.post(f"/api/videos/{stored}/prompt?style=cinematic").status_code == 200
    assert client.post(f"/api/videos/{stored}/intelligence").status_code == 200
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
    assert _save(stored).get("version") == 1
    assert _favorite(stored, 1).status_code == 200
