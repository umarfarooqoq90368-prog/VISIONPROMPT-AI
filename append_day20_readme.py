# -*- coding: utf-8 -*-
"""Append the Day 20 README section."""

SECTION = """

## Day 20 - Prompt Package Generation

Day 20 adds **Prompt Package Generation**: a complete downloadable ZIP production package for any selected prompt-history version. The package reuses the existing Day 19 export functionality instead of duplicating export-generation logic.

### Purpose

- One click produces every format a user needs for a chosen prompt version
- Read-only packaging over existing Day 16-19 data - no new sources of truth
- Deterministic: the same version always produces a byte-identical ZIP
- No files are written to disk - the ZIP is returned directly from the API

### Architecture

- Day 16 `PromptHistoryService` remains the **single source of truth** for versions
- Day 17 `PromptOrganizationService` supplies `favorite` and `tags` metadata
- Day 19 `PromptExportService` renders `prompt.json`, `prompt.md`, and `prompt.txt`
- Day 20 `PromptPackageService(history, organization, export)` only assembles those outputs plus `package_metadata.json` into a ZIP
- No second version store; deleted versions can never be packaged

### Service

`backend/app/services/prompt_package_service.py` - `PromptPackageService`

- `create_package(stored_filename, version)` verifies the version exists (Day 16 raises for invalid/nonexistent/deleted versions), reads Day 17 organization metadata, reuses Day 19 export for the three prompt files, and returns the ZIP bytes plus `media_type`, safe `filename`, `files`, and `metadata`
- Never modifies the history record, favorites, or tags

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/{version}/package
```

- Returns the ZIP as `application/zip` with a deterministic `Content-Disposition` filename: `visionprompt_video_v<version>.zip`
- The download filename never exposes the storage UUID or any path
- The `/package` sub-route is registered before the plain numeric `{version}` route, so history routes never collide

### ZIP Contents

Exactly four files - no extras, no duplicates, no absolute paths, no `../` traversal, UTF-8 content, all entries with a fixed timestamp for determinism:

| File | Source |
|------|--------|
| `prompt.json` | Day 19 JSON export (unchanged bytes) |
| `prompt.md` | Day 19 Markdown export (unchanged bytes) |
| `prompt.txt` | Day 19 TXT export (unchanged bytes) |
| `package_metadata.json` | Safe summary written by the package service |

### Metadata Safety

`package_metadata.json` contains only these safe fields:

```json
{
  "video_filename": "video.mp4",
  "version": 3,
  "version_id": "video.mp4:3",
  "source": "refinement",
  "operation": "cinematic",
  "created_at": "...",
  "favorite": true,
  "tags": ["ai", "cinematic"]
}
```

Never exposed: absolute filesystem paths, internal storage paths, Python object representations, secrets, environment variables, stack traces, or private implementation details.

### Validation

- Valid version returns HTTP 200 (`application/zip`)
- Nonexistent video returns HTTP 404
- Nonexistent version returns HTTP 404
- Deleted version returns HTTP 404
- Version created after a deletion follows Day 16 numbering and is packagable
- `version` below 1 returns HTTP 422
- Path traversal attempts return HTTP 404
- Multiple videos remain fully isolated

### No-Fabrication / Read-Only Rules

- Never modifies stored prompt text, metadata, favorites, or tags
- Never fabricates video information - package files contain only stored data
- Never packages deleted versions
- No absolute paths or internal service details anywhere in the ZIP
- Repeated generation of the same version is byte-identical
- ZIP entries use fixed timestamps and a fixed filename order

### Files Created/Modified

- `backend/app/services/prompt_package_service.py` - `PromptPackageService`
- `backend/app/api/videos.py` - Added `/prompt/history/{version}/package` endpoint
- `tests/test_prompt_package_service.py` - 68 service tests
- `tests/test_prompt_package_api.py` - 33 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 20 section appended")
