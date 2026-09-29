"""Tests for the prompt readiness history analysis service (Day 25)."""
import inspect
import json

import pytest

from app.services.prompt_quality_service import (
    PromptQualityService,
    DIMENSIONS,
)
from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService
from app.services.prompt_readiness_service import (
    PromptReadinessService,
    REQUIRED_DIMENSIONS,
    SUPPORTING_DIMENSIONS,
)
from app.services.prompt_readiness_history_service import (
    PromptReadinessHistoryService,
)

# --- Fixture prompts (Day 21/24 verified) -----------------------------------
FULL = ("Cinematic film grain style portrait of a person, the subject "
        "walking, looking around and gesturing in an outdoor forest "
        "street, camera tracking with shallow depth of field, soft "
        "lighting with rim light and golden hour glow, vibrant teal and "
        "orange palette with warm tones, layered foreground and rule of "
        "thirds composition, ambient sound with quiet music score.")
REQ_ONLY = ("Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, camera tracking with shallow depth of field, soft "
            "lighting with rim light and golden hour glow, layered "
            "foreground and rule of thirds composition.")
CITY = "A person walks through a city street."
WEAK_CAM = ("Cinematic film grain style portrait of a person, the subject "
            "walking, looking around and gesturing in an outdoor forest "
            "street, tracking only, soft lighting with rim light and "
            "golden hour glow, vibrant teal and orange palette with warm "
            "tones, layered foreground and rule of thirds composition, "
            "ambient sound with quiet music score.")
COV71 = ("Cinematic film grain style portrait of a person, the subject "
         "walking, looking around and gesturing in an outdoor forest "
         "street, tracking only, soft lighting with rim light and golden "
         "hour glow, vibrant teal and orange palette with warm tones, "
         "ambient sound with quiet music score.")
MINIMAL = "nothing specific at all"

VIDEO = "sample.mp4"

SUMMARY_KEYS = {
    "versions_analyzed", "ready_count", "needs_attention_count",
    "required_dimensions_total", "required_dimensions_present",
    "required_dimensions_weak", "required_dimensions_missing",
    "required_coverage_percentage", "supporting_dimensions_total",
    "supporting_dimensions_present", "supporting_dimensions_weak",
    "supporting_dimensions_missing", "supporting_coverage_percentage",
}

RESULT_KEYS = {"version", "version_id", "source", "operation", "readiness"}


def _save(history, prompt, source="custom", operation=""):
    return history.create_version(
        VIDEO, prompt, source=source, operation=operation
    )


def _build_history(specs=None):
    """Create a fresh history service with the standard 4-version set."""
    if specs is None:
        specs = [
            (FULL, "advanced_prompt", "generate"),
            (CITY, "custom", ""),
            (REQ_ONLY, "refinement", "expand"),
            (WEAK_CAM, "template", "cinematic"),
        ]
    history = PromptHistoryService()
    for prompt, source, operation in specs:
        _save(history, prompt, source=source, operation=operation)
    return history


@pytest.fixture
def history():
    return _build_history()


@pytest.fixture
def service(history):
    return PromptReadinessHistoryService(
        history, PromptReadinessService(PromptQualityService())
    )


@pytest.fixture
def empty_service():
    return PromptReadinessHistoryService(
        PromptHistoryService(), PromptReadinessService(PromptQualityService())
    )


class TestWiring:
    def test_constructor_state_only_two_dependencies(self, history):
        readiness = PromptReadinessService(PromptQualityService())
        svc = PromptReadinessHistoryService(history, readiness)
        assert set(vars(svc).keys()) == {"history_service", "readiness_service"}
        assert svc.history_service is history
        assert svc.readiness_service is readiness

    def test_no_third_store_or_services(self, history):
        svc = PromptReadinessHistoryService(
            history, PromptReadinessService(PromptQualityService())
        )
        for name in ("quality_service", "organization_service",
                     "search_service", "export_service",
                     "package_service"):
            assert not hasattr(svc, name), name


class TestResultStructure:
    def test_top_level_keys(self, service):
        result = service.analyze_versions(VIDEO)
        assert set(result.keys()) == {
            "video_filename", "versions_analyzed", "results", "summary",
            "dimension_summary",
        }
        assert result["video_filename"] == VIDEO

    def test_versions_analyzed_is_ascending_list_of_ints(self, service):
        result = service.analyze_versions(VIDEO)
        assert result["versions_analyzed"] == [1, 2, 3, 4]
        assert all(type(v) is int for v in result["versions_analyzed"])

    def test_each_result_keys(self, service):
        for item in service.analyze_versions(VIDEO)["results"]:
            assert set(item.keys()) == RESULT_KEYS
            assert type(item["version"]) is int
            assert item["version_id"] == f"{VIDEO}:{item['version']}"
            assert type(item["readiness"]) is dict

    def test_results_order_matches_versions_analyzed(self, service):
        result = service.analyze_versions(VIDEO)
        assert [r["version"] for r in result["results"]] == (
            result["versions_analyzed"]
        )

    def test_source_and_operation_passthrough(self, service):
        results = service.analyze_versions(VIDEO)["results"]
        assert [(r["source"], r["operation"]) for r in results] == [
            ("advanced_prompt", "generate"),
            ("custom", ""),
            ("refinement", "expand"),
            ("template", "cinematic"),
        ]

    @pytest.mark.parametrize("prompt_index,expected", [
        (0, "ready"), (1, "needs_attention"), (2, "ready"),
        (3, "needs_attention"),
    ])
    def test_readiness_is_exact_day24_output(
        self, service, prompt_index, expected
    ):
        item = service.analyze_versions(VIDEO)["results"][prompt_index]
        prompt = [FULL, CITY, REQ_ONLY, WEAK_CAM][prompt_index]
        direct = PromptReadinessService(
            PromptQualityService()
        ).validate_prompt(prompt)["readiness"]
        assert item["readiness"] == direct
        assert item["readiness"]["status"] == expected

    def test_readiness_keys_match_day24_contract(self, service):
        readiness = service.analyze_versions(VIDEO)["results"][0]["readiness"]
        assert set(readiness.keys()) == {
            "status", "required_dimensions", "supporting_dimensions",
            "checklist", "coverage", "missing_dimensions",
            "weak_dimensions", "suggestions",
        }
        assert readiness["required_dimensions"] == list(REQUIRED_DIMENSIONS)
        assert readiness["supporting_dimensions"] == list(SUPPORTING_DIMENSIONS)

    def test_result_does_not_echo_prompt_text(self, service):
        text = json.dumps(service.analyze_versions(VIDEO))
        for fragment in ("Cinematic film grain", "city street",
                         "tracking only"):
            assert fragment not in text, fragment

    def test_summary_keys_exact(self, service):
        summary = service.analyze_versions(VIDEO)["summary"]
        assert set(summary.keys()) == SUMMARY_KEYS

    def test_dimension_summary_entry_keys(self, service):
        for entry in service.analyze_versions(VIDEO)["dimension_summary"]:
            assert set(entry.keys()) == {
                "dimension", "present_count", "weak_count", "missing_count",
            }


class TestAllVersionsSelection:
    def test_no_versions_argument_selects_all_ascending(self, service):
        assert service.analyze_versions(VIDEO)["versions_analyzed"] == [1, 2, 3, 4]

    def test_none_argument_equals_explicit_all(self, service):
        assert (service.analyze_versions(VIDEO, None)
                == service.analyze_versions(VIDEO))

    def test_ascending_even_when_created_out_of_order(self):
        history = PromptHistoryService()
        _save(history, CITY)
        _save(history, FULL)
        _save(history, MINIMAL)
        svc = PromptReadinessHistoryService(
            history, PromptReadinessService(PromptQualityService())
        )
        assert svc.analyze_versions(VIDEO)["versions_analyzed"] == [1, 2, 3]

    def test_deleted_versions_excluded_from_all(self, history, service):
        history.delete_version(VIDEO, 2)
        result = service.analyze_versions(VIDEO)
        assert result["versions_analyzed"] == [1, 3, 4]
        assert result["summary"]["versions_analyzed"] == 3

    def test_unknown_video_returns_empty_analysis(self, service):
        result = service.analyze_versions("does_not_exist.mp4")
        assert result["versions_analyzed"] == []
        assert result["results"] == []


class TestSelectedVersions:
    def test_subset_preserves_requested_order(self, service):
        result = service.analyze_versions(VIDEO, [3, 1])
        assert result["versions_analyzed"] == [3, 1]
        assert [r["version"] for r in result["results"]] == [3, 1]

    def test_single_version(self, service):
        result = service.analyze_versions(VIDEO, [2])
        assert result["versions_analyzed"] == [2]
        assert result["results"][0]["version"] == 2
        assert result["summary"]["versions_analyzed"] == 1

    def test_three_of_five_requested(self):
        history = PromptHistoryService()
        for prompt in (FULL, CITY, REQ_ONLY, WEAK_CAM, MINIMAL):
            _save(history, prompt)
        svc = PromptReadinessHistoryService(
            history, PromptReadinessService(PromptQualityService())
        )
        result = svc.analyze_versions(VIDEO, [1, 3, 5])
        assert result["versions_analyzed"] == [1, 3, 5]
        assert result["summary"]["versions_analyzed"] == 3

    def test_tuple_of_versions_accepted(self, service):
        assert service.analyze_versions(VIDEO, (1, 3))[
            "versions_analyzed"] == [1, 3]

    def test_selected_results_exactly_match_all_results(self, service):
        everything = service.analyze_versions(VIDEO)["results"]
        chosen = service.analyze_versions(VIDEO, [4, 2])["results"]
        by_version = {r["version"]: r for r in everything}
        assert chosen == [by_version[4], by_version[2]]

    def test_input_list_is_not_mutated(self, service):
        requested = [2, 1]
        service.analyze_versions(VIDEO, requested)
        assert requested == [2, 1]


class TestValidation:
    @pytest.mark.parametrize("bad", [
        [], [0], [-1], [-5], ["1"], [1.5], [None], [True], [False],
        [1, 2, 1], [2, 2], [1, 1, 1], 5, "1", 42, True, {"a": 1}, (),
    ])
    def test_invalid_versions_argument_raises(self, service, bad):
        with pytest.raises(ValueError):
            service.analyze_versions(VIDEO, bad)

    def test_nonexistent_version_raises_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.analyze_versions(VIDEO, [99])

    def test_deleted_version_raises_not_found(self, history, service):
        history.delete_version(VIDEO, 2)
        with pytest.raises(ValueError, match="not found"):
            service.analyze_versions(VIDEO, [2])

    def test_one_bad_version_fails_whole_request(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.analyze_versions(VIDEO, [1, 99])

    def test_nonexistent_video_with_selection_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.analyze_versions("gone.mp4", [1])

    def test_version_below_one_rejected_even_if_int(self, service):
        with pytest.raises(ValueError, match="positive"):
            service.analyze_versions(VIDEO, [0])


class TestEmptyHistory:
    def test_empty_video_returns_zeroed_analysis(self, empty_service):
        result = empty_service.analyze_versions(VIDEO)
        assert result["versions_analyzed"] == []
        assert result["results"] == []
        assert result["summary"]["versions_analyzed"] == 0
        assert result["summary"]["ready_count"] == 0
        assert result["summary"]["needs_attention_count"] == 0
        assert result["summary"]["required_dimensions_total"] == 0
        assert result["summary"]["required_coverage_percentage"] == 0
        assert result["summary"]["supporting_coverage_percentage"] == 0

    def test_empty_dimension_summary_covers_all_dimensions(self, empty_service):
        result = empty_service.analyze_versions(VIDEO)
        assert len(result["dimension_summary"]) == len(DIMENSIONS)
        for entry in result["dimension_summary"]:
            assert entry["present_count"] == 0
            assert entry["weak_count"] == 0
            assert entry["missing_count"] == 0

    def test_empty_analysis_is_json_serializable(self, empty_service):
        text = json.dumps(empty_service.analyze_versions(VIDEO))
        assert json.loads(text)["summary"]["versions_analyzed"] == 0


class TestAggregateSummary:
    @pytest.fixture
    def summary(self, service):
        return service.analyze_versions(VIDEO)["summary"]

    def test_versions_analyzed_count(self, summary):
        assert summary["versions_analyzed"] == 4

    def test_ready_and_attention_counts(self, summary):
        assert summary["ready_count"] == 2
        assert summary["needs_attention_count"] == 2

    def test_ready_plus_attention_equals_analyzed(self, summary):
        assert (summary["ready_count"]
                + summary["needs_attention_count"]) == 4

    def test_required_totals(self, summary):
        assert summary["required_dimensions_total"] == 4 * 7
        assert summary["required_dimensions_present"] == 21
        assert summary["required_dimensions_weak"] == 2
        assert summary["required_dimensions_missing"] == 5

    def test_required_counts_sum_to_total(self, summary):
        assert (summary["required_dimensions_present"]
                + summary["required_dimensions_weak"]
                + summary["required_dimensions_missing"]) == 28

    def test_required_coverage_percentage(self, summary):
        assert summary["required_coverage_percentage"] == round(21 / 28 * 100)

    def test_supporting_totals(self, summary):
        assert summary["supporting_dimensions_total"] == 4 * 2
        assert summary["supporting_dimensions_present"] == 4
        assert summary["supporting_dimensions_weak"] == 0
        assert summary["supporting_dimensions_missing"] == 4

    def test_supporting_counts_sum_to_total(self, summary):
        assert (summary["supporting_dimensions_present"]
                + summary["supporting_dimensions_weak"]
                + summary["supporting_dimensions_missing"]) == 8

    def test_supporting_coverage_percentage(self, summary):
        assert summary["supporting_coverage_percentage"] == 50

    def test_percentages_are_bounded_ints(self, summary):
        for key in ("required_coverage_percentage",
                    "supporting_coverage_percentage"):
            assert type(summary[key]) is int
            assert 0 <= summary[key] <= 100

    def test_weak_never_counts_as_present(self, service):
        summary = service.analyze_versions(VIDEO)["summary"]
        weak_present = summary["required_dimensions_present"]
        all_sum = (weak_present
                   + summary["required_dimensions_weak"]
                   + summary["required_dimensions_missing"])
        assert all_sum == summary["required_dimensions_total"]
        assert weak_present == 21, "weak (2) excluded from present"

    def test_two_version_subset_summary(self, service):
        summary = service.analyze_versions(VIDEO, [1, 2])["summary"]
        assert summary["versions_analyzed"] == 2
        assert summary["ready_count"] == 1
        assert summary["needs_attention_count"] == 1
        assert summary["required_dimensions_total"] == 14
        assert summary["required_dimensions_present"] == 8
        assert summary["required_dimensions_weak"] == 1
        assert summary["required_dimensions_missing"] == 5
        assert summary["required_coverage_percentage"] == round(8 / 14 * 100)
        assert summary["supporting_dimensions_present"] == 2
        assert summary["supporting_dimensions_missing"] == 2

    def test_single_version_summary_matches_day24_coverage(self, service):
        summary = service.analyze_versions(VIDEO, [3])["summary"]
        readiness = service.analyze_versions(VIDEO, [3])["results"][0][
            "readiness"]
        coverage = readiness["coverage"]
        assert summary["required_dimensions_present"] == coverage[
            "required_present"]
        assert summary["required_coverage_percentage"] == coverage[
            "required_coverage_percentage"]

    def test_all_ready_single_status_counts(self, service):
        summary = service.analyze_versions(VIDEO, [1])["summary"]
        assert summary["ready_count"] == 1
        assert summary["needs_attention_count"] == 0


class TestDimensionSummary:
    @pytest.fixture
    def dim_summary(self, service):
        return service.analyze_versions(VIDEO)["dimension_summary"]

    def test_covers_all_day21_dimensions_in_order(self, dim_summary):
        assert [d["dimension"] for d in dim_summary] == list(DIMENSIONS)

    def test_no_invented_or_missing_dimensions(self, dim_summary):
        assert len(dim_summary) == 9
        assert {d["dimension"] for d in dim_summary} == set(DIMENSIONS)

    def test_each_dimension_counts_sum_to_versions(self, dim_summary):
        for entry in dim_summary:
            total = (entry["present_count"] + entry["weak_count"]
                     + entry["missing_count"])
            assert total == 4, entry["dimension"]

    @pytest.mark.parametrize("dim,expected", [
        ("subject", (3, 1, 0)),
        ("action", (3, 0, 1)),
        ("environment", (4, 0, 0)),
        ("camera", (2, 1, 1)),
        ("lighting", (3, 0, 1)),
        ("visual_style", (3, 0, 1)),
        ("color", (2, 0, 2)),
        ("composition", (3, 0, 1)),
        ("audio", (2, 0, 2)),
    ])
    def test_exact_counts_per_dimension(self, dim_summary, dim, expected):
        entry = next(d for d in dim_summary if d["dimension"] == dim)
        assert (entry["present_count"], entry["weak_count"],
                entry["missing_count"]) == expected

    def test_counts_match_checklists_directly(self, service):
        result = service.analyze_versions(VIDEO)
        for entry in result["dimension_summary"]:
            dim = entry["dimension"]
            present = weak = missing = 0
            for r in result["results"]:
                item = next(c for c in r["readiness"]["checklist"]
                            if c["dimension"] == dim)
                if item["status"] == "present":
                    present += 1
                elif item["status"] == "weak":
                    weak += 1
                else:
                    missing += 1
            assert (entry["present_count"], entry["weak_count"],
                    entry["missing_count"]) == (present, weak, missing)

    def test_empty_history_dimension_summary_all_zero(self, empty_service):
        entries = empty_service.analyze_versions(VIDEO)["dimension_summary"]
        assert [d["dimension"] for d in entries] == list(DIMENSIONS)
        for entry in entries:
            assert (entry["present_count"], entry["weak_count"],
                    entry["missing_count"]) == (0, 0, 0)


class TestSupportingInformational:
    def test_supporting_missing_version_is_still_ready(self, service):
        results = service.analyze_versions(VIDEO)["results"]
        req_only = next(r for r in results if r["version"] == 3)
        readiness = req_only["readiness"]
        assert readiness["status"] == "ready"
        assert readiness["missing_dimensions"] == ["color", "audio"]

    def test_supporting_missing_ready_counted_ready(self, service):
        summary = service.analyze_versions(VIDEO, [3])["summary"]
        assert summary["ready_count"] == 1
        assert summary["supporting_dimensions_missing"] == 2

    def test_supporting_present_but_required_weak_not_ready(self, service):
        results = service.analyze_versions(VIDEO, [4])["results"]
        readiness = results[0]["readiness"]
        assert readiness["status"] == "needs_attention"
        assert "camera" in readiness["weak_dimensions"]
        assert results[0]["readiness"]["coverage"][
            "supporting_present"] == 2

    def test_supporting_totals_never_change_status(self, service):
        result = service.analyze_versions(VIDEO)
        for r in result["results"]:
            readiness = r["readiness"]
            required_ok = all(
                status == "present"
                for status in (
                    item["status"] for item in readiness["checklist"]
                    if item["dimension"] in REQUIRED_DIMENSIONS
                )
            )
            assert readiness["status"] == ("ready" if required_ok
                                           else "needs_attention")


class TestDeterminism:
    def test_repeated_analysis_identical(self, service):
        assert (service.analyze_versions(VIDEO)
                == service.analyze_versions(VIDEO))

    def test_repeated_selection_identical(self, service):
        assert (service.analyze_versions(VIDEO, [1, 3])
                == service.analyze_versions(VIDEO, [1, 3]))

    def test_json_serializable(self, service):
        text = json.dumps(service.analyze_versions(VIDEO))
        assert json.loads(text)["versions_analyzed"] == [1, 2, 3, 4]

    def test_no_timestamps_uuids_or_random_values(self, service):
        text = json.dumps(service.analyze_versions(VIDEO))
        for token in ("created_at", "uuid", "timestamp", "datetime",
                      "random"):
            assert token not in text, token

    def test_status_values_are_only_the_two_day24_values(self, service):
        statuses = {
            r["readiness"]["status"]
            for r in service.analyze_versions(VIDEO)["results"]
        }
        assert statuses <= {"ready", "needs_attention"}

    def test_analysis_is_pure_function_of_prompts(self):
        first = PromptReadinessHistoryService(
            _build_history(),
            PromptReadinessService(PromptQualityService()),
        ).analyze_versions(VIDEO)
        second = PromptReadinessHistoryService(
            _build_history(),
            PromptReadinessService(PromptQualityService()),
        ).analyze_versions(VIDEO)
        assert first == second


class TestReadOnlyAndIntegrity:
    def test_history_listing_unchanged(self, service, history):
        before = json.dumps(history.list_versions(VIDEO))
        service.analyze_versions(VIDEO)
        service.analyze_versions(VIDEO, [1, 4])
        assert json.dumps(history.list_versions(VIDEO)) == before

    def test_history_record_keys_unchanged(self, service, history):
        before = set(history.get_version(VIDEO, 1).keys())
        service.analyze_versions(VIDEO)
        assert set(history.get_version(VIDEO, 1).keys()) == before

    def test_prompts_unchanged_exactly(self, service, history):
        prompts = {
            v: history.get_version(VIDEO, v)["prompt"]
            for v in (1, 2, 3, 4)
        }
        service.analyze_versions(VIDEO)
        for version, prompt in prompts.items():
            assert history.get_version(VIDEO, version)["prompt"] == prompt

    def test_day21_report_unchanged(self, history, service):
        quality = PromptQualityService()
        before = quality.analyze_prompt(CITY)
        service.analyze_versions(VIDEO)
        assert quality.analyze_prompt(CITY) == before

    def test_favorites_and_tags_unchanged(self, history, service):
        org = PromptOrganizationService(history)
        org.favorite_version(VIDEO, 1)
        org.add_tags(VIDEO, 1, ["cinematic"])
        org.add_tags(VIDEO, 3, ["draft"])
        snapshot_favorites = org.list_favorites(VIDEO)
        snapshot_org = {
            v: org.get_organization(VIDEO, v) for v in (1, 2, 3, 4)
        }

        service.analyze_versions(VIDEO)
        service.analyze_versions(VIDEO, [2])

        assert org.list_favorites(VIDEO) == snapshot_favorites
        for version, entry in snapshot_org.items():
            assert org.get_organization(VIDEO, version) == entry

    def test_deletion_is_respected_not_recreated(self, history, service):
        history.delete_version(VIDEO, 2)
        service.analyze_versions(VIDEO, [1])
        assert history.get_version(VIDEO, 1)["version"] == 1
        with pytest.raises(ValueError):
            history.get_version(VIDEO, 2)


class TestNoLeaksAndNoRanking:
    def test_no_absolute_paths_in_output(self, service):
        text = str(service.analyze_versions(VIDEO))
        for bad in ("C:\\", "C:/", "/home", "/Users", "/var/"):
            assert bad not in text, bad

    def test_no_internal_objects_or_secrets(self, service):
        text = str(service.analyze_versions(VIDEO))
        for token in ("_storage", "PromptReadinessHistoryService",
                      "PromptReadinessService", "PromptQualityService",
                      "PromptHistoryService", "Traceback", "secret",
                      "api_key", "password", "os.environ"):
            assert token not in text, token

    def test_no_forbidden_ranking_language(self, service):
        text = str(service.analyze_versions(VIDEO)).lower()
        for word in ("best", "worst", "winner", "perfect", "guaranteed",
                     "superior", "inferior", "rank", "recommended",
                     "objectively good", "should use"):
            assert word not in text, word

    def test_no_fabricated_visual_words(self, service):
        text = str(service.analyze_versions(VIDEO, [2])).lower()
        for word in ("sunset", "neon", "tokyo", "ferrari", "drone",
                     "luxury"):
            assert word not in text, word


class TestSourceContract:
    def test_module_has_no_network_or_filesystem_access(self):
        import app.services.prompt_readiness_history_service as mod
        source = inspect.getsource(mod)
        for forbidden in ("requests", "urllib", "socket", "http.client",
                          "subprocess", "open(", "os.path", "Path(",
                          "httpx", "aiohttp", "import random",
                          "import datetime", "datetime.now", "import uuid"):
            assert forbidden not in source, forbidden

    def test_module_never_writes_to_history(self):
        import app.services.prompt_readiness_history_service as mod
        source = inspect.getsource(mod)
        for forbidden in ("create_version", "delete_version",
                          "favorite_version", "unfavorite_version",
                          "add_tags", "remove_tags", "save_advanced_prompt",
                          "_storage["):
            assert forbidden not in source, forbidden

    def test_module_uses_only_read_paths_of_history(self):
        import app.services.prompt_readiness_history_service as mod
        source = inspect.getsource(mod)
        assert "list_versions" in source
        assert "get_version" in source
        assert "validate_prompt" in source

    def test_no_llm_or_remote_calls(self):
        import app.services.prompt_readiness_history_service as mod
        source = inspect.getsource(mod)
        for forbidden in ("openai", "anthropic", "completion",
                          "api_key"):
            assert forbidden not in source, forbidden
