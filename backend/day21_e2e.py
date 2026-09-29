import io, json, os, re, subprocess, tempfile, zipfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import DIMENSIONS

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day21_e2e.mp4')

subprocess.run(
    [ffmpeg, '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=5',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-y', tmp],
    capture_output=True, timeout=15,
)

# --- Pipeline: upload -> frames -> visual -> scenes -> subjects -> audio ->
#     intelligence -> advanced prompt -> refinement -> template -> history
#     -> favorites/tags -> search -> export -> package -> quality
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

DETAILED = (
    "Cinematic film grain style portrait of a person, the subject "
    "walking, looking around and gesturing in an outdoor forest street, "
    "camera tracking with shallow depth of field, soft lighting with rim "
    "light and golden hour glow, vibrant teal and orange palette with "
    "warm tones, layered foreground and rule of thirds composition, "
    "ambient sound with quiet music score."
)


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


def assert_report(data, expected_prompt):
    assert data['prompt'] == expected_prompt, 'prompt echoed unchanged'
    q = data['quality']
    assert list(q.keys()) == ['overall_score', 'completeness_percentage',
                              'dimensions', 'missing_dimensions',
                              'suggestions'], list(q.keys())
    assert list(q['dimensions'].keys()) == list(DIMENSIONS), \
        list(q['dimensions'].keys())
    for dim in DIMENSIONS:
        entry = q['dimensions'][dim]
        assert type(entry['present']) is bool, dim
        assert type(entry['score']) is int and not isinstance(entry['score'], bool)
        assert 0 <= entry['score'] <= 100, dim
        assert entry['score'] in (0, 40, 70, 100), dim
        assert (entry['score'] == 0) == (not entry['present']), dim
    expected_missing = [d for d in DIMENSIONS if not q['dimensions'][d]['present']]
    assert q['missing_dimensions'] == expected_missing, 'missing == present=false'
    assert type(q['overall_score']) is int and 0 <= q['overall_score'] <= 100
    assert type(q['completeness_percentage']) is int
    assert 0 <= q['completeness_percentage'] <= 100
    assert len(q['suggestions']) >= len(q['missing_dimensions'])
    for s in q['suggestions']:
        assert s.startswith('Add ') or s.startswith('Expand '), s
        assert s.endswith('information.') or \
            s.endswith('information for better coverage.'), s
    return q


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
e = export(stored, 1, 'json')
assert e.status_code == 200 and e.text.startswith('{')
pk = package(stored, 1)
assert pk.status_code == 200 and pk.content[:2] == b'PK'
print('Day 16/17/18/19/20 setup: OK')

original_record = get_version(stored, 1)
original_json = json.dumps(original_record, sort_keys=True)

# ==================== A. POST quality response ====================
resp = quality(stored, DETAILED)
assert resp.status_code == 200, resp.status_code
qa = assert_report(resp.json(), DETAILED)
print('A. POST quality response: OK (200, 9 dims, integer 0-100 scores)')

# ==================== B. Detailed prompt full coverage ====================
assert all(qa['dimensions'][d] == {'present': True, 'score': 100}
           for d in DIMENSIONS), 'all dimensions present at 100'
assert qa['missing_dimensions'] == []
assert qa['suggestions'] == []
assert qa['overall_score'] == 100
assert qa['completeness_percentage'] == 100
print('B. Detailed prompt: OK (all 9 present, 100/100, no suggestions)')

# ==================== C. Short prompt all-missing ====================
qc = assert_report(quality(stored, 'Hello world.').json(), 'Hello world.')
assert qc['dimensions']['subject'] == {'present': False, 'score': 0}
assert qc['missing_dimensions'] == list(DIMENSIONS)
assert qc['overall_score'] == 0 and qc['completeness_percentage'] == 0
assert qc['suggestions'] == [
    f'Add {d.replace("_", " ")} information.' for d in DIMENSIONS]
print('C. Short prompt: OK (0/0, all missing, 9 Add-suggestions)')

# ==================== D. Dimension isolation ====================
for dim, prompt, expected in [
    ('lighting', 'soft lighting with rim light', 100),
    ('audio', 'ambient sound and quiet music', 100),
    ('subject', 'a portrait of a person', 70),
    ('color', 'vibrant teal and orange palette', 100),
]:
    qd = assert_report(quality(stored, prompt).json(), prompt)
    for other in DIMENSIONS:
        if other == dim:
            assert qd['dimensions'][other] == {'present': True,
                                               'score': expected}, other
        else:
            assert qd['dimensions'][other] == {'present': False, 'score': 0}, \
                f'{other} falsely detected for {prompt!r}'
print('D. Dimension isolation: OK (4 prompts, no cross-dimension leakage)')

# ==================== E. Scoring tiers + suggestions ====================
qe = assert_report(quality(stored, 'with shadows').json(), 'with shadows')
assert qe['dimensions']['lighting'] == {'present': True, 'score': 40}
assert 'Expand lighting information for better coverage.' in qe['suggestions']
assert len(qe['suggestions']) == 9, '8 missing + 1 weak'
assert qe['overall_score'] == 4, int(40 / 9 + 0.5)
assert qe['completeness_percentage'] == 11
assert all(s.startswith('Add ') for s in qe['suggestions']
           if not s.startswith('Expand '))
qmix = assert_report(quality(stored, 'a portrait of a person').json(),
                     'a portrait of a person')
assert qmix['dimensions']['subject']['score'] == 70
assert qmix['missing_dimensions'] == [d for d in DIMENSIONS if d != 'subject']
print('E. Scoring model: OK (0/40/70/100 tiers, weak gets Expand)')

# ==================== F. Determinism ====================
f1 = quality(stored, DETAILED).json()
f2 = quality(stored, DETAILED).json()
f3 = quality(stored, DETAILED).json()
assert f1 == f2 == f3, 'identical reports across repeated calls'
upper = quality(stored, DETAILED.upper()).json()
assert upper['quality'] == f1['quality'], 'case-insensitive detection'
print('F. Determinism: OK (repeated + case-insensitive identical)')

# ==================== G. Validation ====================
assert client.post(f'/api/videos/{stored}/prompt/quality').status_code == 422
assert client.post(f'/api/videos/{stored}/prompt/quality',
                   json={}).status_code == 422
for bad in ('', '   ', '\n\t'):
    assert quality(stored, bad).status_code == 422, repr(bad)
for bad in (None, 42, ['a'], {'a': 1}, True):
    assert quality(stored, bad).status_code == 422, repr(bad)
assert quality('nope.mp4', DETAILED).status_code == 404
assert quality('notavideo.txt', DETAILED).status_code == 400
g_t = client.post('/api/videos/../../../etc/passwd/prompt/quality',
                  json={'prompt': 'x'})
assert g_t.status_code == 404, g_t.status_code
print('G. Validation: OK (422 body/prompt, 404 video, 400 ext, 404 traversal)')

# ==================== H. History quality endpoint ====================
hv = vquality(stored, 1)
assert hv.status_code == 200, hv.status_code
qh = assert_report(hv.json(), P1)
assert qh['dimensions']['visual_style'] == {'present': True, 'score': 40}
assert qh['missing_dimensions'] != [], 'short stored prompt has gaps'
assert vquality(stored, 99).status_code == 404
assert vquality(stored, 0).status_code == 422
assert vquality('missing_video.mp4', 1).status_code == 404
assert client.delete(f'/api/videos/{stored}/prompt/history/2').status_code == 200
assert vquality(stored, 2).status_code == 404, 'deleted version cannot be analyzed'
assert vquality(stored, 1).status_code == 200
v4 = save(stored, P4)
assert v4['version'] == 4, 'Day16 numbering unchanged'
assert vquality(stored, 4).status_code == 200
print('H. History quality: OK (200 stored prompt, 404 missing/deleted, 422 v0)')

# ==================== I. Route collision ====================
assert get_version(stored, 1)['prompt'] == P1, 'numeric route intact'
assert package(stored, 1).content[:2] == b'PK'
assert export(stored, 1, 'json').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/favorites').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/tag/ai').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/compare/1/3').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/1/organization').status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/search').status_code == 200
print('I. Route collision: OK (/quality vs /{version} vs export/package/search)')

# ==================== J. Read-only integrity ====================
quality(stored, 'a quiet test prompt with shadows')
vquality(stored, 1)
after_record = get_version(stored, 1)
assert json.dumps(after_record, sort_keys=True) == original_json, \
    'history record unchanged after quality analysis'
assert after_record['prompt'] == P1
org_after = client.get(f'/api/videos/{stored}/prompt/history/1/organization').json()
assert org_after == org_v1, 'org metadata unchanged after quality analysis'
listing = client.get(f'/api/videos/{stored}/prompt/history').json()
assert [x['version'] for x in listing['versions']] == [1, 3, 4], \
    'no second version store'
print('J. Read-only: OK (history/org/store untouched by analysis)')

# ==================== K. Multiple videos ====================
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
# quality works on B before any history exists (POST endpoint does not
# require or touch history)
qb = quality(stored_b, PB)
assert qb.status_code == 200, 'quality does not require history'
assert_report(qb.json(), PB)
save(stored_b, PB, source='custom')
client.post(f'/api/videos/{stored_b}/prompt/history/1/favorite')
qa_rec = quality(stored, P1).json()
qb_rec = quality(stored_b, PB).json()
assert qa_rec['prompt'] == P1 and qb_rec['prompt'] == PB
assert vquality(stored_b, 1).json()['prompt'] == PB
assert vquality(stored, 1).json()['prompt'] == P1
print('K. Multiple videos: OK (A/B prompts isolated, no history required)')

# ==================== L. Day16 regression ====================
lv = save(stored, 'temporary for delete check')
assert lv['version'] == 5
assert client.delete(f'/api/videos/{stored}/prompt/history/5').status_code == 200
assert [x['version'] for x in listing['versions']] == [1, 3, 4]
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

# ==================== P. Security / integrity ====================
blobs = [json.dumps(quality(stored, DETAILED).json()),
         json.dumps(vquality(stored, 1).json()),
         json.dumps(search().json()),
         json.dumps(client.get(f'/api/videos/{stored}/prompt/history').json())]
for ver in (1, 3, 4):
    blobs += list(read_zip(package(stored, ver)).values())
for blob in blobs:
    for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
        assert bad not in blob, f'absolute path {bad}'
    for internal in ['_storage', '_org', 'PromptQualityService',
                     'PromptPackageService', 'PromptHistoryService',
                     'storage/uploads', 'BytesIO', 'Traceback']:
        assert internal not in blob, f'internal leak {internal}'
# suggestions may only name the neutral dimension vocabulary
allowed_words = set()
for dim in DIMENSIONS:
    allowed_words.update(dim.replace('_', ' ').split())
for s in quality(stored, 'Hello world.').json()['quality']['suggestions']:
    words = re.findall(r'[a-z]+', s.lower())
    for w in words:
        assert w in allowed_words or w in ('add', 'expand', 'information',
                                           'for', 'better', 'coverage'), w
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
assert package(stored, 2).status_code == 404
assert vquality(stored, 2).status_code == 404
print('P. Security/integrity: OK (no paths/internals, neutral vocabulary, '
      'history+org untouched, single store)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 21 MANUAL E2E VERIFICATIONS PASSED')
