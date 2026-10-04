import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from app.services.shot_detection_service import ShotDetectionService

frame_filenames = [
    {
        "filename": "frame_000001.jpg",
        "timestamp_seconds": 0.0,
        "path": "storage/frames/test/frame_000001.jpg",
    },
    {
        "filename": "frame_000002.jpg",
        "timestamp_seconds": 1.0,
        "path": "storage/frames/test/frame_000002.jpg",
    },
]

svc = ShotDetectionService()

# Step through validation manually
valid_frames = []
for i, f in enumerate(frame_filenames):
    print(f"Validating frame {i}:")
    print(f"  isinstance dict: {isinstance(f, dict)}")
    print(f"  has filename: {'filename' in f}")
    print(f"  has timestamp: {'timestamp_seconds' in f}")
    print(f"  filename type: {type(f.get('filename'))}, value: {f.get('filename')!r}, bool: {bool(f.get('filename'))}")
    print(f"  timestamp type: {type(f.get('timestamp_seconds'))}, value: {f.get('timestamp_seconds')!r}")
    try:
        is_valid = True
        if not isinstance(f, dict):
            raise ValueError(f"Invalid frame data at index {i}.")
        if "filename" not in f or "timestamp_seconds" not in f:
            raise ValueError(f"Frame {i} missing required keys")
        if not isinstance(f["filename"], str) or not f["filename"]:
            raise ValueError(f"Frame {i} has an invalid filename.")
        if not isinstance(f["timestamp_seconds"], (int, float)):
            raise ValueError(f"Frame {i} has an invalid timestamp.")
        valid_frames.append(f)
        print(f"  -> PASSED, added to valid_frames")
    except ValueError as e:
        print(f"  -> FAILED: {e}")

print(f"\nvalid_frames count: {len(valid_frames)}")