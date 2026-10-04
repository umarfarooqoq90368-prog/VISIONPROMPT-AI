"""API tests for the prompt readiness report export endpoint (Day 30)."""
import json
import os
import re

import pytest
from fastapi.testclient import TestClient
from app.main import app

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
WEAK_CAM = ("Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, tracking only, soft lighting with rim light and "
            "golden hour glow, vibrant teal and orange palette with warm "
            "tones, layered foreground and rule of thirds composition, "
            "ambient sound with quiet music score.")
W_CAMLESS = ("Cinematic film grain style portrait of a person, the subject "
             "walking, looking around and gesturing in an outdoor forest "
             "street, soft lighting with rim light and golden hour glow, "
             "vibrant teal and orange palette with warm tones, layered "
             "foreground and rule of thirds composition, ambient sound "
             "with quiet music score.")
CITY = "A person walks through a city street."
MINIMAL = "nothing specific at all"

REPORT_TOP = {
    "video_filename", "versions_analyzed", "report", "timeline", "summary",
}

FORMATS = ("json", "markdown", "txt")

MEDIA_TYPES = {
    "json": "application/json",
    "markdown": "text/markdown",
    "txt": "text/plain",
}

FILENAMES = {
    "json": "visionprompt_readiness_report.json",
    "markdown": "visionprompt_readiness_report.md",
    "txt": "visionprompt_readiness_report.txt",
}

FORBIDDEN_WORDS = [
    "best", "worst", "winner", "loser", "superior", "inferior",
    "better", "worse", "improved", "degraded", "recommended",
    "preferred", "optimal",
]

INTERNAL_NAMES = [
    "PromptReadinessExportService", "PromptReadinessReportService",
    "PromptReadinessSnapshotService", "PromptReadinessTimelineService",
    "PromptReadinessChangeService", "PromptReadinessHistoryService",
    "PromptReadinessService", "PromptQualityService",
    "PromptImprovementService", "PromptOrganizationService",
    "PromptHistoryService", "readiness_report_service",
    "readiness_snapshot_service", "readiness_timeline_service",
    "history_service", "organization_service", "report_service",
    "storage/uploads", "BytesIO", "Traceback", "os.environ",
]

PATH_MARKERS = ["C:/", "C:\\", "/home", "/Users", "/var/"]


def _fmt_leaf(value):
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _leaves(obj):
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _leaves(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _leaves(value)
    else:
        yield obj


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


def _url(stored):
    return (f"/api/videos/{stored}/prompt/history/readiness/report"
            f"/export")


def _export(stored, fmt="json", versions=None):
    params = {"format": fmt}
    if versions is not None:
        params["versions"] = versions
    return client.get(_url(stored), params=params)


def _export_raw(stored, params):
    return client.get(_url(stored), params=params)


def _report(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness/report",
        params=params,
    )


def _history(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness", params=params,
    )


def _timeline(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness/timeline",
        params=params,
    )


def _snapshot(stored, versions=None):
    params = None if versions is None else {"versions": versions}
    return client.get(
        f"/api/videos/{stored}/prompt/history/readiness/snapshot",
        params=params,
    )


def _change(stored, a, b):
    return client.get(
        f"/api/videos/{stored}/prompt/history/compare/{a}/{b}/readiness"
    )


def _d19_export(stored, version, fmt):
    return client.get(
        f"/api/videos/{stored}/prompt/history/{version}/export",
        params={"format": fmt},
    )


def _package(stored, version):
    return client.get(
        f"/api/videos/{stored}/prompt/history/{version}/package"
    )


def _quality(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/quality",
                       json={"prompt": prompt})


def _readiness(stored, prompt):
    return client.post(f"/api/videos/{stored}/prompt/readiness",
                       json={"prompt": prompt})


def _versions(stored=None):
    """Upload and save the standard 5-version set."""
    stored = stored or _upload()
    for prompt in (FULL, WEAK_CAM, W_CAMLESS, CITY, MINIMAL):
        _save(stored, prompt)
    return stored


def _marked(stored=None):
    """Standard 5-version set with favorites and tags."""
    stored = _versions(stored)
    assert client.post(
        f"/api/videos/{stored}/prompt/history/1/favorite").status_code == 200
    assert client.post(
        f"/api/videos/{stored}/prompt/history/1/tags",
        json={"tags": [" Cinematic ", "ai"]},
    ).json()["tags"] == ["ai", "cinematic"]
    assert client.post(
        f"/api/videos/{stored}/prompt/history/3/tags",
        json={"tags": ["final"]},
    ).json()["tags"] == ["final"]
    return stored


@pytest.fixture(autouse=True)
def setup_and_teardown():
    _create_real_mp4(TEST_VIDEO_PATH)
    yield
    if os.path.exists(TEST_VIDEO_PATH):
        os.remove(TEST_VIDEO_PATH)


class TestEndpointBasics:
    def test_json_200(self):
        stored = _versions()
        assert _export(stored, "json").status_code == 200

    def test_markdown_200(self):
        stored = _versions()
        assert _export(stored, "markdown").status_code == 200

    def test_txt_200(self):
        stored = _versions()
        assert _export(stored, "txt").status_code == 200

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_media_types(self, fmt):
        stored = _versions()
        response = _export(stored, fmt)
        assert response.headers["content-type"].startswith(
            MEDIA_TYPES[fmt]), response.headers["content-type"]

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_content_disposition_filename(self, fmt):
        stored = _versions()
        assert _export(stored, fmt).headers["content-disposition"] == \
            f'attachment; filename="{FILENAMES[fmt]}"'

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_attachment_download(self, fmt):
        stored = _versions()
        assert _export(stored, fmt).headers["content-disposition"].startswith(
            "attachment;")

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_content_decodes_utf8(self, fmt):
        stored = _versions()
        content = _export(stored, fmt).content
        assert content.decode("utf-8")

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_content_ends_with_newline(self, fmt):
        stored = _versions()
        assert _export(stored, fmt).content.endswith(b"\n")

    def test_missing_format_is_422(self):
        stored = _versions()
        response = client.get(_url(stored))
        assert response.status_code == 422

    @pytest.mark.parametrize("bad", ["xml", "csv", "JSON", "Json",
                                     "json ", "md", "html", ""])
    def test_invalid_format_422(self, bad):
        stored = _versions()
        response = _export(stored, bad)
        assert response.status_code == 422, (bad, response.status_code)
        assert response.json()["detail"] == \
            "Invalid format. Must be one of: json, markdown, txt"

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_endpoint_is_get(self, fmt):
        stored = _versions()
        response = client.post(_url(stored), params={"format": fmt})
        assert response.status_code == 405


class TestJSONExport:
    def test_semantically_equals_day29_report(self):
        stored = _versions()
        export = _export(stored, "json")
        assert export.status_code == 200
        assert json.loads(export.content) == _report(stored).json()

    @pytest.mark.parametrize("versions", [None, "1,3,5", "5,3,1",
                                          "4,2", "1", "2,1,5,4,3"])
    def test_selection_equals_day29_report(self, versions):
        stored = _versions()
        export = _export(stored, "json", versions)
        direct = _report(stored, versions)
        assert export.status_code == direct.status_code == 200
        assert json.loads(export.content) == direct.json()

    def test_exact_five_top_level_keys(self):
        stored = _versions()
        assert set(json.loads(_export(stored, "json").content).keys()) == \
            REPORT_TOP

    def test_trailing_newline_and_indent(self):
        stored = _versions()
        content = _export(stored, "json").content.decode("utf-8")
        assert content.endswith("}\n")
        assert '\n  "video_filename"' in content

    def test_stable_key_ordering_matches_report_bytes_structurally(
            self):
        stored = _versions()
        parsed = json.loads(_export(stored, "json").content)
        report = _report(stored).json()
        assert list(parsed.keys()) == list(report.keys())
        assert list(parsed["report"].keys()) == list(report["report"].keys())
        assert list(parsed["timeline"].keys()) == \
            list(report["timeline"].keys())
        assert list(parsed["summary"].keys()) == \
            list(report["summary"].keys())

    def test_empty_history_json(self):
        stored = _upload()
        export = _export(stored, "json")
        assert export.status_code == 200
        data = json.loads(export.content)
        assert set(data.keys()) == REPORT_TOP
        assert data["video_filename"] == stored
        assert data["versions_analyzed"] == []
        assert data["report"]["version_count"] == 0
        assert data["report"]["snapshots"] == []
        assert data["report"]["first_version"] is None
        assert data["timeline"]["steps"] == []
        assert data["timeline"]["required_coverage_delta"] is None
        assert data["summary"]["required"]["coverage_percentage"] is None
        assert data["summary"]["versions_analyzed"] == 0
        assert data["summary"]["dimension_summary"] == []
        assert data["summary"]["organization"] == {
            "favorite_count": 0, "tag_counts": {}}

    def test_single_version_json(self):
        stored = _versions()
        data = json.loads(_export(stored, "json", "3").content)
        assert data["versions_analyzed"] == [3]
        assert data["report"]["version_count"] == 1
        assert data["report"]["first_version"] == 3
        assert data["report"]["last_version"] == 3
        assert data["timeline"]["steps"] == []
        assert data["timeline"]["required_coverage_delta"] == 0
        assert data["summary"]["required"]["total"] == 7
        assert data["summary"]["supporting"]["total"] == 2
        assert len(data["summary"]["dimension_summary"]) == 9

    @pytest.mark.parametrize("prompt", [FULL, WEAK_CAM, W_CAMLESS, CITY,
                                        MINIMAL])
    def test_no_prompt_text(self, prompt):
        stored = _versions()
        for fmt in FORMATS:
            assert prompt not in _export(
                stored, fmt).content.decode("utf-8"), fmt

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_uuid_beyond_video_filename(self, fmt):
        stored = _versions()
        text = _export(stored, fmt).content.decode("utf-8")
        text = text.replace(stored, "")
        assert "uuid" not in text.lower()
        assert not re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}"
            r"-[0-9a-f]{12}", text)


class TestMarkdownExport:
    def test_title_and_sections(self):
        stored = _versions()
        text = _export(stored, "markdown").content.decode("utf-8")
        assert text.startswith("# Prompt Readiness Report\n")
        positions = [text.index(header) for header in (
            "## Report", "## Version Readiness", "## Timeline",
            "## Summary")]
        assert positions == sorted(positions)

    def test_report_metadata_lines(self):
        stored = _versions()
        text = _export(stored, "markdown").content.decode("utf-8")
        assert f"- Video: {stored}" in text
        assert "- Type: prompt_readiness_report" in text
        assert "- Versions analyzed: 1, 2, 3, 4, 5" in text
        assert "- Version count: 5" in text
        assert "- First version: 1" in text
        assert "- Last version: 5" in text
        assert "- Selection order: 1, 2, 3, 4, 5" in text

    def test_all_five_version_sections(self):
        stored = _versions()
        text = _export(stored, "markdown").content.decode("utf-8")
        for version in range(1, 6):
            assert f"### Version {version}\n" in text
        steps = re.findall(r"(?m)^### Step \d+:", text)
        assert len(steps) == 4

    def test_readiness_information_present(self):
        stored = _versions()
        text = _export(stored, "markdown").content.decode("utf-8")
        block = text.split("### Version 1\n", 1)[1].split(
            "### Version ", 1)[0]
        assert "- Source: custom" in block
        assert "- Status: ready" in block
        assert "- Required coverage: 100%" in block
        assert "#### Required Dimensions" in block
        assert "#### Supporting Dimensions" in block
        assert "| subject | present | 100 |" in block
        assert "- Missing dimensions:" in block
        assert "- Weak dimensions:" in block

    def test_timeline_and_transition_summary(self):
        stored = _versions()
        text = _export(stored, "markdown").content.decode("utf-8")
        assert "### Step 1: Version 1 \u2192 Version 2" in text
        assert "### Step 4: Version 4 \u2192 Version 5" in text
        assert "### Timeline Summary" in text
        assert "- Changed dimensions: " in text
        assert "- Required coverage delta: -100" in text
        assert "  - missing_to_weak: " in text

    def test_aggregate_summary_present(self):
        stored = _marked()
        text = _export(stored, "markdown").content.decode("utf-8")
        block = text.split("### Readiness", 1)[1]
        assert "- Versions analyzed: 5" in block
        assert "- Ready count: 1" in block
        assert "- Needs attention count: 4" in block
        required = text.split("### Required", 1)[1]
        assert "- Total: 35" in required
        assert "- Present: 20" in required
        assert "- Weak: 2" in required
        assert "- Missing: 13" in required
        assert "- Coverage: 57%" in required
        supporting = text.split("### Supporting", 1)[1]
        assert "- Total: 10" in supporting
        assert "- Present: 6" in supporting
        assert "- Missing: 4" in supporting
        dimensions = text.split("### Dimension Summary", 1)[1]
        assert "| Dimension | Present | Weak | Missing |" in dimensions
        assert "| subject | 3 | 1 | 1 |" in dimensions
        assert "| camera | 1 | 1 | 3 |" in dimensions
        organization = text.split("### Organization", 1)[1]
        assert "- Favorite count: 1" in organization
        assert "  - ai: 1" in organization
        assert "  - cinematic: 1" in organization
        assert "  - final: 1" in organization

    @pytest.mark.parametrize("fmt", ["markdown", "txt"])
    def test_every_report_leaf_appears(self, fmt):
        stored = _versions()
        report = _report(stored).json()
        text = _export(stored, fmt).content.decode("utf-8")
        for leaf in _leaves(report):
            assert _fmt_leaf(leaf) in text, (fmt, _fmt_leaf(leaf))

    def test_empty_history_markdown(self):
        stored = _upload()
        text = _export(stored, "markdown").content.decode("utf-8")
        assert "No saved versions." in text
        assert "No timeline steps." in text
        assert "### Version " not in text
        assert "- Version count: 0" in text
        assert "- Coverage: none" in text

    def test_single_version_markdown(self):
        stored = _versions()
        text = _export(stored, "markdown", "4").content.decode("utf-8")
        assert text.count("### Version ") == 1
        assert "### Version 4\n" in text
        assert "No timeline steps." in text
        assert "- Required coverage delta: 0" in text


class TestTXTExport:
    def test_title_and_sections(self):
        stored = _versions()
        text = _export(stored, "txt").content.decode("utf-8")
        assert text.startswith("PROMPT READINESS REPORT\n")
        for section, underline in (("REPORT", "------"),
                                   ("VERSION READINESS", "-----------------"),
                                   ("TIMELINE", "--------"),
                                   ("SUMMARY", "-------")):
            assert f"{section}\n{underline}\n" in text

    def test_factual_content_matches_report(self):
        stored = _versions()
        report = _report(stored).json()
        text = _export(stored, "txt").content.decode("utf-8")
        assert f"Video: {stored}" in text
        assert "Type: prompt_readiness_report" in text
        assert "Versions analyzed: 1, 2, 3, 4, 5" in text
        assert "Selection order: 1, 2, 3, 4, 5" in text
        assert "VERSION 1\n" in text
        assert "Required coverage: 100%" in text
        assert "REQUIRED DIMENSIONS" in text
        assert "SUPPORTING DIMENSIONS" in text
        assert "subject: present (100)" in text
        assert "Step 1: Version 1 -> Version 2" in text
        assert "STEP DIMENSIONS" in text
        assert "TRANSITION SUMMARY" in text
        assert "TIMELINE SUMMARY" in text
        assert "Ready count: 1" in text
        assert "Needs attention count: 4" in text
        assert "DIMENSION SUMMARY" in text
        assert "ORGANIZATION" in text
        for leaf in _leaves(report):
            assert _fmt_leaf(leaf) in text, _fmt_leaf(leaf)

    def test_txt_has_no_unicode_arrow(self):
        stored = _versions()
        text = _export(stored, "txt").content.decode("utf-8")
        assert "\u2192" not in text

    def test_empty_history_txt(self):
        stored = _upload()
        text = _export(stored, "txt").content.decode("utf-8")
        assert "No saved versions." in text
        assert "No timeline steps." in text
        assert re.findall(r"(?m)^VERSION \d+$", text) == []
        assert "Ready count: 0" in text
        assert "Coverage: none" in text

    def test_single_version_txt(self):
        stored = _versions()
        text = _export(stored, "txt", "4").content.decode("utf-8")
        assert re.findall(r"(?m)^VERSION \d+$", text) == ["VERSION 4"]
        assert "No timeline steps." in text
        assert "Required coverage delta: 0" in text


class TestSelection:
    @pytest.mark.parametrize("versions,expected", [
        (None, [1, 2, 3, 4, 5]),
        ("1,3,5", [1, 3, 5]),
        ("5,3,1", [5, 3, 1]),
        ("4,2", [4, 2]),
        ("3", [3]),
        ("5,1,3,2,4", [5, 1, 3, 2, 4]),
    ])
    def test_selected_versions_in_requested_order(
            self, versions, expected):
        stored = _versions()
        data = json.loads(_export(stored, "json", versions).content)
        assert data["versions_analyzed"] == expected
        assert data["report"]["selection_order"] == expected

    def test_repeated_params_equal_comma_form(self):
        stored = _versions()
        repeated = _export_raw(stored, [("format", "json"),
                                        ("versions", "1"),
                                        ("versions", "3")])
        comma = _export(stored, "json", "1,3")
        assert repeated.status_code == 200
        assert repeated.content == comma.content

    def test_repeated_params_reverse(self):
        stored = _versions()
        repeated = _export_raw(stored, [("format", "markdown"),
                                        ("versions", "3"),
                                        ("versions", "1")])
        direct = _export(stored, "markdown", "3,1")
        assert repeated.content == direct.content

    def test_whitespace_tolerated(self):
        stored = _versions()
        spaced = _export(stored, "json", "1 , 3")
        plain = _export(stored, "json", "1,3")
        assert spaced.status_code == 200
        assert spaced.content == plain.content

    def test_whitespace_repeated_mix(self):
        stored = _versions()
        mixed = _export_raw(stored, [("format", "txt"),
                                     ("versions", " 1 "),
                                     ("versions", "3")])
        plain = _export(stored, "txt", "1,3")
        assert mixed.status_code == 200
        assert mixed.content == plain.content

    @pytest.mark.parametrize("fmt", FORMATS)
    @pytest.mark.parametrize("versions", [None, "5,3,1", "2,4", "1"])
    def test_all_formats_agree_on_selection(self, fmt, versions):
        stored = _versions()
        report = _report(stored, versions).json()
        if fmt == "json":
            assert json.loads(_export(
                stored, "json", versions).content) == report
        else:
            text = _export(stored, fmt, versions).content.decode("utf-8")
            for leaf in _leaves(report):
                assert _fmt_leaf(leaf) in text, (fmt, _fmt_leaf(leaf))

    def test_reverse_selection_markdown_order(self):
        stored = _versions()
        text = _export(stored, "markdown", "5,3,1").content.decode("utf-8")
        positions = [text.index(f"### Version {v}") for v in (5, 3, 1)]
        assert positions == sorted(positions)


class TestValidation:
    @pytest.mark.parametrize("versions", ["", "0", "-1", "abc", "1,,2",
                                          "1,1", "1.5", ",", " ", "1;2",
                                          "+2", "1 2", "0,1", "1,1.5"])
    def test_invalid_versions_422(self, versions):
        stored = _versions()
        response = _export(stored, "json", versions)
        assert response.status_code == 422, (versions, response.status_code)

    def test_repeated_duplicate_params_422(self):
        stored = _versions()
        response = _export_raw(stored, [("format", "json"),
                                        ("versions", "2"),
                                        ("versions", "2")])
        assert response.status_code == 422

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_missing_version_404(self, fmt):
        stored = _versions()
        response = _export(stored, fmt, "1,99")
        assert response.status_code == 404
        assert response.json()["detail"] == \
            f"Version 99 not found for video '{stored}'."

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_deleted_version_404(self, fmt):
        stored = _versions()
        created = _save(stored, CITY)
        version = created["version"]
        assert _export(stored, "json", str(version)).status_code == 200
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/{version}"
        ).status_code == 200
        response = _export(stored, fmt, str(version))
        assert response.status_code == 404
        assert response.json()["detail"] == \
            f"Version {version} not found for video '{stored}'."

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_default_selection_skips_deleted(self, fmt):
        stored = _versions()
        created = _save(stored, CITY)
        version = created["version"]
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/{version}"
        ).status_code == 200
        if fmt == "json":
            data = json.loads(_export(stored, "json").content)
            assert data["versions_analyzed"] == [1, 2, 3, 4, 5]
            assert version not in data["versions_analyzed"]
        else:
            text = _export(stored, fmt).content.decode("utf-8")
            assert f"### Version {version}\n" not in text
            assert f"VERSION {version}\n" not in text

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_nonexistent_video_404(self, fmt):
        response = _export("missing.mp4", fmt)
        assert response.status_code == 404

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_path_traversal_404(self, fmt):
        response = client.get(
            "/api/videos/../../../etc/passwd/prompt/history/readiness/"
            f"report/export",
            params={"format": fmt},
        )
        assert response.status_code == 404

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_invalid_extension_400(self, fmt):
        response = _export("clip.txt", fmt)
        assert response.status_code == 400

    def test_nonexistent_video_with_invalid_format_404(self):
        response = _export("missing.mp4", "xml")
        assert response.status_code == 404

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_empty_video_with_selection_404(self, fmt):
        stored = _upload()
        response = _export(stored, fmt, "1")
        assert response.status_code == 404


class TestDeterminism:
    @pytest.mark.parametrize("fmt", FORMATS)
    @pytest.mark.parametrize("versions", [None, "1,4", "5,2"])
    def test_repeated_requests_byte_identical(self, fmt, versions):
        stored = _versions()
        first = _export(stored, fmt, versions)
        second = _export(stored, fmt, versions)
        assert first.status_code == second.status_code == 200
        assert first.content == second.content
        assert first.headers["content-type"] == second.headers["content-type"]
        assert first.headers["content-disposition"] == \
            second.headers["content-disposition"]

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_filename_stable_across_selections(self, fmt):
        stored = _versions()
        names = {
            _export(stored, fmt, versions).headers["content-disposition"]
            for versions in (None, "1", "2,4", "5,3,1")
        }
        assert names == {
            f'attachment; filename="{FILENAMES[fmt]}"'}

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_generated_timestamps(self, fmt):
        stored = _versions()
        text = _export(stored, fmt).content.decode("utf-8")
        for marker in ("generated_at", "exported_at", "timestamp"):
            assert marker not in text.lower(), marker


class TestReadOnlyIntegrity:
    def _state(self, stored):
        listing = client.get(
            f"/api/videos/{stored}/prompt/history").json()["versions"]
        records = {
            entry["version"]: json.dumps(
                client.get(
                    f"/api/videos/{stored}/prompt/history/"
                    f"{entry['version']}").json(), sort_keys=True)
            for entry in listing
        }
        orgs = {
            entry["version"]: json.dumps(client.get(
                f"/api/videos/{stored}/prompt/history/"
                f"{entry['version']}/organization").json(), sort_keys=True)
            for entry in listing
        }
        return {"listing": listing, "records": records, "orgs": orgs}

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_history_and_org_unchanged(self, fmt):
        stored = _marked()
        before = self._state(stored)
        for versions in (None, "1,3", "5,1"):
            _export(stored, fmt, versions)
        after = self._state(stored)
        assert after == before

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_day19_export_unchanged(self, fmt):
        stored = _versions()
        before = [_d19_export(stored, 1, name).content
                  for name in FORMATS]
        _export(stored, fmt)
        after = [_d19_export(stored, 1, name).content
                 for name in FORMATS]
        assert after == before

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_package_unchanged(self, fmt):
        stored = _versions()
        before = _package(stored, 1).content
        _export(stored, fmt)
        assert _package(stored, 1).content == before

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_day21_quality_unchanged(self, fmt):
        stored = _versions()
        before = _quality(stored, FULL).json()
        _export(stored, fmt)
        assert _quality(stored, FULL).json() == before

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_day24_readiness_unchanged(self, fmt):
        stored = _versions()
        before = _readiness(stored, FULL).json()
        _export(stored, fmt)
        assert _readiness(stored, FULL).json() == before

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_files_created_in_storage(self, fmt):
        stored = _versions()
        uploads = os.path.join("storage", "uploads")
        before = sorted(os.listdir(uploads))
        _export(stored, fmt)
        after = sorted(os.listdir(uploads))
        assert after == before
        assert not any(name.startswith("visionprompt")
                       for name in after), after

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_version_listing_never_changes(self, fmt):
        stored = _versions()
        before = [entry["version"] for entry in client.get(
            f"/api/videos/{stored}/prompt/history").json()["versions"]]
        for versions in (None, "1,5", "3"):
            _export(stored, fmt, versions)
        after = [entry["version"] for entry in client.get(
            f"/api/videos/{stored}/prompt/history").json()["versions"]]
        assert after == before == [1, 2, 3, 4, 5]


class TestRouteCollision:
    def test_numeric_history_routes_unaffected(self):
        stored = _versions()
        response = client.get(f"/api/videos/{stored}/prompt/history/2")
        assert response.status_code == 200
        assert response.json()["version"] == 2
        assert "prompt" in response.json()

    def test_report_route_still_returns_json_payload(self):
        stored = _versions()
        response = _report(stored)
        assert response.status_code == 200
        assert set(response.json().keys()) == REPORT_TOP

    def test_day19_export_route_unaffected(self):
        stored = _versions()
        response = _d19_export(stored, 1, "json")
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["version"] == 1
        assert data["prompt"] == FULL

    def test_all_readiness_routes_resolve(self):
        stored = _versions()
        assert _history(stored).status_code == 200
        assert _timeline(stored).status_code == 200
        assert _snapshot(stored).status_code == 200
        assert _report(stored).status_code == 200
        assert _change(stored, 1, 2).status_code == 200

    def test_day23_detailed_comparison_unaffected(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2/detailed")
        assert response.status_code == 200
        assert "comparison" in response.json()

    def test_day26_route_unaffected(self):
        stored = _versions()
        assert _change(stored, 1, 2).json()["video_filename"] == stored

    def test_path_shapes_are_distinct(self):
        stored = _versions()
        paths = [
            f"/api/videos/{stored}/prompt/history/1",
            f"/api/videos/{stored}/prompt/history/1/export",
            f"/api/videos/{stored}/prompt/history/readiness",
            f"/api/videos/{stored}/prompt/history/readiness/timeline",
            f"/api/videos/{stored}/prompt/history/readiness/snapshot",
            f"/api/videos/{stored}/prompt/history/readiness/report",
            f"/api/videos/{stored}/prompt/history/readiness/report/export",
        ]
        for path in paths:
            params = {"format": "json"} if path.endswith("export") else None
            assert client.get(path, params=params).status_code == 200, path


class TestRegressionDay16to29:
    def test_day16_history_save_list_compare_delete(self):
        stored = _versions()
        assert client.get(
            f"/api/videos/{stored}/prompt/history").status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2"
        ).status_code == 200
        created = _save(stored, CITY)
        assert created["version"] == 6
        assert client.delete(
            f"/api/videos/{stored}/prompt/history/6").status_code == 200

    def test_day17_favorites_and_tags(self):
        stored = _marked()
        favorites = client.get(
            f"/api/videos/{stored}/prompt/history/favorites")
        assert favorites.status_code == 200
        assert [entry["version"] for entry in
                favorites.json()["favorites"]] == [1]
        tagged = client.get(f"/api/videos/{stored}/prompt/history/tag/ai")
        assert tagged.status_code == 200

    def test_day18_search(self):
        stored = _versions()
        assert client.get(
            f"/api/videos/{stored}/prompt/search").status_code == 200

    def test_day19_prompt_export_and_day20_package(self):
        stored = _versions()
        for fmt in FORMATS:
            assert _d19_export(stored, 1, fmt).status_code == 200
        assert _package(stored, 1).status_code == 200

    def test_day21_quality_and_day22_improvement(self):
        stored = _versions()
        response = client.post(f"/api/videos/{stored}/prompt/quality",
                               json={"prompt": FULL})
        assert response.status_code == 200
        improved = client.post(f"/api/videos/{stored}/prompt/improve",
                               json={"prompt": FULL})
        assert improved.status_code == 200

    def test_day23_detailed_comparison(self):
        stored = _versions()
        response = client.get(
            f"/api/videos/{stored}/prompt/history/compare/1/2/detailed")
        assert response.status_code == 200

    def test_day24_readiness(self):
        stored = _versions()
        response = client.post(f"/api/videos/{stored}/prompt/readiness",
                               json={"prompt": FULL})
        assert response.status_code == 200
        assert client.get(
            f"/api/videos/{stored}/prompt/history/1/readiness"
        ).status_code == 200

    def test_day25_history_analysis(self):
        stored = _versions()
        assert _history(stored).status_code == 200
        assert _history(stored, "3,1").status_code == 200

    def test_day26_change_tracking(self):
        stored = _versions()
        assert _change(stored, 2, 5).status_code == 200

    def test_day27_timeline(self):
        stored = _versions()
        assert _timeline(stored).status_code == 200
        assert _timeline(stored, "2,1").status_code == 200

    def test_day28_snapshot(self):
        stored = _versions()
        assert _snapshot(stored).status_code == 200
        assert _snapshot(stored, "4,2").status_code == 200

    def test_day29_report(self):
        stored = _versions()
        assert _report(stored).status_code == 200
        assert _report(stored, "5,3,1").status_code == 200
        assert set(_report(stored).json().keys()) == REPORT_TOP

    def test_day30_export_all_formats(self):
        stored = _versions()
        for fmt in FORMATS:
            assert _export(stored, fmt).status_code == 200


class TestNoLeaks:
    @pytest.mark.parametrize("fmt", FORMATS)
    @pytest.mark.parametrize("versions", [None, "1,3", "5,1", "2"])
    def test_no_ranking_language(self, fmt, versions):
        stored = _versions()
        text = _export(stored, fmt, versions).content.decode(
            "utf-8").lower()
        for word in FORBIDDEN_WORDS:
            assert word not in text, (fmt, versions, word)

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_prompt_text(self, fmt):
        stored = _versions()
        text = _export(stored, fmt).content.decode("utf-8")
        assert "film grain style portrait" not in text
        assert "blurry, low quality" not in text
        assert NEGATIVE not in text

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_internal_names(self, fmt):
        stored = _versions()
        text = _export(stored, fmt).content.decode("utf-8")
        for name in INTERNAL_NAMES:
            assert name not in text, name

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_path_leakage(self, fmt):
        stored = _versions()
        text = _export(stored, fmt).content.decode("utf-8")
        for marker in PATH_MARKERS:
            assert marker not in text, marker
        assert "test_assets" not in text
        assert "storage/uploads" not in text

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_secrets(self, fmt):
        stored = _versions()
        text = _export(stored, fmt).content.decode("utf-8").lower()
        for key in ("password", "secret", "api_key", "authorization",
                    "bearer"):
            assert key not in text, key

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_evaluative_commentary(self, fmt):
        stored = _versions()
        text = _export(stored, fmt).content.decode("utf-8").lower()
        for phrase in ("is better", "is the best", "is worse",
                       "should use", "we recommend", "the winner"):
            assert phrase not in text, phrase
