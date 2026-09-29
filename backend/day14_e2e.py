import json, os, subprocess, tempfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day14_e2e.mp4')

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
assert r4.json()['scenes_detected'] >= 1
print(f'4. Scene detection: OK ({r4.json()["scenes_detected"]} scenes)')

# 5. Subject analysis
r5 = client.post(f'/api/videos/{stored}/subjects/analyze')
assert r5.status_code == 200, r5.text
print('5. Subject analysis: OK')

# 6. Audio analysis
r6 = client.post(f'/api/videos/{stored}/audio/analyze')
assert r6.status_code == 200, r6.text
assert r6.json()['has_audio'] is True
print(f'6. Audio analysis: OK (provider={r6.json()["provider"]})')

# 7. Day 12 intelligence
r7 = client.post(f'/api/videos/{stored}/intelligence')
assert r7.status_code == 200, r7.text
d7 = r7.json()
assert d7['success'] is True
for key in ['video_filename', 'duration_seconds', 'visual', 'scenes', 'subjects', 'audio']:
    assert key in d7, f'missing {key}'
print('7. Day 12 intelligence: OK')

# 8. Day 13 advanced prompt (all three styles)
for style in ['cinematic', 'realistic', 'commercial']:
    r8 = client.post(f'/api/videos/{stored}/advanced-prompt?style={style}')
    assert r8.status_code == 200, f'{style}: {r8.status_code}'
    assert r8.json()['success'] is True
print('8. Day 13 advanced prompt: OK (3 styles)')

# 9. Day 14 prompt refinement - all six operations
OPERATIONS = ['refine', 'shorten', 'expand', 'cinematic', 'realistic', 'commercial']
REQUIRED_KEYS = ['success', 'message', 'video_filename', 'operation',
                 'source_prompt', 'refined_prompt', 'negative_prompt',
                 'preserved_information']
results = {}
for op in OPERATIONS:
    r9 = client.post(f'/api/videos/{stored}/prompt/refine', json={'operation': op})
    assert r9.status_code == 200, f'{op}: {r9.status_code} {r9.text}'
    d9 = r9.json()
    for key in REQUIRED_KEYS:
        assert key in d9, f'{op}: missing {key}'
    assert d9['success'] is True
    assert d9['operation'] == op
    assert d9['video_filename'] == stored
    assert isinstance(d9['source_prompt'], str) and d9['source_prompt'], f'{op}: empty source'
    assert isinstance(d9['refined_prompt'], str) and d9['refined_prompt'], f'{op}: empty refined'
    assert d9['preserved_information'] is True, f'{op}: information not preserved'
    # No absolute filesystem paths
    serialized = json.dumps(d9)
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in serialized, f'{op}: absolute path {bad}'
    assert not d9['video_filename'].startswith('/')
    # No fabricated information (mock providers return empty subjects/actions)
    text = d9['refined_prompt'].lower()
    for word in ['person', 'character', 'dialogue', 'walking', 'running',
                 'park', 'city', 'sunset', 'brand', 'product', 'voiceover']:
        assert word not in text, f'{op}: fabricated "{word}"'
    # Generic negative prompt
    neg = d9['negative_prompt'].lower()
    assert 'blurry' in neg and 'watermark' in neg
    assert 'person' not in neg
    results[op] = d9
    print(f'9.{op}: OK source="{d9["source_prompt"][:60]}..." -> refined="{d9["refined_prompt"][:60]}..."')

# Source prompt preserved (identical across operations)
sources = {d['source_prompt'] for d in results.values()}
assert len(sources) == 1, 'source prompt should be identical across operations'
source_prompt = sources.pop()
print('   Source prompt preserved across all operations: OK')

# Factual content preserved in refined outputs
for op, d in results.items():
    for fact in ['Scene progression', 'scenes']:
        assert fact in d['refined_prompt'], f'{op}: lost fact "{fact}"'
print('   Factual information preserved: OK')

# shorten is actually shorter; expand is more structured
assert len(results['shorten']['refined_prompt']) < len(source_prompt), 'shorten should be shorter'
assert ';' not in results['refine']['refined_prompt'], 'refine should remove semicolons'
assert results['commercial']['refined_prompt'] != results['realistic']['refined_prompt']
print('   Operation effects distinct: OK')

# Deterministic
d1 = client.post(f'/api/videos/{stored}/prompt/refine', json={'operation': 'refine'}).json()
d2 = client.post(f'/api/videos/{stored}/prompt/refine', json={'operation': 'refine'}).json()
assert d1['refined_prompt'] == d2['refined_prompt']
print('   Deterministic output: OK')

# Invalid operation -> 400
r_inv = client.post(f'/api/videos/{stored}/prompt/refine', json={'operation': 'reformat'})
assert r_inv.status_code == 400, r_inv.status_code
print(f'   Invalid operation rejected: OK ({r_inv.status_code})')

# Missing operation -> 422
r_missing = client.post(f'/api/videos/{stored}/prompt/refine', json={})
assert r_missing.status_code == 422, r_missing.status_code
print(f'   Missing operation rejected: OK ({r_missing.status_code})')

# Nonexistent video -> 404
r_404 = client.post('/api/videos/nonexistent.mp4/prompt/refine', json={'operation': 'refine'})
assert r_404.status_code == 404, r_404.status_code
print(f'   Nonexistent video: OK ({r_404.status_code})')

# Path traversal -> rejected
r_pt = client.post('/api/videos/../../../etc/passwd/prompt/refine', json={'operation': 'refine'})
assert r_pt.status_code in (400, 404), r_pt.status_code
print(f'   Path traversal rejected: OK ({r_pt.status_code})')

# 10. Previous Day 1-13 endpoints still work
assert client.get('/api/health').status_code == 200
assert client.get(f'/api/videos/{stored}/metadata').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt?style=cinematic').status_code == 200
assert client.post(f'/api/videos/{stored}/scenes/detect').status_code == 200
assert client.post(f'/api/videos/{stored}/subjects/analyze').status_code == 200
assert client.post(f'/api/videos/{stored}/audio/analyze').status_code == 200
assert client.post(f'/api/videos/{stored}/intelligence').status_code == 200
assert client.post(f'/api/videos/{stored}/advanced-prompt?style=cinematic').status_code == 200
print('10. Previous Day 1-13 endpoints still work: OK')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 14 MANUAL E2E VERIFICATIONS PASSED')
