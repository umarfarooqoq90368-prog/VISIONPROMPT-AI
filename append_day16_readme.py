# -*- coding: utf-8 -*-
"""Append the Day 16 README section."""

SECTION = """

## Day 16 - Prompt History & Versioning

Day 16 adds a deterministic **Prompt History & Versioning** layer for generated prompts. A video can hold multiple saved prompt versions, and the API can save, list, retrieve, compare, and delete them. No database is introduced: storage sits behind a service-level abstraction that can later be replaced by PostgreSQL/SQLite without changing the API contract.

### Pipeline

```
Video
  -> Day 12 VideoIntelligenceService
  -> Day 13 AdvancedPromptService / Day 14 PromptRefinementService / Day 15 PromptTemplateService
  -> PromptHistoryService (optional save, never automatic)
  -> Saved Version 1, 2, 3, ...
```

Nothing is saved automatically. Day 13/14/15 outputs can be passed into history creation through the optional helpers `save_advanced_prompt()`, `save_refinement()`, and `save_template()`.

### Storage Abstraction

- In-memory, service-level storage (`backend/app/services/prompt_history_service.py`)
- Safe to swap for PostgreSQL/SQLite later without changing the API contract
- Internal storage structures are never exposed; every response is a copied record
- No absolute filesystem paths in any response
- Uploaded video, frame, and audio files are never modified

### Version Creation & Sequential Numbering

- First version for a video = `1`, next = `2`, then `3`, etc.
- Version numbers are sequential **per video**; numbering is independent between videos
- `version_id` is unique (derived from video filename + version number)
- `prompt` and `negative_prompt` are preserved exactly as submitted
- `created_at` uses a UTC ISO-8601 timestamp
- `metadata` is stored verbatim and never augmented with invented video information

### List / Get / Delete

- `list_versions` returns all versions ordered by ascending version number, or `[]` when empty
- `get_version` returns the exact saved version
- `delete_version` deletes only that version

**Versions are NOT renumbered after deletion.** Example: versions `1, 2, 3`, delete `2`, remaining = `1, 3`. The next newly created version is `4`, not `2`.

### Token-Based Version Comparison

`compare_versions` performs a deterministic token-based comparison (no external diff library):

- `added_tokens` - tokens present in version B but not in version A
- `removed_tokens` - tokens present in version A but not in version B
- `common_tokens` - tokens present in both, in first-appearance order
- `changed` - `true` when any token was added or removed

### Supported Sources

| Source | Origin |
|--------|--------|
| `advanced_prompt` | Day 13 Advanced Prompt output |
| `refinement` | Day 14 Prompt Refinement output |
| `template` | Day 15 Prompt Template output |
| `custom` | Manually saved prompt (default) |

### API Endpoints

```
POST   /api/videos/{stored_filename}/prompt/history
GET    /api/videos/{stored_filename}/prompt/history
GET    /api/videos/{stored_filename}/prompt/history/{version}
DELETE /api/videos/{stored_filename}/prompt/history/{version}
GET    /api/videos/{stored_filename}/prompt/history/compare/{version_a}/{version_b}
```

The static `compare` route is registered before the numeric `{version}` route so it is never captured by the version lookup.

### Request Structure (Create)

```json
{
  "prompt": "...",
  "negative_prompt": "...",
  "source": "custom",
  "operation": "",
  "metadata": {}
}
```

### Response Structures

Saved version object (create / get):

```json
{
  "version_id": "example.mp4:1",
  "video_filename": "example.mp4",
  "version": 1,
  "source": "custom",
  "operation": "",
  "prompt": "...",
  "negative_prompt": "...",
  "created_at": "2026-09-28T12:00:00+00:00",
  "metadata": {}
}
```

List:

```json
{
  "video_filename": "example.mp4",
  "versions": [ ... ]
}
```

Delete:

```json
{
  "deleted": true,
  "video_filename": "example.mp4",
  "version": 1
}
```

Compare:

```json
{
  "video_filename": "example.mp4",
  "version_a": 1,
  "version_b": 2,
  "prompt_a": "...",
  "prompt_b": "...",
  "negative_prompt_a": "...",
  "negative_prompt_b": "...",
  "added_tokens": [],
  "removed_tokens": [],
  "common_tokens": [],
  "changed": true
}
```

### Validation

- `prompt` must not be empty (empty, whitespace, or missing body returns HTTP 422)
- `source` must be one of `advanced_prompt`, `refinement`, `template`, `custom` (invalid returns HTTP 422)
- `operation` may be an empty string or any string
- `version` / `version_a` / `version_b` must be positive integers (invalid returns HTTP 422)
- Nonexistent version returns HTTP 404; nonexistent video returns HTTP 404
- Path traversal protection remains intact (rejected as HTTP 400/404)

### Preservation / No-Fabrication Behavior

- Prompt text and negative prompt are preserved exactly
- Metadata is stored verbatim; history never invents characters, objects, locations, actions, dialogue, camera movement, lighting, colors, sounds, brands, or products
- Comparison only reports token differences between two saved prompts
- Deterministic: same inputs produce the same records and comparison results (only `version_id`/`created_at` vary)
- No absolute filesystem paths in any response

### Files Created/Modified

- `backend/app/services/prompt_history_service.py` - `PromptHistoryService`
- `backend/app/api/videos.py` - Added five `/prompt/history` endpoints
- `tests/test_prompt_history_service.py` - 64 service tests
- `tests/test_prompt_history_api.py` - 24 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 16 section appended")
