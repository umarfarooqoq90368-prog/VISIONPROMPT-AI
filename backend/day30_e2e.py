import io, json, os, re, subprocess, tempfile, zipfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app
from app.services.prompt_quality_service import DIMENSIONS

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day30_e2e.mp4')

from app.api import videos as videos_api
from app.services.prompt_readiness_export_service import (
    PromptReadinessExportService,
)
from app.services.prompt_export_service import VALID_EXPORT_FORMATS
history_svc = videos_api.prompt_history_service
readiness_svc = videos_api.readiness_service
org_svc = videos_api.organization_service
timeline_svc = videos_api.readiness_timeline_service
snapshot_svc = videos_api.readiness_snapshot_service
report_svc = videos_api.readiness_report_service
export_svc = videos_api.readiness_report_export_service
assert isinstance(export_svc, PromptReadinessExportService)
assert export_svc.report_service is report_svc, 'reuses Day29 report service'
assert report_svc.readiness_timeline_service is timeline_svc
assert report_svc.readiness_snapshot_service is snapshot_svc
assert history_svc is timeline_svc.history_service, 'single Day16 store'
assert VALID_EXPORT_FORMATS == {"json", "markdown", "txt"}, 'Day19 formats'

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
CITY_ENV100 = 'A person walks through a quiet city street near the forest park.'
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

REPORT_TOP = {
    'video_filename', 'versions_analyzed', 'report', 'timeline', 'summary',
}
FORMATS = ('json', 'markdown', 'txt')
MEDIA_TYPES = {
    'json': 'application/json', 'markdown': 'text/markdown',
    'txt': 'text/plain',
}
FILENAMES = {
    'json': 'visionprompt_readiness_report.json',
    'markdown': 'visionprompt_readiness_report.md',
    'txt': 'visionprompt_readiness_report.txt',
}
FORBIDDEN_WORDS = (
    'best', 'worst', 'winner', 'loser', 'superior', 'inferior',
    'better', 'worse', 'improved', 'degraded', 'recommended',
    'preferred', 'optimal',
)
INTERNAL_NAMES = (
    'PromptReadinessExportService', 'PromptReadinessReportService',
    'PromptReadinessSnapshotService', 'PromptReadinessTimelineService',
    'PromptHistoryService', 'readiness_report_export_service',
    'report_service', 'storage/uploads', 'Traceback', 'os.environ',
)


def save(video, prompt, negative=NEG1, source='custom', operation=''):
    body = {'prompt': prompt, 'negative_prompt': negative,
            'source': source, 'operation': operation}
    resp = client.post(f'/api/videos/{video}/prompt/history', json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def url(video):
    return f'/api/videos/{video}/prompt/history/readiness/report/export'


def export(video, fmt='json', versions=None):
    params = {'format': fmt}
    if versions is not None:
        params['versions'] = versions
    return client.get(url(video), params=params)


def export_raw(video, params):
    return client.get(url(video), params=params)


def report(video, versions=None):
    params = None if versions is None else {'versions': versions}
    return client.get(f'/api/videos/{video}/prompt/history/readiness/'
                      f'report', params=params)


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


def export_prompt(video, version, fmt):
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


def leaves(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from leaves(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from leaves(v)
    else:
        yield obj


def fmt_leaf(v):
    if v is None:
        return 'none'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    return str(v)


def pairs_of(data):
    return [(s['version_a']['version'], s['version_b']['version'])
            for s in data['timeline']['steps']]


# --- Day 16/17 history: probe-verified 8-version standard set ---
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
export_before = export_prompt(stored, 1, 'json').content
package_before = package(stored, 1).content
report_before = report(stored).text
uploads_dir = os.path.join('storage', 'uploads')
assert listing_before == [1, 2, 3, 4, 5, 6, 7, 8]

# ==================== A. export envelope ====================
for fmt in FORMATS:
    resp = export(stored, fmt)
    assert resp.status_code == 200, (fmt, resp.status_code)
    assert resp.headers['content-type'].startswith(MEDIA_TYPES[fmt]), \
        (fmt, resp.headers['content-type'])
    assert resp.headers['content-disposition'] == \
        f'attachment; filename="{FILENAMES[fmt]}"'
    assert resp.content.endswith(b'\n')
    assert resp.content.decode('utf-8')
missing_format = client.get(url(stored))
assert missing_format.status_code == 422, 'format is required'
assert export(stored, 'xml').status_code == 422
assert export(stored, 'JSON').status_code == 422
assert export(stored, '').status_code == 422
assert export(stored, 'xml').json()['detail'] == \
    'Invalid format. Must be one of: json, markdown, txt'
print('A. export envelope: OK (3 formats 200, media types, filenames, '
      '422 invalid/missing format)')

# ==================== B. JSON == Day29 report ====================
direct = report(stored).json()
jdata = json.loads(export(stored, 'json').content)
assert set(jdata.keys()) == REPORT_TOP, list(jdata.keys())
assert jdata == direct, 'JSON semantically equals the Day29 endpoint'
assert json.loads(export(stored, 'json').content) == \
    report(stored).json(), 'repeated equality'
for versions in ('1,3,5', '5,3,1', '4,2', '6'):
    assert json.loads(export(stored, 'json', versions).content) == \
        report(stored, versions).json(), versions
text = export(stored, 'json').content.decode('utf-8')
assert text.endswith('}\n')
assert '\n  "video_filename"' in text
assert json.dumps(jdata, indent=2, ensure_ascii=False) + '\n' == text, \
    'deterministic formatting'
print('B. JSON equivalence: OK (5 top keys, equals Day29 for all '
      'selections, indent=2 + trailing newline)')

# ==================== C. Markdown/TXT completeness ====================
md = export(stored, 'markdown').content.decode('utf-8')
txt = export(stored, 'txt').content.decode('utf-8')
assert md.startswith('# Prompt Readiness Report\n')
positions = [md.index(h) for h in ('## Report', '## Version Readiness',
                                   '## Timeline', '## Summary')]
assert positions == sorted(positions)
assert f'- Video: {stored}' in md
assert '- Type: prompt_readiness_report' in md
assert '- Versions analyzed: 1, 2, 3, 4, 5, 6, 7, 8' in md
assert '- Version count: 8' in md
assert '- Selection order: 1, 2, 3, 4, 5, 6, 7, 8' in md
for version in range(1, 9):
    assert f'### Version {version}\n' in md
    assert f'VERSION {version}\n' in txt
v1block = md.split('### Version 1\n', 1)[1].split('### Version ', 1)[0]
assert '- Source: advanced_prompt' in v1block
assert '- Operation: generate' in v1block
assert '- Favorite: true' in v1block
assert '- Tags: ai, cinematic' in v1block
assert '- Status: ready' in v1block
assert '- Required coverage: 100%' in v1block
assert '#### Required Dimensions' in v1block
assert '#### Supporting Dimensions' in v1block
assert '| subject | present | 100 |' in v1block
assert '- Missing dimensions: none' in v1block
md_steps = re.findall(r'(?m)^### Step \d+:', md)
assert len(md_steps) == 7, md_steps
assert '### Step 1: Version 1 \u2192 Version 2' in md
assert 'Step 1: Version 1 -> Version 2' in txt, 'ASCII arrow in txt'
assert '\u2192' not in txt
tl = md.split('### Timeline Summary', 1)[1]
assert '- Changed dimensions: 21' in tl
assert '- Unchanged dimensions: 42' in tl
assert '- Required changes: 17' in tl
assert '- Supporting changes: 4' in tl
assert '- Required coverage delta: -14' in tl
assert '  - missing_to_present: 9' in tl
sm = md.split('### Readiness', 1)[1]
assert '- Ready count: 2' in sm
assert '- Needs attention count: 6' in sm
req = md.split('### Required', 1)[1]
assert '- Total: 56' in req and '- Present: 34' in req
assert '- Weak: 4' in req and '- Missing: 18' in req
assert '- Coverage: 61%' in req
sup = md.split('### Supporting', 1)[1]
assert '- Total: 16' in sup and '- Present: 8' in sup
dims = md.split('### Dimension Summary', 1)[1]
assert '| Dimension | Present | Weak | Missing |' in dims
assert '| subject | 5 | 2 | 1 |' in dims
assert '| camera | 3 | 1 | 4 |' in dims
orgb = md.split('### Organization', 1)[1]
assert '- Favorite count: 2' in orgb
assert '  - ai: 1' in orgb and '  - cinematic: 2' in orgb
assert '  - draft: 1' in orgb and '  - final: 1' in orgb
for fmt, blob in (('markdown', md), ('txt', txt)):
    for leaf in leaves(direct):
        assert fmt_leaf(leaf) in blob, (fmt, fmt_leaf(leaf))
assert 'REPORT\n------' in txt
assert 'VERSION READINESS\n-----------------' in txt
assert 'TIMELINE\n--------' in txt
assert 'SUMMARY\n-------' in txt
assert 'subject: present (100)' in txt
assert 'TIMELINE SUMMARY' in txt
assert 'DIMENSION SUMMARY' in txt
assert 'ORGANIZATION' in txt
print('C. Markdown/TXT completeness: OK (structure, 8 versions, 7 steps, '
      'aggregates, org, all report leaves present)')

# ==================== D. selection semantics ====================
sub = json.loads(export(stored, 'json', '1,3,5').content)
assert sub['versions_analyzed'] == [1, 3, 5]
assert sub['report']['selection_order'] == [1, 3, 5]
rev = json.loads(export(stored, 'json', '5,3,1').content)
assert rev['versions_analyzed'] == [5, 3, 1]
assert pairs_of(rev) == [(5, 3), (3, 1)], 'never resorted'
rev_md = export(stored, 'markdown', '5,3,1').content.decode('utf-8')
positions = [rev_md.index(f'### Version {v}') for v in (5, 3, 1)]
assert positions == sorted(positions)
repeated = export_raw(stored, [('format', 'json'), ('versions', '1'),
                               ('versions', '3')])
assert repeated.status_code == 200
assert repeated.content == export(stored, 'json', '1,3').content, \
    'repeated params == comma form'
spaced = export(stored, 'json', '1 , 3')
assert spaced.status_code == 200
assert spaced.content == export(stored, 'json', '1,3').content, \
    'whitespace tolerated'
mixed = export_raw(stored, [('format', 'txt'), ('versions', ' 5 '),
                            ('versions', '1')])
assert mixed.status_code == 200
assert mixed.content == export(stored, 'txt', '5,1').content
sub_md = export(stored, 'markdown', '1,3,5').content.decode('utf-8')
for leaf in leaves(report(stored, '1,3,5').json()):
    assert fmt_leaf(leaf) in sub_md, fmt_leaf(leaf)
print('D. selection: OK (subset/reverse order, repeated params, '
      'whitespace, Markdown leaves)')

# ==================== E. empty + single ====================
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
save(stored_b, PB, source='custom')
single = json.loads(export(stored_b, 'json').content)
assert single['versions_analyzed'] == [1]
assert single['report']['version_count'] == 1
assert single['timeline']['steps'] == []
assert single['timeline']['required_coverage_delta'] == 0
assert single['summary']['required']['total'] == 7
single_md = export(stored_b, 'markdown').content.decode('utf-8')
assert single_md.count('### Version ') == 1
assert 'No timeline steps.' in single_md
with open(tmp, 'rb') as f:
    up_c = client.post('/api/videos/upload', files={'file': ('test3.mp4', f, 'video/mp4')})
stored_c = up_c.json()['video']['stored_filename']
empty_j = json.loads(export(stored_c, 'json').content)
assert set(empty_j.keys()) == REPORT_TOP
assert empty_j['versions_analyzed'] == []
assert empty_j['report']['snapshots'] == []
assert empty_j['report']['first_version'] is None
assert empty_j['timeline']['required_coverage_delta'] is None
assert empty_j['summary']['required']['coverage_percentage'] is None
assert empty_j['summary']['organization'] == {'favorite_count': 0,
                                              'tag_counts': {}}
empty_md = export(stored_c, 'markdown').content.decode('utf-8')
assert 'No saved versions.' in empty_md
assert 'No timeline steps.' in empty_md
assert '### Version ' not in empty_md
assert '- Coverage: none' in empty_md
empty_txt = export(stored_c, 'txt').content.decode('utf-8')
assert 'No saved versions.' in empty_txt
assert re.findall(r'(?m)^VERSION \d+$', empty_txt) == []
assert 'Ready count: 0' in empty_txt
assert 'Coverage: none' in empty_txt
assert export(stored_c, 'json', '1').status_code == 404
print('E. empty + single: OK (0 versions all formats, 1 version, '
      'null coverage/delta)')

# ==================== F. validation ====================
for q in ('', '0', '-1', 'abc', '1,,2', '1,1', '1.5', ',', ' ', '1;2',
          '0,1', '1 2'):
    assert export(stored, 'json', q).status_code == 422, q
dup = export_raw(stored, [('format', 'json'), ('versions', '2'),
                          ('versions', '2')])
assert dup.status_code == 422
assert export(stored, 'json', '1,99').status_code == 404
assert export(stored, 'json', '1,99').json()['detail'] == \
    f"Version 99 not found for video '{stored}'."
assert export('missing.mp4').status_code == 404
assert export('missing.mp4', 'xml').status_code == 404, \
    'video validated before format'
assert export('clip.txt').status_code == 400
trav = client.get('/api/videos/../../../etc/passwd/prompt/history/'
                  'readiness/report/export',
                  params={'format': 'json'})
assert trav.status_code == 404, trav.status_code
tmp_v = save(stored, 'temporary for delete check')
assert tmp_v['version'] == 9
assert export(stored, 'json', '8,9').status_code == 200
assert client.delete(f'/api/videos/{stored}/prompt/history/9').status_code == 200
assert export(stored, 'json', '9').status_code == 404, 'deleted -> 404'
skipped = json.loads(export(stored, 'json').content)
assert skipped['versions_analyzed'] == [1, 2, 3, 4, 5, 6, 7, 8], \
    'default skips deleted'
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == listing_before
print('F. validation: OK (422 matrix, 404 missing/deleted/video/'
      'traversal, 400 extension, default skips gap)')

# ==================== G. determinism ====================
for fmt in FORMATS:
    first = export(stored, fmt)
    second = export(stored, fmt)
    assert first.content == second.content, fmt
    assert first.headers['content-type'] == second.headers['content-type']
    assert first.headers['content-disposition'] == \
        second.headers['content-disposition']
names = {export(stored, fmt, versions).headers['content-disposition']
         for fmt in FORMATS for versions in (None, '1', '5,3,1', '2,4')}
assert names == {f'attachment; filename="{FILENAMES[f]}"'
                 for f in FORMATS}, names
for fmt in FORMATS:
    text = export(stored, fmt).content.decode('utf-8')
    for marker in ('generated_at', 'exported_at', 'timestamp'):
        assert marker not in text.lower(), (fmt, marker)
    scrubbed = text.replace(stored, '')
    assert 'uuid' not in scrubbed.lower()
    assert not re.search(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        scrubbed), fmt
    for version in range(1, 9):
        assert get_version(stored, version)['created_at'] in text, \
            (fmt, version)
print('G. determinism: OK (byte-identical repeats, stable filenames, '
      'only stored created_at values, no generated ids)')

# ==================== H. read-only + no filesystem ====================
uploads_listing_before = sorted(os.listdir(uploads_dir))
for fmt in FORMATS:
    export(stored, fmt)
    export(stored, fmt, '1,5')
    export(stored, fmt, '8,2')
assert json.dumps(get_version(stored, 1), sort_keys=True) == original_json, \
    'history record unchanged'
assert [x['version'] for x in client.get(
    f'/api/videos/{stored}/prompt/history').json()['versions']] == \
    listing_before, 'listing unchanged'
for v in range(1, 9):
    assert org(stored, v).json() == org_state[v], f'org v{v} unchanged'
assert export_prompt(stored, 1, 'json').content == export_before, \
    'Day19 export unchanged'
assert package(stored, 1).content == package_before, 'Day20 package unchanged'
assert quality(stored, FULL).json() == quality_before, 'Day21 unchanged'
assert report(stored).text == report_before, 'Day29 report unchanged'
uploads_after = sorted(os.listdir(uploads_dir))
assert uploads_after == uploads_listing_before, 'no files created in storage'
assert not any(name.startswith('visionprompt') for name in uploads_after)
print('H. read-only + no filesystem: OK (records/listing/org/Day19-21/'
      'Day29 unchanged, storage untouched)')

# ==================== I. multi-video isolation ====================
b_report = report(stored_b).json()
b_json = json.loads(export(stored_b, 'json').content)
assert b_json == b_report
assert b_json['video_filename'] == stored_b
assert export(stored).text.replace(stored, '') == \
    export(stored).text.replace(stored, ''), 'A stable after B exports'
assert report(stored).text == report_before, 'A report byte-identical'
print('I. multiple videos: OK (B export == B report, A unaffected)')

# ==================== J. route collision + Day16-29 regression ====================
old = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2')
detailed = client.get(f'/api/videos/{stored}/prompt/history/compare/1/2/detailed')
numeric = client.get(f'/api/videos/{stored}/prompt/history/1')
assert old.status_code == 200 and 'common_tokens' in old.json()
assert detailed.status_code == 200 and 'comparison' in detailed.json()
assert numeric.status_code == 200 and numeric.json()['version'] == 1
d19 = export_prompt(stored, 1, 'json')
assert d19.status_code == 200 and json.loads(d19.content)['prompt'] == FULL
assert package(stored, 1).status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/favorites'
                  ).status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/history/tag/ai'
                  ).status_code == 200
assert client.get(f'/api/videos/{stored}/prompt/search').status_code == 200
assert analyze(stored).status_code == 200
assert analyze(stored, '7,2').json()['versions_analyzed'] == [7, 2]
assert change(stored, 1, 2).status_code == 200
assert timeline(stored).json()['timeline'] and len(
    timeline(stored).json()['timeline']) == 7
assert snapshot(stored).status_code == 200
assert report(stored).json()['summary'] == snapshot(stored).json()['summary']
assert readiness(stored, FULL).status_code == 200
assert hreadiness(stored, 1).status_code == 200
assert quality(stored, FULL).json() == quality_before
imp = improve(stored, FULL)
assert imp.status_code == 200 and imp.json()['source_prompt'] == FULL
for fmt in FORMATS:
    e1 = export_prompt(stored, 1, fmt)
    e2 = export_prompt(stored, 1, fmt)
    assert e1.status_code == e2.status_code == 200
    assert e1.content == e2.content, fmt
assert export_prompt(stored, 1, 'json').content == export_before, \
    'Day19 export content unchanged after Day30 activity'
paths = [
    f'/api/videos/{stored}/prompt/history/1',
    f'/api/videos/{stored}/prompt/history/1/export',
    f'/api/videos/{stored}/prompt/history/readiness',
    f'/api/videos/{stored}/prompt/history/readiness/timeline',
    f'/api/videos/{stored}/prompt/history/readiness/snapshot',
    f'/api/videos/{stored}/prompt/history/readiness/report',
    f'/api/videos/{stored}/prompt/history/readiness/report/export',
]
for path in paths:
    params = {'format': 'json'} if path.endswith('export') else None
    assert client.get(path, params=params).status_code == 200, path
key_sets = [set(old.json().keys()), set(detailed.json().keys()),
            set(hreadiness(stored, 1).json().keys()),
            set(analyze(stored).json().keys()),
            set(change(stored, 1, 2).json().keys()),
            set(timeline(stored).json().keys()),
            set(snapshot(stored).json().keys()),
            set(report(stored).json().keys())]
for i in range(len(key_sets)):
    for j in range(i + 1, len(key_sets)):
        assert key_sets[i] != key_sets[j], (i, j)
lv = save(stored, 'recreated after delete check')
assert lv['version'] == 9, 'Day16 numbering unchanged'
assert export(stored, 'json', '8,9').status_code == 200
print('J. route collision + Day16-29 regression: OK (all prior '
      'endpoints, 7 distinct key sets, numbering, Day19 unchanged)')

# ==================== K. security + leak scan ====================
export_blobs = [export(stored, f).content.decode('utf-8')
                for f in FORMATS]
export_blobs += [export(stored, f, '1,5').content.decode('utf-8')
                 for f in FORMATS]
export_blobs += [export(stored, f, '5,1').content.decode('utf-8')
                 for f in FORMATS]
export_blobs += [export(stored_b, f).content.decode('utf-8')
                 for f in FORMATS]
export_blobs += [export(stored_c, f).content.decode('utf-8')
                 for f in FORMATS]
blobs = list(export_blobs)
blobs += [d19.text, detailed.text,
          client.get(f'/api/videos/{stored}/prompt/search').text,
          client.get(f'/api/videos/{stored}/prompt/history').text]
for ver in range(1, 10):
    blobs += list(read_zip(package(stored, ver)).values())
for blob in blobs:
    for bad in ('C:/', 'C:\\', '/home', '/Users', '/var/', 'test_assets',
                'storage/uploads'):
        assert bad not in blob, f'path leak {bad}'
    for internal in INTERNAL_NAMES:
        assert internal not in blob, f'internal leak {internal}'
    low = blob.lower()
    for key in ('password', 'secret', 'api_key', 'authorization'):
        assert key not in low, f'secret: {key}'
# Ranking-language scan applies to Day 30 readiness export output.
for blob in export_blobs:
    low = blob.lower()
    for word in FORBIDDEN_WORDS:
        assert word not in low, f'ranking language: {word}'
    assert 'film grain style portrait' not in blob, 'prompt text leak'
    assert 'blurry, low quality' not in blob, 'negative prompt leak'
for blob in blobs:
    if 'prompt_readiness_report' in blob or 'PROMPT READINESS' in blob:
        assert 'film grain style portrait' not in blob
final_rec = get_version(stored, 1)
assert json.dumps(final_rec, sort_keys=True) == original_json, \
    'stored history never modified'
final_list = [x['version'] for x in
              client.get(f'/api/videos/{stored}/prompt/history').json()['versions']]
assert final_list == [1, 2, 3, 4, 5, 6, 7, 8, 9], 'single store intact'
for fmt in FORMATS:
    assert export(stored, fmt).content == export(stored, fmt).content, \
        'final determinism'
print('K. security + leak scan: OK (no leaks, no ranking words, no '
      'secrets, single store)')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 30 MANUAL E2E VERIFICATIONS PASSED')
