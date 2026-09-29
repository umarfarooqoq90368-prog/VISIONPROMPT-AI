import json, os, re, subprocess, tempfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day19_e2e.mp4')

subprocess.run(
    [ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-y', tmp],
    capture_output=True, timeout=15,
)

# --- Pipeline: upload -> frames -> visual -> scenes -> subjects -> audio ->
#     intelligence -> advanced-prompt -> refinement -> template -> Day16/17/18
with open(tmp, 'rb') as f:
    r = client.post('/api/videos/upload', files={'file': ('test.mp4', f, 'video/mp4')})
assert r.status_code == 200, r.text
stored = r.json()['video']['stored_filename']
print(f'Upload: OK ({stored})')

assert client.post(f'/api/videos/{stored}/frames/extract?interval_seconds=1').status_code == 200
assert client.post(f'/api/videos/{stored}/analyze?max_frames=5').status_code == 200
assert client.post(f'/api/videos/{stored}/scenes/detect').status_code == 200
assert client.post(f'/api/videos/{stored}/subjects/analyze').status_code == 200
assert client.post(f'/api/videos/{stored}/audio/analyze').status_code == 200
assert client.post(f'/api/videos/{stored}/intelligence').status_code == 200
assert client.post(f'/api/videos/{stored}/advanced-prompt?style=cinematic').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/refine',
                   json={'operation': 'refine'}).status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/template',
                   json={'template': 'ai_video'}).status_code == 200
print('Pipeline (Day 1-15): OK')

NEG1 = 'blurry, low quality, distorted anatomy, unwanted text, watermark'
P1 = 'cinematic first version prompt'
P2 = 'documentary second version prompt'
P3 = 'cinematic third version prompt'
P4 = 'fourth version created after delete'
PB = 'isolated video B prompt'


def save(video, prompt, negative=NEG1, source='custom', operation='', metadata=None):
    body = {'prompt': prompt, 'negative_prompt': negative,
            'source': source, 'operation': operation}
    if metadata is not None:
        body['metadata'] = metadata
    resp = client.post(f'/api/videos/{video}/prompt/history', json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def export(video, version, format):
    return client.get(
        f'/api/videos/{video}/prompt/history/{version}/export',
        params={'format': format},
    )


def get_version(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}').json()


# --- Day 16 history (video A) ---
v1 = save(stored, P1, source='refinement', operation='cinematic',
          metadata={'style': 'film'})
v2 = save(stored, P2, source='template', operation='ai_video')
v3 = save(stored, P3, negative='', source='custom', operation='')
assert [v1['version'], v2['version'], v3['version']] == [1, 2, 3]

# --- Day 17 organization (video A) ---
assert client.post(f'/api/videos/{stored}/prompt/history/1/favorite').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/history/1/tags',
                   json={'tags': ['  Cinematic ', 'ai', 'ai']}).json()['tags'] == \
    ['ai', 'cinematic']
org_v1 = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert org_v1 == {'video_filename': stored, 'version': 1,
                  'favorite': True, 'tags': ['ai', 'cinematic']}

# --- Day 18 search (video A) ---
search_r = client.get(f'/api/videos/{stored}/prompt/search',
                      params={'query': 'cinematic'})
assert search_r.status_code == 200 and search_r.json()['count'] == 2
print('Day 16/17/18 setup: OK')

# Snapshot the original Day16 record BEFORE any export (check D)
original_record = get_version(stored, 1)
original_json = json.dumps(original_record, sort_keys=True)

# ==================== A. JSON export ====================
resp = export(stored, 1, 'json')
assert resp.status_code == 200, resp.status_code
assert resp.headers['content-type'].startswith('application/json')
data = resp.json()
assert list(data.keys()) == [
    'video_filename', 'version', 'version_id', 'source', 'operation',
    'prompt', 'negative_prompt', 'created_at', 'metadata',
    'favorite', 'tags',
]
assert data['video_filename'] == stored
assert data['version'] == 1
assert data['version_id'] == f'{stored}:1'
assert data['source'] == 'refinement'
assert data['operation'] == 'cinematic'
assert data['prompt'] == P1, 'prompt exactly preserved'
assert data['negative_prompt'] == NEG1, 'negative exactly preserved'
assert data['created_at'] == original_record['created_at']
assert data['metadata'] == {'style': 'film'}
assert data['favorite'] is True
assert data['tags'] == ['ai', 'cinematic']
raw = json.dumps(data)
for word in ['person', 'character', 'dialogue', 'walking', 'park', 'city',
             'sunset', 'brand', 'product', 'voiceover']:
    assert word not in raw.lower(), f'fabricated: {word}'
for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/', '/etc/']:
    assert bad not in raw, f'absolute path {bad}'
print('A. JSON export: OK (all fields exact, no fabrication, no paths)')

# ==================== B. Markdown export ====================
resp = export(stored, 1, 'markdown')
assert resp.status_code == 200
assert resp.headers['content-type'].startswith('text/markdown')
md = resp.text
for heading in ['# VisionPrompt AI Prompt', '## Video', '## Version',
                '## Source', '## Operation', '## Prompt',
                '## Negative Prompt', '## Tags', '## Favorite',
                '## Created At', '## Metadata']:
    assert heading in md, f'missing {heading}'
assert f'## Prompt\n\n{P1}\n' in md, 'exact prompt'
assert f'## Negative Prompt\n\n{NEG1}\n' in md, 'exact negative'
assert f'`{stored}`' in md
assert '## Version\n\n1' in md
assert '## Source\n\nrefinement' in md
assert '## Operation\n\ncinematic' in md
assert '* ai\n* cinematic' in md
assert '## Favorite\n\ntrue' in md
assert original_record['created_at'] in md
assert '"style": "film"' in md
md_lower = md.lower()
for word in ['person', 'character', 'dialogue', 'walking', 'park', 'city',
             'sunset', 'voiceover']:
    assert word not in md_lower, f'fabricated: {word}'
md_again = export(stored, 1, 'markdown')
assert md_again.status_code == 200 and md_again.text == md, 'deterministic'
print('B. Markdown export: OK (headings, exact prompt/negative, deterministic)')

# ==================== C. TXT export ====================
resp = export(stored, 1, 'txt')
assert resp.status_code == 200
assert resp.headers['content-type'].startswith('text/plain')
txt = resp.text
assert txt.startswith('# VISIONPROMPT AI PROMPT\n')
for field in ['Video: ', 'Version: 1', 'Source: refinement',
              'Operation: cinematic', 'Favorite: true',
              'Tags: ai, cinematic', 'Created At: ']:
    assert field in txt, f'missing {field}'
assert f'## PROMPT\n\n{P1}\n' in txt, 'exact prompt'
assert f'## NEGATIVE PROMPT\n\n{NEG1}\n' in txt, 'exact negative'
assert '"style": "film"' in txt
txt_again = export(stored, 1, 'txt')
assert txt_again.status_code == 200 and txt_again.text == txt, 'deterministic'
print('C. TXT export: OK (sections, exact prompt/negative, deterministic)')

# ==================== D. Exact preservation ====================
after_record = get_version(stored, 1)
assert json.dumps(after_record, sort_keys=True) == original_json, \
    'history record must be byte-identical after exports'
assert after_record['prompt'] == P1
assert after_record['negative_prompt'] == NEG1
assert after_record['source'] == 'refinement'
assert after_record['operation'] == 'cinematic'
assert after_record['metadata'] == {'style': 'film'}
assert after_record['created_at'] == original_record['created_at']
org_after = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert org_after == org_v1, 'org metadata must be unchanged by export'
print('D. Exact preservation: OK (history + org byte-identical after exports)')

# ==================== E. Multiple versions ====================
e1 = export(stored, 1, 'json').json()
e2 = export(stored, 2, 'markdown')
e3 = export(stored, 3, 'txt')
assert e1['prompt'] == P1 and e1['version'] == 1
assert e2.status_code == 200 and f'## Prompt\n\n{P2}\n' in e2.text
assert P1 not in e2.text and P3 not in e2.text, 'v2 export must not leak v1/v3'
assert e3.status_code == 200 and f'## PROMPT\n\n{P3}\n' in e3.text
assert P1 not in e3.text and P2 not in e3.text, 'v3 export must not leak v1/v2'
assert '## NEGATIVE PROMPT\n\n(empty)' in e3.text, 'v3 empty negative renders cleanly'
v2_rec = get_version(stored, 2)
assert f'## Version\n\n2' in e2.text
assert v2_rec['created_at'] in e2.text
print('E. Multiple versions: OK (v1 json, v2 markdown, v3 txt each correct)')

# ==================== F. Multiple videos ====================
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
vb = save(stored_b, PB, source='custom')
assert client.post(f'/api/videos/{stored_b}/prompt/history/1/favorite').status_code == 200
assert client.post(f'/api/videos/{stored_b}/prompt/history/1/tags',
                   json={'tags': ['b-video']}).status_code == 200
ea = export(stored, 1, 'json').json()
eb = export(stored_b, 1, 'json').json()
assert ea['video_filename'] == stored and ea['prompt'] == P1
assert eb['video_filename'] == stored_b and eb['prompt'] == PB
assert PB not in json.dumps(ea), 'A export must never contain B prompt'
assert P1 not in json.dumps(eb), 'B export must never contain A prompt'
assert ea['favorite'] is True and ea['tags'] == ['ai', 'cinematic']
assert eb['favorite'] is True and eb['tags'] == ['b-video']
assert ea['version_id'] != eb['version_id']
print('F. Multiple videos: OK (A/B prompts and org metadata isolated)')

# ==================== G. Deleted version ====================
assert client.delete(f'/api/videos/{stored}/prompt/history/2').status_code == 200
g_deleted = export(stored, 2, 'json')
assert g_deleted.status_code == 404, g_deleted.status_code
assert export(stored, 2, 'markdown').status_code == 404
assert export(stored, 2, 'txt').status_code == 404
g1 = export(stored, 1, 'json')
g3 = export(stored, 3, 'txt')
assert g1.status_code == 200 and g1.json()['prompt'] == P1
assert g3.status_code == 200 and f'## PROMPT\n\n{P3}\n' in g3.text
v4 = save(stored, P4)
assert v4['version'] == 4, f'Day16 numbering unchanged, got {v4["version"]}'
listing = client.get(f'/api/videos/{stored}/prompt/history').json()
assert [x['version'] for x in listing['versions']] == [1, 3, 4]
g4 = export(stored, 4, 'json')
assert g4.status_code == 200 and g4.json()['prompt'] == P4
print('G. Deleted version: OK (v2 404, v1/v3 export, next version = 4)')

# ==================== H. Validation ====================
h1 = client.get('/api/videos/nope.mp4/prompt/history/1/export',
                params={'format': 'json'})
assert h1.status_code == 404, h1.status_code
h2 = client.get('/api/videos/../../../etc/passwd/prompt/history/1/export',
                params={'format': 'json'})
assert h2.status_code == 404, h2.status_code
assert export(stored, 0, 'json').status_code == 422
assert export(stored, -1, 'json').status_code == 422
h5 = client.get(f'/api/videos/{stored}/prompt/history/1/export')
assert h5.status_code == 422, h5.status_code
assert export(stored, 1, 'xml').status_code == 422
assert export(stored, 1, 'JSON').status_code == 422
assert export(stored, 1, '').status_code == 422
print('H. Validation: OK (404/404/422/422/422/422/422/422)')

# ==================== I. Route collision ====================
exp = export(stored, 4, 'json').json()
assert exp['favorite'] is False and exp['tags'] == [], 'export shape'
plain = get_version(stored, 4)
assert plain['prompt'] == P4 and 'favorite' not in plain and 'tags' not in plain, \
    'plain version shape must not be export shape'
assert client.get(f'/api/videos/{stored}/prompt/history').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/favorites').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/tag/ai').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/compare/1/3').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization').status_code == 200
print('I. Route collision: OK (/export is export, /{version} still version)')

# ==================== J. Content-Disposition ====================
stem = os.path.splitext(stored)[0]
j1 = export(stored, 1, 'json')
j2 = export(stored, 3, 'markdown')
j3 = export(stored, 3, 'txt')
assert j1.headers['content-disposition'] == \
    f'attachment; filename="visionprompt_{stem}_v1.json"'
assert j2.headers['content-disposition'] == \
    f'attachment; filename="visionprompt_{stem}_v3.md"'
assert j3.headers['content-disposition'] == \
    f'attachment; filename="visionprompt_{stem}_v3.txt"'
for hdr in (j1, j2, j3):
    name = re.search(r'filename="([^"]+)"', hdr.headers['content-disposition']).group(1)
    assert re.fullmatch(r'visionprompt_[A-Za-z0-9_-]+_v\d+\.(json|md|txt)', name), name
    assert ' ' not in name and '..' not in name
print('J. Content-Disposition: OK (safe deterministic filenames)')

# ==================== K. Day16 regression ====================
kv = save(stored, 'temporary version for delete check')
assert kv['version'] == 5
assert client.delete(f'/api/videos/{stored}/prompt/history/5').status_code == 200
k_list = client.get(f'/api/videos/{stored}/prompt/history').json()
assert [x['version'] for x in k_list['versions']] == [1, 3, 4]
k_get = client.get(f'/api/videos/{stored}/prompt/history/3')
assert k_get.status_code == 200 and k_get.json()['prompt'] == P3
k_cmp = client.get(f'/api/videos/{stored}/prompt/history/compare/1/3')
assert k_cmp.status_code == 200
assert 'common_tokens' in k_cmp.json() and 'added_tokens' in k_cmp.json()
print('K. Day16 regression: OK (create/list/get/compare/delete)')

# ==================== L. Day17 regression ====================
assert client.post(f'/api/videos/{stored}/prompt/history/3/favorite').status_code == 200
assert client.delete(f'/api/videos/{stored}/prompt/history/3/favorite').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/history/3/tags',
                   json={'tags': ['Zeta', ' ai ']}).json()['tags'] == ['ai', 'zeta']
assert client.request('DELETE',
                      f'/api/videos/{stored}/prompt/history/3/tags',
                      json={'tags': ['ai']}).json()['tags'] == ['zeta']
org3 = client.get(f'/api/videos/{stored}/prompt/history/3/organization')
assert org3.status_code == 200
assert org3.json() == {'video_filename': stored, 'version': 3,
                       'favorite': False, 'tags': ['zeta']}
org1 = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert org1['favorite'] is True and org1['tags'] == ['ai', 'cinematic']
print('L. Day17 regression: OK (favorite/unfavorite/add/remove tags/org)')

# ==================== M. Day18 regression ====================
def search(**params):
    return client.get(f'/api/videos/{stored}/prompt/search', params=params)

m1 = search(query='cinematic')
assert m1.status_code == 200
assert [r['version'] for r in m1.json()['results']] == [1, 3]
m2 = search(favorite='true')
assert [r['version'] for r in m2.json()['results']] == [1]
m3 = search(tag='ai')
assert [r['version'] for r in m3.json()['results']] == [1]
m4 = search(source='custom')
assert [r['version'] for r in m4.json()['results']] == [3, 4]
m5 = search(min_version=3, max_version=4)
assert [r['version'] for r in m5.json()['results']] == [3, 4]
m6 = search(query='cinematic', source='refinement', favorite='true', tag='ai')
assert [r['version'] for r in m6.json()['results']] == [1]
print('M. Day18 regression: OK (query/favorite/tag/source/range/combined)')

# ==================== N. Determinism ====================
for fmt in ('json', 'markdown', 'txt'):
    first = export(stored, 1, fmt)
    second = export(stored, 1, fmt)
    assert first.status_code == second.status_code == 200
    assert first.content == second.content, f'{fmt} content must be identical'
    assert first.headers['content-disposition'] == second.headers['content-disposition']
    assert first.headers['content-type'] == second.headers['content-type']
print('N. Determinism: OK (identical content + headers for all 3 formats)')

# ==================== O. Security / integrity ====================
all_blobs = [
    export(stored, 1, 'json').text,
    export(stored, 1, 'markdown').text,
    export(stored, 1, 'txt').text,
    export(stored, 3, 'json').text,
    json.dumps(search().json()),
    json.dumps(client.get(f'/api/videos/{stored}/prompt/history').json()),
]
for blob in all_blobs:
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in blob, f'absolute path {bad}'
    for internal in ['_storage', '_org', 'PromptHistoryService',
                     'PromptExportService', 'storage/uploads']:
        assert internal not in blob, f'internal leak: {internal}'
low = ' '.join(b.lower() for b in all_blobs)
for word in ['person', 'character', 'dialogue', 'walking', 'running',
             'park', 'city', 'sunset', 'brand', 'product', 'voiceover']:
    assert word not in low, f'fabricated: {word}'
final_rec = get_version(stored, 1)
assert json.dumps(final_rec, sort_keys=True) == original_json, \
    'stored prompt/metadata never modified'
assert final_rec['prompt'] == P1 and final_rec['negative_prompt'] == NEG1
final_org = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert final_org == org_v1, 'favorite/tags never modified'
final_list = [x['version'] for x in
              client.get(f'/api/videos/{stored}/prompt/history').json()['versions']]
assert final_list == [1, 3, 4], 'single Day16 store, no second version store'
exported_versions = set()
for fmt in ('json', 'markdown', 'txt'):
    for ver in final_list:
        e = export(stored, ver, fmt)
        assert e.status_code == 200
        if fmt == 'json':
            exported_versions.add(e.json()['version'])
assert exported_versions == set(final_list), 'exports only read existing versions'
print('O. Security/integrity: OK (no paths/internals/fabrication, '
      'history+org untouched, single store)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 19 MANUAL E2E VERIFICATIONS PASSED')
