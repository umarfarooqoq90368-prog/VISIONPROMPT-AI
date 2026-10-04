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

try:
    result = ShotDetectionService().detect_shots(
        stored_filename="test_video.mp4",
        frame_filenames=frame_filenames,
        video_duration=3.0,
    )
    print("Success:", result["shots_detected"], "shots")
except ValueError as e:
    print("ValueError:", e)
except Exception as e:
    print(type(e).__name__, ":", e)