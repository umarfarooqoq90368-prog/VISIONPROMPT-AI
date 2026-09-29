# -*- coding: utf-8 -*-
"""Append the Day 14 README section."""

SECTION = """

## Day 14 - Prompt Editor & Prompt Refinement

Day 14 adds a **Prompt Refinement** layer on top of Day 13 Advanced Prompt Generation. Users can take the generated production prompt and receive a refined version while preserving the factual information extracted from the video.

### Pipeline

```
Video
  -> Day 12 VideoIntelligenceService
  -> Day 13 AdvancedPromptService (source prompt)
  -> PromptRefinementService
  -> Refined Prompt
```

### Supported Operations

| Operation | Behavior |
|-----------|----------|
| `refine` | Improves clarity, structure, and production-readiness without adding unsupported facts |
| `shorten` | Produces a more concise version while preserving all factual content |
| `expand` | Adds structural detail using only information already present in the source |
| `cinematic` | Applies cinematic wording without inventing visual details |
| `realistic` | Applies realistic wording without inventing visual details |
| `commercial` | Applies polished commercial wording without inventing products, brands, locations, or objects |

### Endpoint

```
POST /api/videos/{stored_filename}/prompt/refine
```

### Request Format

```json
{
  "operation": "refine"
}
```

### Response Structure

```json
{
  "success": true,
  "message": "Prompt refinement completed successfully",
  "video_filename": "example.mp4",
  "operation": "refine",
  "source_prompt": "...",
  "refined_prompt": "...",
  "negative_prompt": "blurry, low quality, distorted anatomy, unwanted text, watermark",
  "preserved_information": true
}
```

### Preservation / No-Fabrication Behavior

- The service reuses the Day 13 generated prompt from the Day 12 intelligence flow (no second analysis pipeline)
- Refinement operations only restructure wording: facts from the source prompt survive every operation
- `preserved_information` is a verified flag: token-level comparison confirms no source content was lost
- Never fabricates characters, objects, locations, actions, camera movement, lighting, colors, dialogue, or sounds
- Style operations only rephrase style wording (they never add scene details)
- The negative prompt is carried through from Day 13 and stays generic and quality-only
- Output is deterministic: same source + same operation = same result
- Empty input is handled safely; invalid operations return HTTP 400
- No absolute filesystem paths in any response

### Files Created/Modified

- `backend/app/services/prompt_refinement_service.py` - `PromptRefinementService`
- `backend/app/api/videos.py` - Added `/prompt/refine` endpoint
- `tests/test_prompt_refinement_service.py` - 69 service tests
- `tests/test_prompt_refinement_api.py` - 19 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 14 section appended")
