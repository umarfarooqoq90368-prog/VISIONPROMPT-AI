"""Tests for the prompt comparison & diff service (Day 23)."""
import inspect
import json

import pytest

from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_quality_service import (
    PromptQualityService,
    DIMENSIONS,
)
from app.services.prompt_comparison_service import PromptComparisonService

VIDEO = "abc123.mp4"
OTHER = "def456.mp4"

SPEC_A = "A person walks through a road."
SPEC_B = "A person walks through a road. Medium shot with natural lighting."


@pytest.fixture
def history():
    return PromptHistoryService()


@pytest.fixture
def quality():
    return PromptQualityService()


@pytest.fixture
def service(history, quality):
    return PromptComparisonService(history, quality)


def save(history, video, prompt, source="custom", operation=""):
    return history.create_version(
        video_filename=video,
        prompt=prompt,
        source=source,
        operation=operation,
    )


def build(history, video, prompts, **kwargs):
    """Save a list of prompts, return their version numbers (1-based)."""
    return [save(history, video, p, **kwargs)["version"] for p in prompts]


def analyze(quality, prompt):
    return quality.analyze_prompt(prompt)["quality"]


class TestValidation:
    def test_nonexistent_video_raises(self, history, service):
        with pytest.raises(ValueError):
            service.compare_versions("missing.mp4", 1, 1)

    def test_nonexistent_version_a_raises(self, history, service):
        save(history, VIDEO, "only one version here")
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, 99, 1)

    def test_nonexistent_version_b_raises(self, history, service):
        save(history, VIDEO, "only one version here")
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, 1, 99)

    def test_version_zero_raises(self, history, service):
        save(history, VIDEO, "only one version here")
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, 0, 1)
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, 1, 0)

    def test_negative_version_raises(self, history, service):
        save(history, VIDEO, "only one version here")
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, -1, 1)

    def test_deleted_version_raises(self, history, service):
        save(history, VIDEO, "first version prompt")
        save(history, VIDEO, "second version prompt")
        history.delete_version(VIDEO, 1)
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, 1, 2)

    def test_no_versions_at_all_raises(self, service):
        with pytest.raises(ValueError):
            service.compare_versions(VIDEO, 1, 1)


class TestIdenticalPrompts:
    @pytest.fixture
    def result(self, history, service):
        build(history, VIDEO, ["Same prompt text", "Same prompt text"])
        return service.compare_versions(VIDEO, 1, 2)

    def test_identical_flag(self, result):
        assert result["comparison"]["identical"] is True
        assert result["comparison"]["changed"] is False

    def test_no_added_or_removed(self, result):
        assert result["comparison"]["added_text"] == ""
        assert result["comparison"]["removed_text"] == ""

    def test_common_text_still_available(self, result):
        assert result["comparison"]["common_text"] == "Same prompt text"

    def test_zero_deltas_and_unchanged_labels(self, result):
        assert result["comparison"]["quality_score_delta"] == 0
        assert result["comparison"]["completeness_delta"] == 0
        assert result["comparison"]["quality_score_change"] == "unchanged"
        assert result["comparison"]["completeness_change"] == "unchanged"

    def test_no_changed_dimensions(self, result):
        assert result["comparison"]["changed_dimensions"] == []

    def test_same_version_comparison_is_identical(self, history, service):
        save(history, VIDEO, "Only one version prompt")
        result = service.compare_versions(VIDEO, 1, 1)
        assert result["comparison"]["identical"] is True
        assert result["comparison"]["common_text"] == "Only one version prompt"
        assert result["comparison"]["quality_score_delta"] == 0


class TestTextDiff:
    @pytest.fixture
    def setup(self, history):
        history.create_version(VIDEO, "Alpha one")
        history.create_version(VIDEO, "Alpha two")
        history.create_version(VIDEO, "Gamma three")
        return history

    def test_added_text(self, setup, service):
        setup.create_version(VIDEO, "Alpha one with more words")
        result = service.compare_versions(VIDEO, 1, 4)
        comp = result["comparison"]
        assert comp["added_text"] != ""
        assert comp["removed_text"] == ""
        assert "Alpha one" in comp["common_text"]
        assert comp["added_text"] in "Alpha one with more words"

    def test_removed_text(self, setup, service):
        # going from v2 ("Alpha two") back to v1 ("Alpha one")
        result = service.compare_versions(VIDEO, 2, 1)
        comp = result["comparison"]
        assert comp["removed_text"].strip() == "two"
        assert comp["added_text"].strip() == "one"
        assert "Alpha" in comp["common_text"]

    def test_completely_different_prompts(self, history, service):
        build(history, VIDEO, ["completely different wording here",
                               "entirely other sentence now"])
        result = service.compare_versions(VIDEO, 1, 2)
        comp = result["comparison"]
        assert comp["identical"] is False
        assert comp["changed"] is True
        assert comp["added_text"] != ""
        assert comp["removed_text"] != ""
        assert comp["common_text"] == ""

    def test_partially_changed_prompts(self, history, service):
        build(history, VIDEO, [
            "The subject walks slowly forward",
            "The subject runs quickly forward",
        ])
        result = service.compare_versions(VIDEO, 1, 2)
        comp = result["comparison"]
        assert comp["changed"] is True
        assert "walks" in comp["removed_text"]
        assert "runs" in comp["added_text"]
        assert "forward" in comp["common_text"]

    def test_appended_text(self, history, service):
        base = "Base prompt sentence."
        appended = "Base prompt sentence. Extra appended clause."
        build(history, VIDEO, [base, appended])
        result = service.compare_versions(VIDEO, 1, 2)
        comp = result["comparison"]
        assert comp["added_text"].strip() == "Extra appended clause."
        assert comp["removed_text"] == ""
        assert comp["common_text"] == base

    def test_removed_text_is_exact_reverse_of_append(self, history, service):
        base = "Base prompt sentence."
        appended = "Base prompt sentence. Extra appended clause."
        build(history, VIDEO, [base, appended])
        result = service.compare_versions(VIDEO, 2, 1)
        comp = result["comparison"]
        assert comp["removed_text"].strip() == "Extra appended clause."
        assert comp["added_text"] == ""
        assert comp["common_text"] == base

    def test_multiple_changes(self, history, service):
        build(history, VIDEO, [
            "one two three four five",
            "one SIDE three SIDE five",
        ])
        result = service.compare_versions(VIDEO, 1, 2)
        comp = result["comparison"]
        assert "two" in comp["removed_text"]
        assert "four" in comp["removed_text"]
        assert "SIDE" in comp["added_text"]
        assert "one" in comp["common_text"] and "three" in comp["common_text"]

    def test_whitespace_change_detected(self, history, service):
        build(history, VIDEO, ["word  spaced  out", "word spaced out"])
        result = service.compare_versions(VIDEO, 1, 2)
        comp = result["comparison"]
        assert comp["identical"] is False
        assert comp["changed"] is True
        assert comp["removed_text"] != ""
        assert comp["added_text"] != ""

    def test_punctuation_change_detected(self, history, service):
        build(history, VIDEO, ["hello world", "hello, world"])
        result = service.compare_versions(VIDEO, 1, 2)
        comp = result["comparison"]
        assert comp["changed"] is True
        assert comp["added_text"] != ""
        assert comp["removed_text"] != ""

    def test_original_prompts_preserved_exactly(self, history, service):
        pa = "  Leading and trailing   spaces  "
        pb = "Totally (different) prompt: text!"
        build(history, VIDEO, [pa, pb])
        result = service.compare_versions(VIDEO, 1, 2)
        assert result["version_a"]["prompt"] == pa
        assert result["version_b"]["prompt"] == pb

    def test_diff_never_invents_text(self, history, service):
        pa = "Alpha fact one. Beta fact two."
        pb = "Alpha fact one. Gamma fact three."
        build(history, VIDEO, [pa, pb])
        result = service.compare_versions(VIDEO, 1, 2)
        comp = result["comparison"]
        # every word of the diff must come from the source prompts
        for word in comp["added_text"].split():
            assert word in pb.split()
        for word in comp["removed_text"].split():
            assert word in pa.split()
        for word in comp["common_text"].split():
            assert word in pa.split()


class TestQualityComparison:
    @pytest.fixture
    def pair(self, history, service):
        build(history, VIDEO, [SPEC_A, SPEC_B])
        return service.compare_versions(VIDEO, 1, 2)

    def test_quality_reports_equal_direct_day21(self, quality, pair):
        assert pair["version_a"]["quality"] == analyze(quality, SPEC_A)
        assert pair["version_b"]["quality"] == analyze(quality, SPEC_B)

    def test_score_delta_is_b_minus_a(self, quality, pair):
        qa = analyze(quality, SPEC_A)
        qb = analyze(quality, SPEC_B)
        expected = qb["overall_score"] - qa["overall_score"]
        assert pair["comparison"]["quality_score_delta"] == expected
        assert pair["comparison"]["quality_score_delta"] > 0
        assert pair["comparison"]["quality_score_change"] == "increased"

    def test_completeness_delta_is_b_minus_a(self, quality, pair):
        qa = analyze(quality, SPEC_A)
        qb = analyze(quality, SPEC_B)
        expected = (qb["completeness_percentage"]
                    - qa["completeness_percentage"])
        assert pair["comparison"]["completeness_delta"] == expected
        assert pair["comparison"]["completeness_delta"] > 0
        assert pair["comparison"]["completeness_change"] == "increased"

    def test_decreased_label_when_b_is_lower(self, history, service, quality):
        build(history, VIDEO, [SPEC_B, SPEC_A])
        result = service.compare_versions(VIDEO, 1, 2)
        assert result["comparison"]["quality_score_delta"] < 0
        assert result["comparison"]["quality_score_change"] == "decreased"
        assert result["comparison"]["completeness_change"] == "decreased"

    def test_no_ranking_language(self, history, service):
        build(history, VIDEO, [SPEC_A, SPEC_B])
        result = service.compare_versions(VIDEO, 1, 2)
        # the comparison block itself must stay neutral
        text = str(result["comparison"]).lower()
        for word in ("better", "worse", "winner", "superior", "inferior",
                     "rank", "improved over", "best"):
            assert word not in text, word


class TestChangedDimensions:
    @pytest.fixture
    def pair(self, history, service):
        build(history, VIDEO, [SPEC_A, SPEC_B])
        return service.compare_versions(VIDEO, 1, 2)

    def test_changed_dimensions_match_quality_difference(self, quality, pair):
        qa = analyze(quality, SPEC_A)
        qb = analyze(quality, SPEC_B)
        expected = []
        for dim in DIMENSIONS:
            if qa["dimensions"][dim] != qb["dimensions"][dim]:
                expected.append({
                    "dimension": dim,
                    "before_present": qa["dimensions"][dim]["present"],
                    "after_present": qb["dimensions"][dim]["present"],
                    "before_score": qa["dimensions"][dim]["score"],
                    "after_score": qb["dimensions"][dim]["score"],
                })
        assert pair["comparison"]["changed_dimensions"] == expected

    def test_camera_and_lighting_detected(self, pair):
        changed = [c["dimension"] for c in
                   pair["comparison"]["changed_dimensions"]]
        assert changed == ["camera", "lighting"]
        for c in pair["comparison"]["changed_dimensions"]:
            assert c["before_present"] is False
            assert c["after_present"] is True

    def test_ordering_follows_day21_dimension_order(self, pair):
        dims = [c["dimension"] for c in
                pair["comparison"]["changed_dimensions"]]
        assert dims == [d for d in DIMENSIONS if d in set(dims)]

    def test_only_differing_dimensions_included(self, pair):
        for c in pair["comparison"]["changed_dimensions"]:
            assert (c["before_present"] != c["after_present"]
                    or c["before_score"] != c["after_score"])

    def test_identical_quality_gives_empty_list(self, history, service):
        build(history, VIDEO, ["Same prompt text", "Same prompt text"])
        result = service.compare_versions(VIDEO, 1, 2)
        assert result["comparison"]["changed_dimensions"] == []

    def test_quality_unchanged_text_change_gives_empty_list(
            self, history, service):
        # whitespace-only change: text differs but Day21 quality identical
        build(history, VIDEO, ["Person walks here", "Person  walks here"])
        result = service.compare_versions(VIDEO, 1, 2)
        assert result["comparison"]["changed"] is True
        assert result["comparison"]["changed_dimensions"] == []


class TestVersionOrdering:
    @pytest.fixture
    def setup(self, history, service):
        build(history, VIDEO, [SPEC_A, SPEC_B])
        return service

    def test_order_a_then_b(self, setup):
        result = setup.compare_versions(VIDEO, 1, 2)
        assert result["version_a"]["version"] == 1
        assert result["version_b"]["version"] == 2
        assert result["version_a"]["prompt"] == SPEC_A
        assert result["version_b"]["prompt"] == SPEC_B

    def test_order_is_never_swapped(self, setup):
        result = setup.compare_versions(VIDEO, 2, 1)
        assert result["version_a"]["version"] == 2
        assert result["version_b"]["version"] == 1
        assert result["version_a"]["prompt"] == SPEC_B
        assert result["version_b"]["prompt"] == SPEC_A

    def test_reversed_deltas_are_negated(self, setup):
        forward = setup.compare_versions(VIDEO, 1, 2)["comparison"]
        reverse = setup.compare_versions(VIDEO, 2, 1)["comparison"]
        assert (reverse["quality_score_delta"]
                == -forward["quality_score_delta"])
        assert (reverse["completeness_delta"]
                == -forward["completeness_delta"])
        # diff text swaps sides
        assert reverse["added_text"] == forward["removed_text"]
        assert reverse["removed_text"] == forward["added_text"]
        assert reverse["common_text"] == forward["common_text"]


class TestResultStructure:
    @pytest.fixture
    def result(self, history, service):
        build(history, VIDEO, [SPEC_A, SPEC_B],
              source="refinement", operation="cinematic")
        return service.compare_versions(VIDEO, 1, 2)

    def test_top_level_keys(self, result):
        assert set(result.keys()) == {
            "video_filename", "version_a", "version_b", "comparison",
        }
        assert result["video_filename"] == VIDEO

    def test_version_summary_keys(self, result):
        for key in ("version_a", "version_b"):
            summary = result[key]
            assert set(summary.keys()) == {
                "version", "version_id", "source", "operation",
                "prompt", "quality",
            }
            assert summary["version_id"] == f"{VIDEO}:{summary['version']}"

    def test_comparison_keys(self, result):
        assert set(result["comparison"].keys()) == {
            "identical", "changed", "added_text", "removed_text",
            "common_text", "quality_score_delta", "quality_score_change",
            "completeness_delta", "completeness_change",
            "changed_dimensions",
        }

    def test_metadata_preserved_in_summaries(self, result):
        assert result["version_a"]["source"] == "refinement"
        assert result["version_a"]["operation"] == "cinematic"


class TestDeterminism:
    @pytest.fixture
    def setup(self, history, service):
        build(history, VIDEO, [SPEC_A, SPEC_B])
        return service

    def test_repeated_comparisons_identical(self, setup):
        first = setup.compare_versions(VIDEO, 1, 2)
        second = setup.compare_versions(VIDEO, 1, 2)
        third = setup.compare_versions(VIDEO, 1, 2)
        assert first == second == third

    def test_no_timestamps_or_random_ids_generated(self, setup):
        result = setup.compare_versions(VIDEO, 1, 2)
        text = str(result)
        import re
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", text)
        assert "uuid" not in text.lower()
        assert "timestamp" not in text.lower()

    def test_json_serializable(self, setup):
        result = setup.compare_versions(VIDEO, 1, 2)
        json.dumps(result)


class TestReadOnly:
    def test_history_unchanged_after_comparison(self, history, service):
        v1 = save(history, VIDEO, SPEC_A)
        v2 = save(history, VIDEO, SPEC_B)
        org = history.create_version(VIDEO, "third prompt")
        history  # favorites/tags live in org service; snapshot below

        before = json.dumps(history.list_versions(VIDEO), sort_keys=True)
        service.compare_versions(VIDEO, 1, 2)
        service.compare_versions(VIDEO, 2, 1)
        service.compare_versions(VIDEO, 1, 3)
        after = json.dumps(history.list_versions(VIDEO), sort_keys=True)
        assert before == after, "history store must not change"
        assert history.get_version(VIDEO, 1) == v1
        assert history.get_version(VIDEO, 2) == v2
        assert history.get_version(VIDEO, 3) == org

    def test_no_version_created_by_comparison(self, history, service):
        save(history, VIDEO, SPEC_A)
        save(history, VIDEO, SPEC_B)
        service.compare_versions(VIDEO, 1, 2)
        versions = history.list_versions(VIDEO)
        assert [v["version"] for v in versions] == [1, 2]

    def test_service_state_only_constructor_deps(self, history, quality):
        service = PromptComparisonService(history, quality)
        assert set(vars(service).keys()) == {"history_service",
                                             "quality_service"}


class TestSecurity:
    @pytest.fixture
    def result(self, history, service):
        build(history, VIDEO, [SPEC_A, SPEC_B])
        return service.compare_versions(VIDEO, 1, 2)

    def test_no_absolute_paths(self, result):
        text = str(result)
        for bad in ("C:\\", "C:/", "/home", "/Users", "/var/"):
            assert bad not in text

    def test_no_internal_objects_or_secrets(self, result):
        text = str(result)
        for token in ("_storage", "PromptComparisonService",
                      "PromptHistoryService", "PromptQualityService",
                      "Traceback", "secret", "api_key", "password",
                      "os.environ"):
            assert token not in text, token

    def test_no_fabricated_text_in_diff(self, result):
        comp = result["comparison"]
        assert comp["added_text"] in SPEC_B
        assert comp["removed_text"] in SPEC_A
        assert comp["common_text"] in SPEC_A

    def test_module_no_network_or_filesystem_access(self):
        source = inspect.getsource(
            __import__("app.services.prompt_comparison_service",
                       fromlist=["x"])
        )
        for forbidden in ("requests", "urllib", "socket", "http.client",
                          "subprocess", "open(", "os.path", "Path(",
                          "httpx", "aiohttp", "import random",
                          "import datetime", "datetime.now"):
            assert forbidden not in source, forbidden

    def test_module_has_no_state_modifying_helpers(self):
        import app.services.prompt_comparison_service as mod
        for name in dir(mod):
            if name.startswith("_") and name != "__all__":
                continue
            for bad in ("write", "save", "delete", "store", "favorite",
                        "create"):
                assert bad not in name.lower(), name

    def test_multi_video_isolation(self, history, service):
        save(history, VIDEO, "video A only prompt")
        save(history, OTHER, "video B only prompt")
        with pytest.raises(ValueError):
            service.compare_versions(OTHER, 2, 1)
        result = service.compare_versions(VIDEO, 1, 1)
        assert result["version_a"]["prompt"] == "video A only prompt"
