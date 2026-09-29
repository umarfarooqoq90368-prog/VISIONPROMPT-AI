"""Tests for the prompt search service (Day 18)."""
import pytest
from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService
from app.services.prompt_search_service import PromptSearchService, VALID_SORTS

VIDEO = "abc123.mp4"
OTHER = "def456.mp4"

NEGATIVE = "blurry, low quality, distorted anatomy, unwanted text, watermark"


@pytest.fixture
def history():
    return PromptHistoryService()


@pytest.fixture
def org(history):
    return PromptOrganizationService(history)


@pytest.fixture
def search(history, org):
    return PromptSearchService(history, org)


def save(history, video=VIDEO, prompt="alpha beta gamma", source="custom",
         operation="", metadata=None):
    return history.create_version(
        video_filename=video,
        prompt=prompt,
        negative_prompt=NEGATIVE,
        source=source,
        operation=operation,
        metadata=metadata,
    )


class TestEmptyAndNoFilters:
    def test_empty_history_returns_empty(self, search):
        assert search.search_versions(VIDEO) == []

    def test_no_filters_returns_all_live_versions(self, history, search):
        save(history, prompt="one")
        save(history, prompt="two")
        save(history, prompt="three")
        results = search.search_versions(VIDEO)
        assert [r["version"] for r in results] == [1, 2, 3]

    def test_empty_query_behaves_as_no_text_filter(self, history, search):
        save(history, prompt="alpha beta")
        assert len(search.search_versions(VIDEO, query="")) == 1
        assert len(search.search_versions(VIDEO, query="   ")) == 1

    def test_none_filters_all_defaults(self, history, search):
        save(history, prompt="alpha")
        results = search.search_versions(
            VIDEO, query=None, source=None, operation=None,
            favorite=None, tag=None, min_version=None, max_version=None,
        )
        assert len(results) == 1


class TestTextQuery:
    def test_case_insensitive_search(self, history, search):
        save(history, prompt="Cinematic Composition Shot")
        save(history, prompt="documentary style")
        results = search.search_versions(VIDEO, query="CINEMATIC")
        assert len(results) == 1
        assert results[0]["prompt"] == "Cinematic Composition Shot"

    def test_partial_substring_search(self, history, search):
        save(history, prompt="alpha beta gamma")
        save(history, prompt="delta epsilon")
        results = search.search_versions(VIDEO, query="pha be")
        assert len(results) == 1
        assert results[0]["version"] == 1

    def test_search_is_case_insensitive_both_ways(self, history, search):
        save(history, prompt="SCENE progression")
        assert len(search.search_versions(VIDEO, query="scene")) == 1
        assert len(search.search_versions(VIDEO, query="SCENE")) == 1

    def test_no_match_query_returns_empty(self, history, search):
        save(history, prompt="alpha beta")
        assert search.search_versions(VIDEO, query="nonexistent") == []

    def test_query_searches_prompt_not_metadata(self, history, search):
        save(history, prompt="alpha beta", metadata={"note": "gamma delta"})
        assert search.search_versions(VIDEO, query="gamma") == []


class TestSourceFilter:
    @pytest.mark.parametrize("source", ["advanced_prompt", "refinement", "template"])
    def test_source_filter(self, history, search, source):
        save(history, prompt="alpha", source="custom")
        save(history, prompt="beta", source=source)
        results = search.search_versions(VIDEO, source=source)
        assert [r["source"] for r in results] == [source]

    def test_source_filter_custom(self, history, search):
        save(history, prompt="alpha", source="refinement")
        save(history, prompt="beta", source="custom")
        results = search.search_versions(VIDEO, source="custom")
        assert [r["source"] for r in results] == ["custom"]

    def test_source_exact_match(self, history, search):
        save(history, prompt="alpha", source="refinement")
        assert search.search_versions(VIDEO, source="template") == []

    def test_source_case_sensitive_exact(self, history, search):
        save(history, prompt="alpha", source="custom")
        with pytest.raises(ValueError, match="Invalid source"):
            search.search_versions(VIDEO, source="Custom")

    def test_invalid_source_raises(self, search):
        with pytest.raises(ValueError, match="Invalid source"):
            search.search_versions(VIDEO, source="database")


class TestOperationFilter:
    def test_operation_filter(self, history, search):
        save(history, prompt="alpha", operation="shorten")
        save(history, prompt="beta", operation="expand")
        results = search.search_versions(VIDEO, operation="shorten")
        assert [r["operation"] for r in results] == ["shorten"]

    def test_operation_exact_match(self, history, search):
        save(history, prompt="alpha", operation="shorten")
        assert search.search_versions(VIDEO, operation="shor") == []
        assert search.search_versions(VIDEO, operation="Shorten") == []


class TestFavoriteFilter:
    def test_favorite_true(self, history, org, search):
        save(history, prompt="one")
        save(history, prompt="two")
        org.favorite_version(VIDEO, 2)
        results = search.search_versions(VIDEO, favorite=True)
        assert [r["version"] for r in results] == [2]
        assert results[0]["favorite"] is True

    def test_favorite_false(self, history, org, search):
        save(history, prompt="one")
        save(history, prompt="two")
        org.favorite_version(VIDEO, 2)
        results = search.search_versions(VIDEO, favorite=False)
        assert [r["version"] for r in results] == [1]
        assert results[0]["favorite"] is False

    def test_favorite_none_includes_both(self, history, org, search):
        save(history, prompt="one")
        save(history, prompt="two")
        org.favorite_version(VIDEO, 1)
        assert len(search.search_versions(VIDEO, favorite=None)) == 2

    def test_favorite_true_no_favorites_empty(self, history, search):
        save(history, prompt="one")
        assert search.search_versions(VIDEO, favorite=True) == []


class TestTagFilter:
    def test_tag_filter(self, history, org, search):
        save(history, prompt="one")
        save(history, prompt="two")
        org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        org.add_tags(VIDEO, 2, ["commercial"])
        results = search.search_versions(VIDEO, tag="ai")
        assert [r["version"] for r in results] == [1]
        assert results[0]["tags"] == ["ai", "cinematic"]

    def test_tag_normalization(self, history, org, search):
        save(history, prompt="one")
        org.add_tags(VIDEO, 1, ["cinematic"])
        assert len(search.search_versions(VIDEO, tag="  Cinematic ")) == 1

    def test_exact_tag_no_substring(self, history, org, search):
        save(history, prompt="one")
        org.add_tags(VIDEO, 1, ["cinematic"])
        assert search.search_versions(VIDEO, tag="cine") == []
        assert search.search_versions(VIDEO, tag="cinematicx") == []

    def test_whitespace_only_tag_behaves_as_no_tag_filter(self, history, search):
        save(history, prompt="one")
        assert len(search.search_versions(VIDEO, tag="   ")) == 1

    def test_missing_tag_returns_empty(self, history, org, search):
        save(history, prompt="one")
        org.add_tags(VIDEO, 1, ["ai"])
        assert search.search_versions(VIDEO, tag="missing") == []

    def test_tag_too_long_raises(self, search):
        with pytest.raises(ValueError, match="50"):
            search.search_versions(VIDEO, tag="x" * 51)


class TestVersionRange:
    def test_min_version(self, history, search):
        for i in range(4):
            save(history, prompt=f"prompt {i}")
        results = search.search_versions(VIDEO, min_version=3)
        assert [r["version"] for r in results] == [3, 4]

    def test_max_version(self, history, search):
        for i in range(4):
            save(history, prompt=f"prompt {i}")
        results = search.search_versions(VIDEO, max_version=2)
        assert [r["version"] for r in results] == [1, 2]

    def test_inclusive_range(self, history, search):
        for i in range(5):
            save(history, prompt=f"prompt {i}")
        results = search.search_versions(VIDEO, min_version=2, max_version=4)
        assert [r["version"] for r in results] == [2, 3, 4]

    @pytest.mark.parametrize("bad_min", [0, -1])
    def test_invalid_min_version_raises(self, search, bad_min):
        with pytest.raises(ValueError, match="positive integer"):
            search.search_versions(VIDEO, min_version=bad_min)

    @pytest.mark.parametrize("bad_max", [0, -3])
    def test_invalid_max_version_raises(self, search, bad_max):
        with pytest.raises(ValueError, match="positive integer"):
            search.search_versions(VIDEO, max_version=bad_max)

    def test_min_greater_than_max_raises(self, history, search):
        save(history, prompt="alpha")
        with pytest.raises(ValueError, match="greater"):
            search.search_versions(VIDEO, min_version=3, max_version=2)

    def test_min_equals_max_allowed(self, history, search):
        save(history, prompt="alpha")
        save(history, prompt="beta")
        results = search.search_versions(VIDEO, min_version=2, max_version=2)
        assert [r["version"] for r in results] == [2]


class TestCombinedFilters:
    def test_all_filters_and_combined(self, history, org, search):
        # v1: refinement/shorten, favorite, tagged ai, contains "cinematic"
        save(history, prompt="cinematic composition", source="refinement",
             operation="shorten")
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        # v2: refinement but not favorite, tagged ai, contains "cinematic"
        save(history, prompt="cinematic lighting", source="refinement",
             operation="expand")
        org.add_tags(VIDEO, 2, ["ai"])
        # v3: favorite + tag but wrong source
        save(history, prompt="cinematic sound", source="custom")
        org.favorite_version(VIDEO, 3)
        org.add_tags(VIDEO, 3, ["ai"])
        # v4: right source + favorite but no "cinematic" text and no tag
        save(history, prompt="documentary style", source="refinement",
             operation="shorten")
        org.favorite_version(VIDEO, 4)

        results = search.search_versions(
            VIDEO,
            query="cinematic",
            source="refinement",
            favorite=True,
            tag="ai",
        )
        assert [r["version"] for r in results] == [1]
        assert results[0]["operation"] == "shorten"

    def test_pairwise_filters(self, history, org, search):
        save(history, prompt="alpha", source="template")
        save(history, prompt="beta", source="custom")
        org.favorite_version(VIDEO, 2)
        assert [r["version"] for r in
                search.search_versions(VIDEO, source="template")] == [1]
        assert [r["version"] for r in
                search.search_versions(VIDEO, favorite=True)] == [2]
        assert search.search_versions(
            VIDEO, source="template", favorite=True
        ) == []

    def test_range_plus_query(self, history, search):
        save(history, prompt="cinematic one")
        save(history, prompt="cinematic two")
        save(history, prompt="cinematic three")
        results = search.search_versions(
            VIDEO, query="cinematic", min_version=2, max_version=3
        )
        assert [r["version"] for r in results] == [2, 3]


class TestDeletedVersions:
    def test_deleted_versions_excluded(self, history, search):
        save(history, prompt="one")
        save(history, prompt="two")
        save(history, prompt="three")
        history.delete_version(VIDEO, 2)
        results = search.search_versions(VIDEO)
        assert [r["version"] for r in results] == [1, 3]

    def test_deleted_version_not_found_by_query(self, history, search):
        save(history, prompt="unique deleted text")
        history.delete_version(VIDEO, 1)
        assert search.search_versions(VIDEO, query="unique") == []

    def test_deleted_favorite_not_in_favorites_search(self, history, org, search):
        save(history, prompt="one")
        org.favorite_version(VIDEO, 1)
        history.delete_version(VIDEO, 1)
        assert search.search_versions(VIDEO, favorite=True) == []

    def test_deleted_version_not_recreatable_in_results(self, history, org, search):
        save(history, prompt="one")
        org.add_tags(VIDEO, 1, ["ai"])
        history.delete_version(VIDEO, 1)
        save(history, prompt="again")
        results = search.search_versions(VIDEO, tag="ai")
        assert results == [], "stale metadata must not leak onto new version"


class TestMultiVideoIsolation:
    def test_searches_only_requested_video(self, history, org, search):
        save(history, video=VIDEO, prompt="alpha shared text")
        save(history, video=OTHER, prompt="alpha other text")
        org.add_tags(VIDEO, 1, ["ai"])
        org.favorite_version(VIDEO, 1)
        results = search.search_versions(VIDEO, query="alpha")
        assert len(results) == 1
        assert results[0]["video_filename"] == VIDEO
        other = search.search_versions(OTHER, query="alpha")
        assert len(other) == 1
        assert other[0]["video_filename"] == OTHER
        assert other[0]["favorite"] is False
        assert other[0]["tags"] == []

    def test_filters_do_not_cross_videos(self, history, org, search):
        save(history, video=VIDEO, prompt="alpha")
        save(history, video=OTHER, prompt="alpha")
        org.favorite_version(OTHER, 1)
        assert search.search_versions(VIDEO, favorite=True) == []
        assert len(search.search_versions(OTHER, favorite=True)) == 1


class TestOrdering:
    def test_default_order_version_ascending(self, history, search):
        for i in range(4):
            save(history, prompt=f"prompt {i}")
        results = search.search_versions(VIDEO)
        assert [r["version"] for r in results] == [1, 2, 3, 4]

    def test_sort_version_desc(self, history, search):
        for i in range(3):
            save(history, prompt=f"prompt {i}")
        results = search.search_versions(VIDEO, sort="version_desc")
        assert [r["version"] for r in results] == [3, 2, 1]

    def test_sort_created_at_asc(self, history, search):
        for i in range(3):
            save(history, prompt=f"prompt {i}")
        results = search.search_versions(VIDEO, sort="created_at_asc")
        assert [r["version"] for r in results] == [1, 2, 3]

    def test_sort_created_at_desc(self, history, search):
        for i in range(3):
            save(history, prompt=f"prompt {i}")
        results = search.search_versions(VIDEO, sort="created_at_desc")
        assert [r["version"] for r in results] == [3, 2, 1]

    def test_invalid_sort_raises(self, search):
        with pytest.raises(ValueError, match="Invalid sort"):
            search.search_versions(VIDEO, sort="random")

    def test_all_sorts_valid(self, history, search):
        save(history, prompt="alpha")
        for sort in sorted(VALID_SORTS):
            assert len(search.search_versions(VIDEO, sort=sort)) == 1

    def test_deterministic_ordering_repeatable(self, history, search):
        for i in range(5):
            save(history, prompt=f"prompt {i} alpha")
        first = search.search_versions(VIDEO, query="alpha")
        second = search.search_versions(VIDEO, query="alpha")
        assert [r["version"] for r in first] == [r["version"] for r in second]
        assert first == second


class TestResultStructure:
    def test_result_keys(self, history, org, search):
        save(history, prompt="alpha", source="template", operation="ai_video",
             metadata={"k": "v"})
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai"])
        results = search.search_versions(VIDEO)
        assert set(results[0].keys()) == {
            "version_id",
            "video_filename",
            "version",
            "source",
            "operation",
            "prompt",
            "negative_prompt",
            "created_at",
            "metadata",
            "favorite",
            "tags",
        }

    def test_favorite_and_tags_reflected(self, history, org, search):
        save(history, prompt="alpha")
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai", "cinematic"])
        result = search.search_versions(VIDEO)[0]
        assert result["favorite"] is True
        assert result["tags"] == ["ai", "cinematic"]

    def test_prompt_contents_unchanged_by_search(self, history, search):
        prompt = '  Subject: "alpha"  \nBeta 42%  '
        save(history, prompt=prompt)
        result = search.search_versions(VIDEO, query="beta")[0]
        assert result["prompt"] == prompt
        assert history.get_version(VIDEO, 1)["prompt"] == prompt

    def test_negative_prompt_preserved(self, history, search):
        save(history, prompt="alpha")
        assert search.search_versions(VIDEO)[0]["negative_prompt"] == NEGATIVE

    def test_no_fabricated_data(self, history, org, search):
        save(history, prompt="Scene progression across 1 scenes.")
        results = search.search_versions(VIDEO)
        text = str(results).lower()
        for word in ["person", "character", "dialogue", "walking", "park",
                     "city", "sunset", "brand", "product", "voiceover"]:
            assert word not in text, f"fabricated: {word}"
        assert results[0]["tags"] == []
        assert results[0]["favorite"] is False

    def test_no_absolute_paths(self, history, org, search):
        save(history, prompt="alpha")
        org.add_tags(VIDEO, 1, ["ai"])
        import json
        serialized = json.dumps(search.search_versions(VIDEO))
        assert "C:/" not in serialized
        assert "C:\\" not in serialized
        assert "/home" not in serialized
        assert "/Users" not in serialized
        assert "/var" not in serialized

    def test_metadata_preserved(self, history, search):
        save(history, prompt="alpha", metadata={"note": "user saved"})
        assert search.search_versions(VIDEO)[0]["metadata"] == {
            "note": "user saved"
        }

    def test_history_records_not_modified(self, history, org, search):
        save(history, prompt="alpha", source="refinement", operation="shorten")
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["ai"])
        search.search_versions(VIDEO, query="alpha", favorite=True, tag="ai")
        record = history.get_version(VIDEO, 1)
        assert record["prompt"] == "alpha"
        assert record["source"] == "refinement"
        assert record["operation"] == "shorten"
