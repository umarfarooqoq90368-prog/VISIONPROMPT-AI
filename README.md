# VisionPrompt AI

![VisionPrompt AI](https://img.shields.io/badge/version-0.1.0-blue)

## What is VisionPrompt AI?

VisionPrompt AI is a tool that turns any video into a production-ready AI prompt. It analyzes video content — scenes, characters, actions, camera movement, lighting, environment, and audio — and generates detailed prompts for AI video generation.

## Current Project Status

This is the foundational backend for VisionPrompt AI. The current version provides:

- FastAPI server with health check and root endpoints
- Video upload API (`POST /api/videos/upload`)
- Automatic Swagger/OpenAPI documentation
- Environment-based configuration
- Clean project structure ready for future features

**AI model integration, scene detection, frame extraction, and prompt generation are not yet implemented.**

## Setup

### Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

- **Windows:**
  ```bash
  venv\Scripts\activate
  ```
- **macOS/Linux:**
  ```bash
  source venv/bin/activate
  ```

### Install Requirements

```bash
cd backend
pip install -r requirements.txt
```

### Run the FastAPI Server

```bash
cd backend
uvicorn app.main:app --reload
```

### Open Swagger Documentation

Once the server is running, navigate to:

```
http://127.0.0.1:8000/docs
```

## Video Upload API

The upload endpoint accepts video files via multipart/form-data:

```
POST /api/videos/upload
Content-Type: multipart/form-data
```

Field name: `file`

Supported formats: `.mp4`, `.mov`, `.mkv`, `.webm`, `.avi`
Maximum file size: 500 MB (configurable via `MAX_VIDEO_SIZE_MB` in `.env`)

### Upload Response

```json
{
  "success": true,
  "message": "Video uploaded successfully",
  "video": {
    "original_filename": "my_video.mp4",
    "stored_filename": "uuid.mp4",
    "file_size": 1234567,
    "content_type": "video/mp4",
    "extension": ".mp4"
  }
}
```

## Video Metadata Extraction

After uploading, technical metadata is extracted using the **bundled FFmpeg binary** via `imageio-ffmpeg`. No separate ffprobe installation is required.

### Endpoint

```
GET /api/videos/{stored_filename}/metadata
```

### How It Works

The project uses `imageio-ffmpeg` which automatically downloads and bundles the FFmpeg binary. The application calls `ffmpeg -i <file>` internally and parses the output to extract metadata.

### Metadata Response

```json
{
  "success": true,
  "message": "Video metadata extracted successfully",
  "video": {
    "filename": "8f7b2c1e.mp4",
    "format": "mp4",
    "duration_seconds": 1.0,
    "file_size_bytes": 2325,
    "width": 320,
    "height": 240,
    "fps": 25.0,
    "frame_count": null,
    "video_codec": "h264",
    "audio_codec": null
  }
}
```

Fields:
- `audio_codec` is `null` for videos without audio
- `fps` handles fractional rates (e.g., `30000/1001` → `29.97`)
- `frame_count` is `null` if unavailable
- `frame_count` is currently always `null` (ffprobe-specific field)
- Returns appropriate client/server error codes on failure

### Required Dependencies

`imageio-ffmpeg` is included in `requirements.txt`. It automatically manages the bundled FFmpeg binary. No manual FFmpeg installation needed.

## Video Frame Extraction

After uploading, JPEG frames can be extracted from the video at configurable time intervals.

### Endpoint

```
POST /api/videos/{stored_filename}/frames/extract?interval_seconds=1
```

### Parameters

- `interval_seconds` (query): Time in seconds between each extracted frame. Range: 0.1 to 60. Default: 1.0.

### Storage Structure

Extracted frames are saved under `storage/frames/<video_id>/`:

```
storage/frames/8f7b2c1e/
frame_000001.jpg
frame_000002.jpg
frame_000003.jpg
```

### Response

```json
{
  "success": true,
  "message": "Frames extracted successfully",
  "video_filename": "8f7b2c1e.mp4",
  "interval_seconds": 1.0,
  "frame_count": 3,
  "frames": [
    {
      "index": 1,
      "filename": "frame_000001.jpg",
      "path": "storage/frames/8f7b2c1e/frame_000001.jpg",
      "timestamp_seconds": 0.0
    },
    {
      "index": 2,
      "filename": "frame_000002.jpg",
      "path": "storage/frames/8f7b2c1e/frame_000002.jpg",
      "timestamp_seconds": 1.0
    }
  ]
}
```

- Frame paths are relative/project-safe only. No absolute filesystem paths are exposed.
- Frame numbering is sequential (`frame_000001.jpg`, `frame_000002.jpg`, etc.).
- If extraction fails, partially generated frames are automatically cleaned up.

### Requirements

The bundled FFmpeg binary from `imageio-ffmpeg` is used. No separate installation needed.

## Vision AI (Day 5)

Day 5 adds a **vision-language model abstraction** that can analyze a single extracted frame and return a detailed textual description.

### Architecture

```
JPEG Frame
  ↓
VisionService (backend/app/services/vision_service.py)
  ↓
VisionProvider (backend/app/ai/vision_provider.py)
  ↓
Model (Mock / Qwen2.5-VL / External API)
```

### Provider Abstraction

The `VisionProvider` base class defines the interface. Three implementations exist:

| Provider | Status | Description |
|----------|--------|-------------|
| `MockVisionProvider` | **Active (default)** | Returns a fixed development description. No model download required. |
| `Qwen2VLProvider` | Stub / Ready | Placeholder for Qwen2.5-VL local inference. Requires `torch`, `transformers`. |
| Custom providers | Extensible | Implement `VisionProvider` for any vision model. |

### Current Model Configuration

The default provider is `mock`. This is intentional — the full Qwen2.5-VL model requires:
- PyTorch (`torch>=2.3.0`)
- Transformers (`transformers>=4.40.0`)
- Accelerate (`accelerate>=0.30.0`)
- ~10GB+ of model weights

This machine has **no GPU** and **no PyTorch installed**. The mock provider enables full development and testing without requiring large downloads.

To switch to Qwen2.5-VL:
1. Install the ML dependencies
2. Download the model weights
3. Set `VISION_PROVIDER=qwen2vl` in `.env`
4. Uncomment the `Qwen2VLProvider` implementation

### Endpoint

```
POST /api/videos/{stored_filename}/frames/analyze?frame_filename=frame_000001.jpg
```

### Default Analysis Prompt

The model receives a structured prompt for visual description:
> "Describe this image in detail for an AI video reconstruction system. Identify the main subjects, their appearance, actions, environment, objects, composition, camera perspective, lighting, colors, visual style, and any clearly visible text. Do not invent details that are not visible."

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `frame_filename` | string | Yes | Name of the JPEG frame file |

### Response

```json
{
  "success": true,
  "message": "Frame analyzed successfully",
  "video_filename": "example.mp4",
  "frame_filename": "frame_000001.jpg",
  "description": "A cinematic outdoor scene showing...",
  "model": "mock-vision-provider"
}
```

### Manual Test

```bash
cd backend
python -m scripts.test_vision
```

This finds an existing frame, loads the configured provider, and prints the AI description.

### Security

- Frame paths are validated to be inside `storage/frames/`
- Path traversal attempts are rejected with 400/404
- No absolute filesystem paths are exposed in API responses

## Multi-Frame Video Analysis (Day 6)

Day 6 adds a **multi-frame video analysis pipeline** that analyzes selected frames across the entire video and combines observations into a structured video-level analysis.

### Architecture

```
Video
  ↓
Frame Selection (representative sampling)
  ↓
VisionService (per-frame analysis)
  ↓
Frame Observations
  ↓
VideoAnalysisService (combine observations)
  ↓
Structured Video Analysis
```

### Endpoint

```
POST /api/videos/{stored_filename}/analyze?max_frames=10
```

### Frame Selection Strategy

The pipeline uses **deterministic linear spacing** to select representative frames across the full temporal range of the video.

Example:
- 100 extracted frames, `max_frames=10` → selects frames spread evenly: frame 1, 11, 21, 31, 41, 51, 61, 71, 81, 100
- This ensures temporal coverage rather than just taking the first N frames.

`max_frames` parameter:
- Default: 10
- Minimum: 1
- Maximum: 50
- When `max_frames=1`: selects only the first frame (index 0).
- When `max_frames >= total_frames`: selects all frames.
- When `max_frames < total_frames`: uses deterministic linear spacing to evenly distribute selected frames across the video timeline.

### Video-Level Analysis Schema

```json
{
  "video_filename": "example.mp4",
  "frames_analyzed": 10,
  "analysis": {
    "subjects": [],
    "actions": [],
    "environment": "",
    "camera": {
      "perspective": "",
      "shot_type": "",
      "movement": ""
    },
    "lighting": "",
    "visual_style": "",
    "color_palette": [],
    "objects": []
  },
  "frame_observations": [
    {
      "frame_index": 1,
      "timestamp_seconds": 0.0,
      "frame_filename": "frame_000001.jpg",
      "description": "...",
      "model": "mock"
    }
  ]
}
```

### Mock Provider Limitation

The current default provider is `mock`. For the mock provider:
- `frame_observations` contain deterministic placeholder descriptions
- `analysis` fields remain empty/null
- No visual information is fabricated
- The architecture is fully ready for a real Qwen2.5-VL provider

### API Response Example

```json
{
  "success": true,
  "message": "Video analysis completed successfully",
  "video_filename": "example.mp4",
  "frames_analyzed": 5,
  "analysis": {
    "subjects": [],
    "actions": [],
    "environment": "",
    "camera": {
      "perspective": "",
      "shot_type": "",
      "movement": ""
    },
    "lighting": "",
    "visual_style": "",
    "color_palette": [],
    "objects": []
  },
  "frame_observations": [
    {
      "frame_index": 1,
      "timestamp_seconds": 0.0,
      "frame_filename": "frame_000001.jpg",
      "description": "A mock vision description...",
      "model": "mock-vision-provider"
    }
  ]
}
```

### Required Dependencies

No additional dependencies beyond the existing project requirements. Uses the existing `VisionService` and provider abstraction.

## Day 7 — Prompt Generation Engine

Day 7 adds a **prompt generation engine** that converts the structured video analysis from Day 6 into a detailed, natural-language, production-ready AI video-generation prompt.

### Pipeline Position

```
Structured Video Analysis
       ↓
Prompt Generation Engine
       ↓
Production-Ready AI Video Prompt
```

The prompt generator does NOT analyze the video itself. It transforms the existing structured analysis data into coherent prose.

### Prompt Generation Service

`backend/app/services/prompt_service.py` — `PromptGenerationService`

Accepts the structured analysis output from `VideoAnalysisService` and produces a natural-language prompt.

The engine does NOT fabricate visual details. It only transforms existing analysis data into coherent prose. If a field is empty/null/missing, it is simply omitted from the final prompt.

### Supported Styles

| Style | Description |
|-------|-------------|
| `cinematic` (default) | Cinematic visual language and composition terminology |
| `realistic` | Natural and realistic presentation emphasis |
| `commercial` | Polished, clean presentation language |

Style influences wording only. No style invents visual content.

### Endpoint

```
POST /api/videos/{stored_filename}/prompt?style=cinematic
```

**Query parameter `style`**: `cinematic` (default), `realistic`, or `commercial`. Invalid values return HTTP 400.

### Request Example

```
POST /api/videos/example.mp4/prompt?style=cinematic
```

### Response Structure

```json
{
  "success": true,
  "video_filename": "example.mp4",
  "style": "cinematic",
  "prompt": "A young man walks toward a car on an urban street at sunset. Capture the scene from an eye-level perspective in a medium shot with a slow tracking camera movement. Warm sunset lighting with a color palette of amber and orange creates a cinematic realistic atmosphere, with cinematic composition.",
  "negative_prompt": null
}
```

### Grounding Rule

The prompt generator NEVER invents:
- People, clothing, faces
- Locations, vehicles, objects
- Actions, camera movements
- Lighting, colors, atmosphere
- Visual style

When the structured analysis contains no usable visual information (e.g., mock provider placeholder data), the engine returns a safe minimal prompt rather than fabricating content.

### Current MockVisionProvider Limitation

The current default provider is `mock`. The mock provider returns placeholder observations, so the structured analysis fields are typically empty. Prompt quality is currently limited by the available structured analysis. Real visual understanding will be added later through a real vision model.

Do not claim that Qwen2.5-VL is currently running. No real VLM inference is active.

## Day 8 — Qwen2.5-VL Vision Provider

Day 8 implements the real Qwen2.5-VL vision-language model provider behind the existing `VisionProvider` abstraction.

### Purpose

The Qwen provider converts individual frame images into detailed natural-language visual descriptions, which feed into the Day 6 multi-frame analysis pipeline and the Day 7 prompt generation engine.

### Provider Architecture

```
VisionService
     ↓
VisionProvider (abstract)
     ├── MockVisionProvider  ← default, always works
     └── Qwen2VLProvider     ← real Qwen2.5-VL inference
```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_PROVIDER` | `mock` | Active provider: `mock` or `qwen2vl` |
| `VISION_MODEL_NAME` | `Qwen2.5-VL` | Model identifier for Qwen2.5-VL |

### Lazy Model Loading

The Qwen2.5-VL model is loaded **lazily** on the first call to `describe_image()`. This avoids allocating large amounts of memory/VRAM during application startup. The model is cached as a singleton for subsequent calls.

```python
provider = Qwen2VLProvider()  # Model NOT loaded here
description = provider.describe_image("frame_000001.jpg")  # Model loaded here
```

### Device Selection

- **CUDA GPU** if available
- **CPU** otherwise (CPU inference is supported but may be slow)

### Dependencies

To enable real inference, install:

```
torch>=2.14.0
transformers>=5.17.0
accelerate>=1.15.0
safetensors>=0.8.0
pillow>=10.0.0
```

Set `VISION_PROVIDER=qwen2vl` in `.env`.

### Behavior

- `VISION_PROVIDER=mock`: Works without any model dependencies
- `VISION_PROVIDER=qwen2vl`: Uses Qwen2.5-VL for real visual understanding

### MockVisionProvider

The `MockVisionProvider` remains the **safe default** and continues to work without any model dependencies. It returns deterministic placeholder descriptions.

### Real Inference Status

Real Qwen2.5-VL inference requires torch, transformers, and the model weights. On machines without sufficient resources, the Qwen provider raises clear `RuntimeError` messages rather than crashing. The architecture is fully implemented even if real inference is not executed in the current environment.

## Day 9 — Scene Detection and Video Timeline

Day 9 adds **heuristic scene detection** that divides a video into logical visual scenes based on frame-level visual differences.

### Important Limitation

Day 9 scene detection is **purely heuristic**. It identifies likely visual transitions using pixel-level frame comparison. It does NOT provide semantic scene understanding such as "a person enters a room" or "the background changes to a park". It only detects when the visual content appears to change significantly.

### How It Works

```
Video
  ↓
Frame Sampling (at configured interval)
  ↓
Pairwise Frame Comparison (pixel-level difference)
  ↓
Threshold Comparison
  ↓
Scene Boundary Detection
  ↓
Scene Timeline
```

The algorithm:
1. Samples frames at a configurable interval (`scene_sample_interval_seconds`)
2. Compares consecutive sampled frames using normalized pixel difference
3. When the difference exceeds the threshold (`scene_change_threshold`), marks a scene boundary
4. Groups frames into scenes
5. Selects a representative frame (middle of each scene)

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `scene_change_threshold` | `0.30` | Visual difference threshold for scene boundary (0.0-1.0) |
| `scene_sample_interval_seconds` | `1.0` | Interval between sampled frames in seconds |
| `max_scenes` | `100` | Maximum number of scenes to prevent pathological behavior |

The threshold is a configurable heuristic, not an optimality guarantee.

### Scene Data Model

Each scene contains:
- `scene_id`: Sequential identifier
- `start_time`: Scene start in seconds
- `end_time`: Scene end in seconds
- `duration`: Scene duration
- `start_frame`: First frame filename in scene
- `end_frame`: Last frame filename in scene
- `representative_frame`: Middle frame of scene
- `change_score_from_previous`: Pixel difference score that triggered boundary (null for first scene)

### Endpoint

```
POST /api/videos/{stored_filename}/scenes/detect?sample_interval_seconds=1&threshold=0.30
```

**Query parameters:**
- `sample_interval_seconds`: Must be > 0 (default: 1.0)
- `threshold`: Must be between 0.0 and 1.0 (default: 0.30)

### Response Structure

```json
{
  "success": true,
  "video_filename": "example.mp4",
  "duration_seconds": 10.0,
  "scenes_detected": 3,
  "scenes": [
    {
      "scene_id": 1,
      "start_time": 0.0,
      "end_time": 3.0,
      "duration": 3.0,
      "start_frame": "frame_000001.jpg",
      "end_frame": "frame_000003.jpg",
      "representative_frame": "frame_000002.jpg",
      "change_score_from_previous": null
    }
  ]
}
```

### Key Behaviors

- Always returns at least 1 scene (single-scene video if no changes detected)
- Scenes are chronologically ordered and non-overlapping
- Final scene ends at or near video duration
- First scene always has `change_score_from_previous = null`
- Maximum scene limit prevents pathological behavior
- No absolute filesystem paths in response
- Works entirely with `VISION_PROVIDER=mock` — no AI model required

### Dependencies

Uses only `Pillow` and `NumPy` (already project dependencies). No OpenCV, no AI models, no heavy computer-vision libraries.

## Day 10 — Character and Subject Tracking

Day 10 adds **heuristic subject tracking** that identifies recurring visible subjects across frame observations and builds structured subject profiles.

### Important Limitation

Day 10 performs **heuristic text-based subject tracking**. It is NOT facial recognition, biometric identification, or guaranteed identity tracking. Subject matching is based on text description similarity, not visual embeddings or face analysis.

### How It Works

```
Frame Observations
       ↓
Subject Extraction
       ↓
Heuristic Matching (Jaccard similarity + weighted scoring)
       ↓
Subject Profile Building
       ↓
Structured Subject Timeline
```

### Subject Profile Schema

Each subject profile contains:
- `subject_id`: Unique identifier (e.g., `subject_1`)
- `label`: Generic category (`person`, `vehicle`, `object`, `animal`, `unknown`)
- `description`: Normalized subject description
- `appearance_observations`: Descriptive observations
- `actions`: Associated actions
- `first_seen`: Earliest timestamp
- `last_seen`: Latest timestamp
- `frames_seen`: Frame filenames observed
- `confidence`: Heuristic matching confidence (NOT biometric identity confidence)

### Matching Algorithm

Subjects are matched using a transparent scoring approach:
- Label match: +0.40
- Appearance overlap: +0.30
- Description overlap: +0.20
- Temporal proximity: +0.10

If the total score >= `subject_match_threshold`, observations are grouped as the same subject.

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `subject_match_threshold` | `0.60` | Heuristic matching threshold |
| `max_subjects` | `100` | Maximum number of subjects |

### Endpoint

```
POST /api/videos/{stored_filename}/subjects/analyze
```

### Response Structure

```json
{
  "success": true,
  "video_filename": "example.mp4",
  "subjects_detected": 2,
  "subjects": [
    {
      "subject_id": "subject_1",
      "label": "person",
      "description": "young man",
      "appearance_observations": ["young man"],
      "actions": ["walking"],
      "first_seen": 0.0,
      "last_seen": 4.0,
      "frames_seen": ["frame_000001.jpg", "frame_000002.jpg"],
      "confidence": 0.75
    }
  ]
}
```

### Key Behaviors

- Works entirely with `VISION_PROVIDER=mock` — no AI model required
- When mock provider produces no subjects, `subjects_detected = 0` is valid
- Does NOT perform facial recognition or biometric identification
- Does NOT invent subjects or identities
- Uses existing frame observations from `VideoAnalysisService`
- No database, no persistent storage
- Handles empty observations, null subjects, and placeholder descriptions safely

### Dependencies

Uses only `NumPy` and `Pillow` (already project dependencies). No OpenCV, no AI models.

## Project Structure

```
visionprompt-ai/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application entry point
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── health.py    # Health check endpoint
│   │   │   └── videos.py    # Video upload & metadata endpoints
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py    # Environment-based configuration
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── vision_provider.py   # Abstract provider base class
│   │   │   └── providers.py         # Mock, Qwen2VL, and provider factory
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── video_service.py       # Video upload business logic
│   │   │   │   ├── frame_service.py       # Frame extraction business logic
│   │   │   │   ├── vision_service.py      # Vision analysis service
│   │   │   │   ├── video_analysis_service.py  # Multi-frame video analysis
│   │   │   │   ├── prompt_service.py      # Prompt generation engine
│   │   │   │   ├── scene_service.py       # Scene detection and timeline
│   │   │   │   └── subject_service.py     # Subject tracking and profiles
│   │   │   └── utils/
│   │   │       ├── __init__.py
│   │   │       └── ffprobe.py             # FFprobe metadata extraction
│   │   ├── scripts/
│   │   │   └── test_vision.py             # Manual vision test script
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── .gitignore
├── frontend/                 # Frontend application (future)
├── storage/                  # Uploaded videos, frames, audio, outputs
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_video_upload.py
│   ├── test_video_metadata.py
│   ├── test_frame_extraction.py
│   ├── test_vision_service.py
│   ├── test_video_analysis.py
│   ├── test_prompt_service.py
│   ├── test_prompt_api.py
│   └── test_qwen_provider.py
├── README.md
└── .gitignore
```


## Day 11 — Audio Analysis + Speech Transcription

Day 11 adds **audio extraction and speech transcription** to the video analysis pipeline. The system extracts audio tracks from uploaded videos, detects whether speech is present, and returns timestamped transcription results.

### Architecture

```
Video
  -> Audio Extraction (FFmpeg via imageio-ffmpeg) -> 16kHz mono WAV
  -> Audio Detection (has_audio_stream check)
  -> Transcription (AudioProvider abstraction)
  -> Structured Transcription Result
```

### Provider Abstraction

The `AudioProvider` base class defines the transcription interface. Two implementations exist:

| Provider | Status | Description |
|----------|--------|-------------|
| `MockAudioProvider` | **Active (default)** | Returns empty transcription. Never fabricates speech. No model download required. |
| `WhisperAudioProvider` | Stub / Ready | Placeholder for faster-whisper local inference. Uses lazy loading. |

### Key Behaviors

- `AUDIO_PROVIDER=mock` is the default - works without any model dependencies
- Videos without audio streams return `has_audio: false` with empty transcription
- The mock provider **NEVER** fabricates dialogue or invents speech
- The Whisper provider loads the model lazily on first `transcribe()` call
- Audio is extracted as 16kHz mono PCM WAV using the bundled FFmpeg binary
- Audio files are stored under `storage/audio/<video_id>.wav`
- Path traversal protection is enforced on all video filenames

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIO_PROVIDER` | `mock` | Active provider: `mock` or `whisper` |
| `AUDIO_MODEL_NAME` | `small` | Model identifier for Whisper |

### Endpoint

```
POST /api/videos/{stored_filename}/audio/analyze
```

### Response Structure

**With audio:**
```json
{
  "success": true,
  "video_filename": "example.mp4",
  "has_audio": true,
  "duration_seconds": 10.0,
  "audio_format": "wav",
  "sample_rate": 16000,
  "channels": 1,
  "transcription": {
    "language": null,
    "text": "",
    "segments": [],
    "provider": "mock"
  },
  "provider": "mock"
}
```

**Without audio:**
```json
{
  "success": true,
  "video_filename": "example.mp4",
  "has_audio": false,
  "duration_seconds": 10.0,
  "audio_format": null,
  "sample_rate": null,
  "channels": null,
  "transcription": {
    "language": null,
    "text": "",
    "segments": [],
    "provider": "mock"
  },
  "provider": "mock"
}
```

### Grounding Rule

The mock provider **NEVER** invents dialogue:
- `text` is always empty string
- `segments` is always empty list
- No fabricated speech, no hallucinated words
- `provider` field always identifies the provider used

### Dependencies

`numpy>=2.0.0` is required for audio file creation in tests. `faster-whisper` and `librosa` are optional for real Whisper inference. The bundled FFmpeg binary from `imageio-ffmpeg` handles audio extraction.

### Files Created/Modified

- `backend/app/ai/audio_provider.py` - Abstract `AudioProvider` base class
- `backend/app/ai/audio_providers.py` - `MockAudioProvider`, `WhisperAudioProvider`, factory
- `backend/app/services/audio_service.py` - `AudioService` with extraction and analysis
- `backend/app/api/videos.py` - Added `/audio/analyze` endpoint
- `backend/app/core/config.py` - Added `audio_provider`, `audio_model_name` config
- `backend/requirements.txt` - Added `numpy>=2.0.0`
- `backend/.env.example` - Added `AUDIO_PROVIDER`, `AUDIO_MODEL_NAME`
- `tests/test_audio_service.py` - 19 audio service tests
- `tests/test_audio_api.py` - 10 audio API tests

### Test Results

All 29 Day 11 tests pass. Full suite: 189/189 tests passing.

### Security

- Video filenames are validated for path traversal before audio extraction
- Absolute filesystem paths are never exposed in API responses
- Audio extraction failures are handled gracefully with cleanup

### Manual Test

```bash
cd backend
python -m scripts.test_audio
```


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


## Day 21 - Prompt Quality Analyzer

Day 21 adds a **Prompt Quality Analyzer**: a deterministic, heuristic coverage analysis of any prompt text (supplied directly or stored as a history version). It reports nine quality dimensions with integer scores and actionable suggestions. This is analysis only - not prompt generation and not an LLM call.

### Purpose

- Show users exactly which quality dimensions their prompt covers and which are missing
- Give neutral, actionable suggestions ("Add lighting information.") - never fabricate content
- Fully deterministic: the same prompt always yields the identical report
- Read-only: existing Day 16-20 features remain untouched

### Architecture

- Day 16 `PromptHistoryService` remains the **single source of truth** for versions
- Day 21 `PromptQualityService` is a standalone, stateless analyzer with no store of its own
- The history-quality endpoint passes the stored prompt text into the analyzer - it never modifies history records, favorites, or tags
- No LLM, no network, no filesystem, no database - pure in-process text analysis

### Nine Dimensions

`subject`, `action`, `environment`, `camera`, `lighting`, `visual_style`, `color`, `composition`, `audio`

Each dimension reports `{"present": bool, "score": int}` with conservative keyword/phrase detection (case-insensitive, whitespace-normalized):

| Signals matched | present | score |
|-----------------|---------|-------|
| 0 | false | 0 (missing) |
| 1 | true | 40 (weak) |
| 2 | true | 70 |
| 3+ | true | 100 (strong) |

- `overall_score` = round-half-up of the mean of the 9 scores (0-100)
- `completeness_percentage` = round-half-up of (present dimensions / 9) x 100
- `missing_dimensions` = every dimension with `present: false` (dimension order)
- `suggestions` = `"Add <name> information."` for missing dimensions and `"Expand <name> information for better coverage."` for weak (score 40) dimensions, in dimension order

### Service

`backend/app/services/prompt_quality_service.py` - `PromptQualityService`

- `analyze_prompt(prompt)` returns `{"prompt": <original text>, "quality": {overall_score, completeness_percentage, dimensions, missing_dimensions, suggestions}}`
- Raises `ValueError` for non-string, empty, or whitespace-only prompts
- Echoes the original prompt back unchanged; only the internal matching view is normalized
- No state, no network, no filesystem access - safety verified by tests

### Endpoints

```
POST /api/videos/{stored_filename}/prompt/quality
GET  /api/videos/{stored_filename}/prompt/history/{version}/quality
```

- `POST` analyzes arbitrary prompt text from the JSON body `{"prompt": "..."}`
- `GET` analyzes the stored prompt of one history version (read-only, uses Day 16 `get_version`)
- The `/quality` sub-route is registered before the plain numeric `{version}` route, so history routes never collide

### Response Structure

```json
{
  "prompt": "<original text>",
  "quality": {
    "overall_score": 78,
    "completeness_percentage": 67,
    "dimensions": {
      "subject": {"present": true, "score": 100},
      "lighting": {"present": false, "score": 0}
    },
    "missing_dimensions": ["lighting", "audio"],
    "suggestions": ["Add lighting information.", "Add audio information."]
  }
}
```

### Validation

- Valid prompt returns HTTP 200
- Missing body, missing `prompt` field, empty or whitespace-only prompt returns HTTP 422
- Non-string `prompt` returns HTTP 422
- Nonexistent video returns HTTP 404; invalid extension returns HTTP 400
- Path traversal attempts return HTTP 404
- Nonexistent or deleted history version returns HTTP 404; version below 1 returns HTTP 422

### No-Fabrication / Read-Only Rules

- Neutral terminology only - never judges video content, only reports prompt coverage
- Never fabricates missing dimensions; missing information stays missing and is suggested
- Never modifies stored prompt text, history versions, favorites, or tags
- Suggestions correspond exactly to missing or weak dimensions
- No absolute paths, internal object names, or stack traces in responses

### Files Created/Modified

- `backend/app/services/prompt_quality_service.py` - `PromptQualityService`
- `backend/app/api/videos.py` - Added `/prompt/quality` (POST) and `/prompt/history/{version}/quality` (GET) endpoints
- `tests/test_prompt_quality_service.py` - 56 service tests
- `tests/test_prompt_quality_api.py` - 27 API tests


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


## Day 23 - Prompt Version Comparison & Diff

Day 23 adds **Prompt Version Comparison & Diff**: a deterministic, read-only comparison layer that produces a full structured comparison of any two saved prompt versions - text diff (added/removed/common), Day 21 quality reports for both versions, neutral quality deltas, and the quality dimensions that changed. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Show users exactly how two saved prompt versions differ
- Combine Day 16 history data with Day 21 quality analysis in one response
- Never modify history, favorites, tags, or store the comparison result
- Fully deterministic: same two versions -> identical output

### Architecture

- Day 16 `PromptHistoryService` remains the single source of truth for versions; Day 23 **reads** it via `get_version` and never writes
- Day 21 `PromptQualityService` remains the single quality-analysis source; Day 23 **reuses** `analyze_prompt` and never duplicates its scoring logic
- Day 23 `PromptComparisonService(history_service, quality_service)` holds only those two dependencies
- Day 16 token compare endpoint (`/prompt/history/compare/{a}/{b}`) stays unchanged - the Day 23 detailed route is a separate, longer path
- No LLM, no network, no filesystem, no database - pure in-process text analysis

### Comparison Flow

```
version A + version B -> Day 16 get_version (read-only, twice)
                      -> difflib.SequenceMatcher word-level diff
                      -> Day 21 analyze_prompt for each prompt
                      -> structured comparison (diff + deltas + dimensions)
```

### Text Diff (difflib)

- Prompts are tokenized with **leading whitespace attachment** (`\s*\S+`, plus a final token for trailing whitespace), so joining tokens reconstructs each prompt byte-for-byte and appends appear as clean inserts
- `difflib.SequenceMatcher(None, tokens_a, tokens_b, autojunk=False)` opcodes map to: `equal` -> `common_text`, `insert` -> `added_text`, `delete` -> `removed_text`, `replace` -> contributes to both `removed_text` and `added_text`
- The diff only ever reports text that exists in the two source prompts - never invents wording
- `identical` compares the raw prompts (so whitespace-only edits are `identical: false, changed: true`)

Example (`A person walks through a road.` -> `A person walks through a road. Medium shot with natural lighting.`):

- `common_text` = `A person walks through a road.`
- `added_text` = ` Medium shot with natural lighting.`
- `removed_text` = `` (empty)

### Quality Deltas (Day 21)

- `quality_score_delta` = `version_b.overall_score - version_a.overall_score`
- `completeness_delta` = `version_b.completeness_percentage - version_a.completeness_percentage`
- Labels are **neutral**: `increased` / `decreased` / `unchanged` - the service never ranks one version as better, improved, or superior
- `changed_dimensions` lists exactly the Day 21 dimensions whose `present`/`score` pair differs, in Day 21 dimension order (`subject, action, environment, camera, lighting, visual_style, color, composition, audio`)
- Version order is always preserved: deltas are always `b - a` for the requested order, and requesting `(2, 1)` is the exact mirror of `(1, 2)` - versions are never silently swapped

### Service

`backend/app/services/prompt_comparison_service.py` - `PromptComparisonService`

- `compare_versions(stored_filename, version_a, version_b)` returns:
  - `video_filename`
  - `version_a` / `version_b` summaries: `version`, `version_id`, `source`, `operation`, `prompt`, `quality` (the full Day 21 report)
  - `comparison`: `identical`, `changed`, `added_text`, `removed_text`, `common_text`, `quality_score_delta`, `quality_score_change`, `completeness_delta`, `completeness_change`, `changed_dimensions`
- Raises `ValueError` (bubbled from Day 16) when either version does not exist or the version number is invalid

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/compare/{version_a}/{version_b}/detailed
```

- Read-only: never modifies history, favorites, or tags; the result is never persisted
- Registered after the Day 16 token compare route (longer, distinct path) and before the plain numeric `{version}` route, so history routes never collide
- Version order in the URL is the comparison order

### Validation

- Valid versions return HTTP 200 (including `version_a == version_b`, which yields `identical: true`)
- Version below 1 or non-integer version returns HTTP 422
- Nonexistent video returns HTTP 404; invalid extension returns HTTP 400
- Path traversal attempts return HTTP 404
- Nonexistent or deleted history version returns HTTP 404

### Determinism

- Repeated requests for the same version pair return byte-identical JSON
- No timestamps, UUIDs, or random values appear in the response
- No external API calls

### Tests

- `tests/test_prompt_comparison_service.py` - 54 service tests (validation, identical/diff cases, whitespace/punctuation, quality deltas, changed dimensions, ordering/no-swap, structure, determinism, read-only, security)
- `tests/test_prompt_comparison_api.py` - 29 API tests (200/422/404/400 validation, response schema, direct Day 21 cross-checks, determinism, read-only, route collision, Day 16-22 regressions)

### Limitations

- The diff is word-level text comparison; it does not semantically judge which wording is preferable
- Quality analysis is Day 21 signal matching on text only - it does not understand actual video content
- Only two versions can be compared per request
- Results are never persisted; exporting or packaging comparisons is not part of Day 23

### Files Created/Modified

- `backend/app/services/prompt_comparison_service.py` - `PromptComparisonService`
- `backend/app/api/videos.py` - Added `/prompt/history/compare/{version_a}/{version_b}/detailed` (GET) endpoint and service instance
- `tests/test_prompt_comparison_service.py` - 54 service tests
- `tests/test_prompt_comparison_api.py` - 29 API tests


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


## Day 25 - Prompt Readiness History Analysis

Day 25 adds a **Prompt Readiness History Analysis** endpoint: a deterministic, read-only analysis layer that answers *"what readiness information is available across the saved prompt versions of this video?"* It runs the Day 24 Production Readiness Validator over selected Day 16 history versions and aggregates the results. It never ranks versions, never picks a best version, never declares one version superior, and never predicts which prompt will generate better video output. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Analyze readiness across **all** saved versions or a **selected** subset in one call
- Provide aggregate counts (`ready` vs `needs_attention`) and coverage totals
- Provide a per-dimension occurrence summary across versions
- Reuse Day 24 readiness output byte-for-byte - never recompute or alter statuses, scores, or coverage
- Never modify history, favorites, tags, exports, quality reports, or any prompt

### Relationship With Day 16 and Day 24

- Day 16 `PromptHistoryService` remains the single version store; Day 25 only calls its read paths (`list_versions`, `get_version`)
- Day 24 `PromptReadinessService` remains the single readiness source; each analyzed version's `readiness` object is exactly what `validate_prompt` returns for that stored prompt
- Day 21 `PromptQualityService` stays behind Day 24 - Day 25 never touches scoring directly
- Analysis results are never persisted anywhere (no second store, no cache)

### Version Selection

| Query | Behavior |
|-------|----------|
| *(no query)* | Every live version, ascending version order |
| `?versions=1,3,5` | Only those versions, **requested order preserved** |
| `?versions=2` | Single version |
| `?versions=1&versions=3` | Repeated params also accepted |

Selection rules are deterministic: requested versions are never substituted, reordered, or dropped. Deleted versions are not substituted by neighbors. A video with no saved versions returns an empty (zeroed) analysis with HTTP 200.

### Response Shape

```json
{
  "video_filename": "abc123.mp4",
  "versions_analyzed": [1, 2],
  "results": [
    {
      "version": 1,
      "version_id": "abc123.mp4:1",
      "source": "advanced_prompt",
      "operation": "generate",
      "readiness": { "...": "exact Day 24 readiness object" }
    }
  ],
  "summary": { "...": "aggregate counts below" },
  "dimension_summary": [ "...": "one entry per Day 21 dimension" ]
}
```

Each `readiness` is the complete Day 24 object: `status`, `required_dimensions`, `supporting_dimensions`, `checklist`, `coverage`, `missing_dimensions`, `weak_dimensions`, `suggestions`.

### Summary Aggregates

| Key | Meaning |
|-----|---------|
| `versions_analyzed` | Number of versions analyzed |
| `ready_count` / `needs_attention_count` | Day 24 statuses across analyzed versions |
| `required_dimensions_total/present/weak/missing` | Summed Day 24 required coverage counts (`total = versions x 7`) |
| `required_coverage_percentage` | `round(required_present / required_total * 100)`, 0 when empty |
| `supporting_dimensions_total/present/weak/missing` | Summed supporting counts (`total = versions x 2`) |
| `supporting_coverage_percentage` | Informational only - supporting never affects readiness |

`present + weak + missing == total` for both groups. Weak (score 40) never counts as present. All percentages are integers bounded 0-100. `ready_count + needs_attention_count == versions_analyzed`.

### Dimension Summary

One entry per Day 21 dimension, in Day 21 order (`subject` ... `audio`):

```json
{"dimension": "camera", "present_count": 2, "weak_count": 1, "missing_count": 1}
```

For each dimension: `present_count + weak_count + missing_count == versions_analyzed`. Counts come straight from each version's Day 24 checklist statuses - no independent detection.

### Service

`backend/app/services/prompt_readiness_history_service.py` - `PromptReadinessHistoryService(history_service, readiness_service)`

- `analyze_versions(stored_filename, versions=None)` returns `video_filename`, `versions_analyzed`, `results`, `summary`, `dimension_summary`
- Raises `ValueError` for an invalid versions argument (not a non-empty list of unique positive integers) or a missing/deleted version
- Read-only: only `list_versions` / `get_version` / `validate_prompt` are called

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/readiness?versions=1,3,5
```

- The static `/prompt/history/readiness` route is registered **before** the plain numeric `{version}` routes, so history routes never collide
- Malformed, empty, duplicate, or non-positive `versions` values return HTTP 422
- Nonexistent video or missing/deleted version returns HTTP 404; invalid extension returns HTTP 400; path traversal returns HTTP 404

### Determinism and Integrity

- Repeated calls with the same state return exactly equal responses; no random values, timestamps, dates, or UUIDs
- Original prompts, history records, favorites, tags, exports, and quality reports are byte-identical before and after analysis
- No filesystem paths, internal objects, or secrets appear in any response
- Prompt text itself is not echoed in the analysis response (Day 24 GET history readiness remains available for per-version prompts)

### Limitations

- Aggregates Day 24's structural coverage only: it does not evaluate cinematography, aesthetics, or actual video content
- No version ranking of any kind: counts and coverages are neutral tallies, not recommendations
- A `ready` count means required dimensions were textually covered - not that any model will produce a satisfactory video
- The endpoint validates the video file's existence but the service itself operates purely on stored version data

### Tests

- `tests/test_prompt_readiness_history_service.py` - 104 service tests (wiring, result structure, all/selected/empty selection, validation errors, aggregates, dimension summary, supporting informational rule, determinism, read-only integrity, leak/ranking scans, source contract)
- `tests/test_prompt_readiness_history_api.py` - 70 API tests (200/422/404/400 validation, query parsing, per-version Day 24 cross-checks, summary/dimension verification, determinism, read-only integrity, route collision, Day 16-24 regressions, leak scans)

### Files Created/Modified

- `backend/app/services/prompt_readiness_history_service.py` - `PromptReadinessHistoryService`
- `backend/app/api/videos.py` - Added static `GET /prompt/history/readiness` route (registered before numeric `{version}` routes), `_parse_versions_query`, and service instance
- `tests/test_prompt_readiness_history_service.py` - 104 service tests
- `tests/test_prompt_readiness_history_api.py` - 70 API tests


## Day 26 - Prompt Readiness Change Tracking

Day 26 adds **Prompt Readiness Change Tracking**: a deterministic, read-only informational diff that answers one question about two saved prompt versions - *"which production-readiness dimensions changed between these two saved prompt versions?"* It compares Day 24 readiness states dimension-by-dimension. It never ranks versions, never scores versions against each other, never chooses a preferred version, never calls one version better/worse, and never predicts video-generation quality. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Report exactly which readiness dimensions changed state between two saved versions
- Give directional transition counts (e.g. `missing -> present`) in the requested comparison direction
- Split changed dimensions into Day 24 required/supporting groups
- Provide neutral coverage arithmetic (delta) for each version's independent coverage
- Reuse Day 24 readiness output byte-for-byte - never alter Day 21 scores or Day 24 statuses

### Relationship With Day 16/21/24/25

- Day 16 `PromptHistoryService` is the only version store; Day 26 calls only `get_version` (read-only, no listing needed)
- Day 24 `PromptReadinessService` is the single readiness source; both versions' states come from its exact `validate_prompt` checklist
- Day 21 `PromptQualityService` stays behind Day 24 - Day 26 never touches scoring directly
- Day 25 aggregates across many versions; Day 26 compares exactly two versions and reuses no Day 25 aggregation logic
- The comparison result is never persisted anywhere (no second store, no cache)

### Dimension State Mapping

Day 21 order is always preserved (never alphabetically reordered): `subject`, `action`, `environment`, `camera`, `lighting`, `visual_style`, `color`, `composition`, `audio`.

State mapping is Day 24's exact rule:

| Day 21 score | State |
|--------------|-------|
| 100 | `present` |
| 70 | `present` |
| 40 | `weak` |
| 0 | `missing` |

Each dimension entry carries both versions' raw Day 21 scores **and** states:

```json
{
  "dimension": "camera",
  "version_a": {"status": "missing", "score": 0},
  "version_b": {"status": "present", "score": 70},
  "changed": true
}
```

`changed` is true only when the **state** differs. A score change from 70 to 100 is NOT a readiness-state change (both map to `present`), so `changed` is false - but the raw scores are still returned exactly as Day 21 reports them.

### Changed Dimensions

`changed_dimensions` lists only state-changed dimensions, always in Day 21 order (never sorted alphabetically). `dimensions_changed + dimensions_unchanged == 9` always holds.

### Transitions

For every state-changed dimension, a directional transition entry is returned:

```json
{"dimension": "camera", "from": "missing", "to": "present"}
```

`transition_summary` counts all six possible directional transitions (same-state transitions are never counted; all six keys are always present):

```json
{
  "missing_to_weak": 0, "missing_to_present": 2, "weak_to_missing": 0,
  "weak_to_present": 1, "present_to_missing": 0, "present_to_weak": 0
}
```

`sum(transition_summary.values()) == dimensions_changed` always holds.

### Required/Supporting Categorization

Changed dimensions are categorized with Day 24's exact groups: required (`subject`, `action`, `environment`, `camera`, `lighting`, `visual_style`, `composition`) and supporting (`color`, `audio`). `required_changes` + `supporting_changes` partition `changed_dimensions`. Supporting changes are neither more nor less important - they are simply categorized per Day 24.

### Readiness Status and Coverage Delta

Each version's block reports its own independent Day 24 values:

```json
{
  "version": 4, "source": "custom", "operation": "",
  "readiness_status": "needs_attention",
  "required_coverage_percentage": 71
}
```

`required_coverage` is neutral arithmetic only: `delta = version_b - version_a`. The delta is never labeled an improvement, gain, or quality increase, and no comparative score or winner is ever produced.

### Reverse Comparison

The requested direction is always preserved - versions are never auto-sorted or swapped. `compare/4/5/readiness` treats 4 as A and 5 as B; `compare/5/4/readiness` mirrors the transitions (e.g. `missing_to_present = 1` becomes `present_to_missing = 1`) and negates the coverage delta, while version labels stay in place. Comparing a version with itself returns all 9 dimensions unchanged with a delta of 0.

### Service

`backend/app/services/prompt_readiness_change_service.py` - `PromptReadinessChangeService(history_service, readiness_service)`

- `compare_versions(stored_filename, version_a, version_b)` returns `video_filename`, `version_a`, `version_b`, `dimensions`, `changed_dimensions`, `dimensions_changed`, `dimensions_unchanged`, `required_changes`, `supporting_changes`, `transitions`, `transition_summary`, `required_coverage`
- Raises `ValueError` for a non-positive-integer version or a missing/deleted version (never silently substitutes a missing version)

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/compare/{version_a}/{version_b}/readiness
```

- Distinct route from the Day 16 token compare and the Day 23 detailed compare (static `/readiness` suffix); those endpoints remain byte-for-byte unchanged
- Valid versions -> HTTP 200; version below 1 or non-integer -> 422; nonexistent/deleted version -> 404; nonexistent video -> 404; invalid extension -> 400; path traversal -> 404

### Determinism and Read-Only Behavior

- Repeated calls return byte-equivalent responses; no timestamps, UUIDs, random values, network, or filesystem data
- History records, prompts, metadata, favorites, tags, exports, and quality reports are byte-identical before and after any comparison
- The comparison never creates, deletes, or renumbers versions, and never saves its own result
- No prompt text, filesystem paths, internal objects, or secrets appear in any response

### Limitations

- Informational state diff only: it does not evaluate cinematography, aesthetics, or actual video content, and never predicts which prompt will generate better video
- A changed dimension means the Day 21 text-signal state changed, not that the prompt objectively improved or regressed
- Coverage deltas are arithmetic differences of independently computed coverages, not quality measurements
- Status labels (`ready` / `needs_attention`) remain Day 24 structural judgments per version

### Tests

- `tests/test_prompt_readiness_change_service.py` - 116 service tests (structure, identical versions, all six transitions verified independently, score-only changes, multiple changes, reverse mirroring, coverage/delta arithmetic, required/supporting partition, validation, determinism, read-only integrity, no-ranking/no-leak scans, source contract)
- `tests/test_prompt_readiness_change_api.py` - 45 API tests (200/422/404/400 validation, forward/reverse/same-version, Day 21 ordering, determinism, integrity, route collision, Day 16-25 regressions, leak scans)

### Files Created/Modified

- `backend/app/services/prompt_readiness_change_service.py` - `PromptReadinessChangeService`
- `backend/app/api/videos.py` - Added `GET .../compare/{version_a}/{version_b}/readiness` endpoint and service instance
- `tests/test_prompt_readiness_change_service.py` - 116 service tests
- `tests/test_prompt_readiness_change_api.py` - 45 API tests


## Day 27 - Prompt Readiness Timeline

Day 27 adds **Prompt Readiness Timeline**: a deterministic, read-only service that chains Day 26 readiness diffs across consecutive saved prompt versions, answering one question - *"how did production readiness change between each consecutive pair of saved versions?"* Every timeline step is byte-for-byte a Day 26 comparison output; Day 27 only selects version pairs and aggregates their numbers. It never ranks versions, never picks a best version, and never predicts which prompt will generate better video. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Chain Day 26 `compare_versions` results across consecutive selected versions (n versions -> n-1 steps)
- Give one neutral aggregate summary of the whole chain (totals, transition sums, first/last coverage)
- Keep every step identical to calling the Day 26 endpoint for that pair directly
- Support the exact Day 25 `versions` selection semantics (requested order preserved, never substituted or reordered)
- Reuse Day 16's single store read-only - no second store, no cache, no persisted timeline

### Relationship With Day 16/21/24/25/26

- Day 16 `PromptHistoryService` is still the only version store; Day 27 calls only `list_versions` (default selection) and `get_version` (explicit selection), both read-only
- Day 26 `PromptReadinessChangeService` is the only diff engine; every step is its exact `compare_versions` output for one pair (Day 27 never re-derives states or scores)
- Day 25 provides the selection validation rules Day 27 mirrors exactly (same messages for empty, malformed, non-positive, and duplicate lists)
- Day 24 readiness states and Day 21 scores are never recomputed or altered in this layer
- The timeline result is never persisted anywhere (no second store, no cache)

### Timeline Steps

- `steps == len(versions_analyzed) - 1` (0 when a video has zero or one selected version)
- Step `i` compares `versions_analyzed[i]` (A) with `versions_analyzed[i+1]` (B), always in selection order
- Adjacent steps chain: a step's `version_b` is always the next step's `version_a`
- Each step's keys are exactly Day 26's 12 response keys, and each step equals the Day 26 endpoint's response byte-for-byte

Example timeline shape (one exact Day 26 object per consecutive pair):

```json
{
  "video_filename": "abc123.mp4",
  "versions_analyzed": [1, 2],
  "steps": 1,
  "timeline": [
    {
      "video_filename": "abc123.mp4",
      "version_a": {"version": 1, "source": "advanced_prompt", "operation": "generate", "readiness_status": "ready", "required_coverage_percentage": 100},
      "version_b": {"version": 2, "source": "custom", "operation": "", "readiness_status": "needs_attention", "required_coverage_percentage": 86},
      "dimensions": ["9 entries in Day 21 order"],
      "changed_dimensions": ["camera"],
      "dimensions_changed": 1,
      "dimensions_unchanged": 8,
      "required_changes": ["camera"],
      "supporting_changes": [],
      "transitions": [{"dimension": "camera", "from": "present", "to": "weak"}],
      "transition_summary": {"missing_to_weak": 0, "missing_to_present": 0, "weak_to_missing": 0, "weak_to_present": 0, "present_to_missing": 0, "present_to_weak": 1},
      "required_coverage": {"version_a": 100, "version_b": 86, "delta": -14}
    }
  ],
  "summary": {"...": "12 keys, listed below"}
}
```

### Selection Rules

- No `versions` query: every live version, ascending version order
- `?versions=1,3,5`: only those versions, in the requested order - never sorted automatically, never substituted; a deleted or nonexistent requested version -> 404 (Day 16's exact message)
- Selection validation is byte-identical to Day 25: empty, malformed, non-integer, non-positive, or duplicate entries -> 422; whitespace around entries is tolerated; repeated `?versions=1&versions=3` equals `?versions=1,3`
- Default selection after a deletion simply skips deleted versions and compares the remaining neighbors (with version 3 deleted: pairs are 1->2, 2->4, 4->5, ...)

### Summary (12 keys)

```json
{
  "versions_analyzed": 8,
  "steps": 7,
  "dimensions_changed_total": 21,
  "dimensions_unchanged_total": 42,
  "required_changes_total": 17,
  "supporting_changes_total": 4,
  "transition_summary": {"missing_to_weak": 0, "missing_to_present": 9, "weak_to_missing": 2, "weak_to_present": 0, "present_to_missing": 7, "present_to_weak": 3},
  "first_version": 1,
  "last_version": 8,
  "first_required_coverage_percentage": 100,
  "last_required_coverage_percentage": 86,
  "required_coverage_delta": -14
}
```

- `transition_summary` is the element-wise sum of every step's six-key transition summary (all six keys are always present)
- `first_version` / `last_version` are the selection's first and last entries (`null` for an empty timeline)
- Coverage for a single selected version comes from Day 26's same-version comparison (`compare_versions(v, v)`); both coverage fields are `null` for zero versions
- `required_coverage_delta = last - first`, always equal to the sum of every step's `required_coverage.delta` (telescoping)

### Chaining Invariants

- `dimensions_changed_total + dimensions_unchanged_total == steps * 9`
- `required_changes_total + supporting_changes_total == dimensions_changed_total`
- `sum(transition_summary.values()) == dimensions_changed_total`
- `required_coverage_delta == sum(step required_coverage delta) == last_required_coverage_percentage - first_required_coverage_percentage`
- Every total equals the element-wise sum of the steps it aggregates (never independently recomputed)

### Service

`backend/app/services/prompt_readiness_timeline_service.py` - `PromptReadinessTimelineService(history_service, readiness_change_service)`

- `build_timeline(stored_filename, versions=None)` returns `video_filename`, `versions_analyzed`, `steps`, `timeline`, `summary`
- Raises `ValueError` for an invalid versions list (same three messages as Day 25) or a missing/deleted version (Day 16's message); the route maps these to 404
- Exactly two dependencies: the Day 16 store and the Day 26 diff service (never a second store)

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/readiness/timeline?versions=1,3,5
```

- Static route registered before numeric `{version}` routes so it can never collide with them; distinct from Day 25's `/prompt/history/readiness` and Day 26's `/compare/{version_a}/{version_b}/readiness`
- Valid request -> HTTP 200; malformed/empty/duplicate/non-positive `versions` -> 422; nonexistent or deleted version -> 404; nonexistent video -> 404; invalid extension -> 400; path traversal -> 404; a video with no saved versions -> 200 with an empty timeline (`steps: 0`, `timeline: []`, null coverages, zero totals)

### Determinism and Read-Only Behavior

- Repeated calls return byte-equivalent responses; no timestamps, UUIDs, random values, network, or filesystem data
- History records, prompts, favorites, tags, exports, and quality reports are byte-identical before and after any timeline request
- The timeline never creates, deletes, or renumbers versions, and never saves its own result
- No prompt text, filesystem paths, internal objects, or secrets appear in any response

### Limitations

- Informational chain only: it does not evaluate cinematography, aesthetics, or actual video content, and never predicts which prompt will generate better video
- Coverage deltas are arithmetic differences between independently computed coverages, not quality measurements; a positive or negative delta is never labeled an improvement or a regression
- A dimension counted as changed means the Day 24 state changed between those two versions (Day 26's exact rule), nothing more
- The timeline only ever compares consecutive selected versions; it never searches for a preferred pair

### Tests

- `tests/test_prompt_readiness_timeline_service.py` - 191 service tests (wiring and no-second-store checks, response structure, full 8-version chain verified against direct Day 26 outputs, selection subsets and requested order, validation messages, empty/single-version cases, aggregation invariants and telescoping delta across 7 selections, determinism, read-only integrity, no-ranking/no-leak scans, source contract)
- `tests/test_prompt_readiness_timeline_api.py` - 78 API tests (200/422/404/400 validation matrix, `versions` query parsing, every step byte-equal to the Day 26 endpoint, Day 21 ordering, determinism, integrity, route collision, Day 16-26 regressions, leak scans)

### Files Created/Modified

- `backend/app/services/prompt_readiness_timeline_service.py` - `PromptReadinessTimelineService`
- `backend/app/api/videos.py` - Added import, service instance, and static `GET .../prompt/history/readiness/timeline` route (registered before numeric `{version}` routes)
- `tests/test_prompt_readiness_timeline_service.py` - 191 service tests
- `tests/test_prompt_readiness_timeline_api.py` - 78 API tests

## Day 28 - Prompt Readiness Snapshot

Day 28 adds **Prompt Readiness Snapshot**: a deterministic, read-only service that answers one question for a saved prompt version - *"what is this version's current production readiness state, and how do the selected versions look in aggregate?"* Every per-version readiness block is produced by Day 24's exact `validate_prompt` result, every favorite/tag flag is Day 17's exact `get_organization` result, and Day 28 only assembles those values into a stable response shape plus neutral counts. It never ranks versions, never picks a best version, and never predicts which prompt will generate better video. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Produce one readiness snapshot per selected saved version: version metadata, Day 24 readiness states and raw scores, Day 17 favorite and tags
- Aggregate the selected snapshots into neutral counts: ready/needs-attention totals, required and supporting coverage sums, a nine-dimension summary, and favorite/tag counts
- Keep every per-version readiness block byte-equal to calling the Day 24 endpoint for that version directly
- Keep every favorite and tag flag byte-equal to calling the Day 17 organization endpoint for that version directly
- Reuse Day 16's single store read-only - no second store, no cache, no persisted snapshot

### Relationship With Day 16/17/21/24/25

- Day 16 `PromptHistoryService` is still the only version store; Day 28 calls only `list_versions` (default selection) and `get_version` (explicit selection), both read-only
- Day 24 `PromptReadinessService.validate_prompt` is the only readiness engine; Day 28 never recomputes states, scores, checklists, or coverage itself
- Day 17 `PromptOrganizationService.get_organization` is the only favorite/tag source; a version with no organization record yields `{"favorite": false, "tags": []}` (Day 17's default)
- Day 21 dimension order (7 required + 2 supporting) is preserved everywhere: `required`, `supporting`, `missing_dimensions`, `weak_dimensions`, and `dimension_summary`
- Day 25 provides the selection validation rules Day 28 mirrors exactly (same messages for empty, malformed, non-positive, and duplicate lists)
- The snapshot result is never persisted anywhere (no second store, no cache)

### Per-Version Snapshots

- One entry per selected version, in selection order, with exactly 7 keys: `version`, `source`, `operation`, `created_at`, `favorite`, `tags`, `readiness`
- `source`, `operation`, and `created_at` are the stored Day 16 record metadata (allowed); `favorite` and `tags` come from Day 17; nothing is invented
- Each `readiness` block has exactly 6 keys: `status`, `required_coverage_percentage`, `required` (7 dimensions), `supporting` (2 dimensions), `missing_dimensions`, `weak_dimensions`
- Each dimension maps to `{status, score}` exactly as Day 24's checklist produced it (statuses: `present`, `weak`, `missing`)

Example snapshot entry:

```json
{
  "version": 2,
  "source": "custom",
  "operation": "",
  "created_at": "2026-09-30T11:51:44.969917+00:00",
  "favorite": false,
  "tags": ["cinematic"],
  "readiness": {
    "status": "needs_attention",
    "required_coverage_percentage": 86,
    "required": {"subject": {"status": "present", "score": 100}, "action": {"status": "present", "score": 100}, "environment": {"status": "present", "score": 100}, "camera": {"status": "weak", "score": 40}, "lighting": {"status": "present", "score": 100}, "visual_style": {"status": "present", "score": 100}, "composition": {"status": "present", "score": 100}},
    "supporting": {"color": {"status": "present", "score": 100}, "audio": {"status": "present", "score": 100}},
    "missing_dimensions": [],
    "weak_dimensions": ["camera"]
  }
}
```

### Selection Rules

- No `versions` query: every live version, ascending version order
- `?versions=1,3,5`: only those versions, in the requested order - never sorted automatically, never substituted; a deleted or nonexistent requested version -> 404 (Day 16's exact message)
- Selection validation is byte-identical to Day 25: empty, malformed, non-integer, non-positive, or duplicate entries -> 422; whitespace around entries is tolerated; repeated `?versions=1&versions=3` equals `?versions=1,3`
- Default selection after a deletion simply skips deleted versions; an explicitly requested deleted version -> 404

### Summary (7 keys)

```json
{
  "versions_analyzed": 5,
  "ready_count": 1,
  "needs_attention_count": 4,
  "required": {"total": 35, "present": 20, "weak": 2, "missing": 13, "coverage_percentage": 57},
  "supporting": {"total": 10, "present": 6, "weak": 0, "missing": 4},
  "dimension_summary": [{"dimension": "subject", "present": 3, "weak": 1, "missing": 1}, "...": "9 rows in Day 21 order"],
  "organization": {"favorite_count": 1, "tag_counts": {"ai": 1, "cinematic": 1, "final": 1}}
}
```

- `ready_count + needs_attention_count == versions_analyzed`; required totals are `N x 7`, supporting totals are `N x 2`
- `required.coverage_percentage = round(present / total * 100)` (`null` when total is 0); each `dimension_summary` row sums to N
- `organization.favorite_count` counts selected versions currently favorited; `organization.tag_counts` maps each selected tag to how many selected versions carry it (alphabetical keys, each version counted once per tag)

### Service

`backend/app/services/prompt_readiness_snapshot_service.py` - `PromptReadinessSnapshotService(history_service, readiness_service, organization_service)`

- `create_snapshot(stored_filename, versions=None)` returns `video_filename`, `versions_analyzed`, `snapshots`, `summary`
- Raises `ValueError` for an invalid versions list (same three messages as Day 25) or a missing/deleted version (Day 16's message); the route maps these to 404
- Exactly three dependencies: the Day 16 store, the Day 24 readiness service, and the Day 17 organization service (never a second store, never Day 25/26/27 services)

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/readiness/snapshot?versions=1,3,5
```

- Static route registered before numeric `{version}` routes so it can never collide with them; distinct from Day 24's `/prompt/history/{version}/readiness`, Day 25's `/prompt/history/readiness`, Day 26's `/compare/{version_a}/{version_b}/readiness`, and Day 27's `/prompt/history/readiness/timeline`
- Valid request -> HTTP 200; malformed/empty/duplicate/non-positive `versions` -> 422; nonexistent or deleted version -> 404; nonexistent video -> 404; invalid extension -> 400; path traversal -> 404; a video with no saved versions -> 200 with an empty snapshot (`snapshots: []`, `versions_analyzed: []`, all-zero counts, `null` coverage, `dimension_summary: []`)
- A single selected version aggregates to exactly its own Day 24 result (required total 7, supporting total 2)

### Determinism and Read-Only Behavior

- Repeated calls return byte-equivalent responses; no random IDs or generated timestamps (only stored Day 16 `created_at` values)
- History records, prompts, favorites, tags, exports, and quality reports are byte-identical before and after any snapshot request
- The snapshot never creates, deletes, or renumbers versions, and never saves its own result
- No prompt text, filesystem paths, internal objects, or secrets appear in any response

### Limitations

- Informational assembly only: it does not evaluate cinematography, aesthetics, or actual video content, and never predicts which prompt will generate better video
- `ready` / `needs_attention` are Day 24 threshold labels restated, not judgments about video quality; counts are arithmetic sums, never scores or grades
- `favorite_count` and `tag_counts` are neutral tallies - a favorited version is not thereby "better", and tag frequency is not a recommendation
- The snapshot reflects only the selected versions; aggregates change with selection and are never comparable across different selections as rankings

### Tests

- `tests/test_prompt_readiness_snapshot_service.py` - 172 service tests (wiring and no-second-store checks, response structure, Day 24 exact cross-checks with raw-score spot checks, selection subsets and requested order, validation messages, empty/single-version cases, aggregate and dimension invariants across 8 selections, organization counts, determinism, read-only integrity, no-ranking/no-leak scans, source contract)
- `tests/test_prompt_readiness_snapshot_api.py` - 75 API tests (200/422/404/400 validation matrix, `versions` query parsing, per-version equality with Day 24 and Day 17 endpoints, aggregate equality with Day 25, dimension and organization verification, empty/single-version videos, determinism, integrity, route collision, Day 16-27 regressions, leak scans)

### Files Created/Modified

- `backend/app/services/prompt_readiness_snapshot_service.py` - `PromptReadinessSnapshotService`
- `backend/app/api/videos.py` - Added import, service instance, and static `GET .../prompt/history/readiness/snapshot` route (registered before numeric `{version}` routes)
- `tests/test_prompt_readiness_snapshot_service.py` - 172 service tests
- `tests/test_prompt_readiness_snapshot_api.py` - 75 API tests
- `backend/day28_e2e.py` - manual end-to-end verification script

## Day 29 - Prompt Readiness Report

Day 29 adds **Prompt Readiness Report**: a deterministic, read-only orchestration layer that combines existing readiness information into one structured report for a video, answering one question - *"what does the complete readiness report for these saved versions look like?"* The report carries the exact Day 28 per-version snapshots and aggregate summary, the exact Day 27 timeline steps and totals, and deterministic report metadata. It never ranks versions, never chooses a best or worst version, never recommends a version, never calls any number an improvement, and never predicts which prompt will generate better video. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Produce one structured report per selection: report metadata, per-version Day 24 readiness (via Day 28 snapshots), the Day 27 timeline of consecutive Day 26 diffs, and the Day 28 aggregate summary
- Keep every section byte-equal to the existing service output it reuses (Day 24/17 per version via Day 28, Day 26/27 for timeline steps, Day 28 for aggregation)
- Support the exact Day 25 `versions` selection semantics (requested order preserved, never substituted or reordered)
- Reuse the single Day 16 store read-only - no second store, no cache, no persisted report

### Report Structure (5 top-level keys)

```json
{
  "video_filename": "abc123.mp4",
  "versions_analyzed": [1, 3, 5],
  "report": {"...": "metadata + per-version snapshots, listed below"},
  "timeline": {"...": "Day 27 steps + neutral totals, listed below"},
  "summary": {"...": "the exact Day 28 aggregate summary"}
}
```

### Report Metadata

```json
{
  "type": "prompt_readiness_report",
  "version_count": 4,
  "first_version": 1,
  "last_version": 5,
  "selection_order": [1, 3, 4, 5],
  "snapshots": ["the exact Day 28 snapshot entries for the selection"]
}
```

- `type` is a fixed literal; `version_count`, `first_version`, `last_version`, and `selection_order` are derived only from the selected version numbers (first/last are `null` for an empty selection)
- `snapshots` is byte-equal to the Day 28 endpoint's `snapshots` list: each entry carries `version`, `source`, `operation`, `created_at` (stored Day 16 metadata), Day 17 `favorite`/`tags`, and the Day 24 readiness block (`status`, `required_coverage_percentage`, `required` 7 dimensions, `supporting` 2 dimensions, `missing_dimensions`, `weak_dimensions`) with raw Day 21 scores
- No report UUID, no creation timestamp, no random ID is ever generated - the report is a pure function of stored data

### Day 24/25/26/27/28 Reuse

- Day 28 `PromptReadinessSnapshotService` supplies `summary` and `report.snapshots` unchanged (it already holds the Day 16 store, Day 24 readiness service, and Day 17 organization service)
- Day 27 `PromptReadinessTimelineService` supplies `timeline.steps` and the timeline totals unchanged (it already holds the Day 16 store and the Day 26 change service)
- Both delegated services share one Day 16 store and apply identical Day 25 selection semantics, so their selections always agree; the report service itself holds only these two dependencies (minimal dependency graph)
- Day 24 readiness rules, Day 25 selection/aggregation, Day 26 transition semantics, Day 27 timeline semantics, and Day 28 snapshot semantics are never re-implemented or altered in this layer

### Timeline Section (7 keys)

```json
{
  "steps": ["one byte-equal Day 26 comparison per consecutive pair"],
  "changed_dimensions": 21,
  "unchanged_dimensions": 42,
  "required_changes": 17,
  "supporting_changes": 4,
  "transition_summary": {"missing_to_weak": 0, "missing_to_present": 9, "weak_to_missing": 2, "weak_to_present": 0, "present_to_missing": 7, "present_to_weak": 3},
  "required_coverage_delta": -14
}
```

- `steps` is byte-equal to the Day 27 endpoint's `timeline` list; the four counts and `transition_summary` are Day 27's summary totals; steps follow selection order (e.g. `versions=4,2,5` yields steps `4->2` and `2->5`, never resorted)
- `required_coverage_delta` equals the sum of every step's coverage delta, and for N >= 2 equals `coverage(last selected) - coverage(first selected)` (arithmetic only); it is `0` for a single selected version and `null` for zero versions

### Summary (7 keys)

The exact Day 28 aggregate: `versions_analyzed`, `ready_count`, `needs_attention_count`, `required` {total N x 7, present, weak, missing, coverage_percentage}, `supporting` {total N x 2, present, weak, missing}, `dimension_summary` (9 rows in Day 21 order, each row summing to N), and `organization` {favorite_count, tag_counts in alphabetical order, each tag counted at most once per version}.

### Selection Rules

- No `versions` query: every live version, ascending version order
- `?versions=1,3,5`: only those versions, in the requested order - never sorted automatically, never substituted; a deleted or nonexistent requested version -> 404 (Day 16's exact message)
- Selection validation is byte-identical to Day 25: empty, malformed, non-integer, non-positive, or duplicate entries -> 422; whitespace around entries is tolerated; repeated `?versions=1&versions=3` equals `?versions=1,3`

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/readiness/report?versions=1,3,5
```

- Static route registered before numeric `{version}` routes so it can never collide with them; distinct from Day 24's `/prompt/history/{version}/readiness`, Day 25's `/prompt/history/readiness`, Day 26's `/compare/{version_a}/{version_b}/readiness`, Day 27's `/prompt/history/readiness/timeline`, and Day 28's `/prompt/history/readiness/snapshot`
- Valid request -> HTTP 200; malformed/empty/duplicate/non-positive `versions` -> 422; nonexistent or deleted version -> 404; nonexistent video -> 404; invalid extension -> 400; path traversal -> 404; a video with no saved versions -> 200 with an empty report (`versions_analyzed: []`, metadata nulls, zero timeline counts with `null` delta, all-zero summary with `null` coverage and empty `dimension_summary`)
- A single selected version yields `version_count: 1`, an empty zero-step timeline with delta `0`, and a summary exactly matching that version

### Determinism and Read-Only Behavior

- Repeated calls return byte-equivalent responses; no generated timestamps, UUIDs, or random values (only stored Day 16 `created_at` values)
- History records, prompts, favorites, tags, exports, and quality reports are byte-identical before and after any report request
- The report never creates, deletes, or renumbers versions, and never saves its own result
- No prompt text, filesystem paths, internal objects, or secrets appear in any response

### Limitations

- Informational aggregation only: it does not evaluate cinematography, aesthetics, or actual video content, and never predicts which prompt will generate better video
- `ready`/`needs_attention` counts, coverage values, and timeline deltas are Day 24/26 arithmetic restated, never judgments, grades, or labels like improvement or regression
- Favorite and tag counts are neutral tallies - a favorited version is not thereby preferred, and tag frequency is not a recommendation
- The report reflects only the selected versions; aggregates change with selection and are never comparable across different selections as rankings

### Tests

- `tests/test_prompt_readiness_report_service.py` - 210 service tests (wiring and single-store checks, response structure, Day 24/17/26/27/28 byte-equivalence, selection subsets and requested order, timeline and summary invariants with coverage telescoping, organization counts, empty/single-version cases, validation messages, determinism, read-only integrity, no-ranking/no-leak scans, source contract)
- `tests/test_prompt_readiness_report_api.py` - 85 API tests (200/422/404/400 validation matrix, `versions` query parsing, Day 24/27/28 endpoint equivalence, aggregates, empty/single-version videos, determinism, integrity, route collision, Day 16-28 regressions, leak scans)

### Files Created/Modified

- `backend/app/services/prompt_readiness_report_service.py` - `PromptReadinessReportService`
- `backend/app/api/videos.py` - Added import, service instance, and static `GET .../prompt/history/readiness/report` route (registered before numeric `{version}` routes)
- `tests/test_prompt_readiness_report_service.py` - 210 service tests
- `tests/test_prompt_readiness_report_api.py` - 85 API tests
- `backend/day29_e2e.py` - manual end-to-end verification script

## Day 30 - Prompt Readiness Report Export

Day 30 adds **Prompt Readiness Report Export**: deterministic, read-only serialization of the existing Day 29 Prompt Readiness Report into downloadable JSON, Markdown, or plain text. The export represents the Day 29 report exactly - it never alters report data, never rebuilds any readiness calculation, and never persists anything to disk. This is not an LLM feature; no external AI/API/model is called.

### Purpose

- Serialize one Day 29 report (metadata, per-version snapshots, timeline, aggregate summary) in three human- and machine-readable formats
- Reuse `PromptReadinessReportService` unchanged: no duplicate Day 24 readiness, Day 25 aggregation, Day 26 transitions, Day 27 timeline, or Day 28 snapshot logic exists in the export layer
- Keep output fully deterministic: the same stored selection always produces byte-identical content and the same filename

### Supported Formats

| Format | Media type | Filename |
|---|---|---|
| `json` | `application/json` | `visionprompt_readiness_report.json` |
| `markdown` | `text/markdown` | `visionprompt_readiness_report.md` |
| `txt` | `text/plain` | `visionprompt_readiness_report.txt` |

- Any other format value (including empty or wrong-case like `JSON`) -> HTTP 422 with Day 19's exact message: `Invalid format. Must be one of: json, markdown, txt`
- All content is UTF-8; responses carry `Content-Disposition: attachment; filename=...` and are streamed directly from memory (no file is written anywhere)

### JSON Structure

JSON serializes the complete Day 29 report - all five top-level keys (`video_filename`, `versions_analyzed`, `report`, `timeline`, `summary`) and every nested field, with no fields omitted or invented:

```json
{
  "video_filename": "...",
  "versions_analyzed": [1, 3, 5],
  "report": {"type": "...", "version_count": 3, "first_version": 1, "last_version": 5, "selection_order": [1, 3, 5], "snapshots": ["..."]},
  "timeline": {"steps": ["..."], "changed_dimensions": ..., "unchanged_dimensions": ..., "required_changes": ..., "supporting_changes": ..., "transition_summary": {"...": 0}, "required_coverage_delta": -86},
  "summary": {"versions_analyzed": ..., "ready_count": ..., "needs_attention_count": ..., "required": {"...": ...}, "supporting": {"...": ...}, "dimension_summary": ["..."], "organization": {"favorite_count": ..., "tag_counts": {"...": ...}}}
}
```

- Deterministic formatting: UTF-8, `indent=2`, stable key order (report dict order), trailing newline, no random values
- `json.loads(json_export) == GET .../readiness/report` for every selection (semantically and structurally equivalent)

### Markdown Structure

Human-readable `# Prompt Readiness Report` document with four `##` sections, containing all report information as factual data only:

- `## Report` - video filename, type, versions analyzed, version count, first/last version, selection order
- `## Version Readiness` - one `### Version N` block per snapshot: source, operation, created at, favorite, tags, status, required coverage, `#### Required Dimensions` table (7 rows), `#### Supporting Dimensions` table (2 rows), missing/weak dimension lists
- `## Timeline` - one `### Step i: Version A -> Version B` block per consecutive pair (versions A/B metadata, changed/unchanged counts, required/supporting changes, per-dimension `#### Step Dimensions` table, `#### Transitions`, `#### Transition Summary`), plus `### Timeline Summary` (changed/unchanged totals, required/supporting change totals, transition summary, required coverage delta)
- `## Summary` - `### Readiness`, `### Required`, `### Supporting` counts, `### Dimension Summary` table (9 rows in Day 21 order), `### Organization` (favorite count, tag counts alphabetically)

No evaluative commentary is ever written - only the report's own values.

### TXT Structure

Plain-text equivalent with `PROMPT READINESS REPORT` title and underlined `REPORT`, `VERSION READINESS`, `TIMELINE`, `SUMMARY` sections. Each version appears as a `VERSION N` block with `REQUIRED DIMENSIONS` / `SUPPORTING DIMENSIONS` lines (`dimension: status (score)`), timeline steps use ASCII `->` arrows with `STEP DIMENSIONS`, `TRANSITIONS`, `TRANSITION SUMMARY`, `TIMELINE SUMMARY` blocks, and the summary carries `DIMENSION SUMMARY` / `ORGANIZATION` blocks. Same factual information as Markdown; no prompt text, no internal objects, no absolute paths, no secrets.

### Selection Semantics

Byte-identical to Day 25/27/28/29 (delegated, never reimplemented):

- No `versions` query: every live version, ascending version order
- `?versions=1,3,5`: only those versions, in the requested order - never sorted, never substituted
- Repeated `?versions=1&versions=3` equals `?versions=1,3`; whitespace around entries tolerated
- Empty, malformed, non-integer, non-positive, or duplicate entries -> 422; missing or deleted version -> 404 (Day 16's exact message); nonexistent video -> 404; invalid extension -> 400; path traversal -> 404
- A video with no saved versions exports an empty report with HTTP 200 (zero counts, `null` coverage/delta in JSON, `No saved versions.` in Markdown/TXT)

### Filenames and Media Types

- Stable filenames only: `visionprompt_readiness_report.json` / `.md` / `.txt` - never derived from user input, never contain random IDs or version lists
- Media types as listed in the table above; responses are `Content-Disposition: attachment` downloads rendered in memory

### Determinism

- Repeated export calls (any format, any selection) produce byte-identical content, `Content-Type`, and `Content-Disposition`
- No generated timestamps, UUIDs, or random values: the only time values are each snapshot's stored Day 16 `created_at`

### Read-Only Behavior

- Export never modifies prompt history, favorites, tags, quality results, Day 19 prompt exports, or Day 20 packages; never creates, deletes, or renumbers versions
- No filesystem persistence: nothing is written to storage (or anywhere else); no second store, no cache, no saved export results
- The Day 29 report service is called read-only; its output is rendered to a string and returned

### Limitations

- Serialization only: it does not recompute, reinterpret, or extend readiness data, and never evaluates which version is better/worse or recommends a version
- Markdown/TXT present every report value as neutral text; they carry no analysis beyond what Day 29 already reports
- Exports reflect only the selected versions and are identical in content to the report endpoint for the same selection

### Endpoint

```
GET /api/videos/{stored_filename}/prompt/history/readiness/report/export?format=json[&versions=1,3,5]
```

- Static route registered before numeric `{version}` routes; distinct from Day 19's `.../{version}/export` and Day 29's `.../readiness/report`
- Query: `format` required (`json` | `markdown` | `txt`), `versions` optional (same rules as Day 29)
- 200 with rendered content + media type + filename; 422 invalid format or versions; 404 missing/deleted version or unknown video; 400 invalid extension

### Tests

- `tests/test_prompt_readiness_export_service.py` - 450 service tests (wiring/single-store, envelope, JSON structure and Day 29 equivalence, Markdown structure and leaf completeness, TXT structure and leaf completeness, empty history, single version, selection, validation messages, determinism, read-only integrity, no-ranking/leak scans, source contract)
- `tests/test_prompt_readiness_export_api.py` - 208 API tests (200s, media types, Content-Disposition, semantic equivalence with Day 29, selections, repeated/whitespace params, empty/single, full validation matrix, determinism, read-only/no-file checks, route collision, Day 16-29 regression, leak scans)

### Files Created/Modified

- `backend/app/services/prompt_readiness_export_service.py` - `PromptReadinessExportService`
- `backend/app/api/videos.py` - Added import, service instance, and static `GET .../prompt/history/readiness/report/export` route (registered before numeric `{version}` routes)
- `tests/test_prompt_readiness_export_service.py` - 450 service tests
- `tests/test_prompt_readiness_export_api.py` - 208 API tests
- `backend/day30_e2e.py` - manual end-to-end verification script

## Phase 2 - Advanced Video Intelligence

Phase 2 extends the MVP with advanced, provider-aware analysis features implemented strictly in order (P2-01 through P2-13). Every feature reuses the existing service layer, keeps a single source of truth, never fabricates AI output, distinguishes observed vs estimated vs unavailable information, and reports explicit provider status with confidence/uncertainty.

### P2-01 - Video-to-Video Prompt Reconstruction

- Reconstructs a structured analysis report and a production-ready prompt directly from a stored video - no saved prompt required
- Reuses Day 12 unified intelligence, Day 13 advanced prompt generation, Day 21 quality, and Day 24 readiness; reserves slots for P2-02..P2-06 services (wired in later phases)
- Every one of the 12 analysis domains (shots, subjects, actions, environment, camera, lens, lighting, color, composition, visual_style, audio, characters) reports availability as `observed`, `estimated`, or `unavailable` with source, confidence, and note
- AI safety: empty intelligence fields become explicit `unavailable` blocks with notes - no invented visual details; `provider_status` surfaces configured vision/audio providers (local mock by default) and mock usage appears in `confidence.uncertainty_notes`
- `confidence` partitions all 12 domains into observed/estimated/unavailable lists with an overall rating (high <= 2 unavailable, medium <= 6, low otherwise)
- Deterministic: same video + params produce identical output; read-only - no prompt history, favorites, or storage side effects

### Endpoint

```
POST /api/videos/{stored_filename}/prompt/reconstruct?depth=standard&style=cinematic
```

- Query: `depth` (`quick` | `standard` | `deep` - maps to 2/10/25 analyzed frames, default standard), `style` (`cinematic` | `realistic` | `commercial`, default cinematic)
- 200 with success envelope + video_information + analysis + provider_status + confidence + prompt + quality + readiness; 400 invalid depth/style/filename; 404 missing video
- Static path segment; no conflict with numeric `{version}` routes

### Tests

- `tests/test_video_reconstruction_service.py` - 101 service tests (validation and order, depth-to-frame mapping, result shape, rich/sparse intelligence honesty, audio notes, provider status, confidence summary boundaries, optional service wiring, upstream error propagation, determinism, no-leak/no-side-effect, real stack)
- `tests/test_video_reconstruction_api.py` - 56 API tests (happy path, full validation matrix, response structure, AI-safety unavailable blocks, style wording, determinism, read-only storage/history/favorites, multi-video isolation, Day 1-30 regression)

### Files Created/Modified

- `backend/app/services/video_reconstruction_service.py` - `VideoReconstructionService` with `reconstruct()`, `VALID_DEPTHS`, `DEPTH_MAX_FRAMES`
- `backend/app/api/videos.py` - Added import, `reconstruction_service` instance, and `POST .../prompt/reconstruct` route
- `tests/test_video_reconstruction_service.py` - 101 service tests
- `tests/test_video_reconstruction_api.py` - 56 API tests
- `backend/phase2_e2e.py` - progressive Phase 2 manual E2E script (MVP regression + P2-01..P2-13 sections)
