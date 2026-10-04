import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# First create a test video and upload
import imageio_ffmpeg
import subprocess
import tempfile

tmpvid = os.path.join(tempfile.gettempdir(), "test_api.mp4")
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=3", "-y", tmpvid], capture_output=True, timeout=15)

with open(tmpvid, "rb") as f:
    r = client.post("/api/videos/upload", files={"file": ("test.mp4", f, "video/mp4")})
print("Upload:", r.status_code, r.json()["video"]["stored_filename"])
stored = r.json()["video"]["stored_filename"]

r = client.post(f"/api/videos/{stored}/frames/extract?interval_seconds=1")
print("Extract:", r.status_code)

# Now try shot detect
r = client.post(f"/api/videos/{stored}/shots/detect?sample_interval_seconds=1.0&threshold=0.40&max_shots=100")
print("Shot detect:", r.status_code)
print("Response:", r.text[:500])