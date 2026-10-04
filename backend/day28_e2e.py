import io, json, os, re, subprocess, tempfile, zipfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import DIMENSIONS

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day28_e2e.mp4')

# use the app's own service instances (same single stores as the API)
from app.api import videos as videos_api
from app.services.prompt_readiness_snapshot_service import (
    PromptReadinessSnapshotService,
)
history_svc = videos_api.prompt_history_service
readiness_svc = videos_api.readiness_service
org_svc = videos_api.organization_service
snap_svc = videos_api.readiness_snapshot_service
assert isinstance(snap_svc, PromptReadinessSnapshotService)
assert snap_svc.history_service is history_svc, \
    'reuses Day16 history service (no second store)'
assert snap_svc.readiness_service is readiness_svc, \
    'reuses Day24 readiness service (no duplicate engine)'
assert snap_svc.organization_service is org_svc, \
    'reuses Day17 organization service (no duplicate org reader)'

subprocess.run(
    [ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-y', tmp],
    capture_output=True, timeout=15,
)

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

FULL = ('Cinematic film grain style portrait of a person, the subject '
        'walking, looking around and gesturing in an outdoor forest '
        'street, camera tracking with shallow depth of field, soft '
        'lighting with rim light and golden hour glow, vibrant teal and '
        'orange palette with warm tones, layered foreground and rule of '
        'thirds composition, ambient sound with quiet music score.')
WEAK_CAM = ('Cinematic film grain style portrait of a person, the subject '
            'walking, looking around and gesturing in an outdoor forest '
            'street, tracking only, soft lighting with rim light and '
            'golden hour glow, vibrant teal and orange palette with warm '
            'tones, layered foreground and rule of thirds composition, '
            'ambient sound with quiet music score.')
W_CAMLESS = ('Cinematic film grain style portrait of a person, the subject '
             'walking, looking around and gesturing in an outdoor forest '
             'street, soft lighting with rim light and golden hour glow, '
             'vibrant teal and orange palette with warm tones, layered '
             'foreground and rule of thirds composition, ambient sound '
             'with quiet music score.')
CITY = 'A person walks through a city street.'
CITY_ENV100 = ('A person walks through a quiet city street near the '
               'forest park.')
MINIMAL = 'nothing specific at all'
REQ_ONLY = ('Cinematic film grain style portrait of a person, the subject '
            'walking, looking around and gesturing in an outdoor forest '
            'street, camera tracking with shallow depth of field, soft '
            'lighting with rim light and golden hour glow, layered '
            'foreground and rule of thirds composition.')
SUBJ70 = ('Cinematic film grain style portrait of a person, '
          'walking through an outdoor forest street, camera tracking '
          'with shallow depth of field, soft lighting with rim light '
          'and golden hour glow, vibrant teal and orange palette with '
          'warm tones, layered foreground and rule of thirds '
          'composition, ambient sound with quiet music score.')

SNAP_TOP = {'video_filename', 'versions_analyzed', 'snapshots', 'summary'}
SUMMARY_KEYS = {
    'versions_analyzed', 'ready_count', 'needs_attention_count',
    'required', 'supporting', 'dimension_summary', 'organization',
}
SNAPSHOT_KEYS = {
    'version', 'source', 'operation', 'created_at', 'favorite', 'tags',
    'readiness',
}
READINESS_KEYS = {
    'status', 'required_coverage_percentage', 'required', 'supporting',
    'missing_dimensions', 'weak_dimensions',
}
REQUIRED_KEYS = ['subject', 'action', 'environment', 'camera', 'lighting',
                 'visual_style', 'composition']
SUPPORTING_KEYS = ['color', 'audio']
DAY26_TOP = {
    'video_filename', 'version_a', 'version_b', 'dimensions',
    'changed_dimensions', 'dimensions_changed', 'dimensions_unchanged',
    'required_changes', 'supporting_changes', 'transitions',
    'transition_summary', 'required_coverage',
}
DAY25_TOP = {
    'video_filename', 'versions_analyzed', 'results', 'summary',
    'dimension_summary',
}
DAY27_TOP = {
    'video_filename', 'versions_analyzed', 'steps', 'timeline', 'summary',
}


def save(video, prompt, negative=NEG1, source='custom', operation=''):
    body = {'prompt': prompt, 'negative_prompt': negative,
            'source': source, 'operation': operation}
    resp = client.post(f'/api/videos/{video}/prompt/history', json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def snapshot(video, versions=None):
    params = None if versions is None else {'versions': versions}
    return client.get(f'/api/videos/{video}/prompt/history/readiness/'
                      f'snapshot', params=params)


def timeline(video, versions=None):
    params = None if versions is None else {'versions': versions}
    return client.get(f'/api/videos/{video}/prompt/history/readiness/'
                      f'timeline', params=params)


def change(video, va, vb):
    return client.get(f'/api/videos/{video}/prompt/history/compare/'
                      f'{va}/{vb}/readiness')


def readiness(video, prompt):
    return client.post(f'/api/videos/{video}/prompt/readiness',
                       json={'prompt': prompt})


def hreadiness(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}/readiness')


def org(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}'
                      f'/organization')


def analyze(video, versions=None):
    params = None if versions is None else {'versions': versions}
    return client.get(f'/api/videos/{video}/prompt/history/readiness',
                      params=params)


def quality(video, prompt):
    return client.post(f'/api/videos/{video}/prompt/quality',
                       json={'prompt': prompt})


def improve(video, prompt):
    return client.post(f'/api/videos/{video}/prompt/improve',
                       json={'prompt': prompt})


def export(video, version, fmt):
    return client.get(f'/api/videos/{video}/prompt/history/{version}/export',
                      params={'format': fmt})


def package(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}/package')


def read_zip(response):
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return {name: zf.read(name).decode('utf-8') for name in zf.namelist()}


def get_version(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}').json()


# --- Day 16/17 history (video A): the probe-verified 8-version standard set ---
v1 = save(stored, FULL, source='advanced_prompt', operation='generate')
v2 = save(stored, WEAK_CAM, source='custom', operation='')
v3 = save(stored, W_CAMLESS, source='template', operation='cinematic')
v4 = save(stored, CITY, source='refinement', operation='expand')
v5 = save(stored, CITY_ENV100, source='custom', operation='tweak')
v6 = save(stored, MINIMAL, source='template', operation='shorten')
v7 = save(stored, REQ_ONLY, source='refinement', operation='expand')
v8 = save(stored, SUBJ70, source='custom', operation='draft')
assert [x['version'] for x in (v1, v2, v3, v4, v5, v6, v7, v8)] == \
    list(range(1, 9))

assert client.post(f'/api/videos/{stored}/prompt/history/1/favorite'
                   ).status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/history/1/tags',
                   json={'tags': [' Cinematic ', 'ai']}).json()['tags'] == \
    ['ai', 'cinematic']
assert client.post(f'/api/videos/{stored}/prompt/history/4/tags',
                   json={'tags': ['final']}).json()['tags'] == ['final']
assert client.post(f'/api/videos/{stored}/prompt/history/7/favorite'
                   ).status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/history/7/tags',
                   json={'tags': ['cinematic', 'draft']}).json()['tags'] == \
    ['cinematic', 'draft']
org_state = {v: org(stored, v).json() for v in range(1, 9)}
print('Day 16/17 setup: OK (8 versions, 2 favorites, tags)')

original_record = get_version(stored, 1)
original_json = json.dumps(original_record, sort_keys=True)
listing_before = [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']]
quality_before = quality(stored, FULL).json()
export_before = export(stored, 1, 'json').content
default_text_before = snapshot(stored).text
assert listing_before == [1, 2, 3, 4, 5, 6, 7, 8]

# ==================== A. response schema ====================
resp = snapshot(stored)
assert resp.status_code == 200, resp.status_code
a = resp.json()
assert set(a.keys()) == SNAP_TOP, list(a.keys())
assert a['video_filename'] == stored
assert a['versions_analyzed'] == [1, 2, 3, 4, 5, 6, 7, 8]
assert len(a['snapshots']) == 8
assert set(a['summary'].keys()) == SUMMARY_KEYS, list(a['summary'].keys())
for s in a['snapshots']:
    assert set(s.keys()) == SNAPSHOT_KEYS, list(s.keys())
    assert [s['version'] for s in a['snapshots']] == [1, 2, 3, 4, 5, 6, 7, 8]
    block = s['readiness']
    assert set(block.keys()) == READINESS_KEYS, list(block.keys())
    assert list(block['required'].keys()) == REQUIRED_KEYS, 'Day21 order'
    assert list(block['supporting'].keys()) == SUPPORTING_KEYS, 'Day21 order'
assert [row['dimension'] for row in a['summary']['dimension_summary']] == \
    list(DIMENSIONS), 'Day21 dimension order'
print('A. response schema: OK (200, 4 top keys, 7 summary keys, 7 snapshot '
      'keys, 6 readiness keys, Day21 orders)')

# ==================== B. per-version equality vs Day24/Day17 ====================
for s in a['snapshots']:
    ver = s['version']
    d24 = hreadiness(stored, ver).json()['readiness']
    block = s['readiness']
    assert block['status'] == d24['status'], ver
    assert block['required_coverage_percentage'] == \
        d24['coverage']['required_coverage_percentage'], ver
    assert block['missing_dimensions'] == d24['missing_dimensions'], ver
    assert block['weak_dimensions'] == d24['weak_dimensions'], ver
    checks = {i['dimension']: i for i in d24['checklist']}
    for dim in REQUIRED_KEYS + SUPPORTING_KEYS:
        bucket = block['required'] if dim in REQUIRED_KEYS else block['supporting']
        assert bucket[dim] == {'status': checks[dim]['status'],
                               'score': checks[dim]['score']}, (ver, dim)
    d17 = org(stored, ver).json()
    assert s['favorite'] == d17['favorite'], ver
    assert s['tags'] == d17['tags'], ver
    assert s['created_at'] == get_version(stored, ver)['created_at'], ver
    assert s['source'] == get_version(stored, ver)['source'], ver
    assert s['operation'] == get_version(stored, ver)['operation'], ver
print('B. per-version: OK (8 blocks byte-equal to Day24, favorite/tags equal '
      'Day17, metadata equal Day16)')

# ==================== C. aggregates + dimension summary ====================
summary = a['summary']
assert summary['versions_analyzed'] == 8
assert summary['ready_count'] == 2
assert summary['needs_attention_count'] == 6
assert summary['required'] == {'total': 56, 'present': 34, 'weak': 4,
                               'missing': 18, 'coverage_percentage': 61}
assert summary['supporting'] == {'total': 16, 'present': 8, 'weak': 0,
                                 'missing': 8}
assert summary['dimension_summary'] == [
    {'dimension': 'subject', 'present': 5, 'weak': 2, 'missing': 1},
    {'dimension': 'action', 'present': 4, 'weak': 1, 'missing': 3},
    {'dimension': 'environment', 'present': 7, 'weak': 0, 'missing': 1},
    {'dimension': 'camera', 'present': 3, 'weak': 1, 'missing': 4},
    {'dimension': 'lighting', 'present': 5, 'weak': 0, 'missing': 3},
    {'dimension': 'visual_style', 'present': 5, 'weak': 0, 'missing': 3},
    {'dimension': 'color', 'present': 4, 'weak': 0, 'missing': 4},
    {'dimension': 'composition', 'present': 5, 'weak': 0, 'missing': 3},
    {'dimension': 'audio', 'present': 4, 'weak': 0, 'missing': 4},
]
assert summary['organization'] == {
    'favorite_count': 2,
    'tag_counts': {'ai': 1, 'cinematic': 2, 'draft': 1, 'final': 1}}
assert summary['ready_count'] + summary['needs_attention_count'] == 8
assert sum(summary['required'][k] for k in ('present', 'weak', 'missing')) == 56
assert sum(summary['supporting'][k] for k in ('present', 'weak', 'missing')) == 16
for row in summary['dimension_summary']:
    assert row['present'] + row['weak'] + row['missing'] == 8, row
per_ver = {s['version']: s for s in a['snapshots']}
assert (per_ver[1]['readiness']['status'],
        per_ver[1]['readiness']['required_coverage_percentage']) == ('ready', 100)
assert per_ver[2]['readiness']['weak_dimensions'] == ['camera']
assert per_ver[3]['readiness']['missing_dimensions'] == ['camera']
assert (per_ver[4]['readiness']['status'],
        per_ver[4]['readiness']['required_coverage_percentage']) == \
    ('needs_attention', 14)
assert per_ver[4]['readiness']['weak_dimensions'] == ['subject']
assert per_ver[5]['readiness']['required_coverage_percentage'] == 14
assert per_ver[6]['readiness']['required_coverage_percentage'] == 0
assert per_ver[6]['readiness']['missing_dimensions'] == list(DIMENSIONS)
assert (per_ver[7]['readiness']['status'],
        per_ver[7]['readiness']['missing_dimensions']) == \
    ('ready', ['color', 'audio'])
assert per_ver[8]['readiness']['weak_dimensions'] == ['action']
print('C. aggregates: OK (required 56/34/4/18/61, supporting 16/8/0/8, '
      '9 dimension rows, org 2 fav / 4 tags, statuses spot-checked)')

# ==================== D. selection ====================
sub = snapshot(stored, '1,3,5').json()
assert sub['versions_analyzed'] == [1, 3, 5]
assert [s['version'] for s in sub['snapshots']] == [1, 3, 5]
assert sub['summary']['versions_analyzed'] == 3
assert sub['summary']['required'] == {'total': 21, 'present': 14, 'weak': 1,
                                      'missing': 6, 'coverage_percentage': 67}
assert sub['summary']['organization'] == {
    'favorite_count': 1, 'tag_counts': {'ai': 1, 'cinematic': 1}}
rev = snapshot(stored, '3,1').json()
assert rev['versions_analyzed'] == [3, 1], 'requested order preserved'
assert [s['version'] for s in rev['snapshots']] == [3, 1]
assert rev['summary']['required'] == {'total': 14, 'present': 13, 'weak': 0,
                                      'missing': 1, 'coverage_percentage': 93}
assert rev['summary']['organization'] == {
    'favorite_count': 1, 'tag_counts': {'ai': 1, 'cinematic': 1}}
assert len(rev['summary']['dimension_summary']) == 9
single = snapshot(stored, '6').json()
assert single['versions_analyzed'] == [6]
assert len(single['snapshots']) == 1
assert single['summary']['versions_analyzed'] == 1
assert single['summary']['ready_count'] == 0
assert single['summary']['needs_attention_count'] == 1
assert single['summary']['required'] == {'total': 7, 'present': 0, 'weak': 0,
                                         'missing': 7,
                                         'coverage_percentage': 0}
assert single['summary']['supporting'] == {'total': 2, 'present': 0,
                                           'weak': 0, 'missing': 2}
assert single['summary']['organization'] == {
    'favorite_count': 0, 'tag_counts': {}}
rep = client.get(f'/api/videos/{stored}/prompt/history/readiness/snapshot',
                 params=[('versions', '1'), ('versions', '3')])
assert rep.status_code == 200 and rep.json()['versions_analyzed'] == [1, 3]
ws = snapshot(stored, '1 , 3').json()
assert ws['versions_analyzed'] == [1, 3], 'whitespace tolerated'
print('D. selection: OK (subset 21/14/1/6/67, reverse order 3,1 with '
      '14/13/0/1/93, single v6 all-missing, repeated + whitespace)')

# ==================== E. empty + isolated single-version video ====================
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
save(stored_b, PB, source='custom')
sb = snapshot(stored_b).json()
assert set(sb.keys()) == SNAP_TOP
assert sb['versions_analyzed'] == [1]
assert len(sb['snapshots']) == 1
assert sb['snapshots'][0]['favorite'] is False
assert sb['snapshots'][0]['tags'] == []
d24_b = hreadiness(stored_b, 1).json()['readiness']
assert sb['snapshots'][0]['readiness']['status'] == d24_b['status']
assert sb['summary']['versions_analyzed'] == 1
assert sb['summary']['required']['total'] == 7
with open(tmp, 'rb') as f:
    up_c = client.post('/api/videos/upload', files={'file': ('test3.mp4', f, 'video/mp4')})
stored_c = up_c.json()['video']['stored_filename']
ec = snapshot(stored_c)
assert ec.status_code == 200
empty = ec.json()
assert set(empty.keys()) == SNAP_TOP
assert empty['versions_analyzed'] == []
assert empty['snapshots'] == []
esum = empty['summary']
assert set(esum.keys()) == SUMMARY_KEYS
assert esum['versions_analyzed'] == 0
assert esum['ready_count'] == 0 and esum['needs_attention_count'] == 0
assert esum['required'] == {'total': 0, 'present': 0, 'weak': 0,
                            'missing': 0, 'coverage_percentage': None}
assert esum['supporting'] == {'total': 0, 'present': 0, 'weak': 0,
                              'missing': 0}
assert esum['dimension_summary'] == []
assert esum['organization'] == {'favorite_count': 0, 'tag_counts': {}}
assert snapshot(stored_c, '1').status_code == 404
print('E. empty + single: OK (0 versions -> 200 all-zero/null, 1 version -> '
      'totals 7/2)')

# ==================== F. validation ====================
for q in ('', '0', '-1', 'abc', '1,,2', '1,1', '1.5', ',', '1 2', '+2',
          '2,2', '0,1', '1;2', ' ', '1,1.5', '3,1,3'):
    assert snapshot(stored, q).status_code == 422, q
assert snapshot(stored, '1,99').status_code == 404
assert snapshot('missing.mp4').status_code == 404
assert snapshot('clip.txt').status_code == 400
trav = client.get('/api/videos/../../../etc/passwd/prompt/history/'
                  'readiness/snapshot')
assert trav.status_code == 404, trav.status_code
detail = snapshot(stored, '1,99').json()['detail']
assert isinstance(detail, str) and '99' in detail and stored in detail
tmp_v = save(stored, 'temporary for delete check')
assert tmp_v['version'] == 9
assert snapshot(stored, '8,9').status_code == 200, 'live version works'
assert snapshot(stored, '9').status_code == 200, 'single live version'
assert client.delete(f'/api/videos/{stored}/prompt/history/9').status_code == 200
assert snapshot(stored, '1,9').status_code == 404, 'deleted version 404'
assert snapshot(stored, '9').status_code == 404, 'deleted single 404'
skipped = snapshot(stored).json()
assert skipped['versions_analyzed'] == [1, 2, 3, 4, 5, 6, 7, 8], \
    'default selection skips deleted version'
assert skipped['summary']['versions_analyzed'] == 8
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == listing_before
print('F. validation: OK (422/404/400/traversal, deleted 404, default '
      'skips gap, listing intact)')

# ==================== G. determinism ====================
d1 = snapshot(stored).json()
d2 = snapshot(stored).json()
assert d1 == d2, 'identical repeated results'
assert snapshot(stored, '1,4').text == snapshot(stored, '1,4').text
text = snapshot(stored, '2,5').text
assert 'uuid' not in text.lower()
assert not re.search(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    text.replace(stored, '')), 'no generated ids beyond the video filename'
for s in d1['snapshots']:
    assert s['created_at'] == get_version(stored, s['version'])['created_at'], \
        'only stored Day16 timestamps, never generated'
print('G. determinism: OK (repeat identical, byte-equivalent, only stored '
      'created_at values)')

# ==================== H. read-only integrity ====================
snapshot(stored)
snapshot(stored, '1,5')
snapshot(stored, '8,2')
snapshot(stored, '99')
assert json.dumps(get_version(stored, 1), sort_keys=True) == original_json, \
    'history record unchanged after snapshots'
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == \
    listing_before, 'snapshots never created/deleted a version'
for v in range(1, 9):
    assert org(stored, v).json() == org_state[v], \
        f'org v{v} unchanged after snapshots'
assert export(stored, 1, 'json').content == export_before, \
    'export unchanged after snapshots'
assert quality(stored, FULL).json() == quality_before, \
    'Day21 quality unchanged after snapshots'
assert get_version(stored, 4)['prompt'] == CITY, 'prompt text untouched'
print('H. read-only: OK (record/listing/org/export/quality untouched)')

# ==================== I. multiple videos ====================
assert snapshot(stored_b).json()['video_filename'] == stored_b
assert snapshot(stored_b, '1,2').status_code == 404, 'B has one version'
assert snapshot(stored).text == default_text_before, \
    'A snapshot byte-identical after B activity'
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == \
    listing_before, 'A unaffected by B'
print('I. multiple videos: OK (A/B isolated, A byte-identical after B)')

# ==================== J. route collision + Day16-27 regression ====================
old = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2')
assert old.status_code == 200 and 'common_tokens' in old.json()
detailed = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2/detailed')
assert detailed.status_code == 200 and 'comparison' in detailed.json()
new = snapshot(stored, '1,2')
d26 = change(stored, 1, 2)
d25 = analyze(stored)
d27 = timeline(stored)
d24p = readiness(stored, CITY)
d24v = hreadiness(stored, 1)
assert old.status_code == detailed.status_code == new.status_code == 200
assert set(old.json().keys()) != set(new.json().keys())
assert set(detailed.json().keys()) != set(new.json().keys())
assert set(new.json().keys()) == SNAP_TOP
assert set(d26.json().keys()) == DAY26_TOP
assert set(d25.json().keys()) == DAY25_TOP
assert set(d27.json().keys()) == DAY27_TOP
assert set(d24v.json().keys()) == {'video_filename', 'prompt', 'readiness'}
for other in (d25, d26, d27, d24v):
    assert set(other.json().keys()) != set(new.json().keys())
numeric = client.get(f'/api/videos/{stored}/prompt/history/1')
assert numeric.status_code == 200 and 'prompt' in numeric.json()
assert 'prompt' not in snapshot(stored).json(), \
    'static snapshot route not captured by numeric route'
assert client.get(f'/api/videos/{stored}/prompt/history/readiness'
                  ).status_code == 200, 'Day25 route still resolves'
assert client.get(f'/api/videos/{stored}/prompt/history/readiness/timeline'
                  ).status_code == 200, 'Day27 route still resolves'
assert d24p.status_code == 200 and d24v.status_code == 200
assert analyze(stored).json()['versions_analyzed'] == [1, 2, 3, 4, 5, 6, 7, 8]
assert analyze(stored, '7,2').json()['versions_analyzed'] == [7, 2]
assert timeline(stored).json()['steps'] == 7, 'Day27 unchanged'
assert timeline(stored, '2,1').json()['versions_analyzed'] == [2, 1]
assert client.get(f'/api/videos/{stored}/prompt/search').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/favorites').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/tag/ai').status_code == 200
for fmt in ('json', 'markdown', 'txt'):
    e1 = export(stored, 1, fmt)
    e2 = export(stored, 1, fmt)
    assert e1.status_code == e2.status_code == 200 and e1.content == e2.content, fmt
o_files = read_zip(package(stored, 1))
assert o_files['prompt.json'] == export(stored, 1, 'json').text
k1, k2 = package(stored, 1), package(stored, 1)
assert k1.content == k2.content, 'package byte-identical'
assert quality(stored, FULL).json() == quality_before, 'Day21 quality unchanged'
imp = improve(stored, FULL)
assert imp.status_code == 200 and imp.json()['source_prompt'] == FULL
lv = save(stored, 'recreated after delete check')
assert lv['version'] == 9, 'Day16 numbering unchanged (max live + 1)'
assert snapshot(stored, '8,9').status_code == 200
final_default = snapshot(stored).json()
assert final_default['versions_analyzed'] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
assert final_default['summary']['versions_analyzed'] == 9
assert len(final_default['snapshots']) == 9
print('J. route collision + Day16-27 regression: OK (old compares, Day24/25/'
      '26/27, search/export/package/quality/improve intact, numbering)')

# ==================== K. security + leak scan ====================
blobs = [snapshot(stored).text, snapshot(stored, '1,5').text,
         snapshot(stored, '8,2').text, snapshot(stored, '2,1').text,
         snapshot(stored, '9,8').text, snapshot(stored_b).text,
         snapshot(stored_c).text, json.dumps(empty),
         json.dumps(d26.json()), json.dumps(d25.json()),
         json.dumps(d27.json()), json.dumps(detailed.json()),
         json.dumps(imp.json()),
         json.dumps(readiness(stored, FULL).json()),
         json.dumps(hreadiness(stored, 1).json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/search').json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/history').json())]
for ver in range(1, 10):
    blobs += list(read_zip(package(stored, ver)).values())
for blob in blobs:
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in blob, f'absolute path {bad}'
    for internal in ['_storage', 'PromptReadinessSnapshotService',
                     'PromptReadinessTimelineService',
                     'PromptReadinessChangeService',
                     'PromptReadinessHistoryService', 'PromptReadinessService',
                     'PromptQualityService', 'PromptImprovementService',
                     'PromptOrganizationService', 'PromptHistoryService',
                     'readiness_snapshot_service', 'readiness_timeline_service',
                     'readiness_change_service', 'history_service',
                     'organization_service', 'storage/uploads', 'BytesIO',
                     'Traceback', 'os.environ']:
        assert internal not in blob, f'internal leak {internal}'
for data in (a, sub, rev, single, sb, empty, final_default, d27.json()):
    low = json.dumps(data).lower()
    for word in ('best', 'worst', 'winner', 'perfect', 'guaranteed',
                 'superior', 'inferior', 'rank', 'recommended', 'better',
                 'worse', 'improved', 'improvement', 'gain'):
        assert word not in low, f'ranking language: {word}'
assert 'film grain style portrait' not in snapshot(stored).text, \
    'prompt text never echoed'
assert FULL not in snapshot(stored).text and NEG1 not in snapshot(stored).text
final_rec = get_version(stored, 1)
assert json.dumps(final_rec, sort_keys=True) == original_json, \
    'stored history never modified'
for v in range(1, 9):
    assert org(stored, v).json() == org_state[v], 'org metadata never modified'
assert export(stored, 1, 'json').content == export_before, \
    'export never modified'
assert quality(stored, FULL).json() == quality_before, 'quality never modified'
final_list = [x['version'] for x in
              client.get(f'/api/videos/{stored}/prompt/history').json()['versions']]
assert final_list == [1, 2, 3, 4, 5, 6, 7, 8, 9], \
    'single Day16 store, no second store'
for ver in final_list:
    assert hreadiness(stored, ver).status_code == 200
    assert client.get(f'/api/videos/{stored}/prompt/history/compare/'
                      f'{ver}/{ver}').status_code == 200
    assert change(stored, ver, ver).status_code == 200
    assert package(stored, ver).status_code == 200
    assert snapshot(stored, f'{ver}').status_code == 200
assert snapshot(stored, '1,99').status_code == 404
assert snapshot(stored).text == snapshot(stored).text, 'final determinism'
print('K. security + leak scan: OK (no leaks, no ranking words, single '
      'store, Day16-27 all functional)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 28 MANUAL E2E VERIFICATIONS PASSED')
