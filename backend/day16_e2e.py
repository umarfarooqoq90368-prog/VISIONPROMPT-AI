import json, os, subprocess, tempfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day16_e2e.mp4')

subprocess.run(
    [ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-y', tmp],
    capture_output=True, timeout=15,
)

# A. Upload
with open(tmp, 'rb') as f:
    r = client.post('/api/videos/upload', files={'file': ('test.mp4', f, 'video/mp4')})
assert r.status_code == 200, r.text
stored = r.json()['video']['stored_filename']
print(f'A. Upload: OK ({stored})')

# B. Day 1-15 pipeline
r2 = client.post(f'/api/videos/{stored}/frames/extract?interval_seconds=1')
assert r2.status_code == 200 and r2.json()['frame_count'] >= 1
print(f'B1. Extract frames: OK ({r2.json()["frame_count"]} frames)')

r3 = client.post(f'/api/videos/{stored}/analyze?max_frames=5')
assert r3.status_code == 200 and r3.json()['success'] is True
print('B2. Visual analysis: OK')

r4 = client.post(f'/api/videos/{stored}/scenes/detect')
assert r4.status_code == 200 and r4.json()['scenes_detected'] >= 1
print(f'B3. Scene detection: OK ({r4.json()["scenes_detected"]} scenes)')

r5 = client.post(f'/api/videos/{stored}/subjects/analyze')
assert r5.status_code == 200
print('B4. Subject analysis: OK')

r6 = client.post(f'/api/videos/{stored}/audio/analyze')
assert r6.status_code == 200 and r6.json()['has_audio'] is True
print(f'B5. Audio analysis: OK (provider={r6.json()["provider"]})')

r7 = client.post(f'/api/videos/{stored}/intelligence')
assert r7.status_code == 200 and r7.json()['success'] is True
print('B6. Intelligence: OK')

r8 = client.post(f'/api/videos/{stored}/advanced-prompt?style=cinematic')
assert r8.status_code == 200 and r8.json()['success'] is True
print('B7. Advanced prompt: OK')

r9 = client.post(f'/api/videos/{stored}/prompt/refine', json={'operation': 'refine'})
assert r9.status_code == 200 and r9.json()['success'] is True
print('B8. Refinement: OK')

r10 = client.post(f'/api/videos/{stored}/prompt/template', json={'template': 'ai_video'})
assert r10.status_code == 200 and r10.json()['success'] is True
print('B9. Template: OK')


def save(video, prompt, negative='', source='custom', operation='', metadata=None):
    body = {'prompt': prompt, 'negative_prompt': negative, 'source': source,
            'operation': operation, 'metadata': metadata or {}}
    return client.post(f'/api/videos/{video}/prompt/history', json=body)


def history(video):
    return client.get(f'/api/videos/{video}/prompt/history').json()['versions']


NEG = 'blurry, low quality, distorted anatomy, unwanted text, watermark'
P1 = 'Scene progression across 1 scenes, cinematic composition. Subject: none detected.'
P2 = 'Scene progression across 2 scenes, cinematic composition. Subject: none detected.'
P3 = 'Scene progression across 3 scenes, cinematic composition. Subject: none detected.'

# Save prompt version 1 (advanced_prompt source)
advanced_prompt = r8.json()['prompt']
advanced_neg = r8.json()['negative_prompt']
v1 = save(stored, advanced_prompt, advanced_neg, source='advanced_prompt',
          operation='cinematic', metadata={'pipeline': 'day13'})
assert v1.status_code == 200, v1.text
assert v1.json()['version'] == 1, v1.json()
assert v1.json()['source'] == 'advanced_prompt'
print(f'C. First saved version = 1: OK (source={v1.json()["source"]})')

# Save prompt version 2 (refinement source)
refined_prompt = r9.json()['refined_prompt']
v2 = save(stored, refined_prompt, r9.json()['negative_prompt'], source='refinement',
          operation='refine', metadata={'pipeline': 'day14'})
assert v2.status_code == 200
assert v2.json()['version'] == 2
print('D. Second saved version = 2: OK')

# Save version 3 (template source)
v3 = save(stored, r10.json()['prompt'], r10.json()['negative_prompt'],
          source='template', operation='ai_video', metadata={'pipeline': 'day15'})
assert v3.status_code == 200
assert v3.json()['version'] == 3

# Save version 4 (custom source, plain prompts for token comparison)
v4 = save(stored, P1, NEG, source='custom', metadata={'note': 'baseline'})
assert v4.status_code == 200 and v4.json()['version'] == 4

v5 = save(stored, P2, NEG, source='custom', metadata={'note': 'two scenes'})
assert v5.status_code == 200 and v5.json()['version'] == 5

# E. List ascending
versions = history(stored)
assert [v['version'] for v in versions] == [1, 2, 3, 4, 5]
print(f'E. List ascending order: OK ({[v["version"] for v in versions]})')

# F. Get version - exact prompt + negative prompt
got = client.get(f'/api/videos/{stored}/prompt/history/4')
assert got.status_code == 200
assert got.json()['prompt'] == P1
assert got.json()['negative_prompt'] == NEG
assert got.json()['metadata'] == {'note': 'baseline'}
print('F. Get exact version: OK')

# G. Compare structured comparison
cmp_resp = client.get(f'/api/videos/{stored}/prompt/history/compare/4/5')
assert cmp_resp.status_code == 200, cmp_resp.text
cmp_data = cmp_resp.json()
for key in ['video_filename', 'version_a', 'version_b', 'prompt_a', 'prompt_b',
            'negative_prompt_a', 'negative_prompt_b', 'added_tokens',
            'removed_tokens', 'common_tokens', 'changed']:
    assert key in cmp_data, f'missing {key}'
assert cmp_data['version_a'] == 4 and cmp_data['version_b'] == 5
assert cmp_data['prompt_a'] == P1 and cmp_data['prompt_b'] == P2
assert cmp_data['negative_prompt_a'] == NEG
assert cmp_data['changed'] is True
print(f'G. Compare structured: OK (added={cmp_data["added_tokens"]}, removed={cmp_data["removed_tokens"]})')

# H. Deterministic token comparison
cmp2 = client.get(f'/api/videos/{stored}/prompt/history/compare/4/5').json()
assert cmp2 == cmp_data, 'compare must be deterministic'
assert cmp_data['added_tokens'] == ['2']
assert cmp_data['removed_tokens'] == ['1']
assert 'scenes' in cmp_data['common_tokens']
assert 'cinematic' in cmp_data['common_tokens']
print('H. Token comparison deterministic: OK')

# I. Delete version succeeds
d1 = client.delete(f'/api/videos/{stored}/prompt/history/4')
assert d1.status_code == 200
assert d1.json() == {'deleted': True, 'video_filename': stored, 'version': 4}
print('I. Delete version: OK')

# J. No renumbering: versions were 1,2,3,4,5 delete 4 -> 1,2,3,5; next = 6
remaining = [v['version'] for v in history(stored)]
assert remaining == [1, 2, 3, 5], remaining
v6 = save(stored, P3, NEG, source='custom')
assert v6.status_code == 200 and v6.json()['version'] == 6
remaining = [v['version'] for v in history(stored)]
assert remaining == [1, 2, 3, 5, 6], remaining
assert client.get(f'/api/videos/{stored}/prompt/history/4').status_code == 404
print(f'J. No renumbering (delete 4 from 1,2,3,4,5 -> {remaining}; next=6): OK')

# K. Multiple videos isolated
with open(tmp, 'rb') as f:
    up2 = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored2 = up2.json()['video']['stored_filename']
other_history = client.get(f'/api/videos/{stored2}/prompt/history').json()
assert other_history == {'video_filename': stored2, 'versions': []}
v_other = save(stored2, P1, NEG)
assert v_other.json()['version'] == 1
assert [v['version'] for v in history(stored)] == [1, 2, 3, 5, 6]
print('K. Multiple videos isolated: OK')

# L. Metadata preserved
assert v1.json()['metadata'] == {'pipeline': 'day13'}
got_meta = client.get(f'/api/videos/{stored}/prompt/history/1').json()['metadata']
assert got_meta == {'pipeline': 'day13'}
print('L. Metadata preserved: OK')

# M. No fabricated video information
all_payloads = json.dumps({
    'versions': history(stored),
    'compare': cmp_data,
    'v1': v1.json(),
})
text = all_payloads.lower()
for word in ['person', 'character', 'dialogue', 'walking', 'running',
             'park', 'city', 'sunset', 'brand', 'product', 'voiceover']:
    assert word not in text, f'fabricated: {word}'
print('M. No fabricated information: OK')

# N. No absolute filesystem paths
for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
    assert bad not in all_payloads, f'absolute path {bad}'
print('N. No absolute paths: OK')

# O. Invalid source -> 422
o = save(stored, P1, source='database')
assert o.status_code == 422, o.status_code
print(f'O. Invalid source rejected: OK ({o.status_code})')

# P. Empty/missing prompt -> 422
p_empty = save(stored, '')
assert p_empty.status_code == 422, p_empty.status_code
p_missing = client.post(f'/api/videos/{stored}/prompt/history', json={'source': 'custom'})
assert p_missing.status_code == 422, p_missing.status_code
print(f'P. Empty/missing prompt rejected: OK ({p_empty.status_code}/{p_missing.status_code})')

# Q. Invalid version -> 422
q0 = client.get(f'/api/videos/{stored}/prompt/history/0')
assert q0.status_code == 422, q0.status_code
qabc = client.get(f'/api/videos/{stored}/prompt/history/abc')
assert qabc.status_code == 422, qabc.status_code
qc = client.get(f'/api/videos/{stored}/prompt/history/compare/0/1')
assert qc.status_code == 422, qc.status_code
print(f'Q. Invalid version rejected: OK ({q0.status_code}/{qabc.status_code}/{qc.status_code})')

# R. Missing version -> 404
r_missing = client.get(f'/api/videos/{stored}/prompt/history/99')
assert r_missing.status_code == 404, r_missing.status_code
r_cmp_missing = client.get(f'/api/videos/{stored}/prompt/history/compare/6/99')
assert r_cmp_missing.status_code == 404, r_cmp_missing.status_code
print(f'R. Missing version: OK ({r_missing.status_code})')

# S. Nonexistent video -> 404
s_post = client.post('/api/videos/nonexistent.mp4/prompt/history', json={'prompt': 'x y'})
assert s_post.status_code == 404, s_post.status_code
s_get = client.get('/api/videos/nonexistent.mp4/prompt/history')
assert s_get.status_code == 404, s_get.status_code
print(f'S. Nonexistent video: OK ({s_post.status_code})')

# T. Path traversal protected
t_get = client.get('/api/videos/../../../etc/passwd/prompt/history')
assert t_get.status_code in (400, 404), t_get.status_code
t_post = client.post('/api/videos/../../../etc/passwd/prompt/history', json={'prompt': 'x y'})
assert t_post.status_code in (400, 404), t_post.status_code
print(f'T. Path traversal protected: OK ({t_get.status_code}/{t_post.status_code})')

# U. Compare route not captured by numeric version route
u = client.get(f'/api/videos/{stored}/prompt/history/compare/5/6')
assert u.status_code == 200
assert 'added_tokens' in u.json() and 'version_id' not in u.json()
u2 = client.get(f'/api/videos/{stored}/prompt/history/5')
assert u2.status_code == 200 and 'version_id' in u2.json()
print('U. Compare route not captured: OK')

# V. Deterministic behavior
d_a = save(stored, P1, NEG, source='custom')
d_b = save(stored, P1, NEG, source='custom')
assert d_a.json()['prompt'] == d_b.json()['prompt']
assert d_a.json()['negative_prompt'] == d_b.json()['negative_prompt']
c_a = client.get(f'/api/videos/{stored}/prompt/history/compare/7/8').json()
c_b = client.get(f'/api/videos/{stored}/prompt/history/compare/7/8').json()
assert c_a == c_b
assert c_a['changed'] is False
print('V. Deterministic behavior: OK')

# W. Existing Day 1-15 endpoints remain functional
assert client.get('/api/health').status_code == 200
assert client.get(f'/api/videos/{stored}/metadata').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt?style=cinematic').status_code == 200
assert client.post(f'/api/videos/{stored}/scenes/detect').status_code == 200
assert client.post(f'/api/videos/{stored}/subjects/analyze').status_code == 200
assert client.post(f'/api/videos/{stored}/audio/analyze').status_code == 200
assert client.post(f'/api/videos/{stored}/intelligence').status_code == 200
assert client.post(f'/api/videos/{stored}/advanced-prompt?style=realistic').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/refine',
                   json={'operation': 'shorten'}).status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/template',
                   json={'template': 'documentary'}).status_code == 200
print('W. Day 1-15 endpoints still work: OK')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 16 MANUAL E2E VERIFICATIONS PASSED')
