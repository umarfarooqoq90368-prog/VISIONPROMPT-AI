# -*- coding: utf-8 -*-
"""Append the Day 17 README section."""

SECTION = """

## Day 17 - Prompt Favorites & Tags

Day 17 adds a deterministic **Prompt Favorites & Tags** organization layer on top of Day 16 Prompt History & Versioning. Users can mark saved prompt versions as favorites and attach explicit tags to them, then list favorites or filter versions by tag.

### Relationship with Day 16

- Day 17 does **not** create a second prompt/version store
- Favorites and tags are metadata attached to existing Day 16 version records only
- `PromptOrganizationService` wraps the existing `PromptHistoryService`
- Version creation, numbering, prompt storage, and comparison all remain Day 16 behavior
- Nothing is auto-favorited or auto-tagged; every operation is an explicit user action

### Favorites

- `favorite_version` marks an existing version as favorite (idempotent - favoriting twice creates no duplicates)
- `unfavorite_version` removes it (also idempotent; unfavorite without a prior favorite is harmless)
- Nonexistent version raises a service error (API returns HTTP 404)

### Tags

- `add_tags` merges new tags into the version's tag set
- `remove_tags` removes only the requested tags; removing a missing tag is harmless
- Tags never modify the actual prompt text

**Tag normalization** (deterministic):

- Trim surrounding whitespace
- Lowercase
- Empty and whitespace-only tags are ignored
- Duplicate tags are removed
- Result is sorted alphabetically
- Maximum 50 characters per tag (longer tags return HTTP 422)

Example: `[" Cinematic ", "AI", "cinematic", ""]` becomes `["ai", "cinematic"]`.

### Exact Tag Filtering

- `list_by_tag` performs an **exact normalized tag match** - no substring matching
- Requested tag is normalized first (`"  Cinematic "` matches `cinematic`)
- Missing or empty tag returns `[]`
- Results are sorted by version ascending

### List Favorites

- `list_favorites` returns only favorited versions, sorted by version ascending
- Returns `[]` when there are no favorites
- Only existing versions can appear

### Organization Metadata

`get_organization` returns:

```json
{
  "video_filename": "...",
  "version": 1,
  "favorite": false,
  "tags": []
}
```

No internal storage structures or absolute filesystem paths are exposed.

### Deletion Cleanup Behavior

When Day 16 deletes a version:

- Its organization metadata no longer appears in favorites or tag results
- `get_organization` for the deleted version returns HTTP 404
- Remaining versions keep their organization metadata intact
- Day 16 deletion behavior itself is unchanged (no renumbering)
- If a later version is created, its number follows Day 16's existing numbering (for example versions `1,2,3`, delete `2` -> `1,3`, next created -> `4`)

### Multi-Video Isolation

Organization metadata is isolated per video: favoriting or tagging video A's version 1 never affects video B's version 1.

### API Endpoints

```
POST   /api/videos/{stored_filename}/prompt/history/{version}/favorite
DELETE /api/videos/{stored_filename}/prompt/history/{version}/favorite
POST   /api/videos/{stored_filename}/prompt/history/{version}/tags
DELETE /api/videos/{stored_filename}/prompt/history/{version}/tags
GET    /api/videos/{stored_filename}/prompt/history/{version}/organization
GET    /api/videos/{stored_filename}/prompt/history/favorites
GET    /api/videos/{stored_filename}/prompt/history/tag/{tag}
```

The static routes `/favorites` and `/tag/{tag}` are registered before the numeric `/{version}` route so they can never be captured by it.

### Request / Response Structures

Add tags:

```json
POST /api/videos/{stored_filename}/prompt/history/{version}/tags
{ "tags": ["ai", "cinematic"] }
->
{ "video_filename": "example.mp4", "version": 1, "tags": ["ai", "cinematic"] }
```

Remove tags (same request shape; returns the remaining sorted tags):

```json
DELETE /api/videos/{stored_filename}/prompt/history/{version}/tags
{ "tags": ["ai"] }
->
{ "video_filename": "example.mp4", "version": 1, "tags": ["cinematic"] }
```

Favorite / unfavorite:

```json
{ "video_filename": "example.mp4", "version": 1, "favorite": true }
{ "video_filename": "example.mp4", "version": 1, "favorite": false }
```

Favorites list:

```json
{
  "video_filename": "example.mp4",
  "favorites": [
    { "version": 1, "favorite": true, "tags": ["ai", "cinematic"] }
  ]
}
```

Tag filter:

```json
{
  "video_filename": "example.mp4",
  "tag": "cinematic",
  "versions": [
    { "version": 1, "favorite": true, "tags": ["ai", "cinematic"] }
  ]
}
```

### Validation

- `version` must be a positive integer; invalid version returns HTTP 422
- Nonexistent video returns HTTP 404; nonexistent version returns HTTP 404
- Tags request must contain a valid list; invalid payloads or non-string items return HTTP 422
- Empty / whitespace-only tags are simply ignored
- Tags longer than 50 characters return HTTP 422
- Path traversal protection remains intact (rejected as HTTP 400/404)
- No absolute filesystem paths in any response

### No-Fabrication Rules

- Tags are explicit user-provided metadata only
- Tags are never inferred from objects, characters, locations, actions, camera, lighting, colors, brands, audio, or dialogue
- Prompt text and negative prompt are never modified by favorites/tags
- Organization responses contain only `video_filename`, `version`, `favorite`, and `tags`
- Deterministic: the same operations always produce the same results

### Files Created/Modified

- `backend/app/services/prompt_organization_service.py` - `PromptOrganizationService`
- `backend/app/api/videos.py` - Added seven favorites/tags endpoints
- `tests/test_prompt_organization_service.py` - 57 service tests
- `tests/test_prompt_organization_api.py` - 28 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 17 section appended")
