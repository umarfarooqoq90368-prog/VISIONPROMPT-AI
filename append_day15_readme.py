# -*- coding: utf-8 -*-
"""Append the Day 15 README section."""

SECTION = """

## Day 15 - Prompt Templates & Custom Instructions

Day 15 adds a **Prompt Template and Custom Instruction** layer on top of Day 13 Advanced Prompt + Day 14 Prompt Refinement. Users can take an existing generated prompt and apply a predefined production template or a safe user-provided custom instruction.

### Pipeline

```
Video
  -> Day 12 VideoIntelligenceService
  -> Day 13 AdvancedPromptService (source prompt)
  -> PromptTemplateService
  -> Templated Prompt
```

### Supported Templates

| Template | Presentation |
|----------|-------------|
| `cinematic_story` | Narrative ordering with cinematic framing (subject, action, environment first) |
| `ai_video` | Compact comma-joined tags optimized for AI video generators |
| `commercial_ad` | Style/composition-first ordering for commercial presentation |
| `social_media` | Subject/action-first ordering for short-form social content |
| `documentary` | Environment/subject-first ordering for documentary narration |

Each template reorganizes the existing factual information. None invent new video details.

### Custom Instructions

Instructions are pattern-matched into safe structural changes only:

- `make it concise` - drops labels, compacts the prompt
- `focus on camera movement` / `emphasize lighting` - reorders the named section to the front
- `make the prompt suitable for an AI video generator` - compact tag presentation

Unsupported instructions (for example `add a dragon`) are echoed back in the `custom_instruction` field but are never copied into the prompt, so they cannot introduce unsupported factual information.

### Endpoint

```
POST /api/videos/{stored_filename}/prompt/template
```

### Request Structure

```json
{
  "template": "cinematic_story",
  "custom_instruction": ""
}
```

### Response Structure

```json
{
  "success": true,
  "message": "Prompt template applied successfully",
  "video_filename": "example.mp4",
  "template": "cinematic_story",
  "source_prompt": "...",
  "custom_instruction": "",
  "prompt": "...",
  "negative_prompt": "blurry, low quality, distorted anatomy, unwanted text, watermark",
  "preserved_information": true
}
```

### Preservation / No-Fabrication Behavior

- Templates only reorganize or rephrase information already present in the source prompt
- `preserved_information` is a verified token-containment check: no source content is lost
- Never invents characters, objects, locations, actions, dialogue, camera movement, lighting, colors, sounds, brands, or products
- Custom instruction text is never inserted into the prompt
- Empty source is handled safely (falls back to Day 13 generation from intelligence when available)
- The generic Day 13 negative prompt is preserved by default
- Deterministic: same source + same template + same instruction = same output
- Invalid template returns HTTP 400; missing template returns HTTP 422
- No absolute filesystem paths in any response

### Files Created/Modified

- `backend/app/services/prompt_template_service.py` - `PromptTemplateService`
- `backend/app/api/videos.py` - Added `/prompt/template` endpoint
- `tests/test_prompt_template_service.py` - 89 service tests
- `tests/test_prompt_template_api.py` - 17 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 15 section appended")
