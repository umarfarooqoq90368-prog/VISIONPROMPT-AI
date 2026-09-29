import io, json, os, re, subprocess, tempfile, zipfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import DIMENSIONS
from app.services.prompt_readiness_change_service import (
    PromptReadinessChangeService,
    TRANSITION_KEYS,
)

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day26_e2e.mp4')

# use the app's own service instances (same single stores as the API)
from app.api import videos as videos_api
history_svc = videos_api.prompt_history_service
readiness_svc = videos_api.readiness_service
change_svc = videos_api.readiness_change_service
assert isinstance(change_svc, PromptReadinessChangeService)
assert change_svc.history_service is history_svc, \
    'reuses Day16 history service (no second store)'
assert change_svc.readiness_service is readiness_svc, \
    'reuses Day24 readiness service'

subprocess.run(
    [ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-y', tmp],
    capture_output=True, timeout=15,
)

# --- Pipeline: upload -> frames -> visual -> scenes -> subjects -> audio ->
#     intelligence -> advanced prompt -> refinement -> template
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

TOP_KEYS = {
    'video_filename', 'version_a', 'version_b', 'dimensions',
    'changed_dimensions', 'dimensions_changed', 'dimensions_unchanged',
    'required_changes', 'supporting_changes', 'transitions',
    'transition_summary', 'required_coverage',
}


def save(video, prompt, negative=NEG1, source='custom', operation=''):
    body = {'prompt': prompt, 'negative_prompt': negative,
            'source': source, 'operation': operation}
    resp = client.post(f'/api/videos/{video}/prompt/history', json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


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


# --- Day 16 history (video A): 7 fixture versions ---
v1 = save(stored, FULL, source='advanced_prompt', operation='generate')
v2 = save(stored, WEAK_CAM, source='custom', operation='')
v3 = save(stored, W_CAMLESS, source='template', operation='cinematic')
v4 = save(stored, CITY, source='refinement', operation='expand')
v5 = save(stored, MINIMAL, source='template', operation='shorten')
v6 = save(stored, REQ_ONLY, source='refinement', operation='expand')
v7 = save(stored, CITY_ENV100, source='custom', operation='tweak')
assert [x['version'] for x in (v1, v2, v3, v4, v5, v6, v7)] == [1, 2, 3, 4, 5, 6, 7]

# --- Day 17 favorites/tags (video A) ---
assert client.post(f'/api/videos/{stored}/prompt/history/1/favorite').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/history/1/tags',
                   json={'tags': [' Cinematic ', 'ai']}).json()['tags'] == \
    ['ai', 'cinematic']
org_v1 = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
print('Day 16/17 setup: OK (7 versions, favorite, tags)')

original_record = get_version(stored, 1)
original_json = json.dumps(original_record, sort_keys=True)
listing_before = [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']]
quality_before = quality(stored, FULL).json()
export_before = export(stored, 1, 'json').content
fwd_before = change(stored, 1, 2).text
assert listing_before == [1, 2, 3, 4, 5, 6, 7]

# ==================== A. response schema ====================
resp = change(stored, 1, 2)
assert resp.status_code == 200, resp.status_code
a = resp.json()
assert set(a.keys()) == TOP_KEYS, list(a.keys())
assert a['video_filename'] == stored
for block in (a['version_a'], a['version_b']):
    assert set(block.keys()) == {'version', 'source', 'operation',
                                 'readiness_status',
                                 'required_coverage_percentage'}
assert a['version_a'] == {
    'version': 1, 'source': 'advanced_prompt', 'operation': 'generate',
    'readiness_status': 'ready', 'required_coverage_percentage': 100}
assert a['version_b'] == {
    'version': 2, 'source': 'custom', 'operation': '',
    'readiness_status': 'needs_attention', 'required_coverage_percentage': 86}
assert [d['dimension'] for d in a['dimensions']] == list(DIMENSIONS), 'Day21 order'
assert len(a['dimensions']) == 9
for item in a['dimensions']:
    assert set(item.keys()) == {'dimension', 'version_a', 'version_b', 'changed'}
    assert set(item['version_a'].keys()) == {'status', 'score'}
    assert set(item['version_b'].keys()) == {'status', 'score'}
    assert item['version_a']['status'] in ('present', 'weak', 'missing')
    assert type(item['version_a']['score']) is int
assert set(a['transition_summary'].keys()) == set(TRANSITION_KEYS)
assert all(type(v) is int for v in a['transition_summary'].values())
print('A. response schema: OK (200, exact 12 keys, version blocks, Day21 order)')

# ==================== B. forward compare (1 -> 2) ====================
assert a['changed_dimensions'] == ['camera']
assert a['dimensions_changed'] == 1
assert a['dimensions_unchanged'] == 8
assert a['transitions'] == [
    {'dimension': 'camera', 'from': 'present', 'to': 'weak'}]
assert a['transition_summary'] == {
    'missing_to_weak': 0, 'missing_to_present': 0,
    'weak_to_missing': 0, 'weak_to_present': 0,
    'present_to_missing': 0, 'present_to_weak': 1}
assert a['required_changes'] == ['camera']
assert a['supporting_changes'] == []
assert a['required_coverage'] == {'version_a': 100, 'version_b': 86,
                                  'delta': -14}
camera = next(d for d in a['dimensions'] if d['dimension'] == 'camera')
assert camera['version_a'] == {'status': 'present', 'score': 100}
assert camera['version_b'] == {'status': 'weak', 'score': 40}
assert camera['changed'] is True
print('B. forward compare: OK (1->2, camera present->weak, coverage 100/86/-14)')

# ==================== C. reverse compare (2 -> 1) ====================
rev = change(stored, 2, 1).json()
assert rev['version_a']['version'] == 2, 'labels never swapped'
assert rev['version_b']['version'] == 1
assert rev['version_a']['readiness_status'] == 'needs_attention'
assert rev['version_b']['readiness_status'] == 'ready'
assert rev['changed_dimensions'] == ['camera']
assert rev['transitions'] == [
    {'dimension': 'camera', 'from': 'weak', 'to': 'present'}]
assert rev['transition_summary']['weak_to_present'] == 1
assert sum(rev['transition_summary'].values()) == 1
assert rev['required_coverage'] == {'version_a': 86, 'version_b': 100,
                                    'delta': 14}
for f_item, r_item in zip(a['dimensions'], rev['dimensions']):
    assert f_item['version_a'] == r_item['version_b']
    assert f_item['version_b'] == r_item['version_a']
    assert f_item['changed'] == r_item['changed']
print('C. reverse compare: OK (2->1 mirrored, delta +14, direction preserved)')

# ==================== D. same version (1 -> 1) ====================
same = change(stored, 1, 1).json()
assert same['changed_dimensions'] == []
assert same['dimensions_changed'] == 0
assert same['dimensions_unchanged'] == 9
assert same['transitions'] == []
assert same['required_changes'] == [] and same['supporting_changes'] == []
assert set(same['transition_summary'].values()) == {0}
assert same['required_coverage'] == {'version_a': 100, 'version_b': 100,
                                     'delta': 0}
same_c = change(stored, 4, 4).json()
assert all(item['changed'] is False for item in same_c['dimensions'])
assert same_c['required_coverage']['delta'] == 0
print('D. same version: OK (all unchanged, zero transitions, delta 0)')

# ==================== E. all six transition kinds ====================
mw = change(stored, 3, 2).json()
assert mw['transition_summary']['missing_to_weak'] == 1
assert sum(mw['transition_summary'].values()) == 1
cam32 = next(d for d in mw['dimensions'] if d['dimension'] == 'camera')
assert cam32['version_a'] == {'status': 'missing', 'score': 0}
assert cam32['version_b'] == {'status': 'weak', 'score': 40}
wm = change(stored, 2, 3).json()
assert wm['transition_summary']['weak_to_missing'] == 1
assert wm['changed_dimensions'] == ['camera']

p2m = change(stored, 1, 5).json()
assert p2m['transition_summary']['present_to_missing'] == 9
assert sum(p2m['transition_summary'].values()) == 9
assert p2m['dimensions_changed'] == 9 and p2m['dimensions_unchanged'] == 0
assert p2m['changed_dimensions'] == list(DIMENSIONS), 'Day21 order'
assert len(p2m['required_changes']) == 7
assert p2m['supporting_changes'] == ['color', 'audio']
assert p2m['required_coverage'] == {'version_a': 100, 'version_b': 0,
                                    'delta': -100}
m2p = change(stored, 5, 1).json()
assert m2p['transition_summary']['missing_to_present'] == 9
assert m2p['required_changes'] == p2m['required_changes']
assert m2p['supporting_changes'] == ['color', 'audio']
assert m2p['required_coverage'] == {'version_a': 0, 'version_b': 100,
                                    'delta': 100}
wp = change(stored, 2, 1).json()
assert wp['transition_summary']['weak_to_present'] == 1

supporting_only = change(stored, 6, 1).json()
assert supporting_only['changed_dimensions'] == ['color', 'audio']
assert supporting_only['required_changes'] == []
assert supporting_only['supporting_changes'] == ['color', 'audio']
assert supporting_only['transition_summary']['missing_to_present'] == 2
assert supporting_only['required_coverage'] == {'version_a': 100,
                                                'version_b': 100, 'delta': 0}
seen = set()
for data in (mw, wm, p2m, m2p, wp, a, supporting_only):
    seen.update(k for k, v in data['transition_summary'].items() if v)
assert seen == set(TRANSITION_KEYS), seen
print('E. transitions: OK (all 6 kinds exercised, sums == dimensions_changed)')

# ==================== F. coverage + score-only change ====================
c46 = change(stored, 4, 6).json()
assert c46['required_coverage'] == {'version_a': 14, 'version_b': 100,
                                    'delta': 86}
assert c46['version_a']['readiness_status'] == 'needs_attention'
assert c46['version_b']['readiness_status'] == 'ready'
assert c46['dimensions_changed'] == 6
assert c46['transition_summary']['weak_to_present'] == 1
assert c46['transition_summary']['missing_to_present'] == 5
for data in (a, rev, p2m, m2p, c46):
    cov = data['required_coverage']
    assert cov['delta'] == cov['version_b'] - cov['version_a'], 'b - a arithmetic'
score_only = change(stored, 4, 7).json()
assert score_only['changed_dimensions'] == []
assert score_only['dimensions_changed'] == 0
assert score_only['transitions'] == []
assert score_only['required_coverage'] == {'version_a': 14, 'version_b': 14,
                                           'delta': 0}
env = next(d for d in score_only['dimensions'] if d['dimension'] == 'environment')
assert env['version_a'] == {'status': 'present', 'score': 70}
assert env['version_b'] == {'status': 'present', 'score': 100}
assert env['changed'] is False, '70 -> 100 is not a readiness-state change'
print('F. coverage: OK (14/100/+86, delta == b - a, score-only not a change)')

# ==================== G. validation ====================
for bad_a, bad_b in ((0, 2), (-1, 2), (1, 0), (2, -3), (0, 0),
                     ('abc', 2), (1, 'xyz'), ('1.5', 2)):
    assert change(stored, bad_a, bad_b).status_code == 422, (bad_a, bad_b)
assert change(stored, 1, 99).status_code == 404
assert change(stored, 99, 1).status_code == 404
assert change('missing.mp4', 1, 2).status_code == 404
assert change('clip.txt', 1, 2).status_code == 400
trav = client.get('/api/videos/../../../etc/passwd/prompt/history/compare/'
                  '1/2/readiness')
assert trav.status_code == 404, trav.status_code
detail = change(stored, 1, 99).json()['detail']
assert isinstance(detail, str) and '99' in detail and stored in detail
tmp_v = save(stored, 'temporary for delete check')
assert tmp_v['version'] == 8
assert change(stored, 1, 8).status_code == 200, 'live version compares fine'
assert client.delete(f'/api/videos/{stored}/prompt/history/8').status_code == 200
assert change(stored, 1, 8).status_code == 404, 'deleted version 404'
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == listing_before
print('G. validation: OK (422/404/400/traversal, deleted 404, listing intact)')

# ==================== H. determinism ====================
i1 = change(stored, 1, 4).json()
i2 = change(stored, 1, 4).json()
assert i1 == i2, 'identical repeated results'
assert change(stored, 2, 5).text == change(stored, 2, 5).text
text = change(stored, 4, 6).text
for pat in (r'\d{4}-\d{2}-\d{2}', r'\d{2}:\d{2}'):
    assert not re.search(pat, text), pat
for token in ('uuid', 'timestamp', 'created_at'):
    assert token not in text.lower(), token
print('H. determinism: OK (repeat identical, no timestamps/uuids)')

# ==================== I. read-only integrity ====================
change(stored, 1, 2)
change(stored, 2, 1)
change(stored, 1, 5)
change(stored, 6, 1)
change(stored, 4, 7)
change(stored, 1, 99)
assert json.dumps(get_version(stored, 1), sort_keys=True) == original_json, \
    'history record unchanged after comparisons'
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == \
    listing_before, 'comparisons never created/deleted a version'
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization'
                  ).json() == org_v1, 'org unchanged after comparisons'
assert export(stored, 1, 'json').content == export_before, \
    'export unchanged after comparisons'
assert quality(stored, FULL).json() == quality_before, \
    'Day21 quality unchanged after comparisons'
assert get_version(stored, 4)['prompt'] == CITY, 'prompt text untouched'
print('I. read-only: OK (record/listing/org/export/quality untouched)')

# ==================== J. multiple videos ====================
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
assert stored_b != stored
save(stored_b, PB, source='custom')
rb = change(stored_b, 1, 1)
assert rb.status_code == 200 and rb.json()['dimensions_changed'] == 0
assert change(stored_b, 1, 2).status_code == 404, 'B has only one version'
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == \
    listing_before, 'A unaffected by B'
assert change(stored, 1, 2).text == fwd_before, \
    'A comparison identical after B activity'
assert change(stored_b, 1, 1).json()['video_filename'] == stored_b
print('J. multiple videos: OK (A/B isolated, A byte-identical after B)')

# ==================== K. route collision + Day16-25 regression ====================
old = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2')
assert old.status_code == 200 and 'common_tokens' in old.json()
assert 'transition_summary' not in old.json()
detailed = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2/detailed')
assert detailed.status_code == 200 and 'comparison' in detailed.json()
assert 'transition_summary' not in detailed.json()
new = change(stored, 1, 2)
assert old.status_code == detailed.status_code == new.status_code == 200
assert set(old.json().keys()) != set(new.json().keys())
assert set(detailed.json().keys()) != set(new.json().keys())
assert client.get(f'/api/videos/{stored}/prompt/history/1').status_code == 200
assert readiness(stored, CITY).status_code == 200
assert hreadiness(stored, 1).status_code == 200
assert analyze(stored).json()['versions_analyzed'] == [1, 2, 3, 4, 5, 6, 7]
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
assert lv['version'] == 8, 'Day16 numbering unchanged (max live + 1)'
assert change(stored, 8, 8).status_code == 200
print('K. route collision + Day16-25 regression: OK (old compares, readiness '
      'history, search/export/package/quality/improve intact, numbering)')

# ==================== L. security + leak scan ====================
blobs = [change(stored, 1, 2).text, change(stored, 2, 1).text,
         change(stored, 1, 5).text, change(stored, 6, 1).text,
         change(stored, 4, 6).text, change(stored, 4, 7).text,
         change(stored, 8, 8).text, change(stored_b, 1, 1).text,
         json.dumps(analyze(stored).json()),
         json.dumps(hreadiness(stored, 1).json()),
         json.dumps(readiness(stored, FULL).json()),
         json.dumps(imp.json()),
         json.dumps(detailed.json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/search').json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/history').json())]
for ver in range(1, 9):
    blobs += list(read_zip(package(stored, ver)).values())
for blob in blobs:
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in blob, f'absolute path {bad}'
    for internal in ['_storage', 'PromptReadinessChangeService',
                     'PromptReadinessHistoryService', 'PromptReadinessService',
                     'PromptQualityService', 'PromptImprovementService',
                     'PromptHistoryService', 'storage/uploads', 'BytesIO',
                     'Traceback', 'os.environ']:
        assert internal not in blob, f'internal leak {internal}'
for data in (a, rev, same, p2m, c46, score_only):
    low = json.dumps(data).lower()
    for word in ('best', 'worst', 'winner', 'perfect', 'guaranteed',
                 'superior', 'inferior', 'rank', 'recommended', 'better',
                 'worse', 'improved', 'improvement'):
        assert word not in low, f'ranking language: {word}'
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
assert final_list == [1, 2, 3, 4, 5, 6, 7, 8], 'single Day16 store, no second store'
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
assert change(stored, 1, 99).status_code == 404
print('L. security + leak scan: OK (no leaks, no ranking words, single store, '
      'Day16-26 all functional)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 26 MANUAL E2E VERIFICATIONS PASSED')
