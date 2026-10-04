"""API tests for POST /videos/{stored_filename}/prompt/reconstruct (P2-01)."""
import json
import os
import shutil

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)
TEST_VIDEO_PATH = os.path.join(
    os.path.dirname(__file__), "test_assets", "test_video.mp4"
)
UPLOADS_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "backend", "storage", "uploads",
    )
)
FRAME_STORAGE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "backend", "storage", "frames",
    )
)
ANALYSIS_DOMAINS = [
    "shots", "subjects", "actions", "environment", "camera", "lens",
    "lighting", "color", "composition", "visual_style", "audio",
    "characters",
]
BLOCK_KEYS = ["availability", "source", "value", "confidence", "note"]
VALID_AVAILABILITIES = {"observed", "estimated", "unavailable"}
UPLOADED = []


def _create_real_mp4(path: str) -> bool:
    import imageio_ffmpeg
    import subprocess
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        subprocess.run(
            [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=3",
             "-y", path],
            capture_output=True, timeout=15,
        )
        return os.path.exists(path) and os.path.getsize(path) > 0
    except Exception:
        return False


def _upload(extract: bool = True) -> str:
    if not os.path.exists(TEST_VIDEO_PATH):
        _create_real_mp4(TEST_VIDEO_PATH)
    with open(TEST_VIDEO_PATH, "rb") as f:
        upload = client.post(
            "/api/videos/upload",
            files={"file": ("test.mp4", f, "video/mp4")},
        )
    assert upload.status_code == 200
    stored = upload.json()["video"]["stored_filename"]
    UPLOADED.append(stored)
    if extract:
        response = client.post(
            f"/api/videos/{stored}/frames/extract?interval_seconds=1"
        )
        assert response.status_code == 200
    return stored


def _reconstruct(stored, **params):
    return client.post(
        f"/api/videos/{stored}/prompt/reconstruct", params=params
    )


def _cleanup():
    for stored in UPLOADED:
        path = os.path.join(UPLOADS_DIR, stored)
        if os.path.exists(path):
            os.remove(path)
    UPLOADED.clear()
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)
    if os.path.exists(FRAME_STORAGE_DIR):
        for d in os.listdir(FRAME_STORAGE_DIR):
            full = os.path.join(FRAME_STORAGE_DIR, d)
            if os.path.isdir(full):
                shutil.rmtree(full, ignore_errors=True)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    _cleanup()


def _walk_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _walk_strings(key)
            yield from _walk_strings(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_strings(item)


# ----------------------------------------------------------------------
# happy path
# ----------------------------------------------------------------------

class TestHappyPath:
    def test_default_request(self):
        stored = _upload()
        response = _reconstruct(stored)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == (
            "Prompt reconstruction completed successfully"
        )

    def test_top_level_keys(self):
        stored = _upload()
        data = _reconstruct(stored).json()
        assert list(data.keys()) == [
            "success", "message", "video_filename", "depth", "style",
            "video_information", "analysis", "provider_status",
            "confidence", "prompt", "quality", "readiness",
        ]

    def test_identity_fields(self):
        stored = _upload()
        data = _reconstruct(stored, depth="deep", style="realistic").json()
        assert data["video_filename"] == stored
        assert data["depth"] == "deep"
        assert data["style"] == "realistic"

    @pytest.mark.parametrize("depth", ["quick", "standard", "deep"])
    def test_all_depths_accepted(self, depth):
        stored = _upload()
        response = _reconstruct(stored, depth=depth)
        assert response.status_code == 200
        assert response.json()["depth"] == depth

    @pytest.mark.parametrize("style", ["cinematic", "realistic", "commercial"])
    def test_all_styles_accepted(self, style):
        stored = _upload()
        response = _reconstruct(stored, style=style)
        assert response.status_code == 200
        assert response.json()["style"] == style

    def test_depth_and_style_combined(self):
        stored = _upload()
        response = _reconstruct(stored, depth="quick", style="commercial")
        assert response.status_code == 200
        data = response.json()
        assert data["depth"] == "quick"
        assert data["style"] == "commercial"


# ----------------------------------------------------------------------
# validation
# ----------------------------------------------------------------------

class TestValidation:
    @pytest.mark.parametrize("depth", ["", "turbo", "FAST", "deepish", "5"])
    def test_invalid_depth_400(self, depth):
        stored = _upload()
        response = _reconstruct(stored, depth=depth)
        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Invalid depth. Must be one of: deep, quick, standard"
        )

    @pytest.mark.parametrize("style", ["", "gritty", "CINEMATIC", "hd"])
    def test_invalid_style_400(self, style):
        stored = _upload()
        response = _reconstruct(stored, style=style)
        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Invalid style. Must be one of: cinematic, commercial, realistic"
        )

    def test_invalid_extension_400(self):
        response = _reconstruct("notavideo")
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid video filename."

    def test_nonexistent_video_404(self):
        response = _reconstruct("ghost_video_xyz.mp4")
        assert response.status_code == 404
        assert response.json()["detail"] == "Video file not found."

    def test_path_traversal_404(self):
        response = _reconstruct("../../../etc/passwd.mp4")
        assert response.status_code == 404

    def test_depth_checked_before_file(self):
        response = _reconstruct("ghost_video_xyz.mp4", depth="turbo")
        assert response.status_code == 400
        assert "Invalid depth" in response.json()["detail"]


# ----------------------------------------------------------------------
# response structure
# ----------------------------------------------------------------------

class TestResponseStructure:
    @pytest.fixture
    def data(self):
        stored = _upload()
        return _reconstruct(stored).json()

    def test_video_information(self, data):
        block = data["video_information"]
        assert list(block.keys()) == BLOCK_KEYS
        assert block["availability"] == "observed"
        assert block["source"] == "ffprobe"
        value = block["value"]
        assert value["filename"] == data["video_filename"]
        assert value["duration_seconds"] > 0
        assert value["width"] == 320
        assert value["height"] == 240
        assert value["file_size_bytes"] > 0

    def test_analysis_domains(self, data):
        assert list(data["analysis"].keys()) == ANALYSIS_DOMAINS

    def test_block_shapes_and_availability(self, data):
        for domain in ANALYSIS_DOMAINS:
            block = data["analysis"][domain]
            assert list(block.keys()) == BLOCK_KEYS, domain
            assert block["availability"] in VALID_AVAILABILITIES, domain

    def test_confidence_partition(self, data):
        conf = data["confidence"]
        assert list(conf.keys()) == [
            "overall", "observed_domains", "estimated_domains",
            "unavailable_domains", "uncertainty_notes",
        ]
        combined = (
            conf["observed_domains"]
            + conf["estimated_domains"]
            + conf["unavailable_domains"]
        )
        assert sorted(combined) == sorted(ANALYSIS_DOMAINS)
        assert len(combined) == len(set(combined))
        assert conf["overall"] in {"high", "medium", "low"}

    def test_prompt_block(self, data):
        prompt = data["prompt"]
        assert set(prompt.keys()) == {
            "production_prompt", "negative_prompt", "style", "sections",
            "source",
        }
        assert prompt["production_prompt"].strip()
        assert prompt["negative_prompt"].strip()
        assert prompt["source"] == "advanced_prompt_service"
        assert set(prompt["sections"].keys()) == {
            "subject", "action", "environment", "camera", "lighting",
            "visual_style", "color", "audio", "composition",
        }

    def test_quality_block(self, data):
        quality = data["quality"]
        assert isinstance(quality["overall_score"], int)
        assert 0 <= quality["overall_score"] <= 100
        assert 0 <= quality["completeness_percentage"] <= 100
        assert len(quality["dimensions"]) == 9

    def test_readiness_block(self, data):
        readiness = data["readiness"]
        assert readiness["status"] in {"ready", "needs_attention"}
        assert len(readiness["checklist"]) == 9
        assert isinstance(readiness["suggestions"], list)

    def test_provider_status(self, data):
        provider = data["provider_status"]
        assert list(provider.keys()) == [
            "vision_provider", "audio_provider",
            "structured_visual_details_available", "note",
        ]
        assert provider["vision_provider"] == settings.vision_provider
        assert provider["audio_provider"] == settings.audio_provider


# ----------------------------------------------------------------------
# AI safety: honest unavailable domains under mock providers
# ----------------------------------------------------------------------

class TestAISafety:
    def test_mock_vision_domains_marked_unavailable(self):
        if settings.vision_provider != "mock":
            pytest.skip("mock vision provider not configured")
        stored = _upload()
        data = _reconstruct(stored).json()
        for domain in ["environment", "lighting", "visual_style",
                       "actions", "camera"]:
            block = data["analysis"][domain]
            assert block["availability"] == "unavailable", domain
            assert block["note"].strip(), domain

    def test_mock_provider_note_present(self):
        if settings.vision_provider != "mock":
            pytest.skip("mock vision provider not configured")
        stored = _upload()
        data = _reconstruct(stored).json()
        assert "local mock" in data["provider_status"]["note"]
        assert any(
            "local mock" in note
            for note in data["confidence"]["uncertainty_notes"]
        )

    def test_no_fabricated_domain_values(self):
        stored = _upload()
        data = _reconstruct(stored).json()
        for domain in ["environment", "lighting", "visual_style"]:
            block = data["analysis"][domain]
            if block["availability"] == "unavailable":
                assert block["value"] is None, domain

    def test_scenes_observed_from_frames(self):
        stored = _upload()
        data = _reconstruct(stored).json()
        assert data["analysis"]["shots"]["availability"] == "observed"
        assert data["analysis"]["shots"]["value"]["scenes_detected"] >= 1

    def test_audio_observed(self):
        stored = _upload()
        data = _reconstruct(stored).json()
        audio = data["analysis"]["audio"]
        assert audio["availability"] == "observed"
        assert "has_audio" in audio["value"]

    def test_optional_domains_unavailable_before_wiring(self):
        stored = _upload()
        data = _reconstruct(stored).json()
        for domain in ["lens", "characters"]:
            assert data["analysis"][domain]["availability"] == "unavailable"
            assert data["analysis"][domain]["note"].strip()

    def test_video_without_frames(self):
        stored = _upload(extract=False)
        data = _reconstruct(stored).json()
        shots = data["analysis"]["shots"]
        assert shots["availability"] == "unavailable"
        assert "No scenes were detected" in shots["note"]
        subjects = data["analysis"]["subjects"]
        assert subjects["availability"] == "unavailable"
        assert data["prompt"]["production_prompt"].strip()


# ----------------------------------------------------------------------
# style wording
# ----------------------------------------------------------------------

class TestStyleWording:
    @pytest.mark.parametrize("style,term", [
        ("cinematic", "cinematic composition"),
        ("realistic", "realistic presentation"),
        ("commercial", "commercial presentation"),
    ])
    def test_style_term_in_prompt(self, style, term):
        stored = _upload()
        data = _reconstruct(stored, style=style).json()
        assert term in data["prompt"]["production_prompt"].lower()
        assert style in data["prompt"]["sections"]["visual_style"].lower()


# ----------------------------------------------------------------------
# determinism + read-only safety
# ----------------------------------------------------------------------

class TestDeterminismAndSafety:
    def test_two_calls_identical(self):
        stored = _upload()
        first = _reconstruct(stored).json()
        second = _reconstruct(stored).json()
        assert json.dumps(first, sort_keys=True) == json.dumps(
            second, sort_keys=True
        )

    def test_no_absolute_paths_anywhere(self):
        stored = _upload()
        data = _reconstruct(stored).json()
        for text in _walk_strings(data):
            for bad in ("C:\\", "C:/", "/home", "/Users", "/var/",
                        "storage/uploads", "storage/frames", "test_assets"):
                assert bad not in text, f"path leak: {bad}"

    def test_no_internal_leaks(self):
        stored = _upload()
        response = _reconstruct(stored)
        body = response.text
        for bad in ("Traceback", "app.services", "app.api",
                    "site-packages", "DEBUG"):
            assert bad not in body, f"internal leak: {bad}"

    def test_history_unchanged(self):
        stored = _upload()
        before = client.get(f"/api/videos/{stored}/prompt/history").json()
        _reconstruct(stored)
        after = client.get(f"/api/videos/{stored}/prompt/history").json()
        assert before == after

    def test_storage_readonly(self):
        stored = _upload()
        uploads_before = sorted(os.listdir(UPLOADS_DIR))
        frames_before = sorted(os.listdir(FRAME_STORAGE_DIR))
        _reconstruct(stored)
        assert sorted(os.listdir(UPLOADS_DIR)) == uploads_before
        assert sorted(os.listdir(FRAME_STORAGE_DIR)) == frames_before

    def test_no_favorites_side_effect(self):
        stored = _upload()
        before = client.get(
            f"/api/videos/{stored}/prompt/history/favorites"
        ).json()
        _reconstruct(stored)
        after = client.get(
            f"/api/videos/{stored}/prompt/history/favorites"
        ).json()
        assert before == after


# ----------------------------------------------------------------------
# multiple videos
# ----------------------------------------------------------------------

class TestMultipleVideos:
    def test_isolation_between_videos(self):
        stored_a = _upload()
        stored_b = _upload()
        data_a = _reconstruct(stored_a).json()
        data_b = _reconstruct(stored_b).json()
        assert data_a["video_filename"] == stored_a
        assert data_b["video_filename"] == stored_b
        data_a2 = _reconstruct(stored_a).json()
        assert data_a2["video_filename"] == stored_a
        assert json.dumps(data_a, sort_keys=True) == json.dumps(
            data_a2, sort_keys=True
        )


# ----------------------------------------------------------------------
# regression: existing endpoints keep working
# ----------------------------------------------------------------------

class TestRegression:
    def test_health(self):
        assert client.get("/api/health").status_code == 200

    def test_intelligence_still_works(self):
        stored = _upload()
        response = client.post(f"/api/videos/{stored}/intelligence")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_advanced_prompt_still_works(self):
        stored = _upload()
        response = client.post(f"/api/videos/{stored}/advanced-prompt")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_prompt_quality_still_works(self):
        stored = _upload()
        response = client.post(
            f"/api/videos/{stored}/prompt/quality",
            json={"prompt": "A person walks in a park at noon."},
        )
        assert response.status_code == 200

    def test_prompt_readiness_still_works(self):
        stored = _upload()
        response = client.post(
            f"/api/videos/{stored}/prompt/readiness",
            json={"prompt": "A person walks in a park at noon."},
        )
        assert response.status_code == 200

    def test_prompt_history_roundtrip(self):
        stored = _upload()
        post = client.post(
            f"/api/videos/{stored}/prompt/history",
            json={"prompt": "A test prompt.", "negative_prompt": "",
                  "source": "custom", "operation": ""},
        )
        assert post.status_code == 200
        listing = client.get(f"/api/videos/{stored}/prompt/history").json()
        assert len(listing["versions"]) == 1

    def test_readiness_report_export_still_works(self):
        stored = _upload()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/readiness/report/export",
            params={"format": "json"},
        )
        assert response.status_code == 200

    def test_reconstruct_coexists_with_history_routes(self):
        stored = _upload()
        r1 = _reconstruct(stored)
        r2 = client.get(f"/api/videos/{stored}/prompt/history/1")
        assert r1.status_code == 200
        assert r2.status_code in (200, 404)
