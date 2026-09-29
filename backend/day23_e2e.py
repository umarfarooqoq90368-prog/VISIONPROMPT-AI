import io, json, os, re, subprocess, tempfile, zipfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import PromptQualityService, DIMENSIONS
from app.services.prompt_comparison_service import PromptComparisonService

client = TestClient(app)
quality_svc = PromptQualityService()
history_svc = None  # bound from app services below
compare_svc = None
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day23_e2e.mp4')

# use the app's own service instances (same single stores as the API)
from app.api import videos as videos_api
history_svc = videos_api.prompt_history_service
compare_svc = videos_api.comparison_service
assert isinstance(compare_svc, PromptComparisonService)
assert compare_svc.history_service is history_svc, 'same Day16 store'

subprocess.run(
    [ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-y', tmp],
    capture_output=True, timeout=15,
)

# --- Pipeline: upload -> frames -> visual -> scenes -> subjects -> audio ->
#     intelligence -> advanced prompt -> refinement -> template -> history
#     -> favorites/tags -> search -> export -> package -> quality -> improve
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
PB = 'isolated video B prompt'
SPEC_A = 'A person walks through a road.'
SPEC_B = 'A person walks through a road. Medium shot with natural lighting.'


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


def quality(video, prompt):
    return client.post(f'/api/videos/{video}/prompt/quality',
                       json={'prompt': prompt})


def vquality(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}/quality')


def improve(video, prompt):
    return client.post(f'/api/videos/{video}/prompt/improve',
                       json={'prompt': prompt})


def himprove(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}/improve')


def compare(video, va, vb):
    return client.get(f'/api/videos/{video}/prompt/history/compare/'
                      f'{va}/{vb}/detailed')


# --- Day 16 history (video A): 1-3 + spec pair 4-5 ---
v1 = save(stored, P1, source='refinement', operation='cinematic',
          metadata={'style': 'film'})
v2 = save(stored, P2, source='template', operation='ai_video')
v3 = save(stored, P3, negative='', source='custom', operation='')
v4 = save(stored, SPEC_A)
v5 = save(stored, SPEC_B)
assert [v['version'] for v in (v1, v2, v3, v4, v5)] == [1, 2, 3, 4, 5]

# --- Day 17 favorites/tags (video A) ---
assert client.post(f'/api/videos/{stored}/prompt/history/1/favorite').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/history/1/tags',
                   json={'tags': [' Cinematic ', 'ai']}).json()['tags'] == \
    ['ai', 'cinematic']
org_v1 = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert org_v1 == {'video_filename': stored, 'version': 1,
                  'favorite': True, 'tags': ['ai', 'cinematic']}

# --- Day 18 search / Day 19-22 sanity ---
assert client.get(f'/api/videos/{stored}/prompt/search',
                  params={'query': 'cinematic'}).json()['count'] == 2
assert export(stored, 1, 'json').status_code == 200
assert package(stored, 1).content[:2] == b'PK'
assert quality(stored, P1).status_code == 200
assert improve(stored, P1).status_code == 200
assert himprove(stored, 1).status_code == 200
print('Day 16/17/18/19/20/21/22 setup: OK')

original_record = get_version(stored, 1)
original_json = json.dumps(original_record, sort_keys=True)
listing_before = client.get(f'/api/videos/{stored}/prompt/history').json()

# ==================== A. Detailed compare response ====================
resp = compare(stored, 4, 5)
assert resp.status_code == 200, resp.status_code
a = resp.json()
assert set(a.keys()) == {'video_filename', 'version_a', 'version_b',
                         'comparison'}, list(a.keys())
assert a['video_filename'] == stored
for key, num in (('version_a', 4), ('version_b', 5)):
    assert set(a[key].keys()) == {'version', 'version_id', 'source',
                                  'operation', 'prompt', 'quality'}, key
    assert a[key]['version'] == num
    assert a[key]['version_id'] == f'{stored}:{num}'
assert set(a['comparison'].keys()) == {
    'identical', 'changed', 'added_text', 'removed_text', 'common_text',
    'quality_score_delta', 'quality_score_change', 'completeness_delta',
    'completeness_change', 'changed_dimensions',
}, list(a['comparison'].keys())
assert a['version_a']['prompt'] == SPEC_A and a['version_b']['prompt'] == SPEC_B
print('A. Detailed compare response: OK (200, exact schema, prompts echoed)')

# ==================== B. Text diff ====================
b = a['comparison']
assert b['identical'] is False and b['changed'] is True
assert b['common_text'] == SPEC_A, 'original prompt fully common'
assert b['removed_text'] == '', 'nothing removed for a pure append'
assert b['added_text'] in SPEC_B, 'added text comes from version B'
assert b['added_text'].strip() == 'Medium shot with natural lighting.'
d12 = compare(stored, 1, 2).json()['comparison']
assert d12['changed'] is True and d12['identical'] is False
assert d12['added_text'] and d12['removed_text'], 'different prompts show both'
for word in d12['added_text'].split():
    assert word in P2.split(), f'fabricated: {word}'
for word in d12['removed_text'].split():
    assert word in P1.split(), f'fabricated: {word}'
print('B. Text diff: OK (added/removed/common exact, no invented words)')

# ==================== C. Quality deltas ====================
qa = quality(stored, SPEC_A).json()['quality']
qb = quality(stored, SPEC_B).json()['quality']
assert (b['quality_score_delta']
        == qb['overall_score'] - qa['overall_score']) > 0
assert (b['completeness_delta']
        == qb['completeness_percentage'] - qa['completeness_percentage']) > 0
assert b['quality_score_change'] == 'increased'
assert b['completeness_change'] == 'increased'
assert (a['version_a']['quality'] == qa
        and a['version_b']['quality'] == qb), 'embedded quality == Day21'
print('C. Quality deltas: OK (b - a math, neutral labels, Day21 embedded)')

# ==================== D. Changed dimensions ====================
expected_dims = []
for dim in DIMENSIONS:
    if qa['dimensions'][dim] != qb['dimensions'][dim]:
        expected_dims.append(dim)
assert [c['dimension'] for c in b['changed_dimensions']] == expected_dims == \
    ['camera', 'lighting'], 'exactly the differing Day21 dimensions'
for c in b['changed_dimensions']:
    assert set(c.keys()) == {'dimension', 'before_present', 'after_present',
                             'before_score', 'after_score'}
    assert c['before_present'] is False and c['after_present'] is True
assert compare(stored, 1, 1).json()['comparison']['changed_dimensions'] == []
assert [c['dimension'] for c in b['changed_dimensions']] == \
    [d for d in DIMENSIONS if d in set(expected_dims)], 'Day21 order'
print('D. Changed dimensions: OK (matches direct Day21 diff, ordered)')

# ==================== E. Version order never swapped ====================
rev = compare(stored, 5, 4).json()
assert rev['version_a']['version'] == 5 and rev['version_b']['version'] == 4
assert rev['version_a']['prompt'] == SPEC_B and rev['version_b']['prompt'] == SPEC_A
rc = rev['comparison']
assert rc['quality_score_delta'] == -b['quality_score_delta']
assert rc['completeness_delta'] == -b['completeness_delta']
assert rc['quality_score_change'] == 'decreased'
assert rc['added_text'] == b['removed_text']
assert rc['removed_text'] == b['added_text']
assert rc['common_text'] == b['common_text']
print('E. Version order: OK (deltas are b - a, reversed request mirrors)')

# ==================== F. Determinism ====================
f1 = compare(stored, 4, 5).json()
f2 = compare(stored, 4, 5).json()
assert f1 == f2, 'identical repeated comparisons'
text = json.dumps(f1)
for pat in (r'\d{4}-\d{2}-\d{2}', r'\d{2}:\d{2}', 'uuid', 'timestamp'):
    assert pat not in text.lower() and not re.search(pat, text), pat
print('F. Determinism: OK (repeat identical, no dates/uuids/timestamps)')

# ==================== G. Validation ====================
assert compare(stored, 0, 1).status_code == 422
assert compare(stored, 1, -1).status_code == 422
assert client.get(f'/api/videos/{stored}/prompt/history/compare/'
                  'abc/1/detailed').status_code == 422
assert compare('nope.mp4', 1, 2).status_code == 404
assert compare('notavideo.txt', 1, 2).status_code == 400
assert compare(stored, 99, 1).status_code == 404
assert compare(stored, 1, 99).status_code == 404
g_t = client.get('/api/videos/../../../etc/passwd/prompt/history/compare/'
                 '1/1/detailed')
assert g_t.status_code == 404, g_t.status_code
print('G. Validation: OK (422 version<1/non-int, 404 video/version/'
      'traversal, 400 ext)')

# ==================== H. Day16 compare + route collision ====================
old = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2')
assert old.status_code == 200 and 'common_tokens' in old.json()
assert 'comparison' not in old.json(), 'Day16 response unchanged'
assert 'added_tokens' in old.json()
assert get_version(stored, 1)['prompt'] == P1, 'numeric route still resolves'
assert client.post(f'/api/videos/{stored}/prompt/history/1/favorite').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/favorites').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/tag/ai').status_code == 200
assert vquality(stored, 1).status_code == 200
assert himprove(stored, 1).status_code == 200
assert quality(stored, P1).status_code == 200
assert export(stored, 1, 'json').status_code == 200
assert package(stored, 1).content[:2] == b'PK'
assert client.get(f'/api/videos/{stored}/prompt/search').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history').status_code == 200
print('H. Route collision: OK (Day16 compare, numeric, favorites, tag, '
      'quality, improve, export, package, search)')

# ==================== I. Read-only ====================
compare(stored, 1, 2)
compare(stored, 2, 1)
compare(stored, 4, 5)
compare(stored, 1, 1)
assert json.dumps(get_version(stored, 1), sort_keys=True) == original_json, \
    'history record unchanged after comparisons'
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization').json() == \
    org_v1, 'org metadata unchanged after comparisons'
listing_after = client.get(f'/api/videos/{stored}/prompt/history').json()
assert listing_after == listing_before, \
    'comparison never created/deleted a version (single Day16 store)'
print('I. Read-only: OK (history/org/listing untouched, nothing auto-saved)')

# ==================== J. Multiple videos ====================
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
save(stored_b, PB, source='custom')
cb = compare(stored_b, 1, 1)
assert cb.status_code == 200 and cb.json()['comparison']['identical'] is True
assert cb.json()['version_a']['prompt'] == PB
assert compare(stored_b, 2, 1).status_code == 404, 'B has only one version'
assert compare(stored, 6, 1).status_code == 404, 'A still has only 5 versions'
assert compare(stored, 4, 5).json()['version_a']['prompt'] == SPEC_A, \
    'A comparison unaffected by B'
print('J. Multiple videos: OK (A/B isolated, no cross-video comparison)')

# ==================== K. Day16 regression ====================
lv = save(stored, 'temporary for delete check')
assert lv['version'] == 6
assert client.delete(f'/api/videos/{stored}/prompt/history/6').status_code == 200
assert compare(stored, 6, 1).status_code == 404, 'deleted version 404'
assert [x['version'] for x in
        client.get(f'/api/videos/{stored}/prompt/history').json()['versions']] \
    == [1, 2, 3, 4, 5]
lg = client.get(f'/api/videos/{stored}/prompt/history/3')
assert lg.status_code == 200 and lg.json()['prompt'] == P3
lc = client.get(f'/api/videos/{stored}/prompt/history/compare/1/3')
assert lc.status_code == 200 and 'common_tokens' in lc.json()
re_save = save(stored, 'recreated after delete')
assert re_save['version'] == 6, 'Day16 numbering unchanged (max live + 1)'
assert compare(stored, 6, 6).json()['comparison']['identical'] is True
print('K. Day16 regression: OK (create/list/get/compare/delete/numbering)')

# ==================== L. Day17 regression ====================
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
print('L. Day17 regression: OK (favorite/unfavorite/tags/org)')

# ==================== M. Day18 regression ====================
def search(**params):
    return client.get(f'/api/videos/{stored}/prompt/search', params=params)

assert [r['version'] for r in search(query='cinematic').json()['results']] == [1, 3]
assert [r['version'] for r in search(favorite='true').json()['results']] == [1]
assert [r['version'] for r in search(tag='ai').json()['results']] == [1]
assert [r['version'] for r in search(source='custom').json()['results']] == [3, 4, 5, 6]
assert [r['version'] for r in
        search(query='cinematic', source='refinement', favorite='true',
               tag='ai').json()['results']] == [1]
print('M. Day18 regression: OK (query/favorite/tag/source/combined)')

# ==================== N. Day19/20 regression ====================
for fmt in ('json', 'markdown', 'txt'):
    e1 = export(stored, 1, fmt)
    e2 = export(stored, 1, fmt)
    assert e1.status_code == e2.status_code == 200
    assert e1.content == e2.content, f'{fmt} export deterministic'
assert export(stored, 1, 'xml').status_code == 422
o_files = read_zip(package(stored, 1))
assert o_files['prompt.json'] == export(stored, 1, 'json').text
assert o_files['prompt.md'] == export(stored, 1, 'markdown').text
assert o_files['prompt.txt'] == export(stored, 1, 'txt').text
k1, k2 = package(stored, 1), package(stored, 1)
assert k1.content == k2.content, 'package still byte-identical'
print('N. Day19/20 regression: OK (exports + packages intact and deterministic)')

# ==================== O. Day21/22 regression ====================
q_before = quality(stored, P1).json()
improve(stored, 'another prompt for regression check')
compare(stored, 1, 3)
assert quality(stored, P1).json() == q_before, 'Day21 quality unchanged'
vq1, vq2 = vquality(stored, 1), vquality(stored, 1)
assert vq1.content == vq2.content, 'Day21 history quality deterministic'
imp = improve(stored, SPEC_A)
assert imp.status_code == 200 and imp.json()['improvement_applied'] is True
himp = himprove(stored, 4)
assert himp.status_code == 200 and himp.json()['source_prompt'] == SPEC_A
assert quality(stored, P1).json() == q_before, 'quality unchanged by improve'
print('O. Day21/22 regression: OK (quality + improve intact after compare)')

# ==================== P. Security / single store ====================
blobs = [json.dumps(compare(stored, 4, 5).json()),
         json.dumps(compare(stored, 5, 4).json()),
         json.dumps(compare(stored, 1, 2).json()),
         json.dumps(improve(stored, SOURCE := 'A person walks down a road.').json()),
         json.dumps(himprove(stored, 1).json()),
         json.dumps(search().json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/history').json())]
for ver in (1, 3, 5, 6):
    blobs += list(read_zip(package(stored, ver)).values())
for blob in blobs:
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in blob, f'absolute path {bad}'
    for internal in ['_storage', 'PromptComparisonService',
                     'PromptImprovementService', 'PromptQualityService',
                     'PromptHistoryService', 'storage/uploads', 'BytesIO',
                     'Traceback', 'os.environ']:
        assert internal not in blob, f'internal leak {internal}'
final_rec = get_version(stored, 1)
assert json.dumps(final_rec, sort_keys=True) == original_json, \
    'stored history never modified'
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization').json() == \
    org_v1, 'org metadata never modified'
final_list = [x['version'] for x in
              client.get(f'/api/videos/{stored}/prompt/history').json()['versions']]
assert final_list == [1, 2, 3, 4, 5, 6], 'single Day16 store, no second store'
for ver in final_list:
    assert compare(stored, ver, ver).status_code == 200
    assert package(stored, ver).status_code == 200
    assert vquality(stored, ver).status_code == 200
    assert himprove(stored, ver).status_code == 200
assert compare(stored, 7, 1).status_code == 404
assert vquality(stored, 7).status_code == 404
print('P. Security + single store: OK (no leaks, history+org untouched, '
      'every version comparable)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 23 MANUAL E2E VERIFICATIONS PASSED')
