import pathlib

p = pathlib.Path("README.md")
content = p.read_text(encoding="utf-8")

day11 = """

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
"""

p.write_text(content + day11, encoding="utf-8")
print("README.md updated successfully")
