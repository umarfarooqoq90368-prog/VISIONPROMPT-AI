# -*- coding: utf-8 -*-
"""Append the Day 24 README section."""

SECTION = """

## Day 24 - Production Readiness Validator

Day 24 adds a **Production Readiness Validator**: a deterministic, read-only validation layer that answers one question about a prompt - *"does this prompt contain enough structured information to be considered ready for production-oriented AI video prompting?"* It reports structural coverage only: it never claims a prompt will produce a good video, never predicts model output, and never ranks one prompt against another. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Give users a neutral checklist of which prompt dimensions are covered
- Distinguish `ready` from `needs_attention` using deterministic rules
- Surface missing/weak coverage with actionable, non-fabricating suggestions
- Never modify history, favorites, tags, or the prompt itself

### Relationship With Day 21

- Day 21 `PromptQualityService` remains the single detection/scoring source; Day 24 **reuses** `analyze_prompt` and never duplicates dimension detection or scoring
- Every checklist `score` is the Day 21 score echoed byte-for-byte - Day 21 scoring is never altered
- Day 24 only maps Day 21 scores onto readiness statuses and applies the required/supporting structural rule
- Case-insensitivity and normalization therefore match Day 21 exactly

### Required vs Supporting Dimensions

| Group | Dimensions |
|-------|------------|
| Required (core) | `subject`, `action`, `environment`, `camera`, `lighting`, `visual_style`, `composition` |
| Supporting | `color`, `audio` |

This split is structural, not a quality ranking. Both groups are always reported in the checklist, in Day 21 dimension order.

### Readiness Statuses

Each Day 21 score maps deterministically to a checklist status:

| Day 21 score | Status |
|--------------|--------|
| 100 | `present` |
| 70 | `present` |
| 40 | `weak` |
| 0 | `missing` |

Overall readiness:

- **`ready`** - every required dimension has status `present`
- **`needs_attention`** - one or more required dimensions are `weak` or `missing`

Supporting dimensions never block `ready`: a prompt with all 7 required dimensions present but `color`/`audio` missing is still `ready`.

### Coverage Calculation

```json
{
  "required_total": 7,
  "required_present": 5,
  "required_missing": 1,
  "required_weak": 1,
  "required_coverage_percentage": 71,
  "supporting_total": 2,
  "supporting_present": 0,
  "supporting_missing": 2,
  "supporting_weak": 0,
  "supporting_coverage_percentage": 0
}
```

Formula: `required_coverage_percentage = round(required_present / required_total * 100)` (same for supporting). Only status `present` counts as present - **weak dimensions (score 40) do not count** as fully present, so coverage can drop even when nothing is fully missing. The value is always an integer between 0 and 100. `present + missing + weak` always equals the group total. No separate numerical "quality score" is invented; the report returns coverage counts only.

### Checklist

One entry per Day 21 dimension, in Day 21 order:

```json
{
  "dimension": "camera",
  "status": "missing",
  "present": false,
  "score": 0,
  "message": "Camera information is not detected."
}
```

`present` here means status is `present` (score 70 or 100); a weak dimension shows `present: false` with `score: 40`, consistent with coverage counting.

### Validation Messages

Deterministic, dimension-specific templates (label capitalized, `visual_style` renders as `Visual style`):

- present: `<Label> information detected.` (e.g. `Subject information detected.`)
- weak: `<Label> information is present but may need more detail.`
- missing: `<Label> information is not detected.` (e.g. `Camera information is not detected.`)

### Suggestions

Neutral, actionable, and exactly matched to weak/missing dimensions (Day 21 order; present dimensions get none):

- missing: `Specify camera information if known.`
- weak: `Expand camera information if known.`

Every suggestion ends in `if known` - no suggestion ever asserts a fact about the video.

### Service

`backend/app/services/prompt_readiness_service.py` - `PromptReadinessService(quality_service)`

- `validate_prompt(prompt)` returns `prompt` (echoed byte-for-byte) and `readiness` with: `status`, `required_dimensions`, `supporting_dimensions`, `checklist`, `coverage`, `missing_dimensions`, `weak_dimensions`, `suggestions`
- Raises `ValueError` for non-string, empty, or whitespace-only prompts (same messages as Day 21)

### Endpoints

```
POST /api/videos/{stored_filename}/prompt/readiness
GET  /api/videos/{stored_filename}/prompt/history/{version}/readiness
```

- `POST` validates arbitrary prompt text from the JSON body `{"prompt": "..."}`; response adds `video_filename`; does not require history and never saves the report
- `GET` retrieves one history version via Day 16, validates its prompt, and returns the identical report - read-only, never modifies history
- The `/readiness` sub-route is registered before the plain numeric `{version}` route, so history routes never collide

### Validation

- Valid prompt returns HTTP 200
- Missing body, missing `prompt` field, empty or whitespace-only prompt, or non-string prompt returns HTTP 422
- Nonexistent video returns HTTP 404; invalid extension returns HTTP 400
- Path traversal attempts return HTTP 404
- Nonexistent or deleted history version returns HTTP 404; version below 1 returns HTTP 422

### Determinism and No-Fabrication

- Repeated calls with the same prompt produce exactly equivalent reports; no random values, timestamps, or dates
- The original prompt is echoed unchanged - readiness never rewrites, expands, or judges the wording
- No facts are invented: statuses, messages, and suggestions are generic per-dimension text only
- No filesystem paths, no internal objects, no secrets, no environment variables in any response
- Readiness reports are never persisted (single Day 16 store remains the only version store)

### Limitations

- Structural coverage only: it does not evaluate cinematography, aesthetics, or actual video content
- Signal matching is Day 21's conservative regex set - it can neither confirm nor deny real-world accuracy of the prompt's claims
- A `ready` status means required dimensions are covered by text signals, not that any model will produce a satisfactory video
- Supporting dimensions never affect status, only appear in coverage/checklist/suggestions

### Tests

- `tests/test_prompt_readiness_service.py` - 116 service tests (validation, structure, score-to-status mapping, ready/needs-attention rules, supporting exemption, coverage math/rounding/bounds, messages, suggestions, determinism, read-only, no-fabrication, no-ranking-language)
- `tests/test_prompt_readiness_api.py` - 42 API tests (200/422/404/400 validation, response schema, Day 21 cross-checks, history endpoint, determinism, route collision, Day 16-23 regressions, leak scans)

### Files Created/Modified

- `backend/app/services/prompt_readiness_service.py` - `PromptReadinessService`
- `backend/app/api/videos.py` - Added `/prompt/readiness` (POST) and `/prompt/history/{version}/readiness` (GET) endpoints, `PromptReadinessRequest`, and service instance
- `tests/test_prompt_readiness_service.py` - 116 service tests
- `tests/test_prompt_readiness_api.py` - 42 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 24 section appended")
