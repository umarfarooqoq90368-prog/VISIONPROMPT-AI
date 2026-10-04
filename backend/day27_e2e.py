import io, json, os, re, subprocess, tempfile, zipfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import DIMENSIONS
from app.services.prompt_readiness_change_service import (
    PromptReadinessChangeService,
    TRANSITION_KEYS,
)
from app.services.prompt_readiness_timeline_service import (
    PromptReadinessTimelineService,
)

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day27_e2e.mp4')

# use the app's own service instances (same single stores as the API)
from app.api import videos as videos_api
history_svc = videos_api.prompt_history_service
readiness_svc = videos_api.readiness_service
change_svc = videos_api.readiness_change_service
timeline_svc = videos_api.readiness_timeline_service
assert isinstance(change_svc, PromptReadinessChangeService)
assert isinstance(timeline_svc, PromptReadinessTimelineService)
assert timeline_svc.history_service is history_svc, \
    'reuses Day16 history service (no second store)'
assert timeline_svc.readiness_change_service is change_svc, \
    'reuses Day26 change service (no duplicate diff engine)'

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

TL_TOP = {
    'video_filename', 'versions_analyzed', 'steps', 'timeline', 'summary',
}
SUMMARY_KEYS = {
    'versions_analyzed', 'steps', 'dimensions_changed_total',
    'dimensions_unchanged_total', 'required_changes_total',
    'supporting_changes_total', 'transition_summary', 'first_version',
    'last_version', 'first_required_coverage_percentage',
    'last_required_coverage_percentage', 'required_coverage_delta',
}
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


def save(video, prompt, negative=NEG1, source='custom', operation=''):
    body = {'prompt': prompt, 'negative_prompt': negative,
            'source': source, 'operation': operation}
    resp = client.post(f'/api/videos/{video}/prompt/history', json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


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


def analyze(video, versions=None):
    params = None if versions is None else {'versions': versions}
    return client.get(f'/api/videos/{video}/prompt/history/readiness',
                      params=params)


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


def pairs_of(data):
    return [(s['version_a']['version'], s['version_b']['version'])
            for s in data['timeline']]


# --- Day 16 history (video A): the probe-verified 8-version standard set ---
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
org_v1 = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
print('Day 16/17 setup: OK (8 versions, favorite, tags)')

original_record = get_version(stored, 1)
original_json = json.dumps(original_record, sort_keys=True)
listing_before = [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']]
quality_before = quality(stored, FULL).json()
export_before = export(stored, 1, 'json').content
default_text_before = timeline(stored).text
assert listing_before == [1, 2, 3, 4, 5, 6, 7, 8]

# ==================== A. response schema ====================
resp = timeline(stored)
assert resp.status_code == 200, resp.status_code
a = resp.json()
assert set(a.keys()) == TL_TOP, list(a.keys())
assert a['video_filename'] == stored
assert a['versions_analyzed'] == [1, 2, 3, 4, 5, 6, 7, 8]
assert a['steps'] == 7 == len(a['timeline'])
assert set(a['summary'].keys()) == SUMMARY_KEYS, list(a['summary'].keys())
assert set(a['summary']['transition_summary'].keys()) == set(TRANSITION_KEYS)
for step in a['timeline']:
    assert set(step.keys()) == DAY26_TOP, list(step.keys())
    assert [d['dimension'] for d in step['dimensions']] == list(DIMENSIONS), \
        'Day21 order'
    assert len(step['dimensions']) == 9
    assert set(step['transition_summary'].keys()) == set(TRANSITION_KEYS)
assert type(a['summary']['required_coverage_delta']) is int
print('A. response schema: OK (200, 5 top keys, 12 summary keys, '
      'Day26 step keys, Day21 order)')

# ==================== B. full 7-step chain vs direct Day 26 ====================
assert pairs_of(a) == [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8)]
for step in a['timeline']:
    direct = change(stored, step['version_a']['version'],
                    step['version_b']['version'])
    assert direct.status_code == 200
    assert step == direct.json(), 'byte-equal to direct Day26 endpoint'
summary = a['summary']
assert summary['dimensions_changed_total'] == 21
assert summary['dimensions_unchanged_total'] == 42
assert summary['required_changes_total'] == 17
assert summary['supporting_changes_total'] == 4
assert summary['transition_summary'] == {
    'missing_to_weak': 0, 'missing_to_present': 9, 'weak_to_missing': 2,
    'weak_to_present': 0, 'present_to_missing': 7, 'present_to_weak': 3}
assert summary['first_version'] == 1 and summary['last_version'] == 8
assert summary['first_required_coverage_percentage'] == 100
assert summary['last_required_coverage_percentage'] == 86
assert summary['required_coverage_delta'] == -14
s1 = a['timeline'][0]
assert s1['changed_dimensions'] == ['camera']
assert s1['transition_summary']['present_to_weak'] == 1
assert s1['required_coverage'] == {'version_a': 100, 'version_b': 86,
                                   'delta': -14}
s4 = a['timeline'][3]
assert (s4['version_a']['version'], s4['version_b']['version']) == (4, 5)
assert s4['changed_dimensions'] == []
assert s4['dimensions_changed'] == 0
env = next(d for d in s4['dimensions'] if d['dimension'] == 'environment')
assert env['version_a'] == {'status': 'present', 'score': 70}
assert env['version_b'] == {'status': 'present', 'score': 100}
assert env['changed'] is False, 'score-only 70 -> 100 not a state change'
s6 = a['timeline'][5]
assert s6['transition_summary']['missing_to_present'] == 7
assert s6['required_coverage'] == {'version_a': 0, 'version_b': 100,
                                   'delta': 100}
s7 = a['timeline'][6]
assert s7['changed_dimensions'] == ['action', 'color', 'audio']
assert s7['required_changes'] == ['action']
assert s7['supporting_changes'] == ['color', 'audio']
for previous, following in zip(a['timeline'], a['timeline'][1:]):
    assert previous['version_b']['version'] == following['version_a']['version'], \
        'steps chain'
print('B. full chain: OK (7 steps byte-equal to Day26, totals 21/42/17/4, '
      'delta -14, chaining)')

# ==================== C. selection ====================
sub = timeline(stored, '1,3,5').json()
assert sub['versions_analyzed'] == [1, 3, 5]
assert sub['steps'] == 2
assert pairs_of(sub) == [(1, 3), (3, 5)]
assert sub['summary']['dimensions_changed_total'] == 8
assert sub['summary']['required_changes_total'] == 6
assert sub['summary']['supporting_changes_total'] == 2
assert sub['summary']['transition_summary']['present_to_missing'] == 7
assert sub['summary']['transition_summary']['present_to_weak'] == 1
assert sub['summary']['required_coverage_delta'] == -86
single = timeline(stored, '5').json()
assert single['versions_analyzed'] == [5]
assert single['steps'] == 0 and single['timeline'] == []
same5 = change(stored, 5, 5).json()
assert single['summary']['first_required_coverage_percentage'] == \
    same5['version_a']['required_coverage_percentage'] == 14
assert single['summary']['last_required_coverage_percentage'] == 14
assert single['summary']['required_coverage_delta'] == 0
order = timeline(stored, '4,2').json()
assert order['versions_analyzed'] == [4, 2], 'requested order preserved'
assert pairs_of(order) == [(4, 2)]
assert order['summary']['required_coverage_delta'] == 72
rep = client.get(f'/api/videos/{stored}/prompt/history/readiness/timeline',
                 params=[('versions', '1'), ('versions', '3')])
assert rep.status_code == 200 and rep.json()['versions_analyzed'] == [1, 3]
ws = timeline(stored, '1 , 3').json()
assert ws['versions_analyzed'] == [1, 3], 'whitespace tolerated'
print('C. selection: OK (subset 2 steps/delta -86, single via same-version '
      'Day26, order 4,2/delta +72, repeated + whitespace)')

# ==================== D. all six transition kinds ====================
seen = set()
for data in a['timeline'] + timeline(stored, '3,2').json()['timeline'] + \
        timeline(stored, '2,1').json()['timeline']:
    seen.update(k for k, v in data['transition_summary'].items() if v)
assert seen == set(TRANSITION_KEYS), seen
m2w = timeline(stored, '3,2').json()
assert m2w['timeline'][0]['transition_summary']['missing_to_weak'] == 1
w2p = timeline(stored, '2,1').json()
assert w2p['timeline'][0]['transition_summary']['weak_to_present'] == 1
assert w2p['summary']['required_coverage_delta'] == 14
print('D. transitions: OK (all 6 kinds observed across the timeline)')

# ==================== E. empty + single-version video ====================
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
save(stored_b, PB, source='custom')
tb = timeline(stored_b).json()
assert set(tb.keys()) == TL_TOP
assert tb['versions_analyzed'] == [1]
assert tb['steps'] == 0 and tb['timeline'] == []
same_b = change(stored_b, 1, 1).json()
assert tb['summary']['first_required_coverage_percentage'] == \
    same_b['version_a']['required_coverage_percentage']
assert tb['summary']['required_coverage_delta'] == 0
with open(tmp, 'rb') as f:
    up_c = client.post('/api/videos/upload', files={'file': ('test3.mp4', f, 'video/mp4')})
stored_c = up_c.json()['video']['stored_filename']
tc = timeline(stored_c)
assert tc.status_code == 200
empty = tc.json()
assert set(empty.keys()) == TL_TOP
assert empty['versions_analyzed'] == [] and empty['steps'] == 0
assert empty['timeline'] == []
assert empty['summary']['versions_analyzed'] == 0
assert empty['summary']['first_version'] is None
assert empty['summary']['last_version'] is None
assert empty['summary']['first_required_coverage_percentage'] is None
assert empty['summary']['last_required_coverage_percentage'] is None
assert empty['summary']['required_coverage_delta'] == 0
assert set(empty['summary']['transition_summary'].values()) == {0}
assert timeline(stored_c, '1').status_code == 404
print('E. empty + single: OK (0 versions -> 200 empty/nulls, 1 version -> '
      '0 steps via same-version Day26)')

# ==================== F. validation ====================
for q in ('', '0', '-1', 'abc', '1,,2', '1,1', '1.5', ',', '1 2', '+2',
          '2,2', '0,1'):
    assert timeline(stored, q).status_code == 422, q
assert timeline(stored, '1,99').status_code == 404
assert timeline('missing.mp4').status_code == 404
assert timeline('clip.txt').status_code == 400
trav = client.get('/api/videos/../../../etc/passwd/prompt/history/'
                  'readiness/timeline')
assert trav.status_code == 404, trav.status_code
detail = timeline(stored, '1,99').json()['detail']
assert isinstance(detail, str) and '99' in detail and stored in detail
tmp_v = save(stored, 'temporary for delete check')
assert tmp_v['version'] == 9
assert timeline(stored, '8,9').status_code == 200, 'live version works'
assert timeline(stored, '9').status_code == 200, 'single live version'
assert client.delete(f'/api/videos/{stored}/prompt/history/9').status_code == 200
assert timeline(stored, '1,9').status_code == 404, 'deleted version 404'
assert timeline(stored, '9').status_code == 404, 'deleted single 404'
skipped = timeline(stored).json()
assert skipped['versions_analyzed'] == [1, 2, 3, 4, 5, 6, 7, 8], \
    'default selection skips deleted version'
assert skipped['steps'] == 7
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == listing_before
print('F. validation: OK (422/404/400/traversal, deleted 404, default '
      'skips gap, listing intact)')

# ==================== G. determinism ====================
d1 = timeline(stored).json()
d2 = timeline(stored).json()
assert d1 == d2, 'identical repeated results'
assert timeline(stored, '1,4').text == timeline(stored, '1,4').text
text = timeline(stored, '2,5').text
for pat in (r'\d{4}-\d{2}-\d{2}', r'\d{2}:\d{2}'):
    assert not re.search(pat, text), pat
for token in ('uuid', 'timestamp', 'created_at'):
    assert token not in text.lower(), token
print('G. determinism: OK (repeat identical, byte-equivalent, no '
      'timestamps/uuids)')

# ==================== H. read-only integrity ====================
timeline(stored)
timeline(stored, '1,5')
timeline(stored, '8,2')
timeline(stored, '99')
assert json.dumps(get_version(stored, 1), sort_keys=True) == original_json, \
    'history record unchanged after timelines'
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == \
    listing_before, 'timelines never created/deleted a version'
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization'
                  ).json() == org_v1, 'org unchanged after timelines'
assert export(stored, 1, 'json').content == export_before, \
    'export unchanged after timelines'
assert quality(stored, FULL).json() == quality_before, \
    'Day21 quality unchanged after timelines'
assert get_version(stored, 4)['prompt'] == CITY, 'prompt text untouched'
print('H. read-only: OK (record/listing/org/export/quality untouched)')

# ==================== I. multiple videos ====================
assert timeline(stored_b).json()['video_filename'] == stored_b
assert timeline(stored_b, '1,2').status_code == 404, 'B has one version'
assert timeline(stored).text == default_text_before, \
    'A timeline byte-identical after B activity'
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == \
    listing_before, 'A unaffected by B'
print('I. multiple videos: OK (A/B isolated, A byte-identical after B)')

# ==================== J. route collision + Day16-26 regression ====================
old = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2')
assert old.status_code == 200 and 'common_tokens' in old.json()
assert 'timeline' not in old.json()
detailed = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2/detailed')
assert detailed.status_code == 200 and 'comparison' in detailed.json()
assert 'timeline' not in detailed.json()
new = timeline(stored, '1,2')
d26 = change(stored, 1, 2)
d25 = analyze(stored)
assert old.status_code == detailed.status_code == new.status_code == 200
assert set(old.json().keys()) != set(new.json().keys())
assert set(detailed.json().keys()) != set(new.json().keys())
assert set(new.json().keys()) == TL_TOP
assert set(d26.json().keys()) == DAY26_TOP
assert set(d25.json().keys()) == DAY25_TOP
assert set(d25.json().keys()) != set(new.json().keys())
assert set(d26.json().keys()) != set(new.json().keys())
numeric = client.get(f'/api/videos/{stored}/prompt/history/1')
assert numeric.status_code == 200 and 'prompt' in numeric.json()
assert 'prompt' not in timeline(stored).json(), \
    'static timeline route not captured by numeric route'
assert client.get(f'/api/videos/{stored}/prompt/history/readiness'
                  ).status_code == 200, 'Day25 route still resolves'
assert readiness(stored, CITY).status_code == 200
assert hreadiness(stored, 1).status_code == 200
assert analyze(stored).json()['versions_analyzed'] == [1, 2, 3, 4, 5, 6, 7, 8]
assert analyze(stored, '7,2').json()['versions_analyzed'] == [7, 2]
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
assert timeline(stored, '8,9').status_code == 200
final_default = timeline(stored).json()
assert final_default['versions_analyzed'] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
assert final_default['steps'] == 8
print('J. route collision + Day16-26 regression: OK (old compares, Day25/26, '
      'search/export/package/quality/improve intact, numbering)')

# ==================== K. security + leak scan ====================
blobs = [timeline(stored).text, timeline(stored, '1,5').text,
         timeline(stored, '8,2').text, timeline(stored, '2,1').text,
         timeline(stored, '9,8').text, timeline(stored_b).text,
         timeline(stored_c).text, json.dumps(empty),
         json.dumps(d26.json()), json.dumps(d25.json()),
         json.dumps(detailed.json()), json.dumps(imp.json()),
         json.dumps(readiness(stored, FULL).json()),
         json.dumps(hreadiness(stored, 1).json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/search').json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/history').json())]
for ver in range(1, 10):
    blobs += list(read_zip(package(stored, ver)).values())
for blob in blobs:
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in blob, f'absolute path {bad}'
    for internal in ['_storage', 'PromptReadinessTimelineService',
                     'PromptReadinessChangeService',
                     'PromptReadinessHistoryService', 'PromptReadinessService',
                     'PromptQualityService', 'PromptImprovementService',
                     'PromptHistoryService', 'readiness_timeline_service',
                     'readiness_change_service', 'history_service',
                     'storage/uploads', 'BytesIO', 'Traceback', 'os.environ']:
        assert internal not in blob, f'internal leak {internal}'
for data in (a, sub, single, order, m2w, w2p, tb, empty, final_default):
    low = json.dumps(data).lower()
    for word in ('best', 'worst', 'winner', 'perfect', 'guaranteed',
                 'superior', 'inferior', 'rank', 'recommended', 'better',
                 'worse', 'improved', 'improvement', 'gain'):
        assert word not in low, f'ranking language: {word}'
assert 'film grain style portrait' not in timeline(stored).text, \
    'prompt text never echoed'
final_rec = get_version(stored, 1)
assert json.dumps(final_rec, sort_keys=True) == original_json, \
    'stored history never modified'
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization'
                  ).json() == org_v1, 'org metadata never modified'
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
    assert client.get(f'/api/videos/{stored}/prompt/history/compare/'
                      f'{ver}/{ver}/detailed').status_code == 200
    assert change(stored, ver, ver).status_code == 200
    assert package(stored, ver).status_code == 200
    assert vquality(stored, ver).status_code == 200
    assert himprove(stored, ver).status_code == 200
    assert timeline(stored, f'{ver}').status_code == 200
assert timeline(stored, '1,99').status_code == 404
assert timeline(stored).text == timeline(stored).text, 'final determinism'
print('K. security + leak scan: OK (no leaks, no ranking words, single '
      'store, Day16-27 all functional)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 27 MANUAL E2E VERIFICATIONS PASSED')
