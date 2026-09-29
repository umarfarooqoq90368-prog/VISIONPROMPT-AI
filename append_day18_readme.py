# -*- coding: utf-8 -*-
"""Append the Day 18 README section."""

SECTION = """

## Day 18 - Prompt Search & Filtering

Day 18 adds a unified **Prompt Search & Filtering** layer over the existing prompt history. Users can search and filter saved prompt versions by text, source, operation, favorite status, tag, version range, or any combination of these.

### Relationship with Day 16 History

- Day 16 `PromptHistoryService` remains the **single source of truth** for versions
- Day 18 does not create a second version store and never duplicates prompt history
- `PromptSearchService` only reads from Day 16; deleted versions can never appear in results
- Version numbering behavior is unchanged

### Relationship with Day 17 Favorites & Tags

- The search layer reads Day 17 `PromptOrganizationService` metadata for the `favorite` flag and `tags` of each result
- Search never modifies favorites, tags, or stored prompt text
- Favorite and tag filters use the same normalization and exact-match rules as Day 17

### Supported Filters

| Filter | Behavior |
|--------|----------|
| `query` | Case-insensitive substring search inside the saved `prompt`; empty/`None` = no text filter |
| `source` | Exact match: `advanced_prompt`, `refinement`, `template`, `custom` |
| `operation` | Exact match against the saved `operation` |
| `favorite` | `true` = only favorites, `false` = only non-favorites, omitted = both |
| `tag` | Normalized (trim + lowercase) then **exact** tag match - never substring |
| `min_version` | Inclusive lower version bound |
| `max_version` | Inclusive upper version bound |
| `sort` | `version_asc` (default), `version_desc`, `created_at_asc`, `created_at_desc` |

### Combined Filtering

All supplied filters are **AND-combined**. Example:

```
GET /api/videos/video.mp4/prompt/search?query=cinematic&source=refinement&favorite=true&tag=ai
```

A version must satisfy every supplied condition to be returned.

### Result Structure

Each result contains the existing Day 16 version record plus Day 17 organization metadata - the stored record itself is never changed:

```json
{
  "version_id": "...",
  "video_filename": "...",
  "version": 1,
  "source": "refinement",
  "operation": "shorten",
  "prompt": "...",
  "negative_prompt": "...",
  "created_at": "...",
  "metadata": {},
  "favorite": true,
  "tags": ["ai", "cinematic"]
}
```

### Ordering

- Default ordering is `version` ascending - deterministic on every call
- Optional `sort` parameter: `version_asc`, `version_desc`, `created_at_asc`, `created_at_desc`
- Invalid sort values return HTTP 422
- Day 16 version numbering behavior is untouched

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/search
```

Query parameters: `query`, `source`, `operation`, `favorite`, `tag`, `min_version`, `max_version`, `sort`.

Response:

```json
{
  "video_filename": "example.mp4",
  "filters": {
    "query": "cinematic",
    "source": "refinement",
    "operation": null,
    "favorite": true,
    "tag": "ai",
    "min_version": 2,
    "max_version": 5
  },
  "count": 2,
  "results": [ ... ]
}
```

### Validation

- Nonexistent video returns HTTP 404; path traversal is rejected (HTTP 400/404)
- Invalid source returns HTTP 422
- Invalid boolean query parameter returns HTTP 422 (standard FastAPI behavior)
- `min_version` / `max_version` below 1 return HTTP 422
- `min_version > max_version` returns HTTP 422
- Invalid `sort` returns HTTP 422
- Empty `query` behaves as no text filter
- Whitespace-only `tag` behaves as no tag filter (Day 17 normalization)
- Tag matching is exact; tags longer than 50 characters return HTTP 422

### Security / No-Fabrication Rules

- Read-only layer: search never modifies stored prompt text, favorites, tags, or video files
- Never fabricates video information; results contain only stored history and organization data
- Never returns deleted Day 16 versions
- No absolute filesystem paths in any response
- Multi-video isolation: a search only ever sees the requested video's versions
- Deterministic: identical queries always return identical results

### Files Created/Modified

- `backend/app/services/prompt_search_service.py` - `PromptSearchService`
- `backend/app/api/videos.py` - Added `/prompt/search` endpoint
- `tests/test_prompt_search_service.py` - 61 service tests
- `tests/test_prompt_search_api.py` - 34 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 18 section appended")
