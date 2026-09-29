import io, json, os, re, subprocess, tempfile, zipfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import PromptQualityService, DIMENSIONS
from app.services.prompt_readiness_service import PromptReadinessService

client = TestClient(app)
quality_svc = PromptQualityService()
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day24_e2e.mp4')

# use the app's own service instances (same single stores as the API)
from app.api import videos as videos_api
history_svc = videos_api.prompt_history_service
readiness_svc = videos_api.readiness_service
assert isinstance(readiness_svc, PromptReadinessService)
assert readiness_svc.quality_service is videos_api.quality_service, \
    'reuses Day21 quality service'

subprocess.run(
    [ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-y', tmp],
    capture_output=True, timeout=15,
)

# --- Pipeline: upload -> frames -> visual -> scenes -> subjects -> audio ->
#     intelligence -> advanced prompt -> refinement -> template -> history
#     -> favorites/tags -> search -> export -> package -> quality ->
#     improvement -> detailed comparison -> readiness
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

# Day21-verified fixture prompts
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


# --- Day 16 history (video A) ---
v1 = save(stored, P1, source='refinement', operation='cinematic',
          metadata={'style': 'film'})
v2 = save(stored, P2, source='template', operation='ai_video')
v3 = save(stored, P3, negative='', source='custom', operation='')
assert [v['version'] for v in (v1, v2, v3)] == [1, 2, 3]

# --- Day 17 favorites/tags (video A) ---
assert client.post(f'/api/videos/{stored}/prompt/history/1/favorite').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/history/1/tags',
                   json={'tags': [' Cinematic ', 'ai']}).json()['tags'] == \
    ['ai', 'cinematic']
org_v1 = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert org_v1 == {'video_filename': stored, 'version': 1,
                  'favorite': True, 'tags': ['ai', 'cinematic']}

# --- Day 18-23 sanity ---
assert client.get(f'/api/videos/{stored}/prompt/search',
                  params={'query': 'cinematic'}).json()['count'] == 2
assert export(stored, 1, 'json').status_code == 200
assert package(stored, 1).content[:2] == b'PK'
assert quality(stored, P1).status_code == 200
assert improve(stored, P1).status_code == 200
assert compare(stored, 1, 2).status_code == 200
print('Day 16/17/18/19/20/21/22/23 setup: OK')

original_record = get_version(stored, 1)
original_json = json.dumps(original_record, sort_keys=True)
listing_before = client.get(f'/api/videos/{stored}/prompt/history').json()

# ==================== A. POST readiness response ====================
resp = readiness(stored, FULL)
assert resp.status_code == 200, resp.status_code
a = resp.json()
assert set(a.keys()) == {'video_filename', 'prompt', 'readiness'}, list(a.keys())
assert a['video_filename'] == stored
assert a['prompt'] == FULL, 'prompt echoed byte-for-byte'
rd = a['readiness']
assert set(rd.keys()) == {'status', 'required_dimensions',
                          'supporting_dimensions', 'checklist', 'coverage',
                          'missing_dimensions', 'weak_dimensions',
                          'suggestions'}, list(rd.keys())
print('A. POST readiness response: OK (200, exact schema, prompt preserved)')

# ==================== B. ready status ====================
assert rd['status'] == 'ready'
cov = rd['coverage']
assert cov['required_total'] == 7 and cov['required_present'] == 7
assert cov['required_missing'] == 0 and cov['required_weak'] == 0
assert cov['required_coverage_percentage'] == 100
assert rd['missing_dimensions'] == [] and rd['weak_dimensions'] == []
assert rd['suggestions'] == []
print('B. ready status: OK (all 7 required present, coverage 100, no gaps)')

# ==================== C. needs_attention status ====================
c = readiness(stored, CITY).json()['readiness']
assert c['status'] == 'needs_attention'
assert c['weak_dimensions'] == ['subject']
assert c['missing_dimensions'] == ['action', 'camera', 'lighting',
                                   'visual_style', 'color', 'composition',
                                   'audio']
ccov = c['coverage']
assert (ccov['required_present'], ccov['required_weak'],
        ccov['required_missing']) == (1, 1, 5)
assert ccov['required_coverage_percentage'] == 14, 'round(1/7*100) = 14'
print('C. needs_attention status: OK (exact missing/weak, coverage 14)')

# ==================== D. required vs supporting ====================
ro = readiness(stored, REQ_ONLY).json()['readiness']
assert ro['status'] == 'ready', 'missing supporting never blocks ready'
rcov = ro['coverage']
assert rcov['required_coverage_percentage'] == 100
assert rcov['supporting_total'] == 2 and rcov['supporting_present'] == 0
assert rcov['supporting_missing'] == 2 and rcov['supporting_weak'] == 0
assert 'color' in ro['missing_dimensions'] and 'audio' in ro['missing_dimensions']
assert ro['required_dimensions'] == ['subject', 'action', 'environment',
                                     'camera', 'lighting', 'visual_style',
                                     'composition']
assert ro['supporting_dimensions'] == ['color', 'audio']
assert set(ro['required_dimensions']) | set(ro['supporting_dimensions']) == \
    set(DIMENSIONS)
assert set(ro['required_dimensions']).isdisjoint(ro['supporting_dimensions'])
print('D. required/supporting distinction: OK (supporting missing -> '
      'still ready, both groups reported)')

# ==================== E. weak dimension ====================
w = readiness(stored, WEAK_CAM).json()['readiness']
assert w['status'] == 'needs_attention', 'weak required blocks ready'
assert w['weak_dimensions'] == ['camera']
assert w['missing_dimensions'] == []
assert w['suggestions'] == ['Expand camera information if known.']
wcov = w['coverage']
assert wcov['required_present'] == 6 and wcov['required_weak'] == 1
assert wcov['required_coverage_percentage'] == 86, 'weak not counted present'
camera = next(x for x in w['checklist'] if x['dimension'] == 'camera')
assert camera['status'] == 'weak' and camera['score'] == 40
assert camera['message'] == \
    'Camera information is present but may need more detail.'
print('E. weak dimension: OK (status/weak list/Expand suggestion/'
      'coverage excludes weak)')

# ==================== F. checklist + Day21 echo ====================
day21 = quality(stored, CITY).json()['quality']
checklist = c['checklist']
assert [x['dimension'] for x in checklist] == list(DIMENSIONS), 'Day21 order'
for item in checklist:
    score = day21['dimensions'][item['dimension']]['score']
    assert item['score'] == score, 'Day21 score echoed unaltered'
    expected = 'present' if score >= 70 else 'weak' if score > 0 else 'missing'
    assert item['status'] == expected, item['dimension']
    assert item['present'] is (item['status'] == 'present')
    assert set(item.keys()) == {'dimension', 'status', 'present', 'score',
                                'message'}
by_dim = {x['dimension']: x for x in checklist}
assert by_dim['environment']['message'] == 'Environment information detected.'
assert by_dim['subject']['message'] == \
    'Subject information is present but may need more detail.'
assert by_dim['camera']['message'] == 'Camera information is not detected.'
assert readiness(stored, FULL).json()['readiness']['checklist'] == [
    {'dimension': dim, 'status': 'present', 'present': True, 'score': 100,
     'message': ('Visual style information detected.'
                 if dim == 'visual_style'
                 else f'{dim.replace("_", " ").capitalize()} information '
                      'detected.')}
    for dim in DIMENSIONS
]
print('F. checklist + Day21 echo: OK (order, statuses, messages, scores)')

# ==================== G. determinism ====================
g1 = readiness(stored, CITY).json()
g2 = readiness(stored, CITY).json()
assert g1 == g2, 'identical repeated results'
gu = readiness(stored, CITY.upper()).json()['readiness']
assert gu['status'] == c['status']
assert gu['coverage'] == c['coverage']
assert gu['checklist'] == c['checklist']
text = json.dumps(g1)
for pat in (r'\d{4}-\d{2}-\d{2}', r'\d{2}:\d{2}'):
    assert not re.search(pat, text), pat
for token in ('uuid', 'timestamp'):
    assert token not in text.lower(), token
print('G. determinism: OK (repeat identical, case-insensitive, no '
      'timestamps/uuids)')

# ==================== H. validation ====================
assert client.post(f'/api/videos/{stored}/prompt/readiness').status_code == 422
assert client.post(f'/api/videos/{stored}/prompt/readiness',
                   json={}).status_code == 422
for bad in ('', '   ', '\n\t'):
    assert readiness(stored, bad).status_code == 422, repr(bad)
for bad in (None, 42, ['a'], {'a': 1}, True):
    assert readiness(stored, bad).status_code == 422, repr(bad)
assert readiness('nope.mp4', CITY).status_code == 404
assert readiness('notavideo.txt', CITY).status_code == 400
h_t = client.post('/api/videos/../../../etc/passwd/prompt/readiness',
                  json={'prompt': CITY})
assert h_t.status_code == 404, h_t.status_code
assert hreadiness(stored, 0).status_code == 422
assert client.get(f'/api/videos/{stored}/prompt/history/abc/readiness'
                  ).status_code == 422
assert hreadiness(stored, 99).status_code == 404
assert hreadiness('missing_video.mp4', 1).status_code == 404
print('H. validation: OK (422 body/prompt/version, 404 video/version/'
      'traversal, 400 ext)')

# ==================== I. history readiness endpoint ====================
hv = hreadiness(stored, 1)
assert hv.status_code == 200, hv.status_code
h = hv.json()
assert h['prompt'] == P1 and h['video_filename'] == stored
assert h['readiness']['status'] == 'needs_attention'
assert h == readiness(stored, P1).json(), 'history == POST for same prompt'
tmp_v = save(stored, 'temporary for delete check')
assert tmp_v['version'] == 4
assert client.delete(f'/api/videos/{stored}/prompt/history/4').status_code == 200
assert hreadiness(stored, 4).status_code == 404, 'deleted version 404'
print('I. history readiness: OK (200 == POST, 404 deleted/version)')

# ==================== J. read-only ====================
hreadiness(stored, 1)
readiness(stored, FULL)
readiness(stored, CITY)
assert json.dumps(get_version(stored, 1), sort_keys=True) == original_json, \
    'history record unchanged after readiness'
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization'
                  ).json() == org_v1, 'org unchanged after readiness'
assert client.get(f'/api/videos/{stored}/prompt/history').json() == \
    listing_before, 'readiness never created/deleted a version'
assert export(stored, 1, 'json').status_code == 200
print('J. read-only: OK (history/org/listing untouched, nothing saved)')

# ==================== K. multiple videos ====================
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
save(stored_b, PB, source='custom')
rb = readiness(stored_b, PB)
assert rb.status_code == 200 and rb.json()['readiness']['status'] == \
    'needs_attention'
assert hreadiness(stored_b, 1).json()['prompt'] == PB
assert hreadiness(stored_b, 2).status_code == 404
assert readiness(stored_b, FULL).json()['readiness']['status'] == 'ready', \
    'readiness is prompt-only, video B has no history needed'
assert hreadiness(stored, 1).json()['prompt'] == P1, 'A unaffected by B'
print('K. multiple videos: OK (A/B isolated, readiness needs no history)')

# ==================== L. Day16 regression ====================
lv = save(stored, 'recreated after delete')
assert lv['version'] == 4, 'Day16 numbering unchanged (max live + 1)'
lg = client.get(f'/api/videos/{stored}/prompt/history/3')
assert lg.status_code == 200 and lg.json()['prompt'] == P3
lc = client.get(f'/api/videos/{stored}/prompt/history/compare/1/3')
assert lc.status_code == 200 and 'common_tokens' in lc.json()
assert [x['version'] for x in
        client.get(f'/api/videos/{stored}/prompt/history').json()['versions']] \
    == [1, 2, 3, 4]
print('L. Day16 regression: OK (create/list/get/compare/delete/numbering)')

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
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization'
                  ).json() == org_v1
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

# ==================== P. Day21/22/23 regression + security ====================
q_before = quality(stored, P1).json()
readiness(stored, FULL)
assert quality(stored, P1).json() == q_before, 'Day21 quality unchanged'
vq1, vq2 = vquality(stored, 1), vquality(stored, 1)
assert vq1.content == vq2.content, 'Day21 history quality deterministic'
imp = improve(stored, P1)
assert imp.status_code == 200 and imp.json()['source_prompt'] == P1
assert himprove(stored, 1).status_code == 200
d = compare(stored, 1, 2)
assert d.status_code == 200 and d.json()['comparison']['changed'] is True
assert quality(stored, P1).json() == q_before, \
    'quality unchanged by readiness/improve/compare'
old = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2')
assert old.status_code == 200 and 'common_tokens' in old.json()
assert 'readiness' not in old.json(), 'Day16 compare response unchanged'

blobs = [json.dumps(readiness(stored, FULL).json()),
         json.dumps(readiness(stored, CITY).json()),
         json.dumps(hreadiness(stored, 1).json()),
         json.dumps(imp.json()),
         json.dumps(d.json()),
         json.dumps(search().json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/history').json())]
for ver in (1, 2, 3, 4):
    blobs += list(read_zip(package(stored, ver)).values())
for blob in blobs:
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in blob, f'absolute path {bad}'
    for internal in ['_storage', 'PromptReadinessService',
                     'PromptQualityService', 'PromptImprovementService',
                     'PromptHistoryService', 'storage/uploads', 'BytesIO',
                     'Traceback', 'os.environ']:
        assert internal not in blob, f'internal leak {internal}'
    for word in ('best', 'worst', 'winner', 'perfect', 'guaranteed',
                 'objectively good', 'objectively bad'):
        assert word not in blob.lower(), f'ranking language: {word}'
final_rec = get_version(stored, 1)
assert json.dumps(final_rec, sort_keys=True) == original_json, \
    'stored history never modified'
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization'
                  ).json() == org_v1, 'org metadata never modified'
final_list = [x['version'] for x in
              client.get(f'/api/videos/{stored}/prompt/history').json()['versions']]
assert final_list == [1, 2, 3, 4], 'single Day16 store, no second store'
for ver in final_list:
    assert hreadiness(stored, ver).status_code == 200
    assert compare(stored, ver, ver).status_code == 200
    assert package(stored, ver).status_code == 200
    assert vquality(stored, ver).status_code == 200
    assert himprove(stored, ver).status_code == 200
assert hreadiness(stored, 5).status_code == 404
print('P. Day21/22/23 regression + security: OK (quality/improve/compare '
      'intact, no leaks, no ranking words, single store)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 24 MANUAL E2E VERIFICATIONS PASSED')
