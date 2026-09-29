"""API tests for the prompt search endpoint (Day 18)."""
import json
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_assets", "test_video.mp4")

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


def _save(stored, prompt="alpha beta gamma", source="custom", operation=""):
    response = client.post(
        f"/api/videos/{stored}/prompt/history",
        json={"prompt": prompt, "negative_prompt": NEGATIVE,
              "source": source, "operation": operation},
    )
    assert response.status_code == 200
    return response.json()


def _search(stored, **params):
    return client.get(f"/api/videos/{stored}/prompt/search", params=params)


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


def test_search_returns_200():
    stored = _upload()
    _save(stored)
    response = _search(stored)
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_no_filters_returns_all_versions():
    stored = _upload()
    _save(stored, prompt="one alpha")
    _save(stored, prompt="two beta")
    _save(stored, prompt="three gamma")
    data = _search(stored).json()
    assert data["count"] == 3
    assert [r["version"] for r in data["results"]] == [1, 2, 3]


def test_query_filter():
    stored = _upload()
    _save(stored, prompt="Cinematic Composition")
    _save(stored, prompt="documentary style")
    data = _search(stored, query="cinematic").json()
    assert data["count"] == 1
    assert data["results"][0]["prompt"] == "Cinematic Composition"
    assert data["filters"]["query"] == "cinematic"


def test_empty_query_returns_all():
    stored = _upload()
    _save(stored, prompt="alpha")
    assert _search(stored, query="").json()["count"] == 1
    assert _search(stored, query="   ").json()["count"] == 1


def test_query_no_match_empty_results():
    stored = _upload()
    _save(stored, prompt="alpha beta")
    data = _search(stored, query="zzz").json()
    assert data["count"] == 0
    assert data["results"] == []


def test_source_filter():
    stored = _upload()
    _save(stored, prompt="alpha", source="custom")
    _save(stored, prompt="beta", source="refinement")
    data = _search(stored, source="refinement").json()
    assert data["count"] == 1
    assert data["results"][0]["source"] == "refinement"
    assert data["filters"]["source"] == "refinement"


def test_invalid_source_returns_422():
    stored = _upload()
    _save(stored)
    response = _search(stored, source="database")
    assert response.status_code == 422


def test_operation_filter():
    stored = _upload()
    _save(stored, prompt="alpha", operation="shorten")
    _save(stored, prompt="beta", operation="expand")
    data = _search(stored, operation="shorten").json()
    assert data["count"] == 1
    assert data["results"][0]["operation"] == "shorten"


def test_favorite_filter_true():
    stored = _upload()
    _save(stored, prompt="alpha")
    _save(stored, prompt="beta")
    _favorite(stored, 2)
    data = _search(stored, favorite=True).json()
    assert data["count"] == 1
    assert data["results"][0]["version"] == 2
    assert data["results"][0]["favorite"] is True
    assert data["filters"]["favorite"] is True


def test_favorite_filter_false():
    stored = _upload()
    _save(stored, prompt="alpha")
    _save(stored, prompt="beta")
    _favorite(stored, 1)
    data = _search(stored, favorite=False).json()
    assert [r["version"] for r in data["results"]] == [2]
    assert data["results"][0]["favorite"] is False


def test_invalid_boolean_returns_422():
    stored = _upload()
    _save(stored)
    response = _search(stored, favorite="notabool")
    assert response.status_code == 422


def test_tag_filter():
    stored = _upload()
    _save(stored, prompt="alpha")
    _save(stored, prompt="beta")
    _add_tags(stored, 1, ["ai", "cinematic"])
    _add_tags(stored, 2, ["commercial"])
    data = _search(stored, tag="ai").json()
    assert data["count"] == 1
    assert data["results"][0]["version"] == 1
    assert data["results"][0]["tags"] == ["ai", "cinematic"]
    assert data["filters"]["tag"] == "ai"


def test_tag_filter_normalized_and_exact():
    stored = _upload()
    _save(stored, prompt="alpha")
    _add_tags(stored, 1, ["cinematic"])
    assert _search(stored, tag="  Cinematic ").json()["count"] == 1
    assert _search(stored, tag="cine").json()["count"] == 0
    assert _search(stored, tag="cinematicx").json()["count"] == 0


def test_whitespace_only_tag_behaves_as_no_filter():
    stored = _upload()
    _save(stored, prompt="alpha")
    assert _search(stored, tag="   ").json()["count"] == 1


def test_version_range():
    stored = _upload()
    for i in range(5):
        _save(stored, prompt=f"prompt {i}")
    data = _search(stored, min_version=2, max_version=4).json()
    assert [r["version"] for r in data["results"]] == [2, 3, 4]
    assert data["filters"]["min_version"] == 2
    assert data["filters"]["max_version"] == 4
    assert _search(stored, min_version=3).json()["count"] == 3
    assert _search(stored, max_version=2).json()["count"] == 2


@pytest.mark.parametrize("bad_value", ["0", "-1"])
def test_invalid_version_range_returns_422(bad_value):
    stored = _upload()
    _save(stored)
    assert _search(stored, min_version=bad_value).status_code == 422
    assert _search(stored, max_version=bad_value).status_code == 422


def test_non_integer_version_returns_422():
    stored = _upload()
    _save(stored)
    assert _search(stored, min_version="abc").status_code == 422


def test_min_greater_than_max_returns_422():
    stored = _upload()
    _save(stored)
    response = _search(stored, min_version=3, max_version=2)
    assert response.status_code == 422


def test_combined_filters():
    stored = _upload()
    # v1: refinement + favorite + tag ai + "cinematic" text
    _save(stored, prompt="cinematic composition", source="refinement",
          operation="shorten")
    _favorite(stored, 1)
    _add_tags(stored, 1, ["ai", "cinematic"])
    # v2: refinement + tag ai + text but NOT favorite
    _save(stored, prompt="cinematic lighting", source="refinement")
    _add_tags(stored, 2, ["ai"])
    # v3: favorite + tag + text but wrong source
    _save(stored, prompt="cinematic sound", source="custom")
    _favorite(stored, 3)
    _add_tags(stored, 3, ["ai"])
    # v4: refinement + favorite but no text match
    _save(stored, prompt="documentary style", source="refinement")
    _favorite(stored, 4)

    data = _search(
        stored, query="cinematic", source="refinement",
        favorite=True, tag="ai",
    ).json()
    assert data["count"] == 1
    assert data["results"][0]["version"] == 1
    assert data["results"][0]["operation"] == "shorten"


def test_empty_result_structure():
    stored = _upload()
    _save(stored, prompt="alpha beta")
    data = _search(stored, query="zzz").json()
    assert data["video_filename"] == stored
    assert data["count"] == 0
    assert data["results"] == []
    assert set(data["filters"].keys()) == {
        "query", "source", "operation", "favorite", "tag",
        "min_version", "max_version",
    }


def test_response_structure():
    stored = _upload()
    _save(stored, prompt="alpha beta", source="template", operation="ai_video")
    _favorite(stored, 1)
    _add_tags(stored, 1, ["ai"])
    data = _search(stored).json()
    assert set(data.keys()) == {"video_filename", "filters", "count", "results"}
    assert data["video_filename"] == stored
    assert data["count"] == 1
    result = data["results"][0]
    for key in ["version_id", "video_filename", "version", "source", "operation",
                "prompt", "negative_prompt", "created_at", "metadata",
                "favorite", "tags"]:
        assert key in result, f"missing {key}"
    assert result["favorite"] is True
    assert result["tags"] == ["ai"]


def test_deterministic_result_ordering():
    stored = _upload()
    for i in range(5):
        _save(stored, prompt=f"prompt {i} alpha")
    first = _search(stored, query="alpha").json()
    second = _search(stored, query="alpha").json()
    assert first == second
    assert [r["version"] for r in first["results"]] == [1, 2, 3, 4, 5]


def test_invalid_sort_returns_422():
    stored = _upload()
    _save(stored)
    response = _search(stored, sort="random")
    assert response.status_code == 422


def test_sort_options_work():
    stored = _upload()
    for i in range(3):
        _save(stored, prompt=f"prompt {i}")
    desc = _search(stored, sort="version_desc").json()
    assert [r["version"] for r in desc["results"]] == [3, 2, 1]
    asc = _search(stored, sort="version_asc").json()
    assert [r["version"] for r in asc["results"]] == [1, 2, 3]


def test_deleted_versions_excluded():
    stored = _upload()
    _save(stored, prompt="alpha one")
    _save(stored, prompt="alpha two")
    _save(stored, prompt="alpha three")
    _favorite(stored, 2)
    delete = client.delete(f"/api/videos/{stored}/prompt/history/2")
    assert delete.status_code == 200
    data = _search(stored, query="alpha").json()
    assert [r["version"] for r in data["results"]] == [1, 3]
    assert _search(stored, favorite=True).json()["count"] == 0


def test_nonexistent_video_returns_404():
    response = client.get("/api/videos/nonexistent.mp4/prompt/search")
    assert response.status_code == 404
    response = client.get(
        "/api/videos/nonexistent.mp4/prompt/search", params={"query": "alpha"}
    )
    assert response.status_code == 404


def test_path_traversal_returns_404():
    response = client.get("/api/videos/../../../etc/passwd/prompt/search")
    assert response.status_code in (400, 404)


def test_multi_video_isolation():
    stored_a = _upload()
    stored_b = _upload()
    _save(stored_a, prompt="shared alpha text")
    _save(stored_b, prompt="shared alpha text")
    _favorite(stored_a, 1)
    _add_tags(stored_a, 1, ["ai"])
    data_a = _search(stored_a, query="alpha").json()
    data_b = _search(stored_b, query="alpha").json()
    assert data_a["count"] == 1
    assert data_b["count"] == 1
    assert data_a["results"][0]["favorite"] is True
    assert data_a["results"][0]["tags"] == ["ai"]
    assert data_b["results"][0]["favorite"] is False
    assert data_b["results"][0]["tags"] == []
    assert data_a["results"][0]["video_filename"] == stored_a
    assert data_b["results"][0]["video_filename"] == stored_b


def test_no_absolute_paths():
    stored = _upload()
    _save(stored, prompt="alpha beta")
    _favorite(stored, 1)
    _add_tags(stored, 1, ["ai"])
    serialized = json.dumps(_search(stored, query="alpha").json())
    assert "C:/" not in serialized
    assert "C:\\" not in serialized
    assert "/home" not in serialized
    assert "/Users" not in serialized
    assert "/var" not in serialized


def test_no_fabricated_information():
    stored = _upload()
    _save(stored, prompt="Scene progression across 1 scenes.")
    data = _search(stored).json()
    text = json.dumps(data).lower()
    for word in ["person", "character", "dialogue", "walking", "park",
                 "city", "sunset", "brand", "product", "voiceover"]:
        assert word not in text, f"fabricated: {word}"


def test_day16_history_endpoints_still_work():
    stored = _upload()
    _save(stored, prompt="alpha beta gamma")
    _save(stored, prompt="alpha beta delta")
    assert client.get(f"/api/videos/{stored}/prompt/history").status_code == 200
    single = client.get(f"/api/videos/{stored}/prompt/history/1")
    assert single.status_code == 200
    assert single.json()["prompt"] == "alpha beta gamma"
    compare = client.get(f"/api/videos/{stored}/prompt/history/compare/1/2")
    assert compare.status_code == 200
    assert compare.json()["changed"] is True
    assert client.delete(f"/api/videos/{stored}/prompt/history/2").status_code == 200


def test_day17_organization_endpoints_still_work():
    stored = _upload()
    _save(stored)
    assert _favorite(stored, 1).status_code == 200
    assert _add_tags(stored, 1, ["ai"]).status_code == 200
    org = client.get(f"/api/videos/{stored}/prompt/history/1/organization")
    assert org.status_code == 200
    assert org.json()["favorite"] is True
    favorites = client.get(f"/api/videos/{stored}/prompt/history/favorites")
    assert favorites.status_code == 200
    assert favorites.json()["favorites"][0]["version"] == 1
    by_tag = client.get(f"/api/videos/{stored}/prompt/history/tag/ai")
    assert by_tag.status_code == 200
    assert by_tag.json()["versions"][0]["version"] == 1


def test_day1_15_endpoints_still_work():
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
        f"/api/videos/{stored}/prompt/template", json={"template": "ai_video"}
    ).status_code == 200
