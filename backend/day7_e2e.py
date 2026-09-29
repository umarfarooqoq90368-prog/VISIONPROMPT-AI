import os, subprocess, tempfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day7_e2e.mp4')
subprocess.run([ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5', '-y', tmp], capture_output=True, timeout=10)

# Upload
with open(tmp, 'rb') as f:
    r = client.post('/api/videos/upload', files={'file': ('test.mp4', f, 'video/mp4')})
assert r.status_code == 200
stored = r.json()['video']['stored_filename']
print(f'Upload: {stored}')

# Extract frames
r2 = client.post(f'/api/videos/{stored}/frames/extract?interval_seconds=1')
assert r2.status_code == 200
print(f'Extract: {r2.json()["frame_count"]} frames')

# Analyze
r3 = client.post(f'/api/videos/{stored}/analyze?max_frames=5')
assert r3.status_code == 200
d3 = r3.json()
print(f'Analyze: success={d3["success"]}, frames={d3["frames_analyzed"]}')

# Prompt: cinematic
r4 = client.post(f'/api/videos/{stored}/prompt?style=cinematic')
assert r4.status_code == 200
d4 = r4.json()
assert d4['success'] is True
assert d4['style'] == 'cinematic'
assert d4['prompt']
assert d4['negative_prompt'] is None
assert not d4['prompt'].startswith('/')
assert '\\' not in d4['prompt']
assert '{' not in d4['prompt']
assert '}' not in d4['prompt']
print(f'Prompt(cinematic): {d4["prompt"][:80]}...')

# Prompt: realistic
r5 = client.post(f'/api/videos/{stored}/prompt?style=realistic')
assert r5.status_code == 200
d5 = r5.json()
assert d5['style'] == 'realistic'
assert d5['prompt']
print(f'Prompt(realistic): OK')

# Prompt: commercial
r6 = client.post(f'/api/videos/{stored}/prompt?style=commercial')
assert r6.status_code == 200
d6 = r6.json()
assert d6['style'] == 'commercial'
assert d6['prompt']
print(f'Prompt(commercial): OK')

# Invalid style
r7 = client.post(f'/api/videos/{stored}/prompt?style=fantasy')
assert r7.status_code == 400
print(f'Invalid style: 400 OK')

# Nonexistent video
r8 = client.post('/api/videos/nonexistent.mp4/prompt')
assert r8.status_code == 404
print(f'Nonexistent video: 404 OK')

print()
print('ALL MANUAL E2E VERIFICATIONS PASSED')

if os.path.exists(tmp): os.remove(tmp)
