# -*- coding: utf-8 -*-
"""Append the Day 22 README section."""

SECTION = """

## Day 22 - Quality-Guided Prompt Improvement

Day 22 adds **Quality-Guided Prompt Improvement**: a deterministic improvement layer that uses the Day 21 Prompt Quality Analyzer to detect missing/weak dimensions, generate neutral improvement instructions, and produce an improved prompt - without inventing any factual video information. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Close prompt coverage gaps identified by Day 21 with actionable guidance
- Never fabricate video facts (people, places, objects, colors, camera, lighting, audio)
- Keep the original prompt fully intact and verifiable
- Fully deterministic: same input -> identical output

### Architecture

- Day 21 `PromptQualityService` remains the single quality-analysis source; Day 22 **reuses** it and never duplicates its logic
- Day 22 `PromptImprovementService(quality_service)` is a stateless layer: validate -> analyze -> guide -> append
- Day 16 `PromptHistoryService` is untouched; improvement never writes to history, favorites, or tags
- No LLM, no network, no filesystem, no database - pure in-process string handling

### Improvement Flow

```
existing prompt -> PromptQualityService -> missing/weak dimensions
                -> deterministic guidance -> improved prompt
```

### Relationship With Day 21

- `quality_before` is exactly the Day 21 report of the source prompt
- Only dimensions Day 21 reports as **missing** (`present: false`) or **weak** (`score == 40`) receive guidance - never all nine blindly
- `quality_after` is exactly the Day 21 report of the improved prompt, so it reflects the added guidance text
- `guided_dimensions` / `guidance_added` explicitly mark which dimensions are present only because of placeholders - guidance is never presented as a video fact

### No-Fabrication Rule

The service only appends neutral, bracketed instructions such as `[Specify lighting characteristics if known]`. It never adds facts like "a beautiful woman", "a sunset", "cinematic rain", "a luxury car", or "dramatic music" unless those facts already exist in the source prompt. Every guidance item is an instruction ending in `if known`, not a claim about the video.

### Neutral Guidance Placeholders

| Dimension | Guidance (added only when missing/weak) |
|-----------|------------------------------------------|
| subject | `[Clarify the main subject and relevant visual characteristics if known]` |
| action | `[Clarify the subject's action or movement if known]` |
| environment | `[Specify the environment or setting if known]` |
| camera | `[Specify shot type, perspective, framing, or camera movement if known]` |
| lighting | `[Specify lighting characteristics if known]` |
| visual_style | `[Specify the visual style or rendering characteristics if known]` |
| color | `[Specify dominant colors or color treatment if known]` |
| composition | `[Specify framing, subject placement, depth, or composition if known]` |
| audio | `[Specify dialogue, ambience, music, or sound effects if known]` |

### Improved Prompt Format

The source prompt is preserved byte-for-byte, then guidance is appended in Day 21 dimension order (deterministic, no duplicates):

```
A man walks through a city street.

Enhancement Guidance:
[Clarify the main subject and relevant visual characteristics if known]
[Clarify the subject's action or movement if known]
[Specify shot type, perspective, framing, or camera movement if known]
[Specify lighting characteristics if known]
[Specify the visual style or rendering characteristics if known]
[Specify dominant colors or color treatment if known]
[Specify framing, subject placement, depth, or composition if known]
[Specify dialogue, ambience, music, or sound effects if known]
```

(Environment is absent from the list because Day 21 detects `city` and `street` in the source.) When no dimension is missing or weak, `improved_prompt` equals `source_prompt` and `improvement_applied` is `false`.

### Service

`backend/app/services/prompt_improvement_service.py` - `PromptImprovementService`

- `improve_prompt(prompt)` returns `source_prompt`, `improved_prompt`, `quality_before`, `quality_after`, `improvement_applied`, `improvements` (`[{dimension, reason, guidance}]` with `reason` in `missing`/`weak`), `preserved_information`, `guidance_added`, and `guided_dimensions`
- Raises `ValueError` for non-string, empty, or whitespace-only prompts

### Endpoints

```
POST /api/videos/{stored_filename}/prompt/improve
GET  /api/videos/{stored_filename}/prompt/history/{version}/improve
```

- `POST` improves arbitrary prompt text from the JSON body `{"prompt": "..."}`; response adds `video_filename`; does not require history and never saves the result into history
- `GET` retrieves one history version via Day 16, improves its prompt, and returns the same structure - read-only, never modifies history
- The `/improve` sub-route is registered before the plain numeric `{version}` route, so history routes never collide

### Validation

- Valid prompt returns HTTP 200
- Missing body, missing `prompt` field, empty or whitespace-only prompt, or non-string prompt returns HTTP 422
- Nonexistent video returns HTTP 404; invalid extension returns HTTP 400
- Path traversal attempts return HTTP 404
- Nonexistent or deleted history version returns HTTP 404; version below 1 returns HTTP 422

### Determinism

- Repeated calls with the same prompt produce exactly equivalent results
- Case-insensitive behavior matches Day 21 (guidance suffix is identical regardless of source casing)
- No random values, timestamps, or dates inside the generated prompt
- No external API calls

### Tests

- `tests/test_prompt_improvement_service.py` - 73 service tests (validation, structure, Day 21 mapping, format, no-fabrication, quality-after, determinism, preservation, safety)
- `tests/test_prompt_improvement_api.py` - 33 API tests (200/422/404/400 validation, response schema, history endpoint, no-auto-save, Day 16-21 regressions)

### Limitations

- Guidance is generic per-dimension instruction text; it does not understand video content
- `quality_after` measures coverage of the improved *text* (Day 21 signal matching); the `guided_dimensions` field identifies which presence flags come from placeholders rather than original facts
- Improvement is a single pass: placeholders are not recursively re-improved
- Results are never persisted; saving an improved prompt into history remains an explicit user action via the Day 16 history endpoint

### Files Created/Modified

- `backend/app/services/prompt_improvement_service.py` - `PromptImprovementService`
- `backend/app/api/videos.py` - Added `/prompt/improve` (POST) and `/prompt/history/{version}/improve` (GET) endpoints
- `tests/test_prompt_improvement_service.py` - 73 service tests
- `tests/test_prompt_improvement_api.py` - 33 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 22 section appended")
