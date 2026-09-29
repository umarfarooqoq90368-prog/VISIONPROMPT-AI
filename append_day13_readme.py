# -*- coding: utf-8 -*-
"""Append the Day 13 README section."""

SECTION = """

## Day 13 - Advanced Production Prompt Generation

Day 13 adds an **Advanced Production Prompt Generation** layer that converts the unified Video Intelligence from Day 12 into a detailed, production-ready AI video-generation prompt.

### Pipeline

```
Video
  -> Day 12 VideoIntelligenceService (visual, scenes, subjects, audio)
  -> AdvancedPromptService
  -> Production-ready Prompt (+ sections + negative prompt)
```

### Supported Styles

| Style | Wording Influence |
|-------|-------------------|
| `cinematic` (default) | cinematic composition, film-oriented presentation |
| `realistic` | naturalistic, realistic presentation |
| `commercial` | clean, polished, product-oriented presentation |

Style only influences wording. It never adds scene details that are not present in the intelligence data.

### Endpoint

```
POST /api/videos/{stored_filename}/advanced-prompt?style=cinematic
```

### Output Structure

```json
{
  "success": true,
  "message": "Advanced prompt generated successfully",
  "video_filename": "example.mp4",
  "style": "cinematic",
  "prompt": "...",
  "negative_prompt": "blurry, low quality, distorted anatomy, unwanted text, watermark",
  "sections": {
    "subject": "...",
    "action": "...",
    "environment": "...",
    "camera": "...",
    "lighting": "...",
    "visual_style": "...",
    "color": "...",
    "audio": "...",
    "composition": "..."
  }
}
```

### Strict No-Fabrication Behavior

- Only information present in the Day 12 intelligence output is used
- Never invents people, characters, objects, locations, dialogue, camera movement, lighting, colors, actions, sounds, or environment details
- Empty intelligence fields produce empty sections, omitted naturally from the prompt
- Scene timeline is incorporated chronologically when scenes are detected
- Audio/transcription text is included only when actually present
- Negative prompt is generic and quality-only (blurry, low quality, distorted anatomy, unwanted text, watermark)
- Output is deterministic: same intelligence + same style = same prompt
- Invalid style returns HTTP 400
- No absolute filesystem paths in any response

### Files Created/Modified

- `backend/app/services/advanced_prompt_service.py` - `AdvancedPromptService`
- `backend/app/api/videos.py` - Added `/advanced-prompt` endpoint
- `tests/test_advanced_prompt_service.py` - 32 service tests
- `tests/test_advanced_prompt_api.py` - 13 API tests
"""

with open("README.md", "a", encoding="utf-8") as f:
    f.write(SECTION)

print("README Day 13 section appended")
