"""Tests for the prompt package service (Day 20)."""
import io
import json
import re
import zipfile

import pytest

from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService
from app.services.prompt_export_service import PromptExportService
from app.services.prompt_package_service import (
    PromptPackageService,
    PACKAGE_FILES,
    METADATA_KEYS,
)

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


@pytest.fixture
def package(history, org, export):
    return PromptPackageService(history, org, export)


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


def read_files(package, video=VIDEO, version=1):
    """Create a package and return {filename: decoded text}."""
    out = package.create_package(video, version)
    with zipfile.ZipFile(io.BytesIO(out["content"])) as zf:
        return {name: zf.read(name).decode("utf-8") for name in zf.namelist()}


class TestPackageStructure:
    def test_envelope_keys(self, history, package):
        save(history)
        out = package.create_package(VIDEO, 1)
        assert list(out.keys()) == [
            "content", "media_type", "filename", "files", "metadata",
        ]

    def test_content_is_zip_bytes(self, history, package):
        save(history)
        out = package.create_package(VIDEO, 1)
        assert isinstance(out["content"], bytes)
        assert out["content"][:2] == b"PK"

    def test_media_type(self, history, package):
        save(history)
        assert package.create_package(VIDEO, 1)["media_type"] == "application/zip"

    def test_filename_pattern(self, history, package):
        save(history)
        out = package.create_package(VIDEO, 1)
        assert out["filename"] == "visionprompt_video_v1.zip"
        assert re.fullmatch(r"visionprompt_video_v\d+\.zip", out["filename"])

    def test_filename_does_not_expose_storage_uuid(self, history, package):
        uuid_style = "a15cca2a-6b1e-4cf0-b989-30ba8be7cca8.mp4"
        save(history, video=uuid_style)
        out = package.create_package(uuid_style, 1)
        stem = uuid_style[:-4]
        assert stem not in out["filename"]
        assert "a15cca2a" not in out["filename"]
        assert out["filename"] == "visionprompt_video_v1.zip"

    def test_files_list_exact(self, history, package):
        save(history)
        out = package.create_package(VIDEO, 1)
        assert out["files"] == list(PACKAGE_FILES)

    def test_zip_names_exact_order(self, history, package):
        save(history)
        out = package.create_package(VIDEO, 1)
        with zipfile.ZipFile(io.BytesIO(out["content"])) as zf:
            assert zf.namelist() == [
                "prompt.json", "prompt.md", "prompt.txt",
                "package_metadata.json",
            ]

    def test_zip_no_extra_or_duplicate_files(self, history, package):
        save(history)
        out = package.create_package(VIDEO, 1)
        with zipfile.ZipFile(io.BytesIO(out["content"])) as zf:
            names = zf.namelist()
        assert len(names) == len(set(names)) == 4
        assert set(names) == set(PACKAGE_FILES)

    def test_zip_names_have_no_traversal_or_absolute_paths(self, history, package):
        save(history)
        out = package.create_package(VIDEO, 1)
        with zipfile.ZipFile(io.BytesIO(out["content"])) as zf:
            for name in zf.namelist():
                assert "/" not in name and "\\" not in name
                assert ".." not in name
                assert not name.startswith("/")

    def test_zip_readable_and_utf8(self, history, package):
        save(history, prompt="Café — 日本語 prompt", metadata={"k": "v"})
        out = package.create_package(VIDEO, 1)
        with zipfile.ZipFile(io.BytesIO(out["content"])) as zf:
            assert zf.testzip() is None
            for name in zf.namelist():
                zf.read(name).decode("utf-8")

    def test_zip_fixed_timestamp_deterministic_entries(self, history, package):
        save(history)
        out = package.create_package(VIDEO, 1)
        with zipfile.ZipFile(io.BytesIO(out["content"])) as zf:
            for info in zf.infolist():
                assert info.date_time == (1980, 1, 1, 0, 0, 0)


class TestFileContents:
    def test_prompt_json_parses_and_matches_export(self, history, org, export, package):
        save(history, source="refinement", operation="cinematic",
             metadata={"style": "film"})
        files = read_files(package)
        from_zip = json.loads(files["prompt.json"])
        from_export = json.loads(export.export_version(VIDEO, 1, "json")["content"])
        assert from_zip == from_export

    def test_prompt_md_matches_day19_export(self, history, export, package):
        save(history, metadata={"style": "film"})
        files = read_files(package)
        assert files["prompt.md"] == export.export_version(
            VIDEO, 1, "markdown"
        )["content"]

    def test_prompt_txt_matches_day19_export(self, history, export, package):
        save(history, metadata={"style": "film"})
        files = read_files(package)
        assert files["prompt.txt"] == export.export_version(
            VIDEO, 1, "txt"
        )["content"]

    def test_package_metadata_keys_exact(self, history, package):
        save(history, source="refinement", operation="cinematic")
        files = read_files(package)
        meta = json.loads(files["package_metadata.json"])
        assert list(meta.keys()) == list(METADATA_KEYS)
        assert set(meta.keys()) == {
            "video_filename", "version", "version_id", "source",
            "operation", "created_at", "favorite", "tags",
        }

    def test_package_metadata_no_prompt_text(self, history, package):
        save(history, prompt="secret prompt words")
        files = read_files(package)
        assert "secret prompt words" not in files["package_metadata.json"]


class TestExactPreservation:
    def test_prompt_preserved(self, history, package):
        prompt = 'Exact "quoted" prompt with 100% symbols.'
        save(history, prompt=prompt)
        files = read_files(package)
        assert json.loads(files["prompt.json"])["prompt"] == prompt
        assert f"## Prompt\n\n{prompt}" in files["prompt.md"]
        assert f"## PROMPT\n\n{prompt}" in files["prompt.txt"]

    def test_negative_prompt_preserved(self, history, package):
        save(history, negative=NEGATIVE)
        files = read_files(package)
        assert json.loads(files["prompt.json"])["negative_prompt"] == NEGATIVE
        assert NEGATIVE in files["prompt.md"]
        assert NEGATIVE in files["prompt.txt"]

    def test_empty_negative_rendered_cleanly(self, history, package):
        save(history, negative="")
        files = read_files(package)
        assert json.loads(files["prompt.json"])["negative_prompt"] == ""
        assert "## Negative Prompt\n\n(empty)" in files["prompt.md"]
        assert "## NEGATIVE PROMPT\n\n(empty)" in files["prompt.txt"]

    def test_source_preserved(self, history, package):
        save(history, source="template")
        assert json.loads(read_files(package)["prompt.json"])["source"] == "template"

    def test_operation_preserved(self, history, package):
        save(history, source="refinement", operation="shorten")
        data = json.loads(read_files(package)["prompt.json"])
        assert data["operation"] == "shorten"
        meta = json.loads(read_files(package)["package_metadata.json"])
        assert meta["operation"] == "shorten"

    def test_empty_operation_preserved(self, history, package):
        save(history, operation="")
        meta = json.loads(read_files(package)["package_metadata.json"])
        assert meta["operation"] == ""

    def test_version_preserved(self, history, package):
        save(history, prompt="one")
        save(history, prompt="two")
        meta = json.loads(read_files(package, version=2)["package_metadata.json"])
        assert meta["version"] == 2
        assert json.loads(
            read_files(package, version=2)["prompt.json"]
        )["prompt"] == "two"

    def test_version_id_preserved(self, history, package):
        save(history)
        meta = json.loads(read_files(package)["package_metadata.json"])
        assert meta["version_id"] == f"{VIDEO}:1"

    def test_created_at_preserved(self, history, package):
        record = save(history)
        meta = json.loads(read_files(package)["package_metadata.json"])
        assert meta["created_at"] == record["created_at"]

    def test_metadata_preserved_in_prompt_json(self, history, package):
        metadata = {"sections_keys": ["camera", "style"], "nested": {"a": 1}}
        save(history, metadata=metadata)
        files = read_files(package)
        assert json.loads(files["prompt.json"])["metadata"] == metadata

    def test_empty_metadata_preserved(self, history, package):
        save(history, metadata={})
        assert json.loads(read_files(package)["prompt.json"])["metadata"] == {}

    def test_video_filename_preserved(self, history, package):
        save(history)
        meta = json.loads(read_files(package)["package_metadata.json"])
        assert meta["video_filename"] == VIDEO


class TestOrganizationMetadata:
    def test_favorite_true(self, history, org, package):
        save(history)
        org.favorite_version(VIDEO, 1)
        meta = json.loads(read_files(package)["package_metadata.json"])
        assert meta["favorite"] is True

    def test_favorite_default_false(self, history, package):
        save(history)
        meta = json.loads(read_files(package)["package_metadata.json"])
        assert meta["favorite"] is False

    def test_tags_sorted(self, history, org, package):
        save(history)
        org.add_tags(VIDEO, 1, ["Cinematic", "ai", "zeta"])
        meta = json.loads(read_files(package)["package_metadata.json"])
        assert meta["tags"] == ["ai", "cinematic", "zeta"]

    def test_no_tags_default_empty(self, history, package):
        save(history)
        meta = json.loads(read_files(package)["package_metadata.json"])
        assert meta["tags"] == []

    def test_favorite_and_tags_change_reflected_on_regeneration(
        self, history, org, package
    ):
        save(history)
        meta_before = json.loads(read_files(package)["package_metadata.json"])
        assert meta_before["favorite"] is False
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["fresh"])
        meta_after = json.loads(read_files(package)["package_metadata.json"])
        assert meta_after["favorite"] is True
        assert meta_after["tags"] == ["fresh"]

    def test_favorite_tags_in_prompt_json_too(self, history, org, package):
        save(history)
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai"])
        data = json.loads(read_files(package)["prompt.json"])
        assert data["favorite"] is True
        assert data["tags"] == ["ai"]


class TestValidation:
    def test_valid_version_returns_package(self, history, package):
        save(history)
        out = package.create_package(VIDEO, 1)
        assert out["filename"] == "visionprompt_video_v1.zip"

    def test_nonexistent_video_raises(self, history, package):
        with pytest.raises(ValueError):
            package.create_package("missing.mp4", 1)

    def test_nonexistent_version_raises(self, history, package):
        save(history)
        with pytest.raises(ValueError):
            package.create_package(VIDEO, 99)

    def test_deleted_version_raises(self, history, package):
        save(history)
        history.delete_version(VIDEO, 1)
        with pytest.raises(ValueError):
            package.create_package(VIDEO, 1)

    def test_deleted_middle_version_raises(self, history, package):
        save(history, prompt="one")
        save(history, prompt="two")
        history.delete_version(VIDEO, 1)
        with pytest.raises(ValueError):
            package.create_package(VIDEO, 1)
        files = read_files(package, version=2)
        assert json.loads(files["prompt.json"])["prompt"] == "two"

    def test_version_zero_raises(self, history, package):
        save(history)
        with pytest.raises(ValueError):
            package.create_package(VIDEO, 0)

    def test_negative_version_raises(self, history, package):
        save(history)
        with pytest.raises(ValueError):
            package.create_package(VIDEO, -3)

    def test_version_created_after_deletion_packagable(self, history, package):
        save(history, prompt="one")
        save(history, prompt="two")
        save(history, prompt="three")
        history.delete_version(VIDEO, 2)
        four = save(history, prompt="four after delete")
        assert four["version"] == 4
        files = read_files(package, version=4)
        assert json.loads(files["prompt.json"])["prompt"] == "four after delete"
        with pytest.raises(ValueError):
            package.create_package(VIDEO, 2)


class TestMultipleVersions:
    def test_each_version_packages_its_own_prompt(self, history, package):
        save(history, prompt="version one prompt")
        save(history, prompt="version two prompt")
        save(history, prompt="version three prompt")
        for version, prompt in [(1, "version one prompt"),
                                (2, "version two prompt"),
                                (3, "version three prompt")]:
            files = read_files(package, version=version)
            assert json.loads(files["prompt.json"])["prompt"] == prompt
            meta = json.loads(files["package_metadata.json"])
            assert meta["version"] == version
            assert meta["version_id"] == f"{VIDEO}:{version}"

    def test_packages_of_different_versions_differ(self, history, package):
        save(history, prompt="alpha")
        save(history, prompt="beta")
        out1 = package.create_package(VIDEO, 1)
        out2 = package.create_package(VIDEO, 2)
        assert out1["content"] != out2["content"]
        assert out1["filename"] == "visionprompt_video_v1.zip"
        assert out2["filename"] == "visionprompt_video_v2.zip"


class TestMultipleVideos:
    def test_metadata_video_filename_per_video(self, history, package):
        save(history, video=VIDEO, prompt="video A prompt")
        save(history, video=OTHER, prompt="video B prompt")
        meta_a = json.loads(read_files(package, video=VIDEO)["package_metadata.json"])
        meta_b = json.loads(read_files(package, video=OTHER)["package_metadata.json"])
        assert meta_a["video_filename"] == VIDEO
        assert meta_b["video_filename"] == OTHER

    def test_prompts_never_cross_videos(self, history, package):
        save(history, video=VIDEO, prompt="video A prompt")
        save(history, video=OTHER, prompt="video B prompt")
        files_a = read_files(package, video=VIDEO)
        files_b = read_files(package, video=OTHER)
        assert json.loads(files_a["prompt.json"])["prompt"] == "video A prompt"
        assert json.loads(files_b["prompt.json"])["prompt"] == "video B prompt"
        assert "video B prompt" not in files_a["prompt.json"]
        assert "video A prompt" not in files_b["prompt.json"]

    def test_org_metadata_isolated_per_video(self, history, org, package):
        save(history, video=VIDEO, prompt="video A prompt")
        save(history, video=OTHER, prompt="video B prompt")
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["a-tag"])
        meta_a = json.loads(read_files(package, video=VIDEO)["package_metadata.json"])
        meta_b = json.loads(read_files(package, video=OTHER)["package_metadata.json"])
        assert meta_a["favorite"] is True
        assert meta_a["tags"] == ["a-tag"]
        assert meta_b["favorite"] is False
        assert meta_b["tags"] == []

    def test_version_ids_distinct(self, history, package):
        save(history, video=VIDEO)
        save(history, video=OTHER)
        meta_a = json.loads(read_files(package, video=VIDEO)["package_metadata.json"])
        meta_b = json.loads(read_files(package, video=OTHER)["package_metadata.json"])
        assert meta_a["version_id"] != meta_b["version_id"]


class TestDeterminism:
    def test_repeated_generation_identical_bytes(self, history, package):
        save(history, metadata={"k": "v"})
        first = package.create_package(VIDEO, 1)
        second = package.create_package(VIDEO, 1)
        assert first["content"] == second["content"]
        assert first["filename"] == second["filename"]

    def test_repeated_generation_equivalent_contents(self, history, package):
        save(history, metadata={"k": "v"})
        assert read_files(package) == read_files(package)

    def test_identical_across_fresh_service_instances(self, history, org, export):
        save(history, metadata={"k": "v"})
        p1 = PromptPackageService(history, org, export)
        p2 = PromptPackageService(history, org, export)
        assert p1.create_package(VIDEO, 1)["content"] == \
            p2.create_package(VIDEO, 1)["content"]

    def test_metadata_stable_across_repeats(self, history, org, package):
        save(history, source="refinement", operation="cinematic")
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai"])
        meta1 = package.create_package(VIDEO, 1)["metadata"]
        meta2 = package.create_package(VIDEO, 1)["metadata"]
        assert meta1 == meta2
        assert list(meta1.keys()) == list(METADATA_KEYS)


class TestReadOnly:
    def test_history_unchanged(self, history, package):
        save(history, prompt="original prompt", metadata={"k": "v"})
        before = json.dumps(history.list_versions(VIDEO), sort_keys=True)
        package.create_package(VIDEO, 1)
        package.create_package(VIDEO, 1)
        after = json.dumps(history.list_versions(VIDEO), sort_keys=True)
        assert before == after

    def test_history_record_identical(self, history, package):
        save(history, prompt="keep me")
        before = json.dumps(history.get_version(VIDEO, 1), sort_keys=True)
        package.create_package(VIDEO, 1)
        after = json.dumps(history.get_version(VIDEO, 1), sort_keys=True)
        assert before == after

    def test_org_unchanged(self, history, org, package):
        save(history)
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai"])
        before = json.dumps(org.get_organization(VIDEO, 1), sort_keys=True)
        package.create_package(VIDEO, 1)
        after = json.dumps(org.get_organization(VIDEO, 1), sort_keys=True)
        assert before == after

    def test_does_not_create_versions(self, history, package):
        save(history)
        package.create_package(VIDEO, 1)
        assert len(history.list_versions(VIDEO)) == 1

    def test_does_not_favorite_or_tag(self, history, org, package):
        save(history)
        package.create_package(VIDEO, 1)
        state = org.get_organization(VIDEO, 1)
        assert state["favorite"] is False
        assert state["tags"] == []


class TestSecurityAndNoFabrication:
    def test_no_absolute_paths_in_any_file(self, history, package):
        save(history, metadata={"path": "relative/entry"})
        files = read_files(package)
        for content in files.values():
            for bad in ["C:/", "C:\\", "/home", "/Users", "/var/", "/etc/"]:
                assert bad not in content, f"absolute path {bad}"

    def test_no_fabricated_information(self, history, package):
        save(history, prompt="alpha beta gamma", negative="noise watermark")
        combined = " ".join(read_files(package).values()).lower()
        for word in ["person", "character", "dialogue", "walking", "running",
                     "park", "city", "sunset", "brand", "product", "voiceover"]:
            assert word not in combined, f"fabricated: {word}"

    def test_no_internal_service_information(self, history, package):
        save(history, metadata={"k": "v"})
        combined = " ".join(read_files(package).values())
        for internal in ["_storage", "_org", "_history", "_organization",
                         "_export", "PromptHistoryService", "PromptExportService",
                         "PromptPackageService", "storage/uploads", "BytesIO",
                         "zipfile", "self."]:
            assert internal not in combined, f"internal leak: {internal}"

    def test_package_metadata_only_safe_fields(self, history, package):
        save(history, prompt="the prompt itself", metadata={"k": "v"})
        files = read_files(package)
        meta = json.loads(files["package_metadata.json"])
        assert list(meta.keys()) == list(METADATA_KEYS)
        serialized = files["package_metadata.json"]
        assert "the prompt itself" not in serialized
        assert '"k"' not in serialized

    def test_no_secrets_or_environment(self, history, package):
        save(history)
        combined = " ".join(read_files(package).values()).lower()
        for token in ["secret", "api_key", "password", "environ",
                      "traceback", "stack trace"]:
            assert token not in combined, f"leaked: {token}"


class TestEdgeCases:
    def test_unicode_prompt_survives_zip(self, history, package):
        prompt = "Café über naïve — 日本語テキスト"
        save(history, prompt=prompt)
        files = read_files(package)
        assert json.loads(files["prompt.json"])["prompt"] == prompt
        assert prompt in files["prompt.md"]
        assert prompt in files["prompt.txt"]

    def test_multiline_prompt_survives_zip(self, history, package):
        prompt = "first line\nsecond line\n\tindented line"
        save(history, prompt=prompt)
        assert json.loads(read_files(package)["prompt.json"])["prompt"] == prompt

    def test_long_prompt_survives_zip(self, history, package):
        prompt = ("detailed shot description, " * 100).strip()
        save(history, prompt=prompt)
        assert json.loads(read_files(package)["prompt.json"])["prompt"] == prompt

    def test_all_four_files_nonempty(self, history, package):
        save(history, metadata={"style": "film"})
        files = read_files(package)
        for name in PACKAGE_FILES:
            assert name in files
            assert len(files[name]) > 0

    def test_metadata_file_is_valid_json(self, history, package):
        save(history, metadata={"k": "v"})
        meta = json.loads(read_files(package)["package_metadata.json"])
        assert isinstance(meta, dict)

    def test_prompt_json_is_valid_json(self, history, package):
        save(history)
        data = json.loads(read_files(package)["prompt.json"])
        assert data["prompt"] == PROMPT
