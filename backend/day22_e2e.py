import io, json, os, re, subprocess, tempfile, zipfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import (
    PromptQualityService, DIMENSIONS, WEAK_SCORE,
)
from app.services.prompt_improvement_service import (
    PromptImprovementService, GUIDANCE, IMPROVEMENT_HEADER,
)

client = TestClient(app)
quality_svc = PromptQualityService()
improve_svc = PromptImprovementService(quality_svc)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day22_e2e.mp4')

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
P4 = 'fourth version after delete'
PB = 'isolated video B prompt'
SOURCE = 'A person walks down a road.'


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


def expected_improvements(prompt):
    report = quality_svc.analyze_prompt(prompt)['quality']
    expected = []
    for dim in DIMENSIONS:
        entry = report['dimensions'][dim]
        if not entry['present']:
            reason = 'missing'
        elif entry['score'] == WEAK_SCORE:
            reason = 'weak'
        else:
            continue
        expected.append({'dimension': dim, 'reason': reason,
                         'guidance': GUIDANCE[dim]})
    return expected


def assert_improve_report(data, expected_source):
    assert data['source_prompt'] == expected_source, 'source preserved exactly'
    assert data['improved_prompt'].startswith(expected_source), \
        'improved prompt starts with source'
    assert isinstance(data['improvement_applied'], bool)
    assert isinstance(data['preserved_information'], bool)
    assert data['preserved_information'] is True
    assert isinstance(data['guidance_added'], bool)
    for key in ('quality_before', 'quality_after'):
        assert set(data[key].keys()) == {
            'overall_score', 'completeness_percentage', 'dimensions',
            'missing_dimensions', 'suggestions',
        }, key
        assert list(data[key]['dimensions'].keys()) == list(DIMENSIONS), key
        for dim in DIMENSIONS:
            entry = data[key]['dimensions'][dim]
            assert type(entry['present']) is bool
            assert type(entry['score']) is int and 0 <= entry['score'] <= 100
    assert data['improvements'] == expected_improvements(expected_source), \
        'improvements == Day21 missing/weak mapping'
    assert data['guided_dimensions'] == [i['dimension']
                                         for i in data['improvements']]
    dims = [i['dimension'] for i in data['improvements']]
    assert len(dims) == len(set(dims)), 'no duplicate guidance'
    assert dims == [d for d in DIMENSIONS if d in set(dims)], \
        'deterministic dimension ordering'
    for item in data['improvements']:
        assert set(item.keys()) == {'dimension', 'reason', 'guidance'}
        assert item['dimension'] in DIMENSIONS
        assert item['reason'] in ('missing', 'weak')
        assert item['guidance'] == GUIDANCE[item['dimension']]


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

# --- Day 19/20 export/package sanity ---
assert export(stored, 1, 'json').status_code == 200
pk = package(stored, 1)
assert pk.status_code == 200 and pk.content[:2] == b'PK'
# --- Day 21 quality sanity ---
assert quality(stored, P1).status_code == 200
print('Day 16/17/18/19/20/21 setup: OK')

original_record = get_version(stored, 1)
original_json = json.dumps(original_record, sort_keys=True)

# ==================== A. POST improve response ====================
resp = improve(stored, SOURCE)
assert resp.status_code == 200, resp.status_code
a = resp.json()
assert set(a.keys()) == {'video_filename', 'source_prompt', 'improved_prompt',
                         'quality_before', 'quality_after', 'improvements',
                         'improvement_applied', 'preserved_information',
                         'guidance_added', 'guided_dimensions'}, list(a.keys())
assert a['video_filename'] == stored
assert_improve_report(a, SOURCE)
assert a['improvement_applied'] is True
assert a['guidance_added'] is True
print('A. POST improve response: OK (200, full schema, preserved source)')

# ==================== B. Improved prompt format ====================
expected_prompt = (f'{SOURCE}\n\n{IMPROVEMENT_HEADER}\n'
                   + '\n'.join(i['guidance'] for i in a['improvements']))
assert a['improved_prompt'] == expected_prompt, 'exact deterministic format'
assert a['improved_prompt'].count(IMPROVEMENT_HEADER) == 1, 'header once'
lines = a['improved_prompt'][len(SOURCE):].splitlines()
guidance_lines = [ln for ln in lines if ln.startswith('[')]
assert len(guidance_lines) == len(set(guidance_lines)) == len(a['improvements'])
print('B. Improved prompt format: OK (append-only, header once, no dupes)')

# ==================== C. No fabrication ====================
added = a['improved_prompt'][len(SOURCE):]
assert added.startswith('\n\n' + IMPROVEMENT_HEADER + '\n')
assert [ln for ln in added.splitlines() if ln.startswith('[')] == \
    [i['guidance'] for i in a['improvements']], 'added text is only guidance'
low_full = a['improved_prompt'].lower()
for word in ('sunset', 'rain', 'neon', 'night', 'dusk', 'dawn', 'beautiful',
             'sarah', 'tokyo', 'ferrari', 'luxury', 'woman', 'cinematic'):
    if word in SOURCE.lower():
        continue
    assert word not in low_full, f'fabricated: {word}'
for item in a['improvements']:
    g = item['guidance']
    assert g.startswith('[') and g.endswith(']') and 'if known' in g, g
print('C. No fabrication: OK (only bracketed instructions added)')

# ==================== D. Improvements mapping ====================
q_before = quality_svc.analyze_prompt(SOURCE)['quality']
assert a['quality_before'] == q_before, 'quality_before == direct Day21'
missing = [d for d in DIMENSIONS if not q_before['dimensions'][d]['present']]
weak = [d for d in DIMENSIONS
        if q_before['dimensions'][d]['present']
        and q_before['dimensions'][d]['score'] == WEAK_SCORE]
assert set(a['guided_dimensions']) == set(missing) | set(weak)
for item in a['improvements']:
    if item['dimension'] in missing:
        assert item['reason'] == 'missing'
    else:
        assert item['reason'] == 'weak'
        assert item['dimension'] in weak
# fully covered prompt -> no improvements
detailed = quality_svc.analyze_prompt(
    'Cinematic film grain style portrait of a person, the subject walking, '
    'looking around and gesturing in an outdoor forest street, camera '
    'tracking with shallow depth of field, soft lighting with rim light and '
    'golden hour glow, vibrant teal and orange palette with warm tones, '
    'layered foreground and rule of thirds composition, ambient sound with '
    'quiet music score.'
)
assert detailed['quality']['missing_dimensions'] == []
d_resp = improve(stored, detailed['prompt']).json()
assert d_resp['improvement_applied'] is False
assert d_resp['improved_prompt'] == detailed['prompt']
assert d_resp['improvements'] == []
print('D. Improvements mapping: OK (missing/weak only, correct reasons)')

# ==================== E. Quality integration ====================
assert a['quality_after'] == quality_svc.analyze_prompt(
    a['improved_prompt'])['quality'], 'quality_after == direct analysis'
direct_before = quality(stored, SOURCE).json()['quality']
assert a['quality_before'] == direct_before, 'API quality_before matches Day21'
for dim in a['guided_dimensions']:
    assert a['quality_after']['dimensions'][dim]['present'] is True, dim
assert a['quality_after']['missing_dimensions'] == [], \
    'all missing dims covered by guidance'
assert a['quality_after']['overall_score'] >= a['quality_before']['overall_score']
assert (a['quality_after']['completeness_percentage']
        >= a['quality_before']['completeness_percentage'])
assert a['guided_dimensions'], 'guidance marking distinguishes placeholders'
print('E. Quality integration: OK (before==Day21, after==improved analysis)')

# ==================== F. Determinism ====================
f1 = improve(stored, SOURCE).json()
f2 = improve(stored, SOURCE).json()
assert f1 == f2, 'identical repeated results'
upper = improve(stored, SOURCE.upper()).json()
assert upper['guided_dimensions'] == f1['guided_dimensions']
assert upper['improvements'] == f1['improvements']
assert upper['improved_prompt'].startswith(SOURCE.upper())
assert upper['improved_prompt'][len(SOURCE.upper()):] == \
    f1['improved_prompt'][len(SOURCE):], 'guidance identical regardless of case'
assert f1['quality_before'] == upper['quality_before'], 'case-insensitive Day21'
for pat in (r'\d{4}-\d{2}-\d{2}', r'\d{2}:\d{2}'):
    assert not re.search(pat, f1['improved_prompt']), 'no dates/timestamps'
print('F. Determinism: OK (repeated + case-insensitive + no timestamps)')

# ==================== G. Validation ====================
assert client.post(f'/api/videos/{stored}/prompt/improve').status_code == 422
assert client.post(f'/api/videos/{stored}/prompt/improve',
                   json={}).status_code == 422
for bad in ('', '   ', '\n\t'):
    assert improve(stored, bad).status_code == 422, repr(bad)
for bad in (None, 42, ['a'], {'a': 1}, True):
    assert improve(stored, bad).status_code == 422, repr(bad)
assert improve('nope.mp4', SOURCE).status_code == 404
assert improve('notavideo.txt', SOURCE).status_code == 400
g_t = client.post('/api/videos/../../../etc/passwd/prompt/improve',
                  json={'prompt': SOURCE})
assert g_t.status_code == 404, g_t.status_code
print('G. Validation: OK (422 body/prompt, 404 video, 400 ext, 404 traversal)')

# ==================== H. History improve endpoint ====================
hv = himprove(stored, 1)
assert hv.status_code == 200, hv.status_code
h = hv.json()
assert_improve_report(h, P1)
assert h['video_filename'] == stored
post_h = improve(stored, P1).json()
for key in ('source_prompt', 'improved_prompt', 'quality_before',
            'quality_after', 'improvements', 'improvement_applied',
            'preserved_information'):
    assert h[key] == post_h[key], key
assert himprove(stored, 99).status_code == 404
assert himprove(stored, 0).status_code == 422
assert himprove('missing_video.mp4', 1).status_code == 404
assert client.delete(f'/api/videos/{stored}/prompt/history/2').status_code == 200
assert himprove(stored, 2).status_code == 404, 'deleted version cannot improve'
assert himprove(stored, 1).status_code == 200
v4 = save(stored, P4)
assert v4['version'] == 4, 'Day16 numbering unchanged'
assert himprove(stored, 4).status_code == 200
print('H. History improve: OK (200/404/422, matches POST, numbering intact)')

# ==================== I. Route collision ====================
assert get_version(stored, 4)['prompt'] == P4, 'numeric route returns version'
assert package(stored, 1).content[:2] == b'PK'
assert export(stored, 1, 'json').status_code == 200
assert vquality(stored, 1).status_code == 200
assert quality(stored, P1).status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/favorites').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/tag/ai').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/compare/1/3').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/search').status_code == 200
print('I. Route collision: OK (/improve vs /{version} vs quality/export/search)')

# ==================== J. Read-only / no auto-save ====================
improve(stored, 'a different prompt with shadows')
himprove(stored, 1)
after_record = get_version(stored, 1)
assert json.dumps(after_record, sort_keys=True) == original_json, \
    'history record unchanged after improvement'
assert after_record['prompt'] == P1
org_after = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert org_after == org_v1, 'org metadata unchanged after improvement'
listing = client.get(f'/api/videos/{stored}/prompt/history').json()
assert [x['version'] for x in listing['versions']] == [1, 3, 4], \
    'improvement never saved into history (no second store)'
print('J. Read-only: OK (history/org untouched, nothing auto-saved)')

# ==================== K. Multiple videos ====================
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
qb = improve(stored_b, PB)
assert qb.status_code == 200, 'improve does not require history'
assert_improve_report(qb.json(), PB)
save(stored_b, PB, source='custom')
client.post(f'/api/videos/{stored_b}/prompt/history/1/favorite')
assert himprove(stored_b, 1).json()['source_prompt'] == PB
assert himprove(stored, 1).json()['source_prompt'] == P1
assert client.get(f'/api/videos/{stored_b}/prompt/history').json()['versions'] \
    != listing['versions'], 'A and B histories independent'
print('K. Multiple videos: OK (A/B isolated, no history required)')

# ==================== L. Day16 regression ====================
lv = save(stored, 'temporary for delete check')
assert lv['version'] == 5
assert client.delete(f'/api/videos/{stored}/prompt/history/5').status_code == 200
assert [x['version'] for x in
        client.get(f'/api/videos/{stored}/prompt/history').json()['versions']] \
    == [1, 3, 4]
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
print('M. Day17 regression: OK (favorite/unfavorite/tags/org)')

# ==================== N. Day18 regression ====================
def search(**params):
    return client.get(f'/api/videos/{stored}/prompt/search', params=params)

assert [r['version'] for r in search(query='cinematic').json()['results']] == [1, 3]
assert [r['version'] for r in search(favorite='true').json()['results']] == [1]
assert [r['version'] for r in search(tag='ai').json()['results']] == [1]
assert [r['version'] for r in search(source='custom').json()['results']] == [3, 4]
assert [r['version'] for r in
        search(query='cinematic', source='refinement', favorite='true',
               tag='ai').json()['results']] == [1]
print('N. Day18 regression: OK (query/favorite/tag/source/combined)')

# ==================== O. Day19/20 regression ====================
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
print('O. Day19/20 regression: OK (exports + packages intact and deterministic)')

# ==================== P. Day21 regression + security ====================
q_before_improve = quality(stored, P1).json()
improve(stored, 'another prompt for regression check')
q_after_improve = quality(stored, P1).json()
assert q_before_improve == q_after_improve, 'Day21 quality unchanged'
vq1 = vquality(stored, 1)
vq2 = vquality(stored, 1)
assert vq1.status_code == vq2.status_code == 200
assert vq1.content == vq2.content, 'Day21 history quality deterministic'
blobs = [json.dumps(improve(stored, SOURCE).json()),
         json.dumps(himprove(stored, 1).json()),
         json.dumps(search().json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/history').json())]
for ver in (1, 3, 4):
    blobs += list(read_zip(package(stored, ver)).values())
for blob in blobs:
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in blob, f'absolute path {bad}'
    for internal in ['_quality_service', 'PromptImprovementService',
                     'PromptQualityService', 'PromptHistoryService',
                     'storage/uploads', 'BytesIO', 'Traceback',
                     'os.environ']:
        assert internal not in blob, f'internal leak {internal}'
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
    assert vquality(stored, ver).status_code == 200
    assert himprove(stored, ver).status_code == 200
assert package(stored, 2).status_code == 404
assert vquality(stored, 2).status_code == 404
assert himprove(stored, 2).status_code == 404
print('P. Day21 regression + security: OK (quality intact, no leaks, '
      'history+org untouched, single store)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 22 MANUAL E2E VERIFICATIONS PASSED')
