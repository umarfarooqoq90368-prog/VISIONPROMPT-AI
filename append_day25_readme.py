# -*- coding: utf-8 -*-
"""Append the Day 25 README section."""

SECTION = """

## Day 25 - Prompt Readiness History Analysis

Day 25 adds a **Prompt Readiness History Analysis** endpoint: a deterministic, read-only analysis layer that answers *"what readiness information is available across the saved prompt versions of this video?"* It runs the Day 24 Production Readiness Validator over selected Day 16 history versions and aggregates the results. It never ranks versions, never picks a best version, never declares one version superior, and never predicts which prompt will generate better video output. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Analyze readiness across **all** saved versions or a **selected** subset in one call
- Provide aggregate counts (`ready` vs `needs_attention`) and coverage totals
- Provide a per-dimension occurrence summary across versions
- Reuse Day 24 readiness output byte-for-byte - never recompute or alter statuses, scores, or coverage
- Never modify history, favorites, tags, exports, quality reports, or any prompt

### Relationship With Day 16 and Day 24

- Day 16 `PromptHistoryService` remains the single version store; Day 25 only calls its read paths (`list_versions`, `get_version`)
- Day 24 `PromptReadinessService` remains the single readiness source; each analyzed version's `readiness` object is exactly what `validate_prompt` returns for that stored prompt
- Day 21 `PromptQualityService` stays behind Day 24 - Day 25 never touches scoring directly
- Analysis results are never persisted anywhere (no second store, no cache)

### Version Selection

| Query | Behavior |
|-------|----------|
| *(no query)* | Every live version, ascending version order |
| `?versions=1,3,5` | Only those versions, **requested order preserved** |
| `?versions=2` | Single version |
| `?versions=1&versions=3` | Repeated params also accepted |

Selection rules are deterministic: requested versions are never substituted, reordered, or dropped. Deleted versions are not substituted by neighbors. A video with no saved versions returns an empty (zeroed) analysis with HTTP 200.

### Response Shape

```json
{
  "video_filename": "abc123.mp4",
  "versions_analyzed": [1, 2],
  "results": [
    {
      "version": 1,
      "version_id": "abc123.mp4:1",
      "source": "advanced_prompt",
      "operation": "generate",
      "readiness": { "...": "exact Day 24 readiness object" }
    }
  ],
  "summary": { "...": "aggregate counts below" },
  "dimension_summary": [ "...": "one entry per Day 21 dimension" ]
}
```

Each `readiness` is the complete Day 24 object: `status`, `required_dimensions`, `supporting_dimensions`, `checklist`, `coverage`, `missing_dimensions`, `weak_dimensions`, `suggestions`.

### Summary Aggregates

| Key | Meaning |
|-----|---------|
| `versions_analyzed` | Number of versions analyzed |
| `ready_count` / `needs_attention_count` | Day 24 statuses across analyzed versions |
| `required_dimensions_total/present/weak/missing` | Summed Day 24 required coverage counts (`total = versions x 7`) |
| `required_coverage_percentage` | `round(required_present / required_total * 100)`, 0 when empty |
| `supporting_dimensions_total/present/weak/missing` | Summed supporting counts (`total = versions x 2`) |
| `supporting_coverage_percentage` | Informational only - supporting never affects readiness |

`present + weak + missing == total` for both groups. Weak (score 40) never counts as present. All percentages are integers bounded 0-100. `ready_count + needs_attention_count == versions_analyzed`.

### Dimension Summary

One entry per Day 21 dimension, in Day 21 order (`subject` ... `audio`):

```json
{"dimension": "camera", "present_count": 2, "weak_count": 1, "missing_count": 1}
```

For each dimension: `present_count + weak_count + missing_count == versions_analyzed`. Counts come straight from each version's Day 24 checklist statuses - no independent detection.

### Service

`backend/app/services/prompt_readiness_history_service.py` - `PromptReadinessHistoryService(history_service, readiness_service)`

- `analyze_versions(stored_filename, versions=None)` returns `video_filename`, `versions_analyzed`, `results`, `summary`, `dimension_summary`
- Raises `ValueError` for an invalid versions argument (not a non-empty list of unique positive integers) or a missing/deleted version
- Read-only: only `list_versions` / `get_version` / `validate_prompt` are called

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/readiness?versions=1,3,5
```

- The static `/prompt/history/readiness` route is registered **before** the plain numeric `{version}` routes, so history routes never collide
- Malformed, empty, duplicate, or non-positive `versions` values return HTTP 422
- Nonexistent video or missing/deleted version returns HTTP 404; invalid extension returns HTTP 400; path traversal returns HTTP 404

### Determinism and Integrity

- Repeated calls with the same state return exactly equal responses; no random values, timestamps, dates, or UUIDs
- Original prompts, history records, favorites, tags, exports, and quality reports are byte-identical before and after analysis
- No filesystem paths, internal objects, or secrets appear in any response
- Prompt text itself is not echoed in the analysis response (Day 24 GET history readiness remains available for per-version prompts)

### Limitations

- Aggregates Day 24's structural coverage only: it does not evaluate cinematography, aesthetics, or actual video content
- No version ranking of any kind: counts and coverages are neutral tallies, not recommendations
- A `ready` count means required dimensions were textually covered - not that any model will produce a satisfactory video
- The endpoint validates the video file's existence but the service itself operates purely on stored version data

### Tests

- `tests/test_prompt_readiness_history_service.py` - 104 service tests (wiring, result structure, all/selected/empty selection, validation errors, aggregates, dimension summary, supporting informational rule, determinism, read-only integrity, leak/ranking scans, source contract)
- `tests/test_prompt_readiness_history_api.py` - 70 API tests (200/422/404/400 validation, query parsing, per-version Day 24 cross-checks, summary/dimension verification, determinism, read-only integrity, route collision, Day 16-24 regressions, leak scans)

### Files Created/Modified

- `backend/app/services/prompt_readiness_history_service.py` - `PromptReadinessHistoryService`
- `backend/app/api/videos.py` - Added static `GET /prompt/history/readiness` route (registered before numeric `{version}` routes), `_parse_versions_query`, and service instance
- `tests/test_prompt_readiness_history_service.py` - 104 service tests
- `tests/test_prompt_readiness_history_api.py` - 70 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 25 section appended")
