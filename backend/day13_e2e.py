import json, os, subprocess, tempfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day13_e2e.mp4')

# Video with audio so audio analysis has real data
subprocess.run(
    [ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-y', tmp],
    capture_output=True, timeout=15,
)

# 1. Upload
with open(tmp, 'rb') as f:
    r = client.post('/api/videos/upload', files={'file': ('test.mp4', f, 'video/mp4')})
assert r.status_code == 200, r.text
stored = r.json()['video']['stored_filename']
print(f'1. Upload: OK ({stored})')

# 2. Extract frames
r2 = client.post(f'/api/videos/{stored}/frames/extract?interval_seconds=1')
assert r2.status_code == 200, r2.text
print(f'2. Extract frames: OK ({r2.json()["frame_count"]} frames)')

# 3. Visual analysis
r3 = client.post(f'/api/videos/{stored}/analyze?max_frames=5')
assert r3.status_code == 200, r3.text
assert r3.json()['success'] is True
print('3. Visual analysis: OK')

# 4. Scene detection
r4 = client.post(f'/api/videos/{stored}/scenes/detect')
assert r4.status_code == 200, r4.text
d4 = r4.json()
assert d4['scenes_detected'] >= 1
print(f'4. Scene detection: OK ({d4["scenes_detected"]} scenes)')

# 5. Subject analysis
r5 = client.post(f'/api/videos/{stored}/subjects/analyze')
assert r5.status_code == 200, r5.text
print('5. Subject analysis: OK')

# 6. Audio analysis
r6 = client.post(f'/api/videos/{stored}/audio/analyze')
assert r6.status_code == 200, r6.text
d6 = r6.json()
assert d6['has_audio'] is True
print(f'6. Audio analysis: OK (has_audio={d6["has_audio"]}, provider={d6["provider"]})')

# 7. Day 12 intelligence
r7 = client.post(f'/api/videos/{stored}/intelligence')
assert r7.status_code == 200, r7.text
d7 = r7.json()
assert d7['success'] is True
for key in ['video_filename', 'duration_seconds', 'visual', 'scenes', 'subjects', 'audio']:
    assert key in d7, f'missing {key}'
print('7. Day 12 intelligence: OK')

# 8. Day 13 advanced prompt - all three styles
EXPECTED_SECTIONS = ['subject', 'action', 'environment', 'camera', 'lighting',
                     'visual_style', 'color', 'audio', 'composition']
forbidden = ['person', 'character', 'dialogue', 'walking', 'running', 'park',
             'city', 'sunset', 'music', 'orchestral', 'voiceover']
prompts = {}
for style in ['cinematic', 'realistic', 'commercial']:
    r8 = client.post(f'/api/videos/{stored}/advanced-prompt?style={style}')
    assert r8.status_code == 200, f'{style}: {r8.status_code} {r8.text}'
    d8 = r8.json()
    assert d8['success'] is True, d8
    assert d8['style'] == style, d8['style']
    assert d8['video_filename'] == stored
    assert isinstance(d8['prompt'], str) and d8['prompt'], 'empty prompt'
    assert isinstance(d8['negative_prompt'], str) and d8['negative_prompt']
    for section in EXPECTED_SECTIONS:
        assert section in d8['sections'], f'{style}: missing section {section}'
    # No absolute filesystem paths
    serialized = json.dumps(d8)
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in serialized, f'{style}: absolute path {bad}'
    assert not d8['video_filename'].startswith('/')
    # No fabricated content (mock providers return empty subjects/actions)
    full_text = ' '.join(d8['sections'].values()).lower()
    for word in forbidden:
        assert word not in full_text, f'{style}: fabricated "{word}" in: {full_text}'
    # Generic negative prompt only
    neg = d8['negative_prompt'].lower()
    assert 'blurry' in neg and 'watermark' in neg
    for word in ['person', 'dialogue', 'park']:
        assert word not in neg, f'{style}: content-specific negative'
    prompts[style] = d8['prompt']
    print(f'8.{style}: OK prompt="{d8["prompt"][:80]}..."')

# All three styles produce distinct prompts
assert len(set(prompts.values())) == 3, 'styles should produce distinct prompts'
print('   All three styles distinct: OK')

# Deterministic: same style twice = same output
ra = client.post(f'/api/videos/{stored}/advanced-prompt?style=cinematic')
rb = client.post(f'/api/videos/{stored}/advanced-prompt?style=cinematic')
assert ra.json()['prompt'] == rb.json()['prompt']
print('   Deterministic output: OK')

# Invalid style -> 400
rinv = client.post(f'/api/videos/{stored}/advanced-prompt?style=anime')
assert rinv.status_code == 400, rinv.status_code
print(f'   Invalid style rejected: OK ({rinv.status_code})')

# Nonexistent video -> 404
r404 = client.post('/api/videos/nonexistent.mp4/advanced-prompt')
assert r404.status_code == 404, r404.status_code
print(f'   Nonexistent video: OK ({r404.status_code})')

# Path traversal -> rejected
rpt = client.post('/api/videos/../../../etc/passwd/advanced-prompt')
assert rpt.status_code in (400, 404), rpt.status_code
print(f'   Path traversal rejected: OK ({rpt.status_code})')

# Previous endpoints still work
assert client.get('/api/health').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt?style=cinematic').status_code == 200
assert client.post(f'/api/videos/{stored}/intelligence').status_code == 200
print('9. Previous endpoints still work: OK')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 13 MANUAL E2E VERIFICATIONS PASSED')
