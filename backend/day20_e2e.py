import io, json, os, re, subprocess, tempfile, zipfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day20_e2e.mp4')

subprocess.run(
    [ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-y', tmp],
    capture_output=True, timeout=15,
)

# --- Pipeline: upload -> frames -> visual -> scenes -> subjects -> audio ->
#     intelligence -> advanced prompt -> refinement -> template -> history
#     -> favorites/tags -> search -> export -> package
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
P4 = 'fourth version after delete'
PB = 'isolated video B prompt'


def save(video, prompt, negative=NEG1, source='custom', operation='', metadata=None):
    body = {'prompt': prompt, 'negative_prompt': negative,
            'source': source, 'operation': operation}
    if metadata is not None:
        body['metadata'] = metadata
    resp = client.post(f'/api/videos/{video}/prompt/history', json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def package(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}/package')


def export(video, version, fmt):
    return client.get(f'/api/videos/{video}/prompt/history/{version}/export',
                      params={'format': fmt})


def read_zip(response):
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return {name: zf.read(name).decode('utf-8') for name in zf.namelist()}


def get_version(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}').json()


# --- Day 16 history (video A) ---
v1 = save(stored, P1, source='refinement', operation='cinematic',
          metadata={'style': 'film'})
v2 = save(stored, P2, source='template', operation='ai_video')
v3 = save(stored, P3, negative='', source='custom', operation='')
assert [v1['version'], v2['version'], v3['version']] == [1, 2, 3]

# --- Day 17 favorites/tags (video A) ---
assert client.post(f'/api/videos/{stored}/prompt/history/1/favorite').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/history/1/tags',
                   json={'tags': [' Cinematic ', 'ai']}).json()['tags'] == \
    ['ai', 'cinematic']
org_v1 = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert org_v1 == {'video_filename': stored, 'version': 1,
                  'favorite': True, 'tags': ['ai', 'cinematic']}

# --- Day 18 search ---
s = client.get(f'/api/videos/{stored}/prompt/search', params={'query': 'cinematic'})
assert s.status_code == 200 and s.json()['count'] == 2

# --- Day 19 export sanity ---
for fmt, prefix in [('json', '{'), ('markdown', '# VisionPrompt'),
                    ('txt', '# VISIONPROMPT')]:
    e = export(stored, 1, fmt)
    assert e.status_code == 200, fmt
    assert e.text.startswith(prefix), fmt
print('Day 16/17/18/19 setup: OK')

original_record = get_version(stored, 1)
original_json = json.dumps(original_record, sort_keys=True)

# ==================== A. Package response ====================
resp = package(stored, 1)
assert resp.status_code == 200, resp.status_code
assert resp.content[:2] == b'PK', 'valid ZIP signature'
assert resp.headers['content-type'].startswith('application/zip')
cd = resp.headers['content-disposition']
assert cd == 'attachment; filename="visionprompt_video_v1.zip"', cd
stem = os.path.splitext(stored)[0]
assert stem not in cd and 'a15cca2a' not in cd, 'no storage UUID in filename'
assert re.fullmatch(r'attachment; filename="visionprompt_video_v\d+\.zip"', cd)
print('A. Package response: OK (200, application/zip, safe filename)')

# ==================== B. ZIP structure ====================
with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
    names = zf.namelist()
    assert zf.testzip() is None
assert names == ['prompt.json', 'prompt.md', 'prompt.txt',
                 'package_metadata.json'], names
assert len(names) == len(set(names)) == 4, 'no duplicates, no extras'
for name in names:
    assert '/' not in name and '\\' not in name and '..' not in name
    assert not name.startswith('/'), name
with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
    for info in zf.infolist():
        assert info.date_time == (1980, 1, 1, 0, 0, 0), 'fixed timestamp'
files = read_zip(resp)
for content in files.values():
    content.encode('utf-8')  # decodable already; ensure round-trip
print('B. ZIP structure: OK (exactly 4 files, safe names, fixed timestamps)')

# ==================== C. Files match Day19 exports ====================
assert files['prompt.json'] == export(stored, 1, 'json').text, 'json bytes match'
assert files['prompt.md'] == export(stored, 1, 'markdown').text, 'md bytes match'
assert files['prompt.txt'] == export(stored, 1, 'txt').text, 'txt bytes match'
print('C. Package files == Day19 export files: OK')

# ==================== D. Exact preservation ====================
pj = json.loads(files['prompt.json'])
assert pj['prompt'] == P1, 'prompt exact'
assert pj['negative_prompt'] == NEG1, 'negative exact'
assert pj['source'] == 'refinement'
assert pj['operation'] == 'cinematic'
assert pj['version'] == 1
assert pj['version_id'] == f'{stored}:1'
assert pj['created_at'] == original_record['created_at']
assert pj['metadata'] == {'style': 'film'}
assert pj['favorite'] is True
assert pj['tags'] == ['ai', 'cinematic']
assert f'## Prompt\n\n{P1}' in files['prompt.md']
assert f'## Negative Prompt\n\n{NEG1}' in files['prompt.md']
assert f'## PROMPT\n\n{P1}' in files['prompt.txt']
assert f'## NEGATIVE PROMPT\n\n{NEG1}' in files['prompt.txt']
# history record unchanged after packaging
after_record = get_version(stored, 1)
assert json.dumps(after_record, sort_keys=True) == original_json, \
    'history record unchanged after packaging'
assert after_record['prompt'] == P1
assert after_record['negative_prompt'] == NEG1
assert after_record['source'] == 'refinement'
assert after_record['operation'] == 'cinematic'
assert after_record['metadata'] == {'style': 'film'}
org_after = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert org_after == org_v1, 'org unchanged after packaging'
print('D. Exact preservation + read-only: OK')

# ==================== E. package_metadata.json safety ====================
meta = json.loads(files['package_metadata.json'])
assert list(meta.keys()) == ['video_filename', 'version', 'version_id',
                             'source', 'operation', 'created_at',
                             'favorite', 'tags'], list(meta.keys())
assert meta['video_filename'] == stored
assert meta['version'] == 1
assert meta['version_id'] == f'{stored}:1'
assert meta['favorite'] is True
assert meta['tags'] == ['ai', 'cinematic']
assert P1 not in files['package_metadata.json'], 'no prompt text in metadata'
for blob in files.values():
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/', '/etc/']:
        assert bad not in blob, f'absolute path {bad} in package'
    for token in ['_storage', 'PromptPackageService', 'PromptHistoryService',
                  'storage/uploads', 'BytesIO', 'secret', 'api_key',
                  'password', 'environ', 'traceback']:
        assert token not in blob, f'internal leak {token}'
print('E. package_metadata.json safety: OK (8 safe fields only)')

# ==================== F. Multiple versions ====================
f1 = read_zip(package(stored, 1))
f2 = read_zip(package(stored, 2))
f3 = read_zip(package(stored, 3))
assert json.loads(f1['prompt.json'])['prompt'] == P1
assert json.loads(f2['prompt.json'])['prompt'] == P2
assert json.loads(f3['prompt.json'])['prompt'] == P3
assert json.loads(f1['package_metadata.json'])['version'] == 1
assert json.loads(f2['package_metadata.json'])['version'] == 2
assert json.loads(f3['package_metadata.json'])['version'] == 3
assert P1 not in f2['prompt.json'] and P2 not in f1['prompt.json']
assert '## NEGATIVE PROMPT\n\n(empty)' in f3['prompt.txt'], \
    'v3 empty negative renders cleanly'
print('F. Multiple versions: OK (each package maps to its version)')

# ==================== G. Deleted version ====================
assert client.delete(f'/api/videos/{stored}/prompt/history/2').status_code == 200
assert package(stored, 2).status_code == 404, 'deleted version cannot be packaged'
assert package(stored, 1).status_code == 200
assert package(stored, 3).status_code == 200
v4 = save(stored, P4)
assert v4['version'] == 4, 'Day16 numbering unchanged'
g4 = read_zip(package(stored, 4))
assert json.loads(g4['prompt.json'])['prompt'] == P4
assert json.loads(g4['package_metadata.json'])['version'] == 4
listing = client.get(f'/api/videos/{stored}/prompt/history').json()
assert [x['version'] for x in listing['versions']] == [1, 3, 4]
print('G. Deleted version: OK (404 for v2, v4 packagable, numbering intact)')

# ==================== H. Validation ====================
h1 = client.get('/api/videos/nope.mp4/prompt/history/1/package')
assert h1.status_code == 404, h1.status_code
h2 = client.get('/api/videos/../../../etc/passwd/prompt/history/1/package')
assert h2.status_code == 404, h2.status_code
assert package(stored, 0).status_code == 422
assert package(stored, -1).status_code == 422
print('H. Validation: OK (404/404/422/422)')

# ==================== I. Route collision ====================
assert package(stored, 4).content[:2] == b'PK'
plain = get_version(stored, 4)
assert plain['prompt'] == P4, 'numeric route returns version record'
assert client.get(f'/api/videos/{stored}/prompt/history').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/favorites').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/tag/ai').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/compare/1/3').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization').status_code == 200
assert export(stored, 1, 'json').status_code == 200
print('I. Route collision: OK (/package vs /{version} vs export vs static)')

# ==================== J. Multiple videos ====================
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
save(stored_b, PB, source='custom')
client.post(f'/api/videos/{stored_b}/prompt/history/1/favorite')
client.post(f'/api/videos/{stored_b}/prompt/history/1/tags',
            json={'tags': ['b-only']})
pa = read_zip(package(stored, 1))
pb = read_zip(package(stored_b, 1))
assert json.loads(pa['prompt.json'])['prompt'] == P1
assert json.loads(pb['prompt.json'])['prompt'] == PB
assert PB not in pa['prompt.json'], 'A package must not contain B prompt'
assert P1 not in pb['prompt.json'], 'B package must not contain A prompt'
ma = json.loads(pa['package_metadata.json'])
mb = json.loads(pb['package_metadata.json'])
assert ma['video_filename'] == stored and mb['video_filename'] == stored_b
assert ma['tags'] == ['ai', 'cinematic'] and mb['tags'] == ['b-only']
assert ma['version_id'] != mb['version_id']
print('J. Multiple videos: OK (prompts and org metadata isolated)')

# ==================== K. Determinism ====================
k1 = package(stored, 1)
k2 = package(stored, 1)
assert k1.status_code == k2.status_code == 200
assert k1.content == k2.content, 'byte-identical repeated generation'
assert k1.headers['content-disposition'] == k2.headers['content-disposition']
assert k1.headers['content-type'] == k2.headers['content-type']
assert read_zip(k1) == read_zip(k2)
print('K. Determinism: OK (identical bytes + headers)')

# ==================== L. Day16 regression ====================
lv = save(stored, 'temporary for delete check')
assert lv['version'] == 5
assert client.delete(f'/api/videos/{stored}/prompt/history/5').status_code == 200
assert [x['version'] for x in
        client.get(f'/api/videos/{stored}/prompt/history').json()['versions']] == [1, 3, 4]
lg = client.get(f'/api/videos/{stored}/prompt/history/3')
assert lg.status_code == 200 and lg.json()['prompt'] == P3
lc = client.get(f'/api/videos/{stored}/prompt/history/compare/1/3')
assert lc.status_code == 200 and 'common_tokens' in lc.json()
print('L. Day16 regression: OK (create/list/get/compare/delete)')

# ==================== M. Day17 regression ====================
assert client.post(f'/api/videos/{stored}/prompt/history/3/favorite').status_code == 200
assert client.delete(f'/api/videos/{stored}/prompt/history/3/favorite').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/history/3/tags',
                   json={'tags': ['Zeta', ' ai ']}).json()['tags'] == ['ai', 'zeta']
assert client.request('DELETE',
                      f'/api/videos/{stored}/prompt/history/3/tags',
                      json={'tags': ['ai']}).json()['tags'] == ['zeta']
org3 = client.get(f'/api/videos/{stored}/prompt/history/3/organization').json()
assert org3 == {'video_filename': stored, 'version': 3,
                'favorite': False, 'tags': ['zeta']}
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization').json() == org_v1
print('M. Day17 regression: OK (favorite/unfavorite/add/remove tags/org)')

# ==================== N. Day18 regression ====================
def search(**params):
    return client.get(f'/api/videos/{stored}/prompt/search', params=params)

assert [r['version'] for r in search(query='cinematic').json()['results']] == [1, 3]
assert [r['version'] for r in search(favorite='true').json()['results']] == [1]
assert [r['version'] for r in search(tag='ai').json()['results']] == [1]
assert [r['version'] for r in search(source='custom').json()['results']] == [3, 4]
assert [r['version'] for r in
        search(min_version=3, max_version=4).json()['results']] == [3, 4]
assert [r['version'] for r in
        search(query='cinematic', source='refinement', favorite='true',
               tag='ai').json()['results']] == [1]
print('N. Day18 regression: OK (query/favorite/tag/source/range/combined)')

# ==================== O. Day19 regression ====================
o_files = read_zip(package(stored, 1))
for fmt in ('json', 'markdown', 'txt'):
    e1 = export(stored, 1, fmt)
    e2 = export(stored, 1, fmt)
    assert e1.status_code == e2.status_code == 200
    assert e1.content == e2.content, f'{fmt} export deterministic'
assert export(stored, 1, 'xml').status_code == 422
assert client.get(f'/api/videos/{stored}/prompt/history/1/export').status_code == 422
assert o_files['prompt.json'] == export(stored, 1, 'json').text
assert o_files['prompt.md'] == export(stored, 1, 'markdown').text
assert o_files['prompt.txt'] == export(stored, 1, 'txt').text
print('O. Day19 regression: OK (exports intact and byte-match package files)')

# ==================== P. Security / integrity ====================
blobs = [' '.join(read_zip(package(stored, ver)).values())
         for ver in (1, 3, 4)]
blobs.append(json.dumps(search().json()))
blobs.append(json.dumps(client.get(f'/api/videos/{stored}/prompt/history').json()))
for blob in blobs:
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in blob, f'absolute path {bad}'
    for internal in ['_storage', '_org', 'PromptPackageService',
                     'PromptExportService', 'storage/uploads', 'BytesIO']:
        assert internal not in blob, f'internal leak {internal}'
low = ' '.join(blobs).lower()
for word in ['person', 'character', 'dialogue', 'walking', 'running',
             'park', 'city', 'sunset', 'brand', 'product', 'voiceover']:
    assert word not in low, f'fabricated: {word}'
final_rec = get_version(stored, 1)
assert json.dumps(final_rec, sort_keys=True) == original_json, \
    'stored history never modified'
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization').json() == \
    org_v1, 'org metadata never modified'
final_list = [x['version'] for x in
              client.get(f'/api/videos/{stored}/prompt/history').json()['versions']]
assert final_list == [1, 3, 4], 'single Day16 store, no second version store'
for ver in final_list:
    assert package(stored, ver).status_code == 200
assert package(stored, 2).status_code == 404
print('P. Security/integrity: OK (no paths/internals/fabrication, '
      'history+org untouched, single store)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 20 MANUAL E2E VERIFICATIONS PASSED')
