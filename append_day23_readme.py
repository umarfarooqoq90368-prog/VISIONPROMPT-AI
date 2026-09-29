# -*- coding: utf-8 -*-
"""Append the Day 23 README section."""

SECTION = """

## Day 23 - Prompt Version Comparison & Diff

Day 23 adds **Prompt Version Comparison & Diff**: a deterministic, read-only comparison layer that produces a full structured comparison of any two saved prompt versions - text diff (added/removed/common), Day 21 quality reports for both versions, neutral quality deltas, and the quality dimensions that changed. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Show users exactly how two saved prompt versions differ
- Combine Day 16 history data with Day 21 quality analysis in one response
- Never modify history, favorites, tags, or store the comparison result
- Fully deterministic: same two versions -> identical output

### Architecture

- Day 16 `PromptHistoryService` remains the single source of truth for versions; Day 23 **reads** it via `get_version` and never writes
- Day 21 `PromptQualityService` remains the single quality-analysis source; Day 23 **reuses** `analyze_prompt` and never duplicates its scoring logic
- Day 23 `PromptComparisonService(history_service, quality_service)` holds only those two dependencies
- Day 16 token compare endpoint (`/prompt/history/compare/{a}/{b}`) stays unchanged - the Day 23 detailed route is a separate, longer path
- No LLM, no network, no filesystem, no database - pure in-process text analysis

### Comparison Flow

```
version A + version B -> Day 16 get_version (read-only, twice)
                      -> difflib.SequenceMatcher word-level diff
                      -> Day 21 analyze_prompt for each prompt
                      -> structured comparison (diff + deltas + dimensions)
```

### Text Diff (difflib)

- Prompts are tokenized with **leading whitespace attachment** (`\\s*\\S+`, plus a final token for trailing whitespace), so joining tokens reconstructs each prompt byte-for-byte and appends appear as clean inserts
- `difflib.SequenceMatcher(None, tokens_a, tokens_b, autojunk=False)` opcodes map to: `equal` -> `common_text`, `insert` -> `added_text`, `delete` -> `removed_text`, `replace` -> contributes to both `removed_text` and `added_text`
- The diff only ever reports text that exists in the two source prompts - never invents wording
- `identical` compares the raw prompts (so whitespace-only edits are `identical: false, changed: true`)

Example (`A person walks through a road.` -> `A person walks through a road. Medium shot with natural lighting.`):

- `common_text` = `A person walks through a road.`
- `added_text` = ` Medium shot with natural lighting.`
- `removed_text` = `` (empty)

### Quality Deltas (Day 21)

- `quality_score_delta` = `version_b.overall_score - version_a.overall_score`
- `completeness_delta` = `version_b.completeness_percentage - version_a.completeness_percentage`
- Labels are **neutral**: `increased` / `decreased` / `unchanged` - the service never ranks one version as better, improved, or superior
- `changed_dimensions` lists exactly the Day 21 dimensions whose `present`/`score` pair differs, in Day 21 dimension order (`subject, action, environment, camera, lighting, visual_style, color, composition, audio`)
- Version order is always preserved: deltas are always `b - a` for the requested order, and requesting `(2, 1)` is the exact mirror of `(1, 2)` - versions are never silently swapped

### Service

`backend/app/services/prompt_comparison_service.py` - `PromptComparisonService`

- `compare_versions(stored_filename, version_a, version_b)` returns:
  - `video_filename`
  - `version_a` / `version_b` summaries: `version`, `version_id`, `source`, `operation`, `prompt`, `quality` (the full Day 21 report)
  - `comparison`: `identical`, `changed`, `added_text`, `removed_text`, `common_text`, `quality_score_delta`, `quality_score_change`, `completeness_delta`, `completeness_change`, `changed_dimensions`
- Raises `ValueError` (bubbled from Day 16) when either version does not exist or the version number is invalid

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/compare/{version_a}/{version_b}/detailed
```

- Read-only: never modifies history, favorites, or tags; the result is never persisted
- Registered after the Day 16 token compare route (longer, distinct path) and before the plain numeric `{version}` route, so history routes never collide
- Version order in the URL is the comparison order

### Validation

- Valid versions return HTTP 200 (including `version_a == version_b`, which yields `identical: true`)
- Version below 1 or non-integer version returns HTTP 422
- Nonexistent video returns HTTP 404; invalid extension returns HTTP 400
- Path traversal attempts return HTTP 404
- Nonexistent or deleted history version returns HTTP 404

### Determinism

- Repeated requests for the same version pair return byte-identical JSON
- No timestamps, UUIDs, or random values appear in the response
- No external API calls

### Tests

- `tests/test_prompt_comparison_service.py` - 54 service tests (validation, identical/diff cases, whitespace/punctuation, quality deltas, changed dimensions, ordering/no-swap, structure, determinism, read-only, security)
- `tests/test_prompt_comparison_api.py` - 29 API tests (200/422/404/400 validation, response schema, direct Day 21 cross-checks, determinism, read-only, route collision, Day 16-22 regressions)

### Limitations

- The diff is word-level text comparison; it does not semantically judge which wording is preferable
- Quality analysis is Day 21 signal matching on text only - it does not understand actual video content
- Only two versions can be compared per request
- Results are never persisted; exporting or packaging comparisons is not part of Day 23

### Files Created/Modified

- `backend/app/services/prompt_comparison_service.py` - `PromptComparisonService`
- `backend/app/api/videos.py` - Added `/prompt/history/compare/{version_a}/{version_b}/detailed` (GET) endpoint and service instance
- `tests/test_prompt_comparison_service.py` - 54 service tests
- `tests/test_prompt_comparison_api.py` - 29 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 23 section appended")
