import io, json, os, re, subprocess, tempfile, zipfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import PromptQualityService, DIMENSIONS
from app.services.prompt_readiness_history_service import (
    PromptReadinessHistoryService,
)

client = TestClient(app)
quality_svc = PromptQualityService()
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day25_e2e.mp4')

# use the app's own service instances (same single stores as the API)
from app.api import videos as videos_api
history_svc = videos_api.prompt_history_service
readiness_svc = videos_api.readiness_service
rh_svc = videos_api.readiness_history_service
assert isinstance(rh_svc, PromptReadinessHistoryService)
assert rh_svc.history_service is videos_api.prompt_history_service, \
    'reuses Day16 history service (no second store)'
assert rh_svc.readiness_service is videos_api.readiness_service, \
    'reuses Day24 readiness service'

subprocess.run(
    [ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-y', tmp],
    capture_output=True, timeout=15,
)

# --- Pipeline: upload -> frames -> visual -> scenes -> subjects -> audio ->
#     intelligence -> advanced prompt -> refinement -> template -> history
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
PB = 'isolated video B prompt'

# Day21/24-verified fixture prompts
FULL = ('Cinematic film grain style portrait of a person, the subject '
        'walking, looking around and gesturing in an outdoor forest '
        'street, camera tracking with shallow depth of field, soft '
        'lighting with rim light and golden hour glow, vibrant teal and '
        'orange palette with warm tones, layered foreground and rule of '
        'thirds composition, ambient sound with quiet music score.')
REQ_ONLY = ('Cinematic film grain style portrait of a person, the subject '
            'walking, looking around and gesturing in an outdoor forest '
            'street, camera tracking with shallow depth of field, soft '
            'lighting with rim light and golden hour glow, layered '
            'foreground and rule of thirds composition.')
CITY = 'A person walks through a city street.'
WEAK_CAM = ('Cinematic film grain style portrait of a person, the subject '
            'walking, looking around and gesturing in an outdoor forest '
            'street, tracking only, soft lighting with rim light and '
            'golden hour glow, vibrant teal and orange palette with warm '
            'tones, layered foreground and rule of thirds composition, '
            'ambient sound with quiet music score.')


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


def readiness(video, prompt):
    return client.post(f'/api/videos/{video}/prompt/readiness',
                       json={'prompt': prompt})


def hreadiness(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}/readiness')


def analyze(video, versions=None):
    params = None if versions is None else {'versions': versions}
    return client.get(f'/api/videos/{video}/prompt/history/readiness',
                      params=params)


# --- Day 16 history (video A): 4 fixture versions ---
v1 = save(stored, FULL, source='advanced_prompt', operation='generate')
v2 = save(stored, CITY, source='custom', operation='')
v3 = save(stored, REQ_ONLY, source='refinement', operation='expand')
v4 = save(stored, WEAK_CAM, source='template', operation='cinematic')
assert [v['version'] for v in (v1, v2, v3, v4)] == [1, 2, 3, 4]

# --- Day 17 favorites/tags (video A) ---
assert client.post(f'/api/videos/{stored}/prompt/history/1/favorite').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/history/1/tags',
                   json={'tags': [' Cinematic ', 'ai']}).json()['tags'] == \
    ['ai', 'cinematic']
org_v1 = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert org_v1 == {'video_filename': stored, 'version': 1,
                  'favorite': True, 'tags': ['ai', 'cinematic']}
print('Day 16/17 setup: OK')

original_record = get_version(stored, 1)
original_json = json.dumps(original_record, sort_keys=True)
listing_before = client.get(f'/api/videos/{stored}/prompt/history').json()
quality_before = quality(stored, FULL).json()
export_before = export(stored, 1, 'json').content

# ==================== A. response schema ====================
resp = analyze(stored)
assert resp.status_code == 200, resp.status_code
a = resp.json()
assert set(a.keys()) == {'video_filename', 'versions_analyzed', 'results',
                         'summary', 'dimension_summary'}, list(a.keys())
assert a['video_filename'] == stored
for item in a['results']:
    assert set(item.keys()) == {'version', 'version_id', 'source',
                                'operation', 'readiness'}
    assert item['version_id'] == f"{stored}:{item['version']}"
    assert set(item['readiness'].keys()) == {
        'status', 'required_dimensions', 'supporting_dimensions',
        'checklist', 'coverage', 'missing_dimensions', 'weak_dimensions',
        'suggestions'}
print('A. response schema: OK (200, exact keys, version_id, Day24 readiness)')

# ==================== B. all versions ====================
assert a['versions_analyzed'] == [1, 2, 3, 4]
statuses = [r['readiness']['status'] for r in a['results']]
assert statuses == ['ready', 'needs_attention', 'ready', 'needs_attention']
prompts = {1: FULL, 2: CITY, 3: REQ_ONLY, 4: WEAK_CAM}
sources = {1: ('advanced_prompt', 'generate'), 2: ('custom', ''),
           3: ('refinement', 'expand'), 4: ('template', 'cinematic')}
for r in a['results']:
    v = r['version']
    assert (r['source'], r['operation']) == sources[v]
    assert r['readiness'] == hreadiness(stored, v).json()['readiness'], \
        f'v{v} == Day24 history readiness (byte-exact reuse)'
    assert r['readiness'] == readiness(stored, prompts[v]).json()['readiness'], \
        f'v{v} == Day24 POST readiness for same prompt'
assert a['summary']['versions_analyzed'] == 4
assert a['summary']['ready_count'] == 2
assert a['summary']['needs_attention_count'] == 2
print('B. all versions: OK (ascending [1-4], exact Day24 reuse, 2 ready/2 attention)')

# ==================== C. selected versions ====================
s13 = analyze(stored, '1,3').json()
assert s13['versions_analyzed'] == [1, 3]
assert [r['version'] for r in s13['results']] == [1, 3]
s_rev = analyze(stored, '4,2').json()
assert s_rev['versions_analyzed'] == [4, 2], 'requested order preserved'
s_one = analyze(stored, '2').json()
assert s_one['versions_analyzed'] == [2]
assert s_one['summary']['versions_analyzed'] == 1
rep = client.get(f'/api/videos/{stored}/prompt/history/readiness',
                 params=[('versions', '1'), ('versions', '3')])
assert rep.status_code == 200 and rep.json()['versions_analyzed'] == [1, 3]
all_by_v = {r['version']: r for r in a['results']}
assert s_rev['results'] == [all_by_v[4], all_by_v[2]], \
    'selected results identical to all-version results'
sp = analyze(stored, ' 1 , 3 ').json()
assert sp['versions_analyzed'] == [1, 3], 'whitespace tolerated'
print('C. selected versions: OK (1,3 / 4,2 order / single / repeated params)')

# ==================== D. aggregate summary ====================
summary = a['summary']
assert summary['required_dimensions_total'] == 28
assert summary['required_dimensions_present'] == 21
assert summary['required_dimensions_weak'] == 2
assert summary['required_dimensions_missing'] == 5
assert summary['required_coverage_percentage'] == round(21 / 28 * 100)
assert summary['supporting_dimensions_total'] == 8
assert summary['supporting_dimensions_present'] == 4
assert summary['supporting_dimensions_weak'] == 0
assert summary['supporting_dimensions_missing'] == 4
assert summary['supporting_coverage_percentage'] == 50
assert (summary['required_dimensions_present'] + summary['required_dimensions_weak']
        + summary['required_dimensions_missing']) == 28
assert (summary['supporting_dimensions_present'] + summary['supporting_dimensions_weak']
        + summary['supporting_dimensions_missing']) == 8
assert (summary['ready_count'] + summary['needs_attention_count']) == 4
assert set(summary.keys()) == {
    'versions_analyzed', 'ready_count', 'needs_attention_count',
    'required_dimensions_total', 'required_dimensions_present',
    'required_dimensions_weak', 'required_dimensions_missing',
    'required_coverage_percentage', 'supporting_dimensions_total',
    'supporting_dimensions_present', 'supporting_dimensions_weak',
    'supporting_dimensions_missing', 'supporting_coverage_percentage'}
print('D. aggregate summary: OK (21+2+5=28, 75%, supporting 4/8, exact keys)')

# ==================== E. dimension summary ====================
dims = a['dimension_summary']
assert [d['dimension'] for d in dims] == list(DIMENSIONS), 'Day21 order'
assert len(dims) == 9
for entry in dims:
    assert (entry['present_count'] + entry['weak_count']
            + entry['missing_count']) == 4, entry['dimension']
    assert set(entry.keys()) == {'dimension', 'present_count',
                                 'weak_count', 'missing_count'}
by_dim = {d['dimension']: d for d in dims}
assert (by_dim['camera']['present_count'], by_dim['camera']['weak_count'],
        by_dim['camera']['missing_count']) == (2, 1, 1)
assert (by_dim['subject']['present_count'], by_dim['subject']['weak_count'],
        by_dim['subject']['missing_count']) == (3, 1, 0)
assert (by_dim['environment']['present_count'], by_dim['environment']['weak_count'],
        by_dim['environment']['missing_count']) == (4, 0, 0)
assert (by_dim['color']['present_count'], by_dim['color']['weak_count'],
        by_dim['color']['missing_count']) == (2, 0, 2)
print('E. dimension summary: OK (Day21 order, sums==4, exact spot counts)')

# ==================== F. supporting informational only ====================
v3r = all_by_v[3]['readiness']
assert v3r['status'] == 'ready', 'supporting missing never blocks ready'
assert v3r['missing_dimensions'] == ['color', 'audio']
assert all_by_v[4]['readiness']['coverage']['supporting_present'] == 2
assert all_by_v[4]['readiness']['status'] == 'needs_attention', \
    'required weak blocks ready despite supporting present'
s3 = analyze(stored, '3').json()['summary']
assert s3['ready_count'] == 1 and s3['supporting_dimensions_missing'] == 2
print('F. supporting informational: OK (v3 ready, v4 attention, counts align)')

# ==================== G. validation ====================
for bad in ('', '0', '-1', 'abc', '1,,2', '1,1', '1.5', ',', '2,2',
            ' ', '0,1', '1;2', '+2'):
    assert analyze(stored, bad).status_code == 422, repr(bad)
assert analyze('nope.mp4').status_code == 404
assert analyze('notavideo.txt').status_code == 400
trav = client.get('/api/videos/../../../etc/passwd/prompt/history/readiness')
assert trav.status_code == 404, trav.status_code
assert analyze(stored, '99').status_code == 404
tmp_v = save(stored, 'temporary for delete check')
assert tmp_v['version'] == 5
assert analyze(stored).json()['versions_analyzed'] == [1, 2, 3, 4, 5]
assert client.delete(f'/api/videos/{stored}/prompt/history/5').status_code == 200
assert analyze(stored, '5').status_code == 404, 'deleted version 404'
assert analyze(stored).json()['versions_analyzed'] == [1, 2, 3, 4], \
    'deleted version excluded from all-version analysis'
print('G. validation: OK (422 parsing, 404 video/version/traversal, 400 ext, '
      'deleted excluded)')

# ==================== H. empty history video ====================
with open(tmp, 'rb') as f:
    up_c = client.post('/api/videos/upload', files={'file': ('test3.mp4', f, 'video/mp4')})
stored_c = up_c.json()['video']['stored_filename']
empty = analyze(stored_c)
assert empty.status_code == 200, 'no versions -> 200, not error'
e = empty.json()
assert e['versions_analyzed'] == [] and e['results'] == []
assert e['summary']['versions_analyzed'] == 0
assert e['summary']['required_coverage_percentage'] == 0
assert len(e['dimension_summary']) == 9
print('H. empty history: OK (200 with zeroed analysis, 9 dimension entries)')

# ==================== I. determinism ====================
i1 = analyze(stored).json()
i2 = analyze(stored).json()
assert i1 == i2, 'identical repeated results'
iu = client.get(f'/api/videos/{stored}/prompt/history/readiness').json()
assert iu == i1
text = json.dumps(i1)
for pat in (r'\d{4}-\d{2}-\d{2}', r'\d{2}:\d{2}'):
    assert not re.search(pat, text), pat
for token in ('uuid', 'timestamp', 'created_at'):
    assert token not in text.lower(), token
assert json.dumps(analyze(stored, '1,2').json()) == \
    json.dumps(analyze(stored, '1,2').json()), 'selection deterministic'
print('I. determinism: OK (repeat identical, no timestamps/uuids)')

# ==================== J. read-only integrity ====================
analyze(stored)
analyze(stored, '1,4')
analyze(stored_c)
assert json.dumps(get_version(stored, 1), sort_keys=True) == original_json, \
    'history record unchanged after analysis'
assert client.get(f'/api/videos/{stored}/prompt/history').json() == \
    listing_before, 'readiness history never created/deleted a version'
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization'
                  ).json() == org_v1, 'org unchanged after analysis'
assert export(stored, 1, 'json').content == export_before, \
    'export unchanged after analysis'
assert quality(stored, FULL).json() == quality_before, \
    'Day21 quality unchanged after analysis'
assert get_version(stored, 2)['prompt'] == CITY, 'prompt text untouched'
print('J. read-only: OK (history/org/listing/export/quality untouched)')

# ==================== K. multiple videos ====================
save(stored_c, PB, source='custom')
rc = analyze(stored_c)
assert rc.status_code == 200 and rc.json()['versions_analyzed'] == [1]
assert rc.json()['results'][0]['readiness']['status'] == 'needs_attention'
assert analyze(stored).json()['versions_analyzed'] == [1, 2, 3, 4], \
    'A unaffected by C'
assert analyze(stored, '1').json()['results'][0]['readiness'] == \
    hreadiness(stored, 1).json()['readiness'], 'A still exact after C activity'
print('K. multiple videos: OK (A/C isolated, per-video analysis)')

# ==================== L. route collision ====================
assert client.get(f'/api/videos/{stored}/prompt/history/1').status_code == 200
assert hreadiness(stored, 1).status_code == 200
assert readiness(stored, CITY).status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/favorites').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/tag/ai').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/compare/1/2'
                  ).status_code == 200
assert compare(stored, 1, 2).status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/search').status_code == 200
assert quality(stored, FULL).status_code == 200
assert improve(stored, FULL).status_code == 200
assert export(stored, 1, 'json').status_code == 200
assert package(stored, 1).content[:2] == b'PK'
print('L. route collision: OK (numeric/Day24/static/POST routes intact)')

# ==================== M. Day16 regression ====================
lv = save(stored, 'recreated after delete')
assert lv['version'] == 5, 'Day16 numbering unchanged (max live + 1)'
lg = client.get(f'/api/videos/{stored}/prompt/history/3')
assert lg.status_code == 200 and lg.json()['prompt'] == REQ_ONLY
lc = client.get(f'/api/videos/{stored}/prompt/history/compare/1/3')
assert lc.status_code == 200 and 'common_tokens' in lc.json()
assert analyze(stored).json()['versions_analyzed'] == [1, 2, 3, 4, 5]
print('M. Day16 regression: OK (create/list/get/compare/numbering)')


# ==================== N. Day18-20 regression ====================
def search(**params):
    return client.get(f'/api/videos/{stored}/prompt/search', params=params)


assert [r['version'] for r in search(query='cinematic').json()['results']] == \
    [1, 3, 4]
assert [r['version'] for r in search(favorite='true').json()['results']] == [1]
assert [r['version'] for r in search(tag='ai').json()['results']] == [1]
assert [r['version'] for r in search(source='refinement').json()['results']] == [3]
for fmt in ('json', 'markdown', 'txt'):
    e1 = export(stored, 1, fmt)
    e2 = export(stored, 1, fmt)
    assert e1.status_code == e2.status_code == 200
    assert e1.content == e2.content, f'{fmt} export deterministic'
o_files = read_zip(package(stored, 1))
assert o_files['prompt.json'] == export(stored, 1, 'json').text
k1, k2 = package(stored, 1), package(stored, 1)
assert k1.content == k2.content, 'package byte-identical'
print('N. Day18/19/20 regression: OK (search/export/package intact)')

# ==================== O. Day21/22/23/24 regression ====================
assert quality(stored, FULL).json() == quality_before, 'Day21 quality unchanged'
imp = improve(stored, FULL)
assert imp.status_code == 200 and imp.json()['source_prompt'] == FULL
assert hreadiness(stored, 1).json()['readiness'] == \
    readiness(stored, FULL).json()['readiness'], 'Day24 endpoints exact'
d = compare(stored, 1, 2)
assert d.status_code == 200 and d.json()['comparison']['changed'] is True
assert quality(stored, FULL).json() == quality_before, \
    'quality unchanged by readiness/improve/compare/analysis'
old = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2')
assert old.status_code == 200 and 'common_tokens' in old.json()
print('O. Day21/22/23/24 regression: OK (quality/improve/compare/readiness intact)')

# ==================== P. security + leak scan ====================
blobs = [json.dumps(analyze(stored).json()),
         json.dumps(analyze(stored, '1,3').json()),
         json.dumps(analyze(stored_c).json()),
         json.dumps(hreadiness(stored, 1).json()),
         json.dumps(readiness(stored, FULL).json()),
         json.dumps(imp.json()),
         json.dumps(d.json()),
         json.dumps(search().json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/history').json())]
for ver in (1, 2, 3, 4, 5):
    blobs += list(read_zip(package(stored, ver)).values())
for blob in blobs:
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in blob, f'absolute path {bad}'
    for internal in ['_storage', 'PromptReadinessHistoryService',
                     'PromptReadinessService', 'PromptQualityService',
                     'PromptImprovementService', 'PromptHistoryService',
                     'storage/uploads', 'BytesIO', 'Traceback', 'os.environ']:
        assert internal not in blob, f'internal leak {internal}'
    for word in ('best', 'worst', 'winner', 'perfect', 'guaranteed',
                 'superior', 'inferior', 'rank', 'recommended',
                 'objectively good', 'objectively bad'):
        assert word not in blob.lower(), f'ranking language: {word}'
final_rec = get_version(stored, 1)
assert json.dumps(final_rec, sort_keys=True) == original_json, \
    'stored history never modified'
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization'
                  ).json() == org_v1, 'org metadata never modified'
assert export(stored, 1, 'json').content == export_before, \
    'export never modified'
final_list = [x['version'] for x in
              client.get(f'/api/videos/{stored}/prompt/history').json()['versions']]
assert final_list == [1, 2, 3, 4, 5], 'single Day16 store, no second store'
for ver in final_list:
    assert hreadiness(stored, ver).status_code == 200
    assert compare(stored, ver, ver).status_code == 200
    assert package(stored, ver).status_code == 200
    assert vquality(stored, ver).status_code == 200
    assert himprove(stored, ver).status_code == 200
assert analyze(stored, '6').status_code == 404
print('P. security + leak scan: OK (no leaks, no ranking words, single store, '
      'Day16-24 all functional)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 25 MANUAL E2E VERIFICATIONS PASSED')
