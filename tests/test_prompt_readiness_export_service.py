"""Tests for the prompt readiness report export service (Day 30)."""
import json
import re

import pytest

from app.services.prompt_quality_service import PromptQualityService
from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService
from app.services.prompt_readiness_service import PromptReadinessService
from app.services.prompt_readiness_change_service import (
    PromptReadinessChangeService,
)
from app.services.prompt_readiness_timeline_service import (
    PromptReadinessTimelineService,
)
from app.services.prompt_readiness_snapshot_service import (
    PromptReadinessSnapshotService,
)
from app.services.prompt_readiness_report_service import (
    PromptReadinessReportService,
)
from app.services.prompt_readiness_export_service import (
    PromptReadinessExportService,
    FILENAME_STEM,
    _fmt,
    _leaf_values,
)
from app.services.prompt_export_service import (
    VALID_EXPORT_FORMATS as DAY19_FORMATS,
)

# --- Fixture prompts (Day 21/24/26/27/28/29 verified) -----------------------
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
CITY_ENV100 = "A person walks through a quiet city street near the forest park."
MINIMAL = "nothing specific at all"
REQ_ONLY = ("Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, camera tracking with shallow depth of field, soft "
            "lighting with rim light and golden hour glow, layered "
            "foreground and rule of thirds composition.")
SUBJ70 = ("Cinematic film grain style portrait of a person, "
          "walking through an outdoor forest street, camera tracking "
          "with shallow depth of field, soft lighting with rim light "
          "and golden hour glow, vibrant teal and orange palette with "
          "warm tones, layered foreground and rule of thirds "
          "composition, ambient sound with quiet music score.")

VIDEO = "sample.mp4"
EMPTY_VIDEO = "none.mp4"

FORMATS = ("json", "markdown", "txt")

_MEDIA_TYPES = {
    "json": "application/json",
    "markdown": "text/markdown",
    "txt": "text/plain",
}

FILENAMES = {
    "json": "visionprompt_readiness_report.json",
    "markdown": "visionprompt_readiness_report.md",
    "txt": "visionprompt_readiness_report.txt",
}

TOP_KEYS = {
    "video_filename", "versions_analyzed", "report", "timeline", "summary",
}

REPORT_KEYS = {
    "type", "version_count", "first_version", "last_version",
    "selection_order", "snapshots",
}

TIMELINE_KEYS = {
    "steps", "changed_dimensions", "unchanged_dimensions",
    "required_changes", "supporting_changes", "transition_summary",
    "required_coverage_delta",
}

SUMMARY_KEYS = {
    "versions_analyzed", "ready_count", "needs_attention_count",
    "required", "supporting", "dimension_summary", "organization",
}

SNAPSHOT_KEYS = {
    "version", "source", "operation", "created_at", "favorite", "tags",
    "readiness",
}

READINESS_KEYS = {
    "status", "required_coverage_percentage", "required", "supporting",
    "missing_dimensions", "weak_dimensions",
}

REQUIRED_KEYS = [
    "subject", "action", "environment", "camera", "lighting",
    "visual_style", "composition",
]
SUPPORTING_KEYS = ["color", "audio"]

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

# standard 8-version history (Day 29 probe-verified):
# 1 FULL, 2 WEAK_CAM, 3 W_CAMLESS, 4 CITY, 5 CITY_ENV100,
# 6 MINIMAL, 7 REQ_ONLY, 8 SUBJ70
STANDARD = [
    (FULL, "advanced_prompt", "generate"),
    (WEAK_CAM, "custom", ""),
    (W_CAMLESS, "template", "cinematic"),
    (CITY, "refinement", "expand"),
    (CITY_ENV100, "custom", "tweak"),
    (MINIMAL, "template", "shorten"),
    (REQ_ONLY, "refinement", "expand"),
    (SUBJ70, "custom", "draft"),
]

SELECTIONS = [
    None, [1], [6], [1, 3, 5], [5, 3, 1], [4, 2],
    [8, 7, 6, 5, 4, 3, 2, 1],
]


def _build_history(specs=None):
    history = PromptHistoryService()
    for prompt, source, operation in (specs or STANDARD):
        history.create_version(VIDEO, prompt, source=source,
                               operation=operation)
    return history


def _build_chain(history):
    """Build the full Day 16->29 chain over the given history."""
    readiness = PromptReadinessService(PromptQualityService())
    organization = PromptOrganizationService(history)
    change = PromptReadinessChangeService(history, readiness)
    timeline_service = PromptReadinessTimelineService(history, change)
    snapshot_service = PromptReadinessSnapshotService(
        history, readiness, organization
    )
    report_service = PromptReadinessReportService(
        timeline_service, snapshot_service
    )
    return {
        "history": history,
        "readiness": readiness,
        "organization": organization,
        "change": change,
        "timeline_service": timeline_service,
        "snapshot_service": snapshot_service,
        "report_service": report_service,
        "export_service": PromptReadinessExportService(report_service),
    }


@pytest.fixture
def history():
    return _build_history()


@pytest.fixture
def chain(history):
    return _build_chain(history)


@pytest.fixture
def export_service(chain):
    return chain["export_service"]


@pytest.fixture
def report_service(chain):
    return chain["report_service"]


@pytest.fixture
def result(report_service):
    return report_service.generate_report(VIDEO)


@pytest.fixture
def marked(history, chain):
    """Standard history with probe-verified favorites and tags."""
    organization = chain["organization"]
    organization.favorite_version(VIDEO, 1)
    organization.favorite_version(VIDEO, 7)
    organization.add_tags(VIDEO, 1, [" Cinematic ", "ai"])
    organization.add_tags(VIDEO, 4, ["final"])
    organization.add_tags(VIDEO, 7, ["cinematic", "draft", "cinematic"])
    return history


@pytest.fixture
def marked_export(marked, export_service):
    return export_service


@pytest.fixture
def empty_chain():
    return _build_chain(PromptHistoryService())


@pytest.fixture
def empty_export(empty_chain):
    return empty_chain["export_service"]


def _json(service, versions=None, video=VIDEO):
    return service.export_report(video, versions, "json")


def _md(service, versions=None, video=VIDEO):
    return service.export_report(video, versions, "markdown")


def _txt(service, versions=None, video=VIDEO):
    return service.export_report(video, versions, "txt")


def _content(service, versions=None, video=VIDEO, format="json"):
    return service.export_report(video, versions, format)["content"]


def _parsed(service, versions=None, video=VIDEO):
    return json.loads(service.export_report(
        video, versions, "json")["content"])


def _entries(report):
    return report["report"]["snapshots"]


def _pairs(report):
    return [(step["version_a"]["version"], step["version_b"]["version"])
            for step in report["timeline"]["steps"]]


def _leaves(obj):
    return list(_leaf_values(obj))


class TestWiring:
    def test_constructor_holds_only_report_service(self, report_service):
        svc = PromptReadinessExportService(report_service)
        assert set(vars(svc).keys()) == {"report_service"}

    def test_holds_given_report_service(self, report_service):
        svc = PromptReadinessExportService(report_service)
        assert svc.report_service is report_service

    def test_report_service_is_day29_service(self, export_service):
        assert isinstance(export_service.report_service,
                          PromptReadinessReportService)

    def test_chain_reuses_day16_day24_day17_day26_day27_day28(
            self, chain):
        report_service = chain["report_service"]
        snapshot = report_service.readiness_snapshot_service
        timeline = report_service.readiness_timeline_service
        assert snapshot.history_service is chain["history"]
        assert snapshot.readiness_service is chain["readiness"]
        assert snapshot.organization_service is chain["organization"]
        assert timeline.history_service is chain["history"]
        assert timeline.readiness_change_service is chain["change"]

    def test_single_day16_store(self, export_service):
        chain_services = [
            export_service.report_service.readiness_timeline_service,
            export_service.report_service.readiness_snapshot_service,
        ]
        histories = {
            service.history_service for service in chain_services
        }
        assert len(histories) == 1, "no second version store"

    def test_reuses_day19_format_contract(self):
        import app.services.prompt_readiness_export_service as module
        assert module.VALID_EXPORT_FORMATS is DAY19_FORMATS

    def test_no_day24_day25_day26_day27_day28_logic_in_module(self):
        import inspect
        import app.services.prompt_readiness_export_service as module
        source = inspect.getsource(module)
        for forbidden in (
            "validate_prompt", "analyze_versions", "compare_versions",
            "build_timeline", "create_snapshot", "REQUIRED_DIMENSIONS",
            "SUPPORTING_DIMENSIONS", "TRANSITION_KEYS",
        ):
            assert forbidden not in source, forbidden


class TestEnvelope:
    @pytest.mark.parametrize("fmt", FORMATS)
    def test_envelope_keys(self, export_service, fmt):
        envelope = export_service.export_report(VIDEO, format=fmt)
        assert set(envelope.keys()) == {
            "format", "content", "media_type", "filename"}

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_format_echoed(self, export_service, fmt):
        assert export_service.export_report(
            VIDEO, format=fmt)["format"] == fmt

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_media_types(self, export_service, fmt):
        assert export_service.export_report(
            VIDEO, format=fmt)["media_type"] == _MEDIA_TYPES[fmt]

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_deterministic_filenames(self, export_service, fmt):
        assert export_service.export_report(
            VIDEO, format=fmt)["filename"] == FILENAMES[fmt]

    @pytest.mark.parametrize("fmt,ext", [
        ("json", "json"), ("markdown", "md"), ("txt", "txt"),
    ])
    def test_filename_derived_from_stem(self, export_service, fmt, ext):
        assert export_service.export_report(VIDEO, format=fmt)[
            "filename"] == f"{FILENAME_STEM}.{ext}"

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_content_is_str(self, export_service, fmt):
        assert isinstance(
            export_service.export_report(VIDEO, format=fmt)["content"],
            str)

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_content_ends_with_newline(self, export_service, fmt):
        assert export_service.export_report(
            VIDEO, format=fmt)["content"].endswith("\n")


class TestJSONExport:
    def test_json_semantically_equals_day29_report(
            self, export_service, result):
        assert json.loads(_content(export_service)) == result

    def test_all_five_top_level_keys(self, export_service):
        assert set(_parsed(export_service).keys()) == TOP_KEYS

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_selection_matches_day29_exactly(
            self, export_service, report_service, selection):
        assert _parsed(export_service, selection) == \
            report_service.generate_report(VIDEO, selection)

    def test_exact_json_string_formatting(self, export_service, result):
        expected = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        assert _content(export_service) == expected

    def test_trailing_newline_present(self, export_service):
        assert _content(export_service).endswith("}\n")

    def test_indent_two_spaces(self, export_service):
        assert '\n  "video_filename"' in _content(export_service)

    def test_no_fields_omitted_or_invented(self, export_service, result):
        parsed = _parsed(export_service)
        assert set(parsed.keys()) == set(result.keys())
        assert set(parsed["report"].keys()) == set(result["report"].keys())
        assert set(parsed["timeline"].keys()) == \
            set(result["timeline"].keys())
        assert set(parsed["summary"].keys()) == set(result["summary"].keys())

    def test_nested_key_sets_preserved(self, export_service, result):
        parsed = _parsed(export_service)
        assert set(parsed["report"].keys()) == REPORT_KEYS
        assert set(parsed["timeline"].keys()) == TIMELINE_KEYS
        assert set(parsed["summary"].keys()) == SUMMARY_KEYS
        for entry in parsed["report"]["snapshots"]:
            assert set(entry.keys()) == SNAPSHOT_KEYS
            assert set(entry["readiness"].keys()) == READINESS_KEYS

    def test_snapshot_count_is_eight(self, export_service):
        assert len(_parsed(export_service)["report"]["snapshots"]) == 8

    def test_step_count_is_seven(self, export_service):
        assert len(_parsed(export_service)["timeline"]["steps"]) == 7

    def test_utf8_roundtrip(self, export_service):
        content = _content(export_service)
        assert content.encode("utf-8").decode("utf-8") == content

    def test_non_ascii_operation_preserved_raw(self):
        history = PromptHistoryService()
        history.create_version(VIDEO, CITY, source="custom",
                               operation="caf\u00e9")
        service = _build_chain(history)["export_service"]
        content = _content(service)
        assert "caf\u00e9" in content, "ensure_ascii=False keeps UTF-8"
        assert "caf\\u00e9" not in content
        assert "caf\u00e9" in _content(service, format="markdown")
        assert "caf\u00e9" in _content(service, format="txt")

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_deterministic_repeated_json(self, export_service, fmt):
        first = _content(export_service, format=fmt)
        second = _content(export_service, format=fmt)
        assert first == second

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_deterministic_per_selection(
            self, export_service, selection):
        assert _content(export_service, selection) == \
            _content(export_service, selection)

    @pytest.mark.parametrize("prompt", [FULL, WEAK_CAM, W_CAMLESS, CITY,
                                        CITY_ENV100, MINIMAL, REQ_ONLY,
                                        SUBJ70])
    def test_no_prompt_text(self, export_service, prompt):
        assert prompt not in _content(export_service)
        assert prompt not in _content(export_service, format="markdown")
        assert prompt not in _content(export_service, format="txt")

    @pytest.mark.parametrize("name", INTERNAL_NAMES)
    def test_no_internal_objects(self, export_service, name):
        for fmt in FORMATS:
            assert name not in _content(export_service, format=fmt), name

    @pytest.mark.parametrize("marker", PATH_MARKERS)
    def test_no_absolute_paths(self, export_service, marker):
        for fmt in FORMATS:
            assert marker not in _content(export_service, format=fmt)

    def test_no_uuid_or_generated_ids(self, export_service):
        for fmt in FORMATS:
            text = _content(export_service, format=fmt).replace(VIDEO, "")
            assert "uuid" not in text.lower()
            assert not re.search(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}"
                r"-[0-9a-f]{12}", text)

    @pytest.mark.parametrize("word", FORBIDDEN_WORDS)
    def test_no_ranking_language(self, export_service, word):
        for fmt in FORMATS:
            text = _content(export_service, format=fmt).lower()
            assert word not in text, word


class TestMarkdownExport:
    def test_title_first_line(self, export_service):
        assert _content(export_service, format="markdown").startswith(
            "# Prompt Readiness Report\n")

    def test_sections_in_order(self, export_service):
        text = _content(export_service, format="markdown")
        positions = [text.index(header) for header in (
            "## Report", "## Version Readiness", "## Timeline",
            "## Summary",
        )]
        assert positions == sorted(positions)

    def test_report_metadata_lines(self, export_service, result):
        text = _content(export_service, format="markdown")
        assert f"- Video: {VIDEO}" in text
        assert "- Type: prompt_readiness_report" in text
        assert "- Versions analyzed: 1, 2, 3, 4, 5, 6, 7, 8" in text
        assert "- Version count: 8" in text
        assert "- First version: 1" in text
        assert "- Last version: 8" in text
        assert "- Selection order: 1, 2, 3, 4, 5, 6, 7, 8" in text

    def test_version_sections_for_all_eight(self, export_service):
        text = _content(export_service, format="markdown")
        for version in range(1, 9):
            assert f"### Version {version}\n" in text
        assert text.count("### Version ") == 8

    @pytest.mark.parametrize("version", list(range(1, 9)))
    def test_version_source_and_operation_lines(
            self, export_service, version):
        _prompt, source, operation = STANDARD[version - 1]
        text = _content(export_service, format="markdown")
        block = text.split(f"### Version {version}\n", 1)[1]
        block = block.split("### Version ", 1)[0]
        assert f"- Source: {source}" in block
        expected_op = operation if operation else "(empty)"
        assert f"- Operation: {expected_op}" in block

    def test_created_at_equals_stored_day16_value(
            self, export_service, history):
        text = _content(export_service, format="markdown")
        for version in range(1, 9):
            record = history.get_version(VIDEO, version)
            assert record["created_at"] in text

    def test_favorite_and_tags_lines(self, marked_export):
        text = _content(marked_export, format="markdown")
        v1 = text.split("### Version 1\n", 1)[1].split(
            "### Version ", 1)[0]
        assert "- Favorite: true" in v1
        assert "- Tags: ai, cinematic" in v1
        v2 = text.split("### Version 2\n", 1)[1].split(
            "### Version ", 1)[0]
        assert "- Favorite: false" in v2
        assert "- Tags: none" in v2

    def test_status_and_coverage_lines(self, export_service):
        text = _content(export_service, format="markdown")
        v1 = text.split("### Version 1\n", 1)[1].split(
            "### Version ", 1)[0]
        assert "- Status: ready" in v1
        assert "- Required coverage: 100%" in v1
        v6 = text.split("### Version 6\n", 1)[1].split(
            "### Version ", 1)[0]
        assert "- Required coverage: 0%" in v6

    def test_required_dimension_table_seven_rows(self, export_service):
        text = _content(export_service, format="markdown")
        block = text.split("#### Required Dimensions\n", 1)[1]
        block = block.split("#### Supporting Dimensions", 1)[0]
        rows = [line for line in block.splitlines()
                if line.startswith("| ") and "---" not in line
                and "Dimension" not in line]
        assert len(rows) == 7, rows
        for dimension in REQUIRED_KEYS:
            assert f"| {dimension} | " in block

    def test_supporting_dimension_table_two_rows(self, export_service):
        text = _content(export_service, format="markdown")
        block = text.split("#### Supporting Dimensions\n", 1)[1]
        block = block.split("- Missing dimensions:", 1)[0]
        rows = [line for line in block.splitlines()
                if line.startswith("| ") and "---" not in line
                and "Dimension" not in line]
        assert len(rows) == 2, rows
        for dimension in SUPPORTING_KEYS:
            assert f"| {dimension} | " in block

    def test_known_dimension_row_values(self, export_service):
        text = _content(export_service, format="markdown")
        v1 = text.split("### Version 1\n", 1)[1].split(
            "### Version ", 1)[0]
        assert "| subject | present | 100 |" in v1
        v3 = text.split("### Version 3\n", 1)[1].split(
            "### Version ", 1)[0]
        assert "| camera | missing | 0 |" in v3

    def test_missing_and_weak_dimension_lines(self, export_service):
        text = _content(export_service, format="markdown")
        v2 = text.split("### Version 2\n", 1)[1].split(
            "### Version ", 1)[0]
        assert "- Missing dimensions: none" in v2
        assert "- Weak dimensions: camera" in v2
        v7 = text.split("### Version 7\n", 1)[1].split(
            "### Version ", 1)[0]
        assert "- Missing dimensions: color, audio" in v7

    def test_timeline_step_headings_with_arrow(self, export_service):
        text = _content(export_service, format="markdown")
        expected = [
            f"### Step {i}: Version {a} \u2192 Version {b}"
            for i, (a, b) in enumerate(
                [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7),
                 (7, 8)], start=1)
        ]
        for heading in expected:
            assert heading in text, heading
        steps = re.findall(r"(?m)^### Step \d+:", text)
        assert len(steps) == 7, steps

    def test_step_dimensions_table_nine_rows(self, export_service):
        text = _content(export_service, format="markdown")
        block = text.split("### Step 1:", 1)[1]
        block = block.split("### Step 2:", 1)[0]
        block = block.split("#### Step Dimensions", 1)[1]
        block = block.split("#### Transitions", 1)[0]
        rows = [line for line in block.splitlines()
                if line.startswith("| ") and "---" not in line
                and "Dimension" not in line]
        assert len(rows) == 9, rows
        for dimension in ("subject", "action", "environment", "camera",
                          "lighting", "visual_style", "color",
                          "composition", "audio"):
            assert f"| {dimension} | " in block

    def test_step_transitions_rendered(self, export_service):
        text = _content(export_service, format="markdown")
        block = text.split("### Step 1:", 1)[1].split(
            "### Step 2:", 1)[0]
        assert "#### Transitions" in block
        assert re.search(
            r"- [a-z_]+: (missing|weak|present) -> "
            r"(missing|weak|present)", block), "a transition line"
        assert "#### Transition Summary" in block
        for key in ("missing_to_weak", "missing_to_present",
                    "weak_to_missing", "weak_to_present",
                    "present_to_missing", "present_to_weak"):
            assert f"- {key}: " in block

    def test_step_coverage_line(self, export_service):
        text = _content(export_service, format="markdown")
        block = text.split("### Step 1:", 1)[1].split(
            "### Step 2:", 1)[0]
        assert "- Required coverage: 100% -> 86% (delta -14)" in block

    def test_timeline_summary_section(self, export_service):
        text = _content(export_service, format="markdown")
        block = text.split("### Timeline Summary", 1)[1]
        assert "- Changed dimensions: 21" in block
        assert "- Unchanged dimensions: 42" in block
        assert "- Required changes: 17" in block
        assert "- Supporting changes: 4" in block
        assert "  - missing_to_present: 9" in block
        assert "  - present_to_missing: 7" in block
        assert "- Required coverage delta: -14" in block

    def test_summary_readiness_block(self, export_service):
        text = _content(export_service, format="markdown")
        block = text.split("### Readiness", 1)[1]
        assert "- Versions analyzed: 8" in block
        assert "- Ready count: 2" in block
        assert "- Needs attention count: 6" in block

    def test_summary_required_block(self, export_service):
        text = _content(export_service, format="markdown")
        block = text.split("### Required", 1)[1]
        assert "- Total: 56" in block
        assert "- Present: 34" in block
        assert "- Weak: 4" in block
        assert "- Missing: 18" in block
        assert "- Coverage: 61%" in block

    def test_summary_supporting_block(self, export_service):
        text = _content(export_service, format="markdown")
        block = text.split("### Supporting", 1)[1]
        assert "- Total: 16" in block
        assert "- Present: 8" in block
        assert "- Weak: 0" in block
        assert "- Missing: 8" in block

    def test_dimension_summary_table(self, export_service):
        text = _content(export_service, format="markdown")
        block = text.split("### Dimension Summary", 1)[1]
        assert "| Dimension | Present | Weak | Missing |" in block
        expected = [
            ("subject", 5, 2, 1), ("action", 4, 1, 3),
            ("environment", 7, 0, 1), ("camera", 3, 1, 4),
            ("lighting", 5, 0, 3), ("visual_style", 5, 0, 3),
            ("color", 4, 0, 4), ("composition", 5, 0, 3),
            ("audio", 4, 0, 4),
        ]
        for dimension, present, weak, missing in expected:
            assert (f"| {dimension} | {present} | {weak} "
                    f"| {missing} |") in block, dimension

    def test_organization_block(self, marked_export):
        text = _content(marked_export, format="markdown")
        block = text.split("### Organization", 1)[1]
        assert "- Favorite count: 2" in block
        assert "  - ai: 1" in block
        assert "  - cinematic: 2" in block
        assert "  - draft: 1" in block
        assert "  - final: 1" in block

    def test_every_report_leaf_appears(self, export_service, result):
        text = _content(export_service, format="markdown")
        for leaf in _leaves(result):
            assert _fmt(leaf) in text, _fmt(leaf)

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_selected_report_leaves_all_present(
            self, export_service, report_service, selection):
        report = report_service.generate_report(VIDEO, selection)
        text = _content(export_service, selection, format="markdown")
        for leaf in _leaves(report):
            assert _fmt(leaf) in text, _fmt(leaf)

    @pytest.mark.parametrize("word", FORBIDDEN_WORDS)
    def test_no_ranking_language(self, export_service, word):
        assert word not in _content(
            export_service, format="markdown").lower(), word

    @pytest.mark.parametrize("prompt", [FULL, CITY, MINIMAL, SUBJ70])
    def test_no_prompt_text(self, export_service, prompt):
        assert prompt not in _content(export_service, format="markdown")

    @pytest.mark.parametrize("name", INTERNAL_NAMES)
    def test_no_internal_objects(self, export_service, name):
        assert name not in _content(export_service, format="markdown")

    @pytest.mark.parametrize("marker", PATH_MARKERS)
    def test_no_absolute_paths(self, export_service, marker):
        assert marker not in _content(export_service, format="markdown")

    def test_no_evaluative_commentary(self, export_service):
        text = _content(export_service, format="markdown").lower()
        for phrase in ("is better", "is the best", "improved", "winner",
                       "is worse", "should use", "we recommend"):
            assert phrase not in text, phrase

    def test_deterministic_repeated(self, export_service):
        assert _content(export_service, format="markdown") == \
            _content(export_service, format="markdown")


class TestTXTExport:
    def test_title_and_underline(self, export_service):
        text = _content(export_service, format="txt")
        assert text.startswith(
            "PROMPT READINESS REPORT\n=======================\n")

    @pytest.mark.parametrize("section,underline", [
        ("REPORT", "------"),
        ("VERSION READINESS", "-----------------"),
        ("TIMELINE", "--------"),
        ("SUMMARY", "-------"),
    ])
    def test_section_headers_with_underlines(
            self, export_service, section, underline):
        text = _content(export_service, format="txt")
        assert f"{section}\n{underline}\n" in text

    def test_report_metadata_lines(self, export_service):
        text = _content(export_service, format="txt")
        assert f"Video: {VIDEO}" in text
        assert "Type: prompt_readiness_report" in text
        assert "Versions analyzed: 1, 2, 3, 4, 5, 6, 7, 8" in text
        assert "Version count: 8" in text
        assert "First version: 1" in text
        assert "Last version: 8" in text
        assert "Selection order: 1, 2, 3, 4, 5, 6, 7, 8" in text

    @pytest.mark.parametrize("version", list(range(1, 9)))
    def test_version_blocks_present(self, export_service, version):
        _prompt, source, operation = STANDARD[version - 1]
        text = _content(export_service, format="txt")
        assert f"VERSION {version}\n" in text
        block = text.split(f"VERSION {version}\n", 1)[1]
        block = re.split(r"\nVERSION \d+\n", block, maxsplit=1)[0]
        assert f"Source: {source}" in block
        expected_op = operation if operation else "(empty)"
        assert f"Operation: {expected_op}" in block

    def test_required_and_supporting_dimension_lines(self,
                                                      export_service):
        text = _content(export_service, format="txt")
        block = text.split("VERSION 1\n", 1)[1].split(
            "VERSION 2\n", 1)[0]
        assert "REQUIRED DIMENSIONS" in block
        assert "SUPPORTING DIMENSIONS" in block
        for dimension in REQUIRED_KEYS:
            assert re.search(
                rf"{dimension}: (present|weak|missing) \(\d+\)",
                block), dimension
        for dimension in SUPPORTING_KEYS:
            assert re.search(
                rf"{dimension}: (present|weak|missing) \(\d+\)",
                block), dimension
        assert "Missing dimensions:" in block
        assert "Weak dimensions:" in block

    def test_known_dimension_values(self, export_service):
        text = _content(export_service, format="txt")
        block = text.split("VERSION 1\n", 1)[1].split(
            "VERSION 2\n", 1)[0]
        assert "subject: present (100)" in block
        v3 = text.split("VERSION 3\n", 1)[1].split(
            "VERSION 4\n", 1)[0]
        assert "camera: missing (0)" in v3

    def test_timeline_steps_ascii_arrow(self, export_service):
        text = _content(export_service, format="txt")
        for index, (a, b) in enumerate(
                [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7),
                 (7, 8)], start=1):
            assert f"Step {index}: Version {a} -> Version {b}" in text
        assert "\u2192" not in text, "TXT uses ASCII arrow only"

    def test_step_dimensions_and_transitions(self, export_service):
        text = _content(export_service, format="txt")
        block = text.split("Step 1:", 1)[1].split("Step 2:", 1)[0]
        assert "STEP DIMENSIONS" in block
        for dimension in ("subject", "action", "environment", "camera",
                          "lighting", "visual_style", "color",
                          "composition", "audio"):
            assert re.search(
                rf"{dimension}: (present|weak|missing) \(\d+\) -> "
                rf"(present|weak|missing) \(\d+\), changed: "
                rf"(true|false)", block), dimension
        assert "TRANSITIONS" in block
        assert "TRANSITION SUMMARY" in block
        for key in ("missing_to_weak", "missing_to_present",
                    "weak_to_missing", "weak_to_present",
                    "present_to_missing", "present_to_weak"):
            assert f"{key}: " in block
        assert "Required coverage: 100% -> 86% (delta -14)" in block

    def test_timeline_summary_block(self, export_service):
        text = _content(export_service, format="txt")
        block = text.split("TIMELINE SUMMARY", 1)[1]
        assert "Changed dimensions: 21" in block
        assert "Unchanged dimensions: 42" in block
        assert "Required changes: 17" in block
        assert "Supporting changes: 4" in block
        assert "Required coverage delta: -14" in block

    def test_summary_blocks(self, export_service):
        text = _content(export_service, format="txt")
        block = text.split("SUMMARY\n-------", 1)[1]
        assert "Versions analyzed: 8" in block
        assert "Ready count: 2" in block
        assert "Needs attention count: 6" in block
        assert "Total: 56" in block
        assert "Present: 34" in block
        assert "Coverage: 61%" in block
        assert "Total: 16" in block
        assert "DIMENSION SUMMARY" in block
        expected = [
            ("subject", 5, 2, 1), ("action", 4, 1, 3),
            ("environment", 7, 0, 1), ("camera", 3, 1, 4),
            ("lighting", 5, 0, 3), ("visual_style", 5, 0, 3),
            ("color", 4, 0, 4), ("composition", 5, 0, 3),
            ("audio", 4, 0, 4),
        ]
        for dimension, present, weak, missing in expected:
            assert (f"{dimension}: present {present}, weak {weak}, "
                    f"missing {missing}") in block, dimension

    def test_organization_block(self, marked_export):
        text = _content(marked_export, format="txt")
        block = text.split("ORGANIZATION", 1)[1]
        assert "Favorite count: 2" in block
        assert "Tags:" in block
        assert "ai: 1" in block
        assert "cinematic: 2" in block
        assert "draft: 1" in block
        assert "final: 1" in block

    def test_every_report_leaf_appears(self, export_service, result):
        text = _content(export_service, format="txt")
        for leaf in _leaves(result):
            assert _fmt(leaf) in text, _fmt(leaf)

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_selected_report_leaves_all_present(
            self, export_service, report_service, selection):
        report = report_service.generate_report(VIDEO, selection)
        text = _content(export_service, selection, format="txt")
        for leaf in _leaves(report):
            assert _fmt(leaf) in text, _fmt(leaf)

    def test_same_factual_information_as_markdown(
            self, export_service, result):
        md = _content(export_service, format="markdown")
        txt = _content(export_service, format="txt")
        for leaf in _leaves(result):
            rendered = _fmt(leaf)
            assert rendered in md and rendered in txt, rendered

    @pytest.mark.parametrize("word", FORBIDDEN_WORDS)
    def test_no_ranking_language(self, export_service, word):
        assert word not in _content(
            export_service, format="txt").lower(), word

    @pytest.mark.parametrize("prompt", [FULL, CITY, MINIMAL, SUBJ70])
    def test_no_prompt_text(self, export_service, prompt):
        assert prompt not in _content(export_service, format="txt")

    @pytest.mark.parametrize("name", INTERNAL_NAMES)
    def test_no_internal_objects(self, export_service, name):
        assert name not in _content(export_service, format="txt")

    @pytest.mark.parametrize("marker", PATH_MARKERS)
    def test_no_absolute_paths(self, export_service, marker):
        assert marker not in _content(export_service, format="txt")

    def test_deterministic_repeated(self, export_service):
        assert _content(export_service, format="txt") == \
            _content(export_service, format="txt")


class TestEmptyHistory:
    @pytest.fixture
    def empty_report(self, empty_chain):
        return empty_chain["report_service"].generate_report(EMPTY_VIDEO)

    @pytest.fixture
    def empty_json(self, empty_export):
        return json.loads(_content(empty_export, video=EMPTY_VIDEO))

    def test_json_exact_empty_structure(self, empty_export, empty_json):
        assert set(empty_json.keys()) == TOP_KEYS
        assert empty_json["video_filename"] == EMPTY_VIDEO
        assert empty_json["versions_analyzed"] == []
        assert empty_json["report"] == {
            "type": "prompt_readiness_report",
            "version_count": 0,
            "first_version": None,
            "last_version": None,
            "selection_order": [],
            "snapshots": [],
        }
        assert empty_json["timeline"] == {
            "steps": [],
            "changed_dimensions": 0,
            "unchanged_dimensions": 0,
            "required_changes": 0,
            "supporting_changes": 0,
            "transition_summary": {
                "missing_to_weak": 0, "missing_to_present": 0,
                "weak_to_missing": 0, "weak_to_present": 0,
                "present_to_missing": 0, "present_to_weak": 0,
            },
            "required_coverage_delta": None,
        }
        summary = empty_json["summary"]
        assert set(summary.keys()) == SUMMARY_KEYS
        assert summary["versions_analyzed"] == 0
        assert summary["ready_count"] == 0
        assert summary["needs_attention_count"] == 0
        assert summary["required"] == {
            "total": 0, "present": 0, "weak": 0, "missing": 0,
            "coverage_percentage": None,
        }
        assert summary["supporting"] == {
            "total": 0, "present": 0, "weak": 0, "missing": 0,
        }
        assert summary["dimension_summary"] == []
        assert summary["organization"] == {
            "favorite_count": 0, "tag_counts": {},
        }

    def test_json_null_values_rendered(self, empty_export):
        text = _content(empty_export, video=EMPTY_VIDEO)
        assert '"first_version": null' in text
        assert '"last_version": null' in text
        assert '"required_coverage_delta": null' in text
        assert '"coverage_percentage": null' in text

    def test_json_equals_day29_empty_report(
            self, empty_export, empty_report):
        assert json.loads(_content(
            empty_export, video=EMPTY_VIDEO)) == empty_report

    def test_markdown_zero_versions(self, empty_export):
        text = _content(empty_export, video=EMPTY_VIDEO,
                        format="markdown")
        assert "No saved versions." in text
        assert "No timeline steps." in text
        assert "### Version " not in text
        assert "- Version count: 0" in text
        assert "- Versions analyzed: none" in text
        assert "- First version: none" in text
        assert "- Last version: none" in text
        assert "- Selection order: none" in text

    def test_markdown_zero_summary(self, empty_export):
        text = _content(empty_export, video=EMPTY_VIDEO,
                        format="markdown")
        assert "- Ready count: 0" in text
        assert "- Needs attention count: 0" in text
        assert "- Coverage: none" in text
        assert "- Required coverage delta: none" in text
        assert "- Favorite count: 0" in text
        assert "- Tags: none" in text

    def test_markdown_no_fabricated_version_data(self, empty_export):
        text = _content(empty_export, video=EMPTY_VIDEO,
                        format="markdown")
        for version in ("Source:", "Status:", "| subject |"):
            assert version not in text, version

    def test_txt_zero_versions(self, empty_export):
        text = _content(empty_export, video=EMPTY_VIDEO, format="txt")
        assert "No saved versions." in text
        assert "No timeline steps." in text
        assert "VERSION 1\n" not in text
        assert "Version count: 0" in text
        assert "Versions analyzed: none" in text
        assert "First version: none" in text

    def test_txt_zero_summary(self, empty_export):
        text = _content(empty_export, video=EMPTY_VIDEO, format="txt")
        assert "Ready count: 0" in text
        assert "Needs attention count: 0" in text
        assert "Coverage: none" in text
        assert "Required coverage delta: none" in text
        assert "Favorite count: 0" in text
        assert "Tags: none" in text

    def test_empty_leaves_present_in_both(
            self, empty_export, empty_report):
        for fmt in ("markdown", "txt"):
            text = _content(empty_export, video=EMPTY_VIDEO, format=fmt)
            for leaf in _leaves(empty_report):
                assert _fmt(leaf) in text, (fmt, _fmt(leaf))

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_empty_deterministic(self, empty_export, fmt):
        assert _content(empty_export, video=EMPTY_VIDEO,
                        format=fmt) == \
            _content(empty_export, video=EMPTY_VIDEO, format=fmt)


class TestSingleVersion:
    @pytest.mark.parametrize("fmt", FORMATS)
    def test_single_version_export(self, export_service, fmt):
        text = _content(export_service, [6], format=fmt)
        report = _parsed(export_service, [6])
        assert report["report"]["version_count"] == 1
        assert report["report"]["first_version"] == 6
        assert report["report"]["last_version"] == 6
        assert report["versions_analyzed"] == [6]
        assert report["timeline"]["steps"] == []
        assert report["timeline"]["required_coverage_delta"] == 0
        for leaf in _leaves(report):
            assert _fmt(leaf) in text, (fmt, _fmt(leaf))

    def test_markdown_has_exactly_one_version_section(
            self, export_service):
        text = _content(export_service, [6], format="markdown")
        assert text.count("### Version ") == 1
        assert "### Version 6\n" in text
        assert "No timeline steps." in text

    def test_txt_has_exactly_one_version_block(self, export_service):
        text = _content(export_service, [6], format="txt")
        blocks = re.findall(r"(?m)^VERSION \d+$", text)
        assert blocks == ["VERSION 6"], blocks
        assert "No timeline steps." in text

    def test_aggregates_match_that_version(self, export_service):
        report = _parsed(export_service, [6])
        summary = report["summary"]
        assert summary["versions_analyzed"] == 1
        assert summary["required"] == {
            "total": 7, "present": 0, "weak": 0, "missing": 7,
            "coverage_percentage": 0,
        }
        assert summary["supporting"] == {
            "total": 2, "present": 0, "weak": 0, "missing": 2,
        }
        assert len(summary["dimension_summary"]) == 9
        for row in summary["dimension_summary"]:
            assert row["present"] + row["weak"] + row["missing"] == 1

    def test_single_markdown_summary_values(self, export_service):
        text = _content(export_service, [6], format="markdown")
        assert "- Total: 7" in text
        assert "- Total: 2" in text
        assert "- Coverage: 0%" in text
        assert "- Required coverage delta: 0" in text


class TestSelection:
    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_selection_order_preserved(
            self, export_service, selection):
        report = _parsed(export_service, selection)
        if selection is None:
            assert report["versions_analyzed"] == list(range(1, 9))
        else:
            assert report["versions_analyzed"] == selection
        assert report["report"]["selection_order"] == \
            report["versions_analyzed"]

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_pairs_follow_requested_order(
            self, export_service, selection):
        report = _parsed(export_service, selection)
        versions = report["versions_analyzed"]
        expected = list(zip(versions, versions[1:]))
        assert _pairs(report) == expected

    def test_reverse_selection_markdown(self, export_service):
        text = _content(export_service, [5, 3, 1], format="markdown")
        assert "- Selection order: 5, 3, 1" in text
        positions = [text.index(f"### Version {v}")
                     for v in (5, 3, 1)]
        assert positions == sorted(positions)

    def test_reverse_selection_txt(self, export_service):
        text = _content(export_service, [5, 3, 1], format="txt")
        assert "Selection order: 5, 3, 1" in text

    def test_subset_summary_values(self, export_service):
        report = _parsed(export_service, [1, 3, 5])
        assert report["summary"]["required"] == {
            "total": 21, "present": 14, "weak": 1, "missing": 6,
            "coverage_percentage": 67,
        }
        assert report["timeline"]["required_coverage_delta"] == -86

    def test_all_formats_agree_on_selection(
            self, export_service, report_service):
        report = report_service.generate_report(VIDEO, [4, 2])
        assert json.loads(_content(
            export_service, [4, 2])) == report
        for fmt in ("markdown", "txt"):
            text = _content(export_service, [4, 2], format=fmt)
            for leaf in _leaves(report):
                assert _fmt(leaf) in text, (fmt, _fmt(leaf))

    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_json_byte_identical_across_repeated_selection_calls(
            self, export_service, selection):
        assert _content(export_service, selection) == \
            _content(export_service, selection)


class TestValidation:
    @pytest.mark.parametrize("bad_format", [
        "xml", "csv", "json ", " json", "JSON", "Json", "Markdown",
        "md", "html", "", "js", "application/json",
    ])
    def test_invalid_format_raises_value_error(
            self, export_service, bad_format):
        with pytest.raises(ValueError,
                           match="Invalid format. Must be one of:"):
            export_service.export_report(VIDEO, format=bad_format)

    @pytest.mark.parametrize("bad_format", [None, 123, ["json"], {}])
    def test_non_string_format_raises_value_error(
            self, export_service, bad_format):
        with pytest.raises(ValueError,
                           match="Invalid format. Must be one of:"):
            export_service.export_report(VIDEO, format=bad_format)

    def test_invalid_format_message_is_day19_exact(self, export_service):
        with pytest.raises(ValueError) as exc:
            export_service.export_report(VIDEO, format="xml")
        assert str(exc.value) == (
            "Invalid format. Must be one of: json, markdown, txt")

    def test_format_checked_before_report_build(self, export_service):
        # invalid format AND nonexistent video: format wins (ValueError
        # about format, never a not-found message).
        with pytest.raises(ValueError, match="Invalid format"):
            export_service.export_report("missing.mp4", format="xml")

    @pytest.mark.parametrize("bad_versions,message", [
        ([], "versions must be a non-empty list of positive integers."),
        ("1,3", "versions must be a non-empty list of positive "
                "integers."),
        ({1}, "versions must be a non-empty list of positive integers."),
        ([0], "versions must contain positive integers."),
        ([-1], "versions must contain positive integers."),
        ([0, 3], "versions must contain positive integers."),
        ([1, 1], "duplicate versions are not allowed."),
        ([2, 1, 2], "duplicate versions are not allowed."),
    ])
    def test_invalid_versions_propagate_exact_messages(
            self, export_service, bad_versions, message):
        for fmt in FORMATS:
            with pytest.raises(ValueError) as exc:
                export_service.export_report(
                    VIDEO, bad_versions, format=fmt)
            assert str(exc.value) == message

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_missing_version_message(self, export_service, fmt):
        with pytest.raises(ValueError) as exc:
            export_service.export_report(VIDEO, [99], format=fmt)
        assert str(exc.value) == \
            f"Version 99 not found for video '{VIDEO}'."

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_missing_version_within_selection(self, export_service, fmt):
        with pytest.raises(ValueError) as exc:
            export_service.export_report(VIDEO, [1, 99], format=fmt)
        assert str(exc.value) == \
            f"Version 99 not found for video '{VIDEO}'."

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_deleted_version_message(self, export_service, history, fmt):
        created = history.create_version(VIDEO, CITY, source="custom")
        version = created["version"]
        history.delete_version(VIDEO, version)
        with pytest.raises(ValueError) as exc:
            export_service.export_report(VIDEO, [version], format=fmt)
        assert str(exc.value) == \
            f"Version {version} not found for video '{VIDEO}'."

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_deleted_version_absent_from_default_selection(
            self, export_service, history, fmt):
        created = history.create_version(VIDEO, CITY, source="custom")
        version = created["version"]
        history.delete_version(VIDEO, version)
        text = _content(export_service, format=fmt)
        assert f"VERSION {version}\n" not in text
        assert f"### Version {version}\n" not in text
        if fmt == "json":
            assert version not in json.loads(text)["versions_analyzed"]


class TestDeterminism:
    @pytest.mark.parametrize("fmt", FORMATS)
    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_byte_identical_repeated_exports(
            self, export_service, fmt, selection):
        first = _content(export_service, selection, format=fmt)
        second = _content(export_service, selection, format=fmt)
        assert first == second

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_generated_timestamps(self, export_service, history, fmt):
        text = _content(export_service, format=fmt)
        for version in range(1, 9):
            record = history.get_version(VIDEO, version)
            assert record["created_at"] in text, version
        assert "generated_at" not in text
        assert "exported_at" not in text
        assert "timestamp" not in text.lower()

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_uuids_beyond_video_filename(self, export_service, fmt):
        text = _content(export_service, format=fmt).replace(VIDEO, "")
        assert not re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}"
            r"-[0-9a-f]{12}", text)

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_random_markers(self, export_service, fmt):
        text = _content(export_service, format=fmt).lower()
        for marker in ("random", "nonce", "uuid4", "time.time",
                       "datetime.now"):
            assert marker not in text, marker

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_filenames_stable_across_selections(self, export_service,
                                                fmt):
        names = {
            export_service.export_report(VIDEO, selection, fmt)["filename"]
            for selection in SELECTIONS
        }
        assert names == {FILENAMES[fmt]}


class TestReadOnlyIntegrity:
    @pytest.fixture
    def snapshot_state(self, chain, history):
        """Capture full stored state before any export runs."""
        organization = chain["organization"]
        listing = [entry["version"] for entry in
                   history.list_versions(VIDEO)]
        records = {
            version: json.dumps(
                history.get_version(VIDEO, version), sort_keys=True)
            for version in listing
        }
        orgs = {
            version: json.dumps(
                organization.get_organization(VIDEO, version),
                sort_keys=True)
            for version in listing
        }
        return {"listing": listing, "records": records, "orgs": orgs}

    @pytest.mark.parametrize("fmt", FORMATS)
    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_history_unchanged(
            self, export_service, chain, history, snapshot_state,
            fmt, selection):
        _content(export_service, selection, format=fmt)
        listing = [entry["version"] for entry in
                   history.list_versions(VIDEO)]
        assert listing == snapshot_state["listing"]
        for version in listing:
            assert json.dumps(
                history.get_version(VIDEO, version),
                sort_keys=True) == snapshot_state["records"][version]

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_favorites_and_tags_unchanged(
            self, marked, marked_export, chain, snapshot_state, fmt):
        organization = chain["organization"]
        _content(marked_export, format=fmt)
        for version in snapshot_state["listing"]:
            assert json.dumps(
                organization.get_organization(VIDEO, version),
                sort_keys=True) == snapshot_state["orgs"][version]

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_reports_never_create_or_delete_versions(
            self, export_service, history, fmt):
        before = [entry["version"] for entry in
                  history.list_versions(VIDEO)]
        for selection in SELECTIONS:
            _content(export_service, selection, format=fmt)
        after = [entry["version"] for entry in
                 history.list_versions(VIDEO)]
        assert after == before == list(range(1, 9))

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_day19_export_unchanged(
            self, export_service, chain, history, fmt):
        from app.services.prompt_export_service import PromptExportService
        day19 = PromptExportService(
            history, chain["organization"])
        before = {
            name: day19.export_version(VIDEO, 1, name)["content"]
            for name in DAY19_FORMATS
        }
        _content(export_service, format=fmt)
        after = {
            name: day19.export_version(VIDEO, 1, name)["content"]
            for name in DAY19_FORMATS
        }
        assert after == before

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_readiness_output_unchanged(self, export_service, chain, fmt):
        before = chain["readiness"].validate_prompt(FULL)
        _content(export_service, format=fmt)
        assert chain["readiness"].validate_prompt(FULL) == before

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_prompt_records_untouched(
            self, export_service, history, fmt):
        record = history.get_version(VIDEO, 1)
        _content(export_service, format=fmt)
        assert history.get_version(VIDEO, 1) == record

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_report_payload_stable_after_exports(
            self, export_service, report_service, fmt):
        before = report_service.generate_report(VIDEO)
        for _ in range(3):
            _content(export_service, format=fmt)
        assert report_service.generate_report(VIDEO) == before


class TestNoRankingAndLeakScans:
    @pytest.mark.parametrize("fmt", FORMATS)
    @pytest.mark.parametrize("selection", SELECTIONS)
    def test_no_forbidden_words(
            self, export_service, fmt, selection):
        text = _content(export_service, selection, format=fmt).lower()
        for word in FORBIDDEN_WORDS:
            assert word not in text, (fmt, selection, word)

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_prompt_or_negative_prompt_text(self, export_service,
                                               fmt):
        text = _content(export_service, format=fmt)
        assert "film grain style portrait" not in text
        assert "blurry, low quality" not in text
        assert "walking, looking around" not in text

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_internal_names(self, export_service, fmt):
        text = _content(export_service, format=fmt)
        for name in INTERNAL_NAMES:
            assert name not in text, name

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_absolute_paths(self, export_service, fmt):
        text = _content(export_service, format=fmt)
        for marker in PATH_MARKERS:
            assert marker not in text, marker

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_secret_like_keys(self, export_service, fmt):
        text = _content(export_service, format=fmt).lower()
        for key in ("password", "secret", "api_key", "authorization",
                    "bearer"):
            assert key not in text, key

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_no_filesystem_persistence_markers(self, export_service,
                                               fmt):
        text = _content(export_service, format=fmt)
        for marker in ("open(", "write(", ".save(", "with open",
                       "os.makedirs", "Path("):
            assert marker not in text, marker
