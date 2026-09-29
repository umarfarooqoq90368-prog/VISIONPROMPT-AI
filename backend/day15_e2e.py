import json, os, subprocess, tempfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day15_e2e.mp4')

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

# 9. Day 14 refinement (all six operations)
for op in ['refine', 'shorten', 'expand', 'cinematic', 'realistic', 'commercial']:
    r9 = client.post(f'/api/videos/{stored}/prompt/refine', json={'operation': op})
    assert r9.status_code == 200, f'{op}: {r9.status_code}'
    assert r9.json()['success'] is True
print('9. Day 14 refinement: OK (6 operations)')

# 10. Day 15 template generation - all five templates
TEMPLATES = ['cinematic_story', 'ai_video', 'commercial_ad', 'social_media', 'documentary']
REQUIRED_KEYS = ['success', 'message', 'video_filename', 'template', 'source_prompt',
                 'custom_instruction', 'prompt', 'negative_prompt', 'preserved_information']
results = {}
for template in TEMPLATES:
    r10 = client.post(
        f'/api/videos/{stored}/prompt/template',
        json={'template': template, 'custom_instruction': ''},
    )
    assert r10.status_code == 200, f'{template}: {r10.status_code} {r10.text}'
    d10 = r10.json()
    for key in REQUIRED_KEYS:
        assert key in d10, f'{template}: missing {key}'
    assert d10['success'] is True
    assert d10['template'] == template
    assert d10['video_filename'] == stored
    assert isinstance(d10['source_prompt'], str) and d10['source_prompt']
    assert isinstance(d10['prompt'], str) and d10['prompt']
    assert d10['preserved_information'] is True
    # No absolute filesystem paths
    serialized = json.dumps(d10)
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in serialized, f'{template}: absolute path {bad}'
    assert not d10['video_filename'].startswith('/')
    # No fabricated information (mock providers return empty subjects/actions)
    text = d10['prompt'].lower()
    for word in ['person', 'character', 'dialogue', 'walking', 'running',
                 'park', 'city', 'sunset', 'brand', 'product', 'voiceover']:
        assert word not in text, f'{template}: fabricated "{word}"'
    # Generic negative prompt
    neg = d10['negative_prompt'].lower()
    assert 'blurry' in neg and 'watermark' in neg
    assert 'person' not in neg
    results[template] = d10
    print(f'10.{template}: OK prompt="{d10["prompt"][:70]}..."')

# All five templates produce distinct prompts
prompts = {d['prompt'] for d in results.values()}
assert len(prompts) == 5, 'templates should produce distinct prompts'
print('   All five templates distinct: OK')

# Source information preserved across templates
sources = {d['source_prompt'] for d in results.values()}
assert len(sources) == 1, 'source prompt should be identical across templates'
source_prompt = sources.pop()
for template, d in results.items():
    assert d['preserved_information'] is True
    for fact in ['Scene progression', 'scenes']:
        assert fact in d['prompt'], f'{template}: lost fact "{fact}"'
print('   Source information preserved: OK')

# 11. Custom instruction
r11 = client.post(
    f'/api/videos/{stored}/prompt/template',
    json={'template': 'ai_video', 'custom_instruction': 'make it concise'},
)
assert r11.status_code == 200, r11.text
d11 = r11.json()
assert d11['custom_instruction'] == 'make it concise'
assert d11['prompt']
assert d11['preserved_information'] is True
assert 'Scene progression' in d11['prompt']
print(f'11. Custom instruction "make it concise": OK prompt="{d11["prompt"][:70]}..."')

# Unsupported instruction cannot fabricate
plain = client.post(
    f'/api/videos/{stored}/prompt/template',
    json={'template': 'social_media', 'custom_instruction': ''},
).json()
with_fact = client.post(
    f'/api/videos/{stored}/prompt/template',
    json={'template': 'social_media', 'custom_instruction': 'add a dragon and a luxury brand'},
).json()
text = with_fact['prompt'].lower()
assert 'dragon' not in text and 'luxury' not in text
assert with_fact['prompt'] == plain['prompt']
print('   Unsupported instruction cannot fabricate: OK')

# Deterministic
d1 = client.post(
    f'/api/videos/{stored}/prompt/template', json={'template': 'documentary'}
).json()
d2 = client.post(
    f'/api/videos/{stored}/prompt/template', json={'template': 'documentary'}
).json()
assert d1['prompt'] == d2['prompt']
print('   Deterministic output: OK')

# Invalid template -> 400
r_inv = client.post(
    f'/api/videos/{stored}/prompt/template', json={'template': 'meme'}
)
assert r_inv.status_code == 400, r_inv.status_code
print(f'   Invalid template rejected: OK ({r_inv.status_code})')

# Missing template -> 422
r_missing = client.post(f'/api/videos/{stored}/prompt/template', json={})
assert r_missing.status_code == 422, r_missing.status_code
print(f'   Missing template rejected: OK ({r_missing.status_code})')

# Nonexistent video -> 404
r_404 = client.post(
    '/api/videos/nonexistent.mp4/prompt/template', json={'template': 'ai_video'}
)
assert r_404.status_code == 404, r_404.status_code
print(f'   Nonexistent video: OK ({r_404.status_code})')

# Path traversal -> rejected
r_pt = client.post(
    '/api/videos/../../../etc/passwd/prompt/template',
    json={'template': 'ai_video'},
)
assert r_pt.status_code in (400, 404), r_pt.status_code
print(f'   Path traversal rejected: OK ({r_pt.status_code})')

# 12. Day 1-14 endpoints remain intact
assert client.get('/api/health').status_code == 200
assert client.get(f'/api/videos/{stored}/metadata').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt?style=cinematic').status_code == 200
assert client.post(f'/api/videos/{stored}/scenes/detect').status_code == 200
assert client.post(f'/api/videos/{stored}/subjects/analyze').status_code == 200
assert client.post(f'/api/videos/{stored}/audio/analyze').status_code == 200
assert client.post(f'/api/videos/{stored}/intelligence').status_code == 200
assert client.post(f'/api/videos/{stored}/advanced-prompt?style=cinematic').status_code == 200
r_refine = client.post(
    f'/api/videos/{stored}/prompt/refine', json={'operation': 'refine'}
)
assert r_refine.status_code == 200
print('12. Day 1-14 endpoints still work: OK')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 15 MANUAL E2E VERIFICATIONS PASSED')
