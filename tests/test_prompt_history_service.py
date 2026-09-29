"""Tests for the prompt history service (Day 16)."""
import pytest
from app.services.prompt_history_service import (
    PromptHistoryService,
    VALID_SOURCES,
)

VIDEO = "abc123.mp4"
OTHER = "def456.mp4"

PROMPT_V1 = "Subject: a person; Action: walking; Scene progression across 3 scenes."
PROMPT_V2 = "Subject: a person; Action: running; Scene progression across 4 scenes."
PROMPT_V3 = "Subject: a person; Action: running fast; Scene progression across 4 scenes."
NEG_V1 = "blurry, low quality"
NEG_V2 = "blurry, low quality, distorted anatomy"


@pytest.fixture
def service():
    return PromptHistoryService()


def make(service, video=VIDEO, prompt=PROMPT_V1, negative="", source="custom",
         operation="", metadata=None):
    return service.create_version(
        video_filename=video,
        prompt=prompt,
        negative_prompt=negative,
        source=source,
        operation=operation,
        metadata=metadata,
    )


class TestVersionCreation:
    def test_first_version_is_one(self, service):
        assert make(service)["version"] == 1

    def test_second_version_is_two(self, service):
        make(service)
        assert make(service, prompt=PROMPT_V2)["version"] == 2

    def test_sequential_numbering(self, service):
        versions = [make(service)["version"] for _ in range(5)]
        assert versions == [1, 2, 3, 4, 5]

    def test_version_ids_unique(self, service):
        ids = [make(service)["version_id"] for _ in range(3)]
        assert len(set(ids)) == 3

    def test_version_id_no_absolute_path(self, service):
        vid = make(service)["version_id"]
        assert "C:/" not in vid
        assert "C:\\" not in vid
        assert vid.startswith(VIDEO)

    def test_exact_prompt_preserved(self, service):
        weird = '  Subject: "a person"  \nAction: walking... 42%  '
        assert make(service, prompt=weird)["prompt"] == weird

    def test_exact_negative_prompt_preserved(self, service):
        neg = "blurry, low quality, distorted anatomy, unwanted text, watermark"
        assert make(service, negative=neg)["negative_prompt"] == neg

    def test_negative_prompt_default_empty(self, service):
        assert make(service)["negative_prompt"] == ""

    def test_created_at_is_utc_iso(self, service):
        created = make(service)["created_at"]
        assert "T" in created
        assert "+00:00" in created

    def test_record_keys(self, service):
        assert set(make(service).keys()) == {
            "version_id",
            "video_filename",
            "version",
            "source",
            "operation",
            "prompt",
            "negative_prompt",
            "created_at",
            "metadata",
        }

    @pytest.mark.parametrize("source", sorted(VALID_SOURCES))
    def test_valid_sources_accepted(self, service, source):
        assert make(service, source=source)["source"] == source

    def test_invalid_source_rejected(self, service):
        with pytest.raises(ValueError, match="Invalid source"):
            make(service, source="database")

    def test_empty_prompt_rejected(self, service):
        with pytest.raises(ValueError):
            make(service, prompt="")

    def test_whitespace_prompt_rejected(self, service):
        with pytest.raises(ValueError):
            make(service, prompt="   ")

    def test_empty_video_filename_rejected(self, service):
        with pytest.raises(ValueError):
            make(service, video="")

    def test_invalid_version_in_create_metadata_default(self, service):
        assert make(service)["metadata"] == {}


class TestListVersions:
    def test_empty_returns_empty_list(self, service):
        assert service.list_versions(VIDEO) == []

    def test_unknown_video_returns_empty_list(self, service):
        assert service.list_versions("never.mp4") == []

    def test_list_ascending_order(self, service):
        make(service, prompt=PROMPT_V1)
        make(service, prompt=PROMPT_V2)
        make(service, prompt=PROMPT_V3)
        versions = [v["version"] for v in service.list_versions(VIDEO)]
        assert versions == [1, 2, 3]

    def test_list_does_not_expose_internal_storage(self, service):
        make(service)
        listed = service.list_versions(VIDEO)
        listed[0]["version"] = 999
        assert service.get_version(VIDEO, 1)["version"] == 1


class TestGetVersion:
    def test_get_existing(self, service):
        saved = make(service, prompt=PROMPT_V2, negative=NEG_V1)
        fetched = service.get_version(VIDEO, saved["version"])
        assert fetched == saved

    def test_get_missing_version_raises(self, service):
        with pytest.raises(ValueError):
            service.get_version(VIDEO, 1)

    def test_get_missing_video_raises(self, service):
        with pytest.raises(ValueError):
            service.get_version("never.mp4", 1)

    @pytest.mark.parametrize("bad_version", [0, -1])
    def test_invalid_version_rejected(self, service, bad_version):
        with pytest.raises(ValueError, match="positive integer"):
            service.get_version(VIDEO, bad_version)

    def test_non_int_version_rejected(self, service):
        with pytest.raises(ValueError, match="positive integer"):
            service.get_version(VIDEO, "1")

    def test_returned_record_is_a_copy(self, service):
        saved = make(service)
        fetched = service.get_version(VIDEO, saved["version"])
        fetched["prompt"] = "tampered"
        fetched["metadata"]["x"] = 1
        assert service.get_version(VIDEO, 1)["prompt"] == PROMPT_V1
        assert "x" not in service.get_version(VIDEO, 1)["metadata"]


class TestDeleteVersion:
    def test_delete_existing(self, service):
        make(service)
        deleted = service.delete_version(VIDEO, 1)
        assert deleted["version"] == 1
        assert service.list_versions(VIDEO) == []

    def test_delete_missing_raises(self, service):
        with pytest.raises(ValueError):
            service.delete_version(VIDEO, 1)

    def test_delete_invalid_version_rejected(self, service):
        with pytest.raises(ValueError, match="positive integer"):
            service.delete_version(VIDEO, 0)

    def test_deleted_versions_not_renumbered(self, service):
        make(service, prompt=PROMPT_V1)
        make(service, prompt=PROMPT_V2)
        make(service, prompt=PROMPT_V3)
        service.delete_version(VIDEO, 2)
        versions = [v["version"] for v in service.list_versions(VIDEO)]
        assert versions == [1, 3]

    def test_next_version_after_deletion(self, service):
        make(service, prompt=PROMPT_V1)
        make(service, prompt=PROMPT_V2)
        make(service, prompt=PROMPT_V3)
        service.delete_version(VIDEO, 2)
        assert make(service, prompt=PROMPT_V2)["version"] == 4

    def test_deleted_version_not_retrievable(self, service):
        make(service)
        service.delete_version(VIDEO, 1)
        with pytest.raises(ValueError):
            service.get_version(VIDEO, 1)


class TestCompareVersions:
    def test_compare_identical_prompts(self, service):
        make(service, prompt=PROMPT_V1, negative=NEG_V1)
        make(service, prompt=PROMPT_V1, negative=NEG_V1)
        result = service.compare_versions(VIDEO, 1, 2)
        assert result["changed"] is False
        assert result["added_tokens"] == []
        assert result["removed_tokens"] == []
        assert result["common_tokens"]

    def test_compare_different_prompts(self, service):
        make(service, prompt=PROMPT_V1)
        make(service, prompt=PROMPT_V2)
        result = service.compare_versions(VIDEO, 1, 2)
        assert result["changed"] is True

    def test_added_tokens(self, service):
        make(service, prompt="alpha beta")
        make(service, prompt="alpha beta gamma")
        result = service.compare_versions(VIDEO, 1, 2)
        assert result["added_tokens"] == ["gamma"]

    def test_removed_tokens(self, service):
        make(service, prompt="alpha beta gamma")
        make(service, prompt="alpha beta")
        result = service.compare_versions(VIDEO, 1, 2)
        assert result["removed_tokens"] == ["gamma"]

    def test_common_tokens(self, service):
        make(service, prompt="alpha beta gamma")
        make(service, prompt="alpha delta gamma")
        result = service.compare_versions(VIDEO, 1, 2)
        assert set(result["common_tokens"]) == {"alpha", "gamma"}

    def test_changed_flag_false_when_identical(self, service):
        make(service, prompt="same prompt here")
        make(service, prompt="same prompt here")
        assert service.compare_versions(VIDEO, 1, 2)["changed"] is False

    def test_compare_structure_keys(self, service):
        make(service, prompt=PROMPT_V1, negative=NEG_V1)
        make(service, prompt=PROMPT_V2, negative=NEG_V2)
        result = service.compare_versions(VIDEO, 1, 2)
        assert set(result.keys()) == {
            "video_filename",
            "version_a",
            "version_b",
            "prompt_a",
            "prompt_b",
            "negative_prompt_a",
            "negative_prompt_b",
            "added_tokens",
            "removed_tokens",
            "common_tokens",
            "changed",
        }
        assert result["video_filename"] == VIDEO
        assert result["version_a"] == 1
        assert result["version_b"] == 2
        assert result["prompt_a"] == PROMPT_V1
        assert result["prompt_b"] == PROMPT_V2
        assert result["negative_prompt_a"] == NEG_V1
        assert result["negative_prompt_b"] == NEG_V2

    def test_compare_deterministic(self, service):
        make(service, prompt=PROMPT_V1)
        make(service, prompt=PROMPT_V2)
        first = service.compare_versions(VIDEO, 1, 2)
        second = service.compare_versions(VIDEO, 1, 2)
        assert first == second

    def test_compare_missing_version_raises(self, service):
        make(service, prompt=PROMPT_V1)
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, 1, 2)

    @pytest.mark.parametrize("bad", [0, -2])
    def test_compare_invalid_version_rejected(self, service, bad):
        with pytest.raises(ValueError, match="positive integer"):
            service.compare_versions(VIDEO, bad, 1)

    def test_compare_same_version(self, service):
        make(service, prompt=PROMPT_V1)
        result = service.compare_versions(VIDEO, 1, 1)
        assert result["changed"] is False


class TestMetadata:
    def test_metadata_preserved_exactly(self, service):
        meta = {"operation_note": "user saved", "tags": ["draft"]}
        saved = make(service, metadata=meta)
        assert saved["metadata"] == meta

    def test_metadata_not_fabricated(self, service):
        saved = make(service, prompt="Scene progression across 1 scenes.")
        assert saved["metadata"] == {}
        text = saved["prompt"].lower()
        for word in ["person", "character", "dialogue", "park", "sunset"]:
            assert word not in text

    def test_metadata_is_copied_not_referenced(self, service):
        meta = {"a": 1}
        saved = make(service, metadata=meta)
        meta["a"] = 999
        assert saved["metadata"]["a"] == 1


class TestMultipleVideos:
    def test_videos_isolated(self, service):
        make(service, video=VIDEO, prompt=PROMPT_V1)
        make(service, video=VIDEO, prompt=PROMPT_V2)
        make(service, video=OTHER, prompt=PROMPT_V3)
        assert [v["version"] for v in service.list_versions(VIDEO)] == [1, 2]
        assert [v["version"] for v in service.list_versions(OTHER)] == [1]

    def test_numbering_independent_per_video(self, service):
        make(service, video=VIDEO)
        assert make(service, video=OTHER)["version"] == 1

    def test_delete_does_not_affect_other_video(self, service):
        make(service, video=VIDEO)
        make(service, video=OTHER)
        service.delete_version(VIDEO, 1)
        assert [v["version"] for v in service.list_versions(OTHER)] == [1]

    def test_version_ids_unique_across_videos(self, service):
        a = make(service, video=VIDEO)
        b = make(service, video=OTHER)
        assert a["version_id"] != b["version_id"]


class TestPipelineIntegrationHelpers:
    def test_save_advanced_prompt_output(self, service):
        advanced_result = {
            "video_filename": VIDEO,
            "style": "cinematic",
            "prompt": PROMPT_V1,
            "negative_prompt": NEG_V1,
            "sections": {"subject": ["a person"]},
        }
        saved = service.save_advanced_prompt(VIDEO, advanced_result)
        assert saved["version"] == 1
        assert saved["source"] == "advanced_prompt"
        assert saved["operation"] == "cinematic"
        assert saved["prompt"] == PROMPT_V1
        assert saved["negative_prompt"] == NEG_V1

    def test_save_refinement_output(self, service):
        refinement_result = {
            "source_prompt": PROMPT_V1,
            "refined_prompt": PROMPT_V2,
            "operation": "shorten",
            "negative_prompt": NEG_V2,
            "preserved_information": True,
        }
        saved = service.save_refinement(VIDEO, refinement_result)
        assert saved["source"] == "refinement"
        assert saved["operation"] == "shorten"
        assert saved["prompt"] == PROMPT_V2
        assert saved["negative_prompt"] == NEG_V2
        assert saved["metadata"]["preserved_information"] is True

    def test_save_template_output(self, service):
        template_result = {
            "template": "ai_video",
            "source_prompt": PROMPT_V1,
            "custom_instruction": "make it concise",
            "prompt": PROMPT_V3,
            "negative_prompt": NEG_V1,
            "preserved_information": True,
        }
        saved = service.save_template(VIDEO, template_result)
        assert saved["source"] == "template"
        assert saved["operation"] == "ai_video"
        assert saved["prompt"] == PROMPT_V3
        assert saved["metadata"]["custom_instruction"] == "make it concise"

    def test_pipeline_outputs_sequential_versions(self, service):
        service.save_advanced_prompt(VIDEO, {
            "prompt": PROMPT_V1, "negative_prompt": NEG_V1, "style": "cinematic",
        })
        service.save_refinement(VIDEO, {
            "refined_prompt": PROMPT_V2, "operation": "expand",
            "negative_prompt": NEG_V1, "preserved_information": True,
        })
        service.save_template(VIDEO, {
            "template": "documentary", "prompt": PROMPT_V3,
            "negative_prompt": NEG_V1, "custom_instruction": "",
        })
        assert [v["version"] for v in service.list_versions(VIDEO)] == [1, 2, 3]
