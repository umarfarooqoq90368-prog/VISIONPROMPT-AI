# -*- coding: utf-8 -*-
"""Append the Day 19 README section."""

SECTION = """

## Day 19 - Prompt Export & Packaging

Day 19 adds a read-only **Prompt Export & Packaging** layer. Any existing saved prompt-history version can be exported as JSON, Markdown, or plain TXT. The export represents the existing saved prompt/version exactly - it is a presentation format, never a new source of data.

### Purpose

- Export a saved prompt version for use outside the app (copy, share, archive)
- Three deterministic output formats: `json`, `markdown`, `txt`
- Read-only: export never modifies stored prompts, favorites, tags, or video files
- No files are written to disk - content is returned directly from the API

### Relationship with Day 16 History

- Day 16 `PromptHistoryService` remains the **single source of truth** for versions
- Export reads exactly one live version via `get_version` and renders it
- Deleted versions return HTTP 404 - export never resurfaces them
- No second version store is created; version numbering is untouched
- Empty metadata renders as `{}` in JSON and is omitted from Markdown/TXT

### Relationship with Day 17 Favorites & Tags

- `favorite` and `tags` come from Day 17 `PromptOrganizationService`
- Tags are rendered in their sorted, normalized Day 17 order
- Default metadata for a never-organized version: `favorite: false`, `tags: []`
- Export never changes favorite flags or tags

### Relationship with Day 18 Search

- Day 18 search finds versions; Day 19 exports one already-found version
- Both are read-only layers over Day 16 + Day 17 with no version store of their own
- Search results supply `version` values that feed directly into the export endpoint
- Neither layer fabricates video information

### Supported Formats

| Format | Media type | Extension | Description |
|--------|-----------|-----------|-------------|
| `json` | `application/json` | `.json` | Machine-readable, fixed key structure |
| `markdown` | `text/markdown` | `.md` | Human-readable Markdown document |
| `txt` | `text/plain` | `.txt` | Clean plain-text representation |

Format matching is explicit and case-sensitive. Unsupported formats are never silently accepted.

### JSON Structure

```json
{
  "video_filename": "video.mp4",
  "version": 3,
  "version_id": "video.mp4:3",
  "source": "refinement",
  "operation": "cinematic",
  "prompt": "...",
  "negative_prompt": "...",
  "created_at": "...",
  "metadata": {},
  "favorite": true,
  "tags": ["ai", "cinematic"]
}
```

- Valid JSON with a fixed, deterministic key order
- `tags` sorted exactly as Day 17 stores them
- No filesystem paths, no internal service information, no fabricated fields

### Markdown Export

A clean human-readable document: title `# VisionPrompt AI Prompt` followed by `## Video`, `## Version`, `## Source`, `## Operation`, `## Prompt`, `## Negative Prompt`, `## Tags` (bullet list), `## Favorite`, `## Created At`, and `## Metadata` (only when metadata exists).

- The saved prompt and negative prompt appear verbatim - never rewritten
- Empty operation/negative render as `(empty)`; no tags renders as `(none)`
- The `## Metadata` section is omitted entirely when metadata is empty - nothing is invented
- Output is byte-identical on every call

### TXT Export

Plain-text header (`# VISIONPROMPT AI PROMPT`, `Video`, `Version`, `Source`, `Operation`, `Favorite`, `Tags`, `Created At`) followed by `## PROMPT` and `## NEGATIVE PROMPT` blocks with the exact saved text, plus a `## METADATA` block only when metadata exists.

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/{version}/export?format=json
GET /api/videos/{stored_filename}/prompt/history/{version}/export?format=markdown
GET /api/videos/{stored_filename}/prompt/history/{version}/export?format=txt
```

- JSON format returns a valid JSON body; Markdown returns `text/markdown`; TXT returns `text/plain`
- Response includes a deterministic `Content-Disposition` filename, e.g. `visionprompt_video_v3.json` (sanitized from the stored video name, never raw user input)
- The `/export` sub-route is registered before the plain numeric `{version}` route, so history routes never collide

### Validation

- Nonexistent video returns HTTP 404
- Nonexistent version returns HTTP 404
- Deleted version returns HTTP 404
- Path traversal returns HTTP 404
- `version` below 1 returns HTTP 422
- Missing `format` returns HTTP 422
- Invalid format returns HTTP 422 (explicit list: `json`, `markdown`, `txt`)

### Deterministic Behavior

- The same stored version always produces byte-identical export content
- Fixed JSON key order; tags in fixed Day 17 sorted order
- Fixed `Content-Disposition` filename per format and version
- No timestamps are injected at export time - only the stored `created_at` is used

### Read-Only / No-Fabrication Rules

- Never modifies the stored prompt, negative prompt, source, operation, metadata, favorites, or tags
- Never creates or deletes history versions
- Never fabricates video information - exports contain only stored data
- Never returns deleted versions
- No absolute filesystem paths, no internal storage details in any format
- No files are written to disk

### Files Created/Modified

- `backend/app/services/prompt_export_service.py` - `PromptExportService`
- `backend/app/api/videos.py` - Added `/prompt/history/{version}/export` endpoint
- `tests/test_prompt_export_service.py` - 93 service tests
- `tests/test_prompt_export_api.py` - 36 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 19 section appended")
