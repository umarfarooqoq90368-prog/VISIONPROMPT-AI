"""Tests for the prompt export service (Day 19)."""
import json
import re

import pytest

from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService
from app.services.prompt_export_service import PromptExportService, VALID_EXPORT_FORMATS

VIDEO = "abc123.mp4"
OTHER = "def456.mp4"

NEGATIVE = "blurry, low quality, distorted anatomy, unwanted text, watermark"
PROMPT = "Cinematic wide shot of the subject, golden hour lighting, slow dolly in."


@pytest.fixture
def history():
    return PromptHistoryService()


@pytest.fixture
def org(history):
    return PromptOrganizationService(history)


@pytest.fixture
def export(history, org):
    return PromptExportService(history, org)


def save(history, video=VIDEO, prompt=PROMPT, source="custom", operation="",
         metadata=None, negative=NEGATIVE):
    return history.create_version(
        video_filename=video,
        prompt=prompt,
        negative_prompt=negative,
        source=source,
        operation=operation,
        metadata=metadata,
    )


def payload(export, video=VIDEO, version=1, format="json"):
    return json.loads(export.export_version(video, version, format)["content"])


class TestJsonExport:
    def test_json_export_valid_json(self, history, export):
        save(history)
        out = export.export_version(VIDEO, 1, "json")
        assert out["format"] == "json"
        parsed = json.loads(out["content"])
        assert isinstance(parsed, dict)

    def test_json_media_type_and_filename(self, history, export):
        save(history)
        out = export.export_version(VIDEO, 1, "json")
        assert out["media_type"] == "application/json"
        assert out["filename"] == "visionprompt_abc123_v1.json"

    def test_json_exact_key_structure(self, history, export):
        save(history, source="refinement", operation="cinematic",
             metadata={"style": "film"})
        data = payload(export, version=1)
        assert list(data.keys()) == [
            "video_filename", "version", "version_id", "source",
            "operation", "prompt", "negative_prompt", "created_at",
            "metadata", "favorite", "tags",
        ]

    def test_json_no_extra_keys(self, history, export):
        save(history)
        data = payload(export, version=1)
        assert set(data.keys()) == {
            "video_filename", "version", "version_id", "source",
            "operation", "prompt", "negative_prompt", "created_at",
            "metadata", "favorite", "tags",
        }

    def test_json_metadata_default_empty_dict(self, history, export):
        save(history)
        assert payload(export, version=1)["metadata"] == {}

    def test_json_metadata_preserved(self, history, export):
        save(history, metadata={"style": "film", "sections_keys": ["a", "b"]})
        data = payload(export, version=1)
        assert data["metadata"] == {"style": "film", "sections_keys": ["a", "b"]}

    def test_json_all_formats_valid_set(self, export):
        assert VALID_EXPORT_FORMATS == {"json", "markdown", "txt"}


class TestMarkdownExport:
    def test_markdown_title_and_sections(self, history, export):
        save(history, source="refinement", operation="cinematic")
        out = export.export_version(VIDEO, 1, "markdown")
        content = out["content"]
        assert content.startswith("# VisionPrompt AI Prompt\n")
        for heading in ["## Video", "## Version", "## Source", "## Operation",
                        "## Prompt", "## Negative Prompt", "## Tags",
                        "## Favorite", "## Created At"]:
            assert heading in content
        assert out["media_type"] == "text/markdown"
        assert out["filename"] == "visionprompt_abc123_v1.md"

    def test_markdown_video_version_source_operation(self, history, export):
        save(history, source="refinement", operation="cinematic")
        content = export.export_version(VIDEO, 1, "markdown")["content"]
        assert "`abc123.mp4`" in content
        assert "## Version\n\n1" in content
        assert "## Source\n\nrefinement" in content
        assert "## Operation\n\ncinematic" in content

    def test_markdown_exact_prompt_preserved(self, history, export):
        prompt = "Shot 1: establishing wide.\nShot 2: slow push-in, detail."
        save(history, prompt=prompt)
        content = export.export_version(VIDEO, 1, "markdown")["content"]
        assert f"## Prompt\n\n{prompt}\n" in content

    def test_markdown_exact_negative_preserved(self, history, export):
        save(history)
        content = export.export_version(VIDEO, 1, "markdown")["content"]
        assert f"## Negative Prompt\n\n{NEGATIVE}\n" in content

    def test_markdown_prompt_with_markdown_syntax_untouched(self, history, export):
        prompt = "# not a heading\n```code```\n* not a list"
        save(history, prompt=prompt, negative="")
        content = export.export_version(VIDEO, 1, "markdown")["content"]
        assert f"## Prompt\n\n{prompt}\n" in content

    def test_markdown_empty_operation_and_negative(self, history, export):
        save(history, operation="", negative="")
        content = export.export_version(VIDEO, 1, "markdown")["content"]
        assert "## Operation\n\n(empty)" in content
        assert "## Negative Prompt\n\n(empty)" in content

    def test_markdown_tags_bullets_sorted(self, history, export):
        save(history)
        org = PromptOrganizationService(history)
        export2 = PromptExportService(history, org)
        org.add_tags(VIDEO, 1, ["Cinematic", "ai", "  Zeta "])
        content = export2.export_version(VIDEO, 1, "markdown")["content"]
        assert "## Tags\n\n* ai\n* cinematic\n* zeta" in content

    def test_markdown_no_tags(self, history, export):
        save(history)
        content = export.export_version(VIDEO, 1, "markdown")["content"]
        assert "## Tags\n\n(none)" in content

    def test_markdown_favorite_true_and_false(self, history, export):
        save(history)
        org = PromptOrganizationService(history)
        export2 = PromptExportService(history, org)
        content = export2.export_version(VIDEO, 1, "markdown")["content"]
        assert "## Favorite\n\nfalse" in content
        org.favorite_version(VIDEO, 1)
        content = export2.export_version(VIDEO, 1, "markdown")["content"]
        assert "## Favorite\n\ntrue" in content

    def test_markdown_metadata_section_only_when_exists(self, history, export):
        save(history, metadata={"style": "film"})
        content = export.export_version(VIDEO, 1, "markdown")["content"]
        assert "## Metadata" in content
        assert "```json" in content
        assert '"style": "film"' in content

    def test_markdown_omits_metadata_when_empty(self, history, export):
        save(history, metadata={})
        content = export.export_version(VIDEO, 1, "markdown")["content"]
        assert "## Metadata" not in content

    def test_markdown_created_at_present(self, history, export):
        record = save(history)
        content = export.export_version(VIDEO, 1, "markdown")["content"]
        assert f"## Created At\n\n{record['created_at']}" in content

    def test_markdown_ends_with_single_newline(self, history, export):
        save(history)
        content = export.export_version(VIDEO, 1, "markdown")["content"]
        assert content.endswith("\n") and not content.endswith("\n\n")


class TestTxtExport:
    def test_txt_header_and_fields(self, history, export):
        save(history, source="refinement", operation="cinematic")
        out = export.export_version(VIDEO, 1, "txt")
        content = out["content"]
        assert content.startswith("# VISIONPROMPT AI PROMPT\n")
        assert "Video: abc123.mp4" in content
        assert "Version: 1" in content
        assert "Source: refinement" in content
        assert "Operation: cinematic" in content
        assert out["media_type"] == "text/plain"
        assert out["filename"] == "visionprompt_abc123_v1.txt"

    def test_txt_favorite_and_tags(self, history, export):
        save(history)
        org = PromptOrganizationService(history)
        export2 = PromptExportService(history, org)
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        content = export2.export_version(VIDEO, 1, "txt")["content"]
        assert "Favorite: true" in content
        assert "Tags: ai, cinematic" in content

    def test_txt_no_tags(self, history, export):
        save(history)
        content = export.export_version(VIDEO, 1, "txt")["content"]
        assert "Tags: (none)" in content

    def test_txt_exact_prompt_preserved(self, history, export):
        prompt = "Line one of prompt.\nLine two of prompt."
        save(history, prompt=prompt)
        content = export.export_version(VIDEO, 1, "txt")["content"]
        assert f"## PROMPT\n\n{prompt}\n" in content

    def test_txt_exact_negative_preserved(self, history, export):
        save(history)
        content = export.export_version(VIDEO, 1, "txt")["content"]
        assert f"## NEGATIVE PROMPT\n\n{NEGATIVE}\n" in content

    def test_txt_empty_operation_and_negative(self, history, export):
        save(history, operation="", negative="")
        content = export.export_version(VIDEO, 1, "txt")["content"]
        assert "Operation: (empty)" in content
        assert "## NEGATIVE PROMPT\n\n(empty)" in content

    def test_txt_metadata_only_when_exists(self, history, export):
        save(history, metadata={"custom_instruction": "keep faces sharp"})
        content = export.export_version(VIDEO, 1, "txt")["content"]
        assert "## METADATA" in content
        assert '"custom_instruction": "keep faces sharp"' in content

    def test_txt_omits_metadata_when_empty(self, history, export):
        save(history, metadata={})
        content = export.export_version(VIDEO, 1, "txt")["content"]
        assert "## METADATA" not in content

    def test_txt_created_at_present(self, history, export):
        record = save(history)
        content = export.export_version(VIDEO, 1, "txt")["content"]
        assert f"Created At: {record['created_at']}" in content


class TestPreservation:
    def test_prompt_preserved_all_formats(self, history, export):
        prompt = 'Exact "quoted" prompt, with 100% punctuation & symbols.'
        save(history, prompt=prompt)
        data = payload(export, version=1)
        assert data["prompt"] == prompt
        assert f"## Prompt\n\n{prompt}" in export.export_version(VIDEO, 1, "markdown")["content"]
        assert f"## PROMPT\n\n{prompt}" in export.export_version(VIDEO, 1, "txt")["content"]

    def test_negative_prompt_preserved(self, history, export):
        save(history, negative=NEGATIVE)
        data = payload(export, version=1)
        assert data["negative_prompt"] == NEGATIVE

    def test_source_preserved(self, history, export):
        save(history, source="template")
        assert payload(export, version=1)["source"] == "template"

    def test_operation_preserved(self, history, export):
        save(history, source="refinement", operation="shorten")
        assert payload(export, version=1)["operation"] == "shorten"

    def test_version_preserved(self, history, export):
        save(history, prompt="one")
        save(history, prompt="two")
        assert payload(export, version=2)["version"] == 2

    def test_version_id_preserved(self, history, export):
        save(history)
        assert payload(export, version=1)["version_id"] == f"{VIDEO}:1"

    def test_created_at_preserved(self, history, export):
        record = save(history)
        assert payload(export, version=1)["created_at"] == record["created_at"]

    def test_metadata_preserved_json(self, history, export):
        metadata = {"sections_keys": ["camera", "style"], "nested": {"a": 1}}
        save(history, metadata=metadata)
        assert payload(export, version=1)["metadata"] == metadata

    def test_video_filename_preserved(self, history, export):
        save(history)
        assert payload(export, version=1)["video_filename"] == VIDEO

    def test_unicode_prompt_round_trip(self, history, export):
        prompt = "Café über naïve — 日本語テキスト"
        save(history, prompt=prompt)
        out = export.export_version(VIDEO, 1, "json")
        assert json.loads(out["content"])["prompt"] == prompt
        assert prompt in out["content"]

    def test_multiline_prompt_round_trip(self, history, export):
        prompt = "first line\nsecond line\n\tindented line"
        save(history, prompt=prompt)
        assert payload(export, version=1)["prompt"] == prompt


class TestOrganizationMetadata:
    def test_favorite_true_included(self, history, org):
        export = PromptExportService(history, org)
        save(history)
        org.favorite_version(VIDEO, 1)
        assert payload(export, version=1)["favorite"] is True

    def test_favorite_default_false(self, history, org):
        export = PromptExportService(history, org)
        save(history)
        assert payload(export, version=1)["favorite"] is False

    def test_tags_included(self, history, org):
        export = PromptExportService(history, org)
        save(history)
        org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        assert payload(export, version=1)["tags"] == ["ai", "cinematic"]

    def test_tag_normalization_and_order(self, history, org):
        export = PromptExportService(history, org)
        save(history)
        org.add_tags(VIDEO, 1, ["  Cinematic ", "AI", "ai", "Zeta"])
        assert payload(export, version=1)["tags"] == ["ai", "cinematic", "zeta"]

    def test_no_tags_default_empty(self, history, org):
        export = PromptExportService(history, org)
        save(history)
        assert payload(export, version=1)["tags"] == []

    def test_org_metadata_reflects_later_changes(self, history, org):
        export = PromptExportService(history, org)
        save(history)
        assert payload(export, version=1)["favorite"] is False
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["fresh"])
        data = payload(export, version=1)
        assert data["favorite"] is True
        assert data["tags"] == ["fresh"]


class TestNotFoundAndValidation:
    def test_nonexistent_version_raises(self, history, export):
        save(history)
        with pytest.raises(ValueError):
            export.export_version(VIDEO, 99, "json")

    def test_deleted_version_raises(self, history, export):
        save(history)
        history.delete_version(VIDEO, 1)
        for fmt in ("json", "markdown", "txt"):
            with pytest.raises(ValueError):
                export.export_version(VIDEO, 1, fmt)

    def test_nonexistent_video_raises(self, history, export):
        with pytest.raises(ValueError):
            export.export_version("missing.mp4", 1, "json")

    def test_deleted_middle_version_raises(self, history, export):
        save(history, prompt="one")
        save(history, prompt="two")
        history.delete_version(VIDEO, 1)
        with pytest.raises(ValueError):
            export.export_version(VIDEO, 1, "json")
        assert payload(export, version=2)["prompt"] == "two"

    def test_version_zero_raises(self, history, export):
        save(history)
        with pytest.raises(ValueError):
            export.export_version(VIDEO, 0, "json")

    def test_negative_version_raises(self, history, export):
        save(history)
        with pytest.raises(ValueError):
            export.export_version(VIDEO, -1, "json")

    @pytest.mark.parametrize("fmt", ["xml", "html", "Json", "TXT", "", " json", "json "])
    def test_invalid_format_raises(self, history, export, fmt):
        save(history)
        with pytest.raises(ValueError):
            export.export_version(VIDEO, 1, fmt)

    @pytest.mark.parametrize("fmt", ["json", "markdown", "txt"])
    def test_valid_formats_accepted(self, history, export, fmt):
        save(history)
        out = export.export_version(VIDEO, 1, fmt)
        assert out["format"] == fmt
        assert isinstance(out["content"], str) and out["content"]


class TestMultipleVersionsAndVideos:
    def test_multiple_versions_export_correctly(self, history, export):
        save(history, prompt="first prompt")
        save(history, prompt="second prompt")
        assert payload(export, version=1)["prompt"] == "first prompt"
        assert payload(export, version=2)["prompt"] == "second prompt"
        v1 = export.export_version(VIDEO, 1, "markdown")["content"]
        v2 = export.export_version(VIDEO, 2, "markdown")["content"]
        assert "first prompt" in v1 and "second prompt" not in v1
        assert "second prompt" in v2 and "first prompt" not in v2

    def test_multiple_videos_isolated(self, history, export):
        save(history, video=VIDEO, prompt="video A prompt")
        save(history, video=OTHER, prompt="video B prompt")
        a = payload(export, video=VIDEO, version=1)
        b = payload(export, video=OTHER, version=1)
        assert a["video_filename"] == VIDEO
        assert b["video_filename"] == OTHER
        assert a["version_id"] == f"{VIDEO}:1"
        assert b["version_id"] == f"{OTHER}:1"
        assert a["prompt"] == "video A prompt"
        assert b["prompt"] == "video B prompt"

    def test_version_ids_distinct_per_video(self, history, export):
        save(history, video=VIDEO)
        save(history, video=OTHER)
        assert payload(export, video=VIDEO, version=1)["version_id"] != \
            payload(export, video=OTHER, version=1)["version_id"]


class TestDeterminism:
    def test_deterministic_json(self, history, export):
        save(history, source="refinement", operation="cinematic",
             metadata={"k": "v"})
        first = export.export_version(VIDEO, 1, "json")["content"]
        second = export.export_version(VIDEO, 1, "json")["content"]
        assert first == second

    def test_deterministic_markdown(self, history, export):
        save(history, metadata={"k": "v"})
        first = export.export_version(VIDEO, 1, "markdown")["content"]
        second = export.export_version(VIDEO, 1, "markdown")["content"]
        assert first == second

    def test_deterministic_txt(self, history, export):
        save(history, metadata={"k": "v"})
        first = export.export_version(VIDEO, 1, "txt")["content"]
        second = export.export_version(VIDEO, 1, "txt")["content"]
        assert first == second

    def test_deterministic_across_fresh_service_instances(self, history, export):
        save(history, metadata={"k": "v"})
        other = PromptExportService(
            history, PromptOrganizationService(history)
        )
        for fmt in ("json", "markdown", "txt"):
            assert (export.export_version(VIDEO, 1, fmt)["content"]
                    == other.export_version(VIDEO, 1, fmt)["content"])

    def test_export_envelope_keys_stable(self, history, export):
        save(history)
        out = export.export_version(VIDEO, 1, "txt")
        assert list(out.keys()) == ["format", "content", "media_type", "filename"]


class TestNoFabrication:
    @pytest.mark.parametrize("fmt", ["json", "markdown", "txt"])
    def test_no_fabricated_video_information(self, history, export, fmt):
        save(history, prompt="alpha beta gamma", negative="noise watermark")
        content = export.export_version(VIDEO, 1, fmt)["content"].lower()
        for word in ["person", "character", "dialogue", "walking", "running",
                     "park", "city", "sunset", "brand", "product", "voiceover",
                     "camera pan", "zoom"]:
            assert word not in content, f"fabricated: {word}"

    @pytest.mark.parametrize("fmt", ["json", "markdown", "txt"])
    def test_no_absolute_filesystem_paths(self, history, export, fmt):
        save(history, metadata={"path": "relative/entry"})
        content = export.export_version(VIDEO, 1, fmt)["content"]
        for bad in ["C:/", "C:\\", "/home", "/Users", "/var/", "/etc/"]:
            assert bad not in content, f"absolute path {bad}"

    def test_json_no_internal_service_information(self, history, export):
        save(history)
        content = export.export_version(VIDEO, 1, "json")["content"]
        for internal in ["_storage", "_org", "_history", "_organization",
                         "PromptHistoryService", "storage/uploads", "self."]:
            assert internal not in content, f"internal leak: {internal}"


class TestReadOnly:
    def test_history_unchanged_after_export(self, history, export):
        save(history, prompt="original prompt", metadata={"k": "v"})
        before = json.dumps(history.list_versions(VIDEO), sort_keys=True)
        for fmt in ("json", "markdown", "txt"):
            export.export_version(VIDEO, 1, fmt)
        after = json.dumps(history.list_versions(VIDEO), sort_keys=True)
        assert before == after

    def test_history_record_exactly_identical_after_export(self, history, export):
        record = save(history, prompt="keep me")
        before = json.dumps(history.get_version(VIDEO, 1), sort_keys=True)
        export.export_version(VIDEO, 1, "json")
        export.export_version(VIDEO, 1, "markdown")
        export.export_version(VIDEO, 1, "txt")
        after = json.dumps(history.get_version(VIDEO, 1), sort_keys=True)
        assert before == after
        assert history.get_version(VIDEO, 1)["prompt"] == record["prompt"]

    def test_org_unchanged_after_export(self, history, org):
        export = PromptExportService(history, org)
        save(history)
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        before = json.dumps(org.get_organization(VIDEO, 1), sort_keys=True)
        export.export_version(VIDEO, 1, "json")
        export.export_version(VIDEO, 1, "markdown")
        after = json.dumps(org.get_organization(VIDEO, 1), sort_keys=True)
        assert before == after

    def test_export_does_not_create_versions(self, history, export):
        save(history)
        save(history, prompt="two")
        export.export_version(VIDEO, 1, "json")
        export.export_version(VIDEO, 2, "txt")
        assert len(history.list_versions(VIDEO)) == 2

    def test_export_does_not_favorite_or_tag(self, history, org):
        export = PromptExportService(history, org)
        save(history)
        export.export_version(VIDEO, 1, "json")
        org_state = org.get_organization(VIDEO, 1)
        assert org_state["favorite"] is False
        assert org_state["tags"] == []


class TestFilenameSafety:
    @pytest.mark.parametrize("fmt,ext", [
        ("json", "json"), ("markdown", "md"), ("txt", "txt"),
    ])
    def test_filename_pattern(self, history, export, fmt, ext):
        save(history)
        out = export.export_version(VIDEO, 1, fmt)
        assert out["filename"] == f"visionprompt_abc123_v1.{ext}"
        assert re.fullmatch(
            r"visionprompt_[A-Za-z0-9_-]+_v\d+\.(json|md|txt)", out["filename"]
        )

    def test_filename_sanitizes_unsafe_video_names(self, history, export):
        weird = "my video (final).mp4"
        save(history, video=weird)
        out = export.export_version(weird, 1, "json")
        assert re.fullmatch(
            r"visionprompt_[A-Za-z0-9_-]+_v1\.json", out["filename"]
        )
        assert " " not in out["filename"]
        assert "(" not in out["filename"]

    def test_filename_version_numbers_change_with_version(self, history, export):
        save(history, prompt="one")
        save(history, prompt="two")
        assert export.export_version(VIDEO, 1, "json")["filename"] == \
            "visionprompt_abc123_v1.json"
        assert export.export_version(VIDEO, 2, "markdown")["filename"] == \
            "visionprompt_abc123_v2.md"


class TestEdgeCases:
    def test_empty_metadata_dict(self, history, export):
        save(history, metadata={})
        assert payload(export, version=1)["metadata"] == {}

    def test_metadata_with_nested_structures(self, history, export):
        metadata = {"preserved_information": ["a", "b"], "count": 2}
        save(history, metadata=metadata)
        assert payload(export, version=1)["metadata"] == metadata
        md = export.export_version(VIDEO, 1, "markdown")["content"]
        assert '"preserved_information"' in md
        txt = export.export_version(VIDEO, 1, "txt")["content"]
        assert '"count": 2' in txt

    def test_prompt_with_double_quotes_json_valid(self, history, export):
        prompt = 'He said "exact words" carefully.'
        save(history, prompt=prompt, negative='avoid "text" overlays')
        out = export.export_version(VIDEO, 1, "json")
        data = json.loads(out["content"])
        assert data["prompt"] == prompt
        assert data["negative_prompt"] == 'avoid "text" overlays'

    def test_operation_with_spaces_preserved(self, history, export):
        save(history, source="advanced_prompt", operation="cinematic style")
        data = payload(export, version=1)
        assert data["operation"] == "cinematic style"
        md = export.export_version(VIDEO, 1, "markdown")["content"]
        assert "## Operation\n\ncinematic style" in md

    def test_long_prompt_preserved_exactly(self, history, export):
        prompt = ("detailed shot description, " * 50).strip()
        save(history, prompt=prompt)
        assert payload(export, version=1)["prompt"] == prompt

    def test_txt_export_contains_no_markdown_bullets_for_tags(self, history, export):
        save(history)
        org = PromptOrganizationService(history)
        export2 = PromptExportService(history, org)
        org.add_tags(VIDEO, 1, ["ai"])
        content = export2.export_version(VIDEO, 1, "txt")["content"]
        assert "Tags: ai" in content
        assert "* ai" not in content
