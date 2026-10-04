import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from app.services.shot_detection_service import ShotDetectionService
from PIL import Image

# Create a test video and extract frames via the API approach
import imageio_ffmpeg
import subprocess
import tempfile

tmpvid = os.path.join(tempfile.gettempdir(), "debug_video.mp4")
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ffmpeg, "-f", "lavifi", "-i", "color=c=blue:s=320x240:d=3", "-y", tmpvid], capture_output=True, timeout=15)

# Upload via the app
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

with open(tmpvid, "rb") as f:
    r = client.post("/api/videos/upload", files={"file": ("test.mp4", f, "video/mp4")})
print("Upload:", r.status_code)
stored = r.json()["video"]["stored_filename"]

# Extract frames
r = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds=1")
print("Extract:", r.status_code)

# Now check frame dir and call service
video_id = stored.rsplit(".", 1)[0]
frame_dir = os.path.join("storage", "frames", video_id)
print("Frame dir:", frame_dir)
print("Files:", os.listdir(frame_dir) if os.path.isdir(frame_dir) else "NOSUCHDIR")

# Create a couple of additional frames if needed
os.makedirs(frame_dir, exist_ok=True)
for i in range(1, 4):
    fname = os.path.join(frame_dir, f"frame_{i:06d}.jpg")
    if not os.path.exists(fname):
        img = Image.new("RGB", (32, 32), color="blue")
        img.save(fname)

# Now call the service directly
svc = ShotDetectionService()
frame_filenames = [
    {
        "filename": "frame_000001.jpg",
        "timestamp_seconds": 0.0,
        "path": os.path.join(frame_dir, "frame_000001.jpg").replace("\\", "/"),
    },
    {
        "filename": "frame_000002.jpg",
        "timestamp_seconds": 1.0,
        "path": os.path.join(frame_dir, "frame_000002.jpg").replace("\\", "/"),
    },
]

try:
    result = svc.detect_shots(
        stored_filename=stored,
        frame_filenames=frame_filenames,
        video_duration=3.0,
    )
    print("Success:", result["shots_detected"], "shots")
except Exception as e:
    print("Error:", type(e).__name__, ":", e)
    import traceback
    traceback.print_exc()