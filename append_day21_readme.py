# -*- coding: utf-8 -*-
"""Append the Day 21 README section."""

SECTION = """

## Day 21 - Prompt Quality Analyzer

Day 21 adds a **Prompt Quality Analyzer**: a deterministic, heuristic coverage analysis of any prompt text (supplied directly or stored as a history version). It reports nine quality dimensions with integer scores and actionable suggestions. This is analysis only - not prompt generation and not an LLM call.

### Purpose

- Show users exactly which quality dimensions their prompt covers and which are missing
- Give neutral, actionable suggestions ("Add lighting information.") - never fabricate content
- Fully deterministic: the same prompt always yields the identical report
- Read-only: existing Day 16-20 features remain untouched

### Architecture

- Day 16 `PromptHistoryService` remains the **single source of truth** for versions
- Day 21 `PromptQualityService` is a standalone, stateless analyzer with no store of its own
- The history-quality endpoint passes the stored prompt text into the analyzer - it never modifies history records, favorites, or tags
- No LLM, no network, no filesystem, no database - pure in-process text analysis

### Nine Dimensions

`subject`, `action`, `environment`, `camera`, `lighting`, `visual_style`, `color`, `composition`, `audio`

Each dimension reports `{"present": bool, "score": int}` with conservative keyword/phrase detection (case-insensitive, whitespace-normalized):

| Signals matched | present | score |
|-----------------|---------|-------|
| 0 | false | 0 (missing) |
| 1 | true | 40 (weak) |
| 2 | true | 70 |
| 3+ | true | 100 (strong) |

- `overall_score` = round-half-up of the mean of the 9 scores (0-100)
- `completeness_percentage` = round-half-up of (present dimensions / 9) x 100
- `missing_dimensions` = every dimension with `present: false` (dimension order)
- `suggestions` = `"Add <name> information."` for missing dimensions and `"Expand <name> information for better coverage."` for weak (score 40) dimensions, in dimension order

### Service

`backend/app/services/prompt_quality_service.py` - `PromptQualityService`

- `analyze_prompt(prompt)` returns `{"prompt": <original text>, "quality": {overall_score, completeness_percentage, dimensions, missing_dimensions, suggestions}}`
- Raises `ValueError` for non-string, empty, or whitespace-only prompts
- Echoes the original prompt back unchanged; only the internal matching view is normalized
- No state, no network, no filesystem access - safety verified by tests

### Endpoints

```
POST /api/videos/{stored_filename}/prompt/quality
GET  /api/videos/{stored_filename}/prompt/history/{version}/quality
```

- `POST` analyzes arbitrary prompt text from the JSON body `{"prompt": "..."}`
- `GET` analyzes the stored prompt of one history version (read-only, uses Day 16 `get_version`)
- The `/quality` sub-route is registered before the plain numeric `{version}` route, so history routes never collide

### Response Structure

```json
{
  "prompt": "<original text>",
  "quality": {
    "overall_score": 78,
    "completeness_percentage": 67,
    "dimensions": {
      "subject": {"present": true, "score": 100},
      "lighting": {"present": false, "score": 0}
    },
    "missing_dimensions": ["lighting", "audio"],
    "suggestions": ["Add lighting information.", "Add audio information."]
  }
}
```

### Validation

- Valid prompt returns HTTP 200
- Missing body, missing `prompt` field, empty or whitespace-only prompt returns HTTP 422
- Non-string `prompt` returns HTTP 422
- Nonexistent video returns HTTP 404; invalid extension returns HTTP 400
- Path traversal attempts return HTTP 404
- Nonexistent or deleted history version returns HTTP 404; version below 1 returns HTTP 422

### No-Fabrication / Read-Only Rules

- Neutral terminology only - never judges video content, only reports prompt coverage
- Never fabricates missing dimensions; missing information stays missing and is suggested
- Never modifies stored prompt text, history versions, favorites, or tags
- Suggestions correspond exactly to missing or weak dimensions
- No absolute paths, internal object names, or stack traces in responses

### Files Created/Modified

- `backend/app/services/prompt_quality_service.py` - `PromptQualityService`
- `backend/app/api/videos.py` - Added `/prompt/quality` (POST) and `/prompt/history/{version}/quality` (GET) endpoints
- `tests/test_prompt_quality_service.py` - 56 service tests
- `tests/test_prompt_quality_api.py` - 27 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 21 section appended")
