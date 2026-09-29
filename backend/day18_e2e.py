import json, os, subprocess, tempfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day18_e2e.mp4')

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
print('B. Day 1-15 pipeline: OK')


def save(video, prompt, source='custom', operation='', negative='blurry, low quality'):
    resp = client.post(
        f'/api/videos/{video}/prompt/history',
        json={'prompt': prompt, 'negative_prompt': negative,
              'source': source, 'operation': operation},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def search(video, **params):
    resp = client.get(f'/api/videos/{video}/prompt/search', params=params)
    return resp


def fav(video, version):
    return client.post(f'/api/videos/{video}/prompt/history/{version}/favorite')


def unfav(video, version):
    return client.delete(f'/api/videos/{video}/prompt/history/{version}/favorite')


def add_tags(video, version, tags):
    return client.post(
        f'/api/videos/{video}/prompt/history/{version}/tags', json={'tags': tags}
    )


def rm_tags(video, version, tags):
    return client.request(
        'DELETE', f'/api/videos/{video}/prompt/history/{version}/tags',
        json={'tags': tags},
    )


# --- Create several history versions with different prompts/sources/operations ---
v1 = save(stored, 'cinematic composition shot one', source='advanced_prompt',
          operation='cinematic')
v2 = save(stored, 'CINEMATIC lighting design two', source='refinement',
          operation='shorten')
v3 = save(stored, 'cinematic sound design three', source='template',
          operation='ai_video')
v4 = save(stored, 'documentary style four', source='custom', operation='')
v5 = save(stored, 'cinematic wide angle five', source='refinement',
          operation='expand')
assert [v1['version'], v2['version'], v3['version'], v4['version'],
        v5['version']] == [1, 2, 3, 4, 5]

# Favorites + tags
fav(stored, 1)
fav(stored, 3)
add_tags(stored, 1, ['ai', 'cinematic'])
add_tags(stored, 2, ['ai'])
add_tags(stored, 3, ['Cinematic'])
add_tags(stored, 5, ['ai', 'cinematic-pro'])

# --- A. No filters returns all live versions ---
resp = search(stored)
assert resp.status_code == 200, resp.text
data = resp.json()
assert data['count'] == 5
assert [r['version'] for r in data['results']] == [1, 2, 3, 4, 5]
assert data['video_filename'] == stored
assert set(data['filters'].keys()) == {'query', 'source', 'operation',
                                       'favorite', 'tag', 'min_version',
                                       'max_version'}
print('A. No filters returns all live versions: OK (count=5)')

# --- B. query=cinematic case-insensitive substring ---
data = search(stored, query='cinematic').json()
assert data['count'] == 4, data['count']
assert [r['version'] for r in data['results']] == [1, 2, 3, 5]
assert all('cinematic' in r['prompt'].lower() for r in data['results'])
data = search(stored, query='CINEMATIC').json()
assert [r['version'] for r in data['results']] == [1, 2, 3, 5], 'case-insensitive'
data = search(stored, query='cinema').json()
assert [r['version'] for r in data['results']] == [1, 2, 3, 5], 'substring'
data = search(stored, query='lighting').json()
assert [r['version'] for r in data['results']] == [2]
print('B. query=cinematic (case-insensitive, substring): OK (1,2,3,5)')

# --- C. Source filtering (all four sources) ---
for src, expected in [('advanced_prompt', [1]), ('refinement', [2, 5]),
                      ('template', [3]), ('custom', [4])]:
    data = search(stored, source=src).json()
    assert [r['version'] for r in data['results']] == expected, (src, data)
    assert all(r['source'] == src for r in data['results'])
print('C. Source filtering (advanced_prompt/refinement/template/custom): OK')

# --- D. Operation filtering ---
data = search(stored, operation='shorten').json()
assert [r['version'] for r in data['results']] == [2]
assert data['results'][0]['operation'] == 'shorten'
data = search(stored, operation='expand').json()
assert [r['version'] for r in data['results']] == [5]
data = search(stored, operation='').json()
assert [r['version'] for r in data['results']] == [4], 'empty operation = exact ""'
print('D. Operation filtering: OK')

# --- E. favorite=true ---
data = search(stored, favorite='true').json()
assert [r['version'] for r in data['results']] == [1, 3]
assert all(r['favorite'] is True for r in data['results'])
print('E. favorite=true: OK (1, 3)')

# --- F. favorite=false ---
data = search(stored, favorite='false').json()
assert [r['version'] for r in data['results']] == [2, 4, 5]
assert all(r['favorite'] is False for r in data['results'])
print('F. favorite=false: OK (2, 4, 5)')

# --- G. Tag filtering: normalization, exact, no substring ---
data = search(stored, tag='ai').json()
assert [r['version'] for r in data['results']] == [1, 2, 5]
data = search(stored, tag='  AI ').json()
assert [r['version'] for r in data['results']] == [1, 2, 5], 'normalize + trim'
data = search(stored, tag='CINEMATIC').json()
assert [r['version'] for r in data['results']] == [1, 3], 'exact match (2 has ai only, 5 has cinematic-pro)'
data = search(stored, tag='cinematic-pro').json()
assert [r['version'] for r in data['results']] == [5]
data = search(stored, tag='cine').json()
assert data['count'] == 0, 'no substring matching'
data = search(stored, tag='cinematicx').json()
assert data['count'] == 0, 'no substring matching'
print('G. Tag filtering (normalize/trim/exact/no substring): OK')

# --- H. Version range inclusive ---
data = search(stored, min_version=2, max_version=4).json()
assert [r['version'] for r in data['results']] == [2, 3, 4], 'inclusive'
data = search(stored, min_version=3).json()
assert [r['version'] for r in data['results']] == [3, 4, 5]
data = search(stored, max_version=2).json()
assert [r['version'] for r in data['results']] == [1, 2]
data = search(stored, min_version=4, max_version=4).json()
assert [r['version'] for r in data['results']] == [4], 'boundary inclusive'
print('H. Version range (min/max/inclusive): OK')

# --- I. Combined filters AND logic ---
# query=cinematic & source=refinement & favorite=true & tag=ai & range 1..4
# cinematic: 1,2,3,5 -> refinement: 2,5 -> favorite: none (2,5 not fav)
data = search(stored, query='cinematic', source='refinement',
              favorite='true', tag='ai', min_version=1, max_version=4).json()
assert data['count'] == 0
# drop favorite constraint: refinement+cinematic+tag ai+range 1..4 -> v2
data = search(stored, query='cinematic', source='refinement',
              tag='ai', min_version=1, max_version=4).json()
assert [r['version'] for r in data['results']] == [2]
for r in data['results']:
    assert 'cinematic' in r['prompt'].lower()
    assert r['source'] == 'refinement'
    assert 'ai' in r['tags']
    assert 1 <= r['version'] <= 4
# AND: adding impossible constraint yields empty
data = search(stored, query='cinematic', source='custom').json()
assert data['count'] == 0
print('I. Combined filters AND logic: OK')

# --- J. Empty/no-match search ---
data = search(stored, query='zzzznonexistent').json()
assert data['count'] == 0 and data['results'] == []
data = search(stored, query='').json()
assert data['count'] == 5, 'empty query = no text filter'
data = search(stored, tag='missingtag').json()
assert data['count'] == 0 and data['results'] == []
print('J. Empty/no-match search: OK (count=0, results=[])')

# --- K. Sorting ---
asc = search(stored, sort='version_asc').json()
assert [r['version'] for r in asc['results']] == [1, 2, 3, 4, 5]
desc = search(stored, sort='version_desc').json()
assert [r['version'] for r in desc['results']] == [5, 4, 3, 2, 1]
ca_asc = search(stored, sort='created_at_asc').json()
assert [r['version'] for r in ca_asc['results']] == [1, 2, 3, 4, 5]
ca_desc = search(stored, sort='created_at_desc').json()
assert [r['version'] for r in ca_desc['results']] == [5, 4, 3, 2, 1]
# deterministic
assert asc == search(stored, sort='version_asc').json()
assert desc == search(stored, sort='version_desc').json()
print('K. Sorting (version_asc/desc, created_at_asc/desc, deterministic): OK')

# --- L. Delete a Day16 version ---
# favorite v4 + tag it, then delete it
fav(stored, 4)
add_tags(stored, 4, ['deleteme'])
assert search(stored, favorite='true').json()['count'] == 3  # 1,3,4
deleted = client.delete(f'/api/videos/{stored}/prompt/history/4')
assert deleted.status_code == 200, deleted.status_code
# deleted version does not appear
data = search(stored).json()
assert [r['version'] for r in data['results']] == [1, 2, 3, 5]
assert 4 not in [r['version'] for r in data['results']]
# its favorite metadata does not appear
data = search(stored, favorite='true').json()
assert [r['version'] for r in data['results']] == [1, 3]
# its tags do not appear
data = search(stored, tag='deleteme').json()
assert data['count'] == 0
# remaining versions still search correctly
data = search(stored, query='cinematic').json()
assert [r['version'] for r in data['results']] == [1, 2, 3, 5]
# next created version keeps Day16 numbering (1,2,3,5 -> next = 6)
v6 = save(stored, 'cinematic epilogue six')
assert v6['version'] == 6, v6['version']
data = search(stored, query='cinematic').json()
assert [r['version'] for r in data['results']] == [1, 2, 3, 5, 6]
print(f'L. Deletion integration: OK (4 gone; favorites 1,3; next version=6)')

# --- M. Multi-video isolation ---
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
save(stored_b, 'cinematic other video prompt', source='custom')
fav(stored_b, 1)
add_tags(stored_b, 1, ['ai', 'other'])
data_a = search(stored, query='cinematic').json()
data_b = search(stored_b, query='cinematic').json()
assert all(r['video_filename'] == stored for r in data_a['results'])
assert all(r['video_filename'] == stored_b for r in data_b['results'])
assert [r['version'] for r in data_b['results']] == [1]
assert data_b['results'][0]['favorite'] is True
# favorites/tags from B never affect A
assert [r['version'] for r in search(stored, tag='other').json()['results']] == []
a_favs = [r['version'] for r in search(stored, favorite='true').json()['results']]
assert a_favs == [1, 3], a_favs
b_favs = [r['version'] for r in search(stored_b, favorite='true').json()['results']]
assert b_favs == [1], b_favs
assert search(stored_b, tag='other').json()['count'] == 1
assert search(stored, tag='other').json()['count'] == 0
assert search(stored, source='custom').json()['count'] == 1  # v4 deleted, only custom left? v4 was custom
print('M. Multi-video isolation: OK')

# --- N. Route collision: /prompt/search not a numeric version route ---
resp = client.get(f'/api/videos/{stored}/prompt/search')
assert resp.status_code == 200
assert 'results' in resp.json() and 'version_id' not in resp.json()
# numeric version route still intact
resp = client.get(f'/api/videos/{stored}/prompt/history/1')
assert resp.status_code == 200 and 'version_id' in resp.json()
print('N. Route collision (/prompt/search vs numeric route): OK')

# --- O. Validation ---
o1 = client.get('/api/videos/nonexistent.mp4/prompt/search')
assert o1.status_code == 404, o1.status_code
o2 = client.get('/api/videos/../../../etc/passwd/prompt/search')
assert o2.status_code in (400, 404), o2.status_code
o3 = search(stored, source='database')
assert o3.status_code == 422, o3.status_code
o4 = search(stored, sort='random')
assert o4.status_code == 422, o4.status_code
o5 = search(stored, favorite='notabool')
assert o5.status_code == 422, o5.status_code
o6 = search(stored, min_version=0)
assert o6.status_code == 422, o6.status_code
o7 = search(stored, max_version=0)
assert o7.status_code == 422, o7.status_code
o8 = search(stored, min_version=5, max_version=2)
assert o8.status_code == 422, o8.status_code
print(f'O. Validation: OK (404/{o2.status_code}/422/422/422/422/422/422)')

# --- P. Data integrity ---
v1_after = client.get(f'/api/videos/{stored}/prompt/history/1').json()
assert v1_after['prompt'] == v1['prompt'], 'prompt unchanged'
assert v1_after['negative_prompt'] == v1['negative_prompt'], 'negative unchanged'
assert v1_after['source'] == v1['source'], 'source unchanged'
assert v1_after['operation'] == v1['operation'], 'operation unchanged'
blob = json.dumps({
    'search': search(stored).json(),
    'filtered': search(stored, query='cinematic', favorite='true').json(),
}).lower()
for word in ['person', 'character', 'dialogue', 'walking', 'running',
             'park', 'city', 'sunset', 'brand', 'product', 'voiceover']:
    assert word not in blob, f'fabricated: {word}'
raw = json.dumps(search(stored).json())
for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
    assert bad not in raw, f'absolute path {bad}'
print('P. Data integrity (prompt/neg/source/op unchanged, no fabrication, no paths): OK')

# --- Q. Determinism ---
q1 = search(stored, query='cinematic', favorite='true', sort='version_desc').json()
q2 = search(stored, query='cinematic', favorite='true', sort='version_desc').json()
assert q1 == q2, 'identical searches must return identical results'
q3 = search(stored, tag='ai').json()
q4 = search(stored, tag='ai').json()
assert q3 == q4
print('Q. Determinism: OK')

# --- R. Regression: Day16 + Day17 ---
hist = client.get(f'/api/videos/{stored}/prompt/history')
assert hist.status_code == 200
versions = [x['version'] for x in hist.json()['versions']]
assert versions == [1, 2, 3, 5, 6], versions
single = client.get(f'/api/videos/{stored}/prompt/history/1')
assert single.status_code == 200 and single.json()['prompt'] == v1['prompt']
cmp_r = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2')
assert cmp_r.status_code == 200
assert 'added_tokens' in cmp_r.json() and 'common_tokens' in cmp_r.json()
assert fav(stored, 6).status_code == 200
assert unfav(stored, 6).status_code == 200
assert add_tags(stored, 6, [' Cinematic ', 'AI', 'ai']).json()['tags'] == ['ai', 'cinematic']
assert rm_tags(stored, 6, ['ai']).json()['tags'] == ['cinematic']
org = client.get(f'/api/videos/{stored}/prompt/history/6/organization')
assert org.status_code == 200
assert org.json() == {'video_filename': stored, 'version': 6,
                      'favorite': False, 'tags': ['cinematic']}
favs = client.get(f'/api/videos/{stored}/prompt/history/favorites')
assert favs.status_code == 200
assert [x['version'] for x in favs.json()['favorites']] == [1, 3]
by_tag = client.get(f'/api/videos/{stored}/prompt/history/tag/cinematic')
assert by_tag.status_code == 200
assert [x['version'] for x in by_tag.json()['versions']] == [1, 3, 6]
# Day 1-15 representative
assert client.get('/api/health').status_code == 200
assert client.post(f'/api/videos/{stored}/intelligence').status_code == 200
assert client.post(f'/api/videos/{stored}/advanced-prompt?style=realistic').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/refine',
                   json={'operation': 'shorten'}).status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/template',
                   json={'template': 'documentary'}).status_code == 200
print('R. Day16/Day17/Day1-15 regression: OK')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 18 MANUAL E2E VERIFICATIONS PASSED')
