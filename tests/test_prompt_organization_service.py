"""Tests for the prompt organization service (Day 17)."""
import json
import pytest
from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import (
    PromptOrganizationService,
    MAX_TAG_LENGTH,
)

VIDEO = "abc123.mp4"
OTHER = "def456.mp4"

PROMPT = "Scene progression across 3 scenes, cinematic composition."
NEGATIVE = "blurry, low quality, distorted anatomy, unwanted text, watermark"


@pytest.fixture
def history():
    return PromptHistoryService()


@pytest.fixture
def org(history):
    return PromptOrganizationService(history)


def create(history, video=VIDEO, prompt=PROMPT):
    return history.create_version(
        video_filename=video, prompt=prompt, negative_prompt=NEGATIVE
    )


class TestFavorites:
    def test_favorite_existing_version(self, org, history):
        create(history)
        result = org.favorite_version(VIDEO, 1)
        assert result == {
            "video_filename": VIDEO,
            "version": 1,
            "favorite": True,
        }

    def test_favorite_missing_version_raises(self, org, history):
        with pytest.raises(ValueError):
            org.favorite_version(VIDEO, 1)

    def test_favorite_twice_idempotent(self, org, history):
        create(history)
        org.favorite_version(VIDEO, 1)
        second = org.favorite_version(VIDEO, 1)
        assert second["favorite"] is True
        assert len(org.list_favorites(VIDEO)) == 1

    def test_unfavorite_existing_version(self, org, history):
        create(history)
        org.favorite_version(VIDEO, 1)
        result = org.unfavorite_version(VIDEO, 1)
        assert result == {
            "video_filename": VIDEO,
            "version": 1,
            "favorite": False,
        }

    def test_unfavorite_twice_idempotent(self, org, history):
        create(history)
        org.unfavorite_version(VIDEO, 1)
        second = org.unfavorite_version(VIDEO, 1)
        assert second["favorite"] is False
        assert org.list_favorites(VIDEO) == []

    def test_unfavorite_without_prior_favorite(self, org, history):
        create(history)
        result = org.unfavorite_version(VIDEO, 1)
        assert result["favorite"] is False

    @pytest.mark.parametrize("bad_version", [0, -1])
    def test_invalid_version_rejected(self, org, history, bad_version):
        with pytest.raises(ValueError, match="positive integer"):
            org.favorite_version(VIDEO, bad_version)


class TestAddTags:
    def test_add_tags(self, org, history):
        create(history)
        result = org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        assert result == {
            "video_filename": VIDEO,
            "version": 1,
            "tags": ["ai", "cinematic"],
        }

    def test_normalize_whitespace(self, org, history):
        create(history)
        result = org.add_tags(VIDEO, 1, ["  ai  ", " cinematic "])
        assert result["tags"] == ["ai", "cinematic"]

    def test_lowercase_normalization(self, org, history):
        create(history)
        result = org.add_tags(VIDEO, 1, ["AI", "Cinematic"])
        assert result["tags"] == ["ai", "cinematic"]

    def test_duplicate_removal(self, org, history):
        create(history)
        result = org.add_tags(VIDEO, 1, ["AI", "ai", "Ai"])
        assert result["tags"] == ["ai"]

    def test_alphabetical_ordering(self, org, history):
        create(history)
        result = org.add_tags(VIDEO, 1, ["zebra", "ai", "meta"])
        assert result["tags"] == ["ai", "meta", "zebra"]

    def test_empty_tags_ignored(self, org, history):
        create(history)
        result = org.add_tags(VIDEO, 1, ["", "   ", "ai"])
        assert result["tags"] == ["ai"]

    def test_all_empty_tags_result_empty(self, org, history):
        create(history)
        result = org.add_tags(VIDEO, 1, ["", "  "])
        assert result["tags"] == []

    def test_spec_example_normalization(self, org, history):
        create(history)
        result = org.add_tags(VIDEO, 1, [" Cinematic ", "AI", "cinematic", ""])
        assert result["tags"] == ["ai", "cinematic"]

    def test_add_tags_accumulates(self, org, history):
        create(history)
        org.add_tags(VIDEO, 1, ["ai"])
        result = org.add_tags(VIDEO, 1, ["commercial"])
        assert result["tags"] == ["ai", "commercial"]

    def test_add_tags_missing_version_raises(self, org, history):
        with pytest.raises(ValueError):
            org.add_tags(VIDEO, 1, ["ai"])

    def test_non_string_tag_rejected(self, org, history):
        create(history)
        with pytest.raises(ValueError, match="strings"):
            org.add_tags(VIDEO, 1, ["ai", 42])

    def test_non_list_tags_rejected(self, org, history):
        create(history)
        with pytest.raises(ValueError, match="list"):
            org.add_tags(VIDEO, 1, "ai")

    def test_tag_max_length_enforced(self, org, history):
        create(history)
        with pytest.raises(ValueError, match="50"):
            org.add_tags(VIDEO, 1, ["x" * (MAX_TAG_LENGTH + 1)])

    def test_tag_at_max_length_allowed(self, org, history):
        create(history)
        result = org.add_tags(VIDEO, 1, ["x" * MAX_TAG_LENGTH])
        assert result["tags"] == ["x" * MAX_TAG_LENGTH]


class TestRemoveTags:
    def test_remove_tags(self, org, history):
        create(history)
        org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        result = org.remove_tags(VIDEO, 1, ["ai"])
        assert result == {
            "video_filename": VIDEO,
            "version": 1,
            "tags": ["cinematic"],
        }

    def test_remove_missing_tag_harmless(self, org, history):
        create(history)
        org.add_tags(VIDEO, 1, ["ai"])
        result = org.remove_tags(VIDEO, 1, ["nonexistent"])
        assert result["tags"] == ["ai"]

    def test_remove_normalizes_input(self, org, history):
        create(history)
        org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        result = org.remove_tags(VIDEO, 1, ["  AI "])
        assert result["tags"] == ["cinematic"]

    def test_remove_from_empty_tags(self, org, history):
        create(history)
        result = org.remove_tags(VIDEO, 1, ["ai"])
        assert result["tags"] == []

    def test_remove_missing_version_raises(self, org, history):
        with pytest.raises(ValueError):
            org.remove_tags(VIDEO, 1, ["ai"])


class TestGetOrganization:
    def test_get_organization_defaults(self, org, history):
        create(history)
        assert org.get_organization(VIDEO, 1) == {
            "video_filename": VIDEO,
            "version": 1,
            "favorite": False,
            "tags": [],
        }

    def test_get_organization_after_changes(self, org, history):
        create(history)
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai"])
        assert org.get_organization(VIDEO, 1) == {
            "video_filename": VIDEO,
            "version": 1,
            "favorite": True,
            "tags": ["ai"],
        }

    def test_get_organization_missing_version_raises(self, org, history):
        with pytest.raises(ValueError):
            org.get_organization(VIDEO, 1)

    def test_no_absolute_paths(self, org, history):
        create(history)
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai"])
        serialized = json.dumps(org.get_organization(VIDEO, 1))
        assert "C:/" not in serialized
        assert "C:\\" not in serialized
        assert "/home" not in serialized
        assert "/Users" not in serialized
        assert "/var" not in serialized


class TestListFavorites:
    def test_empty_favorites(self, org, history):
        assert org.list_favorites(VIDEO) == []

    def test_favorites_only_including_versions(self, org, history):
        create(history, prompt="one")
        create(history, prompt="two")
        create(history, prompt="three")
        org.favorite_version(VIDEO, 2)
        result = org.list_favorites(VIDEO)
        assert result == [{"version": 2, "favorite": True, "tags": []}]

    def test_favorites_sorted_ascending(self, org, history):
        for i in range(4):
            create(history, prompt=f"prompt {i}")
        for v in [3, 1, 4]:
            org.favorite_version(VIDEO, v)
        result = org.list_favorites(VIDEO)
        assert [r["version"] for r in result] == [1, 3, 4]
        assert all(r["favorite"] is True for r in result)

    def test_favorites_include_tags(self, org, history):
        create(history)
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai", "meta"])
        result = org.list_favorites(VIDEO)
        assert result[0]["tags"] == ["ai", "meta"]

    def test_list_favorites_unknown_video(self, org, history):
        assert org.list_favorites("never.mp4") == []


class TestListByTag:
    def test_list_by_exact_tag(self, org, history):
        create(history, prompt="one")
        create(history, prompt="two")
        org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        org.add_tags(VIDEO, 2, ["commercial"])
        result = org.list_by_tag(VIDEO, "ai")
        assert len(result) == 1
        assert result[0]["version"] == 1
        assert result[0]["favorite"] is False
        assert result[0]["tags"] == ["ai", "cinematic"]

    def test_missing_tag_returns_empty(self, org, history):
        create(history)
        assert org.list_by_tag(VIDEO, "missing") == []

    def test_no_substring_matching(self, org, history):
        create(history)
        org.add_tags(VIDEO, 1, ["cinematic"])
        assert org.list_by_tag(VIDEO, "cine") == []
        assert org.list_by_tag(VIDEO, "cinematicx") == []

    def test_requested_tag_normalized(self, org, history):
        create(history)
        org.add_tags(VIDEO, 1, ["cinematic"])
        result = org.list_by_tag(VIDEO, "  Cinematic ")
        assert len(result) == 1
        assert result[0]["version"] == 1

    def test_empty_tag_returns_empty(self, org, history):
        create(history)
        org.add_tags(VIDEO, 1, ["ai"])
        assert org.list_by_tag(VIDEO, "  ") == []

    def test_sorted_ascending(self, org, history):
        for i in range(3):
            create(history, prompt=f"prompt {i}")
        org.add_tags(VIDEO, 3, ["ai"])
        org.add_tags(VIDEO, 1, ["ai"])
        result = org.list_by_tag(VIDEO, "ai")
        assert [r["version"] for r in result] == [1, 3]

    def test_favorites_flag_reflected(self, org, history):
        create(history)
        org.add_tags(VIDEO, 1, ["ai"])
        org.favorite_version(VIDEO, 1)
        assert org.list_by_tag(VIDEO, "ai")[0]["favorite"] is True


class TestDeletionIntegration:
    def test_deleted_version_disappears_from_favorites(self, org, history):
        for i in range(3):
            create(history, prompt=f"prompt {i}")
        org.favorite_version(VIDEO, 1)
        org.favorite_version(VIDEO, 2)
        org.favorite_version(VIDEO, 3)
        history.delete_version(VIDEO, 2)
        assert [r["version"] for r in org.list_favorites(VIDEO)] == [1, 3]

    def test_deleted_version_disappears_from_tag_list(self, org, history):
        for i in range(3):
            create(history, prompt=f"prompt {i}")
        for v in (1, 2, 3):
            org.add_tags(VIDEO, v, ["ai"])
        history.delete_version(VIDEO, 2)
        assert [r["version"] for r in org.list_by_tag(VIDEO, "ai")] == [1, 3]

    def test_deleted_version_organization_not_retrievable(self, org, history):
        create(history)
        org.favorite_version(VIDEO, 1)
        history.delete_version(VIDEO, 1)
        with pytest.raises(ValueError):
            org.get_organization(VIDEO, 1)
        with pytest.raises(ValueError):
            org.favorite_version(VIDEO, 1)

    def test_remaining_versions_preserve_metadata(self, org, history):
        for i in range(3):
            create(history, prompt=f"prompt {i}")
        org.favorite_version(VIDEO, 1)
        org.favorite_version(VIDEO, 3)
        org.add_tags(VIDEO, 1, ["ai"])
        org.add_tags(VIDEO, 3, ["commercial"])
        history.delete_version(VIDEO, 2)
        assert org.get_organization(VIDEO, 1) == {
            "video_filename": VIDEO,
            "version": 1,
            "favorite": True,
            "tags": ["ai"],
        }
        assert org.get_organization(VIDEO, 3) == {
            "video_filename": VIDEO,
            "version": 3,
            "favorite": True,
            "tags": ["commercial"],
        }

    def test_recreated_version_has_fresh_metadata(self, org, history):
        create(history, prompt="one")
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai"])
        history.delete_version(VIDEO, 1)
        assert create(history, prompt="again")["version"] == 1
        assert org.get_organization(VIDEO, 1) == {
            "video_filename": VIDEO,
            "version": 1,
            "favorite": False,
            "tags": [],
        }


class TestMultiVideoIsolation:
    def test_metadata_isolated_per_video(self, org, history):
        create(history, video=VIDEO)
        create(history, video=OTHER)
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai"])
        org.add_tags(OTHER, 1, ["commercial"])
        assert org.get_organization(VIDEO, 1) == {
            "video_filename": VIDEO,
            "version": 1,
            "favorite": True,
            "tags": ["ai"],
        }
        assert org.get_organization(OTHER, 1) == {
            "video_filename": OTHER,
            "version": 1,
            "favorite": False,
            "tags": ["commercial"],
        }

    def test_delete_on_one_video_does_not_affect_other(self, org, history):
        create(history, video=VIDEO)
        create(history, video=OTHER)
        org.favorite_version(VIDEO, 1)
        org.favorite_version(OTHER, 1)
        history.delete_version(VIDEO, 1)
        assert org.list_favorites(VIDEO) == []
        assert [r["version"] for r in org.list_favorites(OTHER)] == [1]


class TestNoSideEffectsOnPrompt:
    def test_add_tags_does_not_modify_prompt(self, org, history):
        saved = create(history)
        org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        org.favorite_version(VIDEO, 1)
        fetched = history.get_version(VIDEO, 1)
        assert fetched["prompt"] == PROMPT
        assert fetched["negative_prompt"] == NEGATIVE

    def test_remove_tags_does_not_modify_prompt(self, org, history):
        create(history)
        org.add_tags(VIDEO, 1, ["ai"])
        org.remove_tags(VIDEO, 1, ["ai"])
        fetched = history.get_version(VIDEO, 1)
        assert fetched["prompt"] == PROMPT

    def test_no_tags_invented_from_video_content(self, org, history):
        create(history)
        org.favorite_version(VIDEO, 1)
        org.get_organization(VIDEO, 1)
        org.list_favorites(VIDEO)
        org.list_by_tag(VIDEO, "scene")
        assert org.get_organization(VIDEO, 1)["tags"] == []
        forbidden = ["person", "character", "dialogue", "park", "sunset",
                     "brand", "cinematic", "ai", "scene"]
        stored_tags = org.get_organization(VIDEO, 1)["tags"]
        for word in forbidden:
            assert word not in stored_tags

    def test_organization_does_not_expose_internal_storage(self, org, history):
        create(history)
        org.add_tags(VIDEO, 1, ["ai"])
        result = org.get_organization(VIDEO, 1)
        assert set(result.keys()) == {
            "video_filename", "version", "favorite", "tags",
        }
        assert result["video_filename"] == VIDEO
