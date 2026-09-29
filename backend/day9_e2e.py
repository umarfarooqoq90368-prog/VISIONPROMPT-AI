import os, subprocess, tempfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day9_e2e.mp4')
subprocess.run([ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5', '-y', tmp], capture_output=True, timeout=10)

# Upload
with open(tmp, 'rb') as f:
    r = client.post('/api/videos/upload', files={'file': ('test.mp4', f, 'video/mp4')})
assert r.status_code == 200
stored = r.json()['video']['stored_filename']
print(f'1. Upload: OK ({stored})')

# Extract frames
r2 = client.post(f'/api/videos/{stored}/frames/extract?interval_seconds=1')
assert r2.status_code == 200
print(f'2. Extract frames: OK ({r2.json()["frame_count"]} frames)')

# Scene detection (default params)
r3 = client.post(f'/api/videos/{stored}/scenes/detect')
assert r3.status_code == 200, f"Expected 200, got {r3.status_code}: {r3.json()}"
d3 = r3.json()
assert d3['success'] is True
assert d3['scenes_detected'] >= 1
assert len(d3['scenes']) == d3['scenes_detected']
print(f'3. Scene detection (default): OK ({d3["scenes_detected"]} scenes)')

# Verify chronological ordering
scenes = d3['scenes']
for i in range(len(scenes) - 1):
    assert scenes[i]['start_time'] < scenes[i]['end_time']
    assert scenes[i]['end_time'] <= scenes[i + 1]['start_time']
print('   Chronological ordering: OK')

# Verify timestamps
for s in scenes:
    assert s['start_time'] >= 0
    assert s['end_time'] <= d3['duration_seconds'] + 0.1
    assert s['duration'] > 0
print('   Valid timestamps: OK')

# Verify representative frames
for s in scenes:
    assert s['representative_frame'] != ''
    assert s['representative_frame'].endswith('.jpg')
print('   Representative frames: OK')

# Verify no absolute paths
for s in scenes:
    assert not s['start_frame'].startswith('/')
    assert not s['end_frame'].startswith('/')
    assert not s['representative_frame'].startswith('/')
print('   No absolute paths: OK')

# First scene has null change_score
assert scenes[0]['change_score_from_previous'] is None
print('   First scene change_score is null: OK')

# Scene detection with custom params
r4 = client.post(f'/api/videos/{stored}/scenes/detect?sample_interval_seconds=1&threshold=0.5')
assert r4.status_code == 200
d4 = r4.json()
assert d4['success'] is True
assert d4['scenes_detected'] >= 1
print(f'4. Scene detection (custom params): OK ({d4["scenes_detected"]} scenes)')

# Path traversal protection
r5 = client.post('/api/videos/../../../etc/passwd/scenes/detect')
assert r5.status_code == 404
print('5. Path traversal protection: OK (404)')

# Previous endpoints still work
r6 = client.get('/api/health')
assert r6.status_code == 200
r7 = client.get(f'/api/videos/{stored}/metadata')
assert r7.status_code == 200
print('6. Previous endpoints still work: OK')

print('\nALL MANUAL E2E VERIFICATIONS PASSED')

if os.path.exists(tmp): os.remove(tmp)
