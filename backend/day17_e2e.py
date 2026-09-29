import json, os, subprocess, tempfile, imageio_ffmpeg
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), 'day17_e2e.mp4')

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
adv = client.post(f'/api/videos/{stored}/advanced-prompt?style=cinematic')
assert adv.status_code == 200
ref = client.post(f'/api/videos/{stored}/prompt/refine', json={'operation': 'refine'})
assert ref.status_code == 200
tpl = client.post(f'/api/videos/{stored}/prompt/template', json={'template': 'ai_video'})
assert tpl.status_code == 200
print('B. Day 1-15 pipeline: OK')


def save(video, prompt, negative='blurry, low quality'):
    resp = client.post(
        f'/api/videos/{video}/prompt/history',
        json={'prompt': prompt, 'negative_prompt': negative, 'source': 'custom'},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


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
        'DELETE',
        f'/api/videos/{video}/prompt/history/{version}/tags',
        json={'tags': tags},
    )


def org(video, version):
    return client.get(f'/api/videos/{video}/prompt/history/{version}/organization')


def favorites(video):
    return client.get(f'/api/videos/{video}/prompt/history/favorites').json()['favorites']


def by_tag(video, tag):
    return client.get(f'/api/videos/{video}/prompt/history/tag/{tag}').json()['versions']


# C. Create 3 Day 16 versions
v1 = save(stored, 'alpha beta gamma one one')
v2 = save(stored, 'alpha beta delta two two')
v3 = save(stored, 'alpha beta epsilon three three')
assert [v1['version'], v2['version'], v3['version']] == [1, 2, 3]
print('C. Three prompt versions created: OK (1, 2, 3)')

# D. Favorite version 1 -> 200
d = fav(stored, 1)
assert d.status_code == 200, d.status_code
assert d.json() == {'video_filename': stored, 'version': 1, 'favorite': True}
print('D. Favorite version 1: OK (200)')

# E. Favorite again -> idempotent
d2 = fav(stored, 1)
assert d2.status_code == 200 and d2.json()['favorite'] is True
assert len(favorites(stored)) == 1, 'no duplicate favorite records'
print('E. Favorite twice idempotent: OK')

# F. Unfavorite -> 200
f1 = unfav(stored, 1)
assert f1.status_code == 200, f1.status_code
assert f1.json() == {'video_filename': stored, 'version': 1, 'favorite': False}
print('F. Unfavorite version 1: OK (200)')

# G. Unfavorite again -> idempotent
f2 = unfav(stored, 1)
assert f2.status_code == 200 and f2.json()['favorite'] is False
assert favorites(stored) == []
print('G. Unfavorite twice idempotent: OK')

# H. Favorite another version; favorites list returns only favorited
assert fav(stored, 2).status_code == 200
assert fav(stored, 3).status_code == 200
fav_list = favorites(stored)
assert [x['version'] for x in fav_list] == [2, 3]
assert all(x['favorite'] is True for x in fav_list)
print('H. Favorites listing only favorited: OK ([2, 3])')

# I. Add tags with messy input -> normalized
messy = [' Cinematic ', 'AI', 'cinematic', '', '  ']
t = add_tags(stored, 1, messy)
assert t.status_code == 200, t.status_code
assert t.json()['tags'] == ['ai', 'cinematic'], t.json()
print(f'I. Messy tag normalization: OK ({t.json()["tags"]})')

# J. Add tags again -> no duplicates
t2 = add_tags(stored, 1, ['AI', 'ai', ' Cinematic '])
assert t2.json()['tags'] == ['ai', 'cinematic']
print('J. Duplicate tags not created: OK')

# K. Remove one tag -> only requested disappears
t3 = add_tags(stored, 1, ['meta'])
assert t3.json()['tags'] == ['ai', 'cinematic', 'meta']
t4 = rm_tags(stored, 1, ['ai'])
assert t4.status_code == 200
assert t4.json()['tags'] == ['cinematic', 'meta']
print('K. Remove one tag: OK (remaining: cinematic, meta)')

# L. Removing a missing tag is harmless
t5 = rm_tags(stored, 1, ['nonexistent'])
assert t5.status_code == 200
assert t5.json()['tags'] == ['cinematic', 'meta']
print('L. Remove missing tag harmless: OK')

# M. Get organization structure
m = org(stored, 1)
assert m.status_code == 200
m_data = m.json()
assert set(m_data.keys()) == {'video_filename', 'version', 'favorite', 'tags'}
assert m_data['video_filename'] == stored
assert m_data['version'] == 1
assert m_data['favorite'] is False
assert m_data['tags'] == ['cinematic', 'meta']
print(f'M. Organization structure: OK ({m_data})')

# N. Exact tag filtering (no substring matching)
add_tags(stored, 1, ['cinematic-pro'])
n_exact = by_tag(stored, 'cinematic')
assert [x['version'] for x in n_exact] == [1], n_exact
n_sub = by_tag(stored, 'cinematic-')
assert n_sub == [], n_sub
n_missing = by_tag(stored, 'cine')
assert n_missing == [], n_missing
rm_tags(stored, 1, ['cinematic-pro'])
assert by_tag(stored, 'cinematic-pro') == []
print('N. Exact tag filter (no substring): OK')

# O. Favorites/tags do NOT modify the original prompt
p1 = client.get(f'/api/videos/{stored}/prompt/history/1').json()
assert p1['prompt'] == v1['prompt']
assert p1['negative_prompt'] == v1['negative_prompt']
print('O. Original prompt unmodified: OK')

# P. Metadata is explicit user-provided only
assert m_data['tags'] == ['cinematic', 'meta'], 'only user-provided tags stored'
assert set(m_data.keys()) == {'video_filename', 'version', 'favorite', 'tags'}
print('P. Explicit user-provided metadata only: OK')

# Q. No video facts fabricated
q_blob = json.dumps({
    'org': m_data,
    'favorites': favorites(stored),
    'tag_list': by_tag(stored, 'cinematic'),
}).lower()
for word in ['person', 'character', 'dialogue', 'walking', 'running',
             'park', 'city', 'sunset', 'brand', 'product', 'voiceover',
             'camera', 'lighting']:
    assert word not in q_blob, f'fabricated: {word}'
print('Q. No fabricated video information: OK')

# R. No absolute filesystem paths
r_blob = json.dumps({
    'org': m_data,
    'favorites': favorites(stored),
    'tag_list': by_tag(stored, 'cinematic'),
    'add': add_tags(stored, 1, ['x']).json(),
})
for bad in ['C:/', 'C:\\', '/home', '/Users', '/var/']:
    assert bad not in r_blob, f'absolute path {bad}'
print('R. No absolute filesystem paths: OK')

# S. Nonexistent version -> 404
s = fav(stored, 99)
assert s.status_code == 404, s.status_code
s2 = org(stored, 99)
assert s2.status_code == 404
s3 = add_tags(stored, 99, ['ai'])
assert s3.status_code == 404
print(f'S. Nonexistent version: OK ({s.status_code})')

# T. Invalid version -> 422
t_0 = fav(stored, 0)
assert t_0.status_code == 422, t_0.status_code
t_abc = client.post(f'/api/videos/{stored}/prompt/history/abc/favorite')
assert t_abc.status_code == 422, t_abc.status_code
print(f'T. Invalid version: OK ({t_0.status_code}/{t_abc.status_code})')

# U. Invalid tag payload -> 422
u_missing = client.post(f'/api/videos/{stored}/prompt/history/1/tags', json={})
assert u_missing.status_code == 422, u_missing.status_code
u_notlist = client.post(
    f'/api/videos/{stored}/prompt/history/1/tags', json={'tags': 'ai'}
)
assert u_notlist.status_code == 422, u_notlist.status_code
u_item = add_tags(stored, 1, ['ai', 42])
assert u_item.status_code == 422, u_item.status_code
print(f'U. Invalid tag payload: OK ({u_missing.status_code}/{u_notlist.status_code}/{u_item.status_code})')

# V. Tag > 50 characters -> 422
v_long = add_tags(stored, 1, ['x' * 51])
assert v_long.status_code == 422, v_long.status_code
print(f'V. Tag > 50 chars: OK ({v_long.status_code})')

# W. Path traversal protection
w1 = client.post('/api/videos/../../../etc/passwd/prompt/history/1/favorite')
assert w1.status_code in (400, 404), w1.status_code
w2 = client.get('/api/videos/../../../etc/passwd/prompt/history/favorites')
assert w2.status_code in (400, 404), w2.status_code
w3 = client.get('/api/videos/../../../etc/passwd/prompt/history/tag/ai')
assert w3.status_code in (400, 404), w3.status_code
print(f'W. Path traversal protected: OK ({w1.status_code}/{w2.status_code}/{w3.status_code})')

# X. Static routes not captured by numeric version route
x1 = client.get(f'/api/videos/{stored}/prompt/history/favorites')
assert x1.status_code == 200 and 'favorites' in x1.json()
assert 'version_id' not in x1.json()
x2 = client.get(f'/api/videos/{stored}/prompt/history/tag/ai')
assert x2.status_code == 200 and 'versions' in x2.json() and 'tag' in x2.json()
x3 = client.get(f'/api/videos/{stored}/prompt/history/1')
assert x3.status_code == 200 and 'version_id' in x3.json()
print('X. Static routes not captured: OK')

# Y. Multi-video isolation
with open(tmp, 'rb') as f:
    up_b = client.post('/api/videos/upload', files={'file': ('test2.mp4', f, 'video/mp4')})
stored_b = up_b.json()['video']['stored_filename']
save(stored_b, 'other prompt text here')
assert fav(stored_b, 1).status_code == 200 and unfav(stored_b, 1).status_code == 200
add_tags(stored_b, 1, ['commercial'])
# Video A: version 1 favorite=false, tags=[cinematic, meta, x]; A v2 + v3 favorited
org_a = org(stored, 1).json()
org_b = org(stored_b, 1).json()
assert org_a['favorite'] is False and org_a['tags'] == ['cinematic', 'meta', 'x']
assert org_b['favorite'] is False and org_b['tags'] == ['commercial']
assert favorites(stored_b) == []
assert [x['version'] for x in favorites(stored)] == [2, 3]
assert [x['version'] for x in by_tag(stored_b, 'commercial')] == [1]
assert by_tag(stored, 'commercial') == []
# Affects only A: favorite A v1 again
fav(stored, 1)
assert org(stored_b, 1).json()['favorite'] is False
unfav(stored, 1)
print('Y. Multi-video isolation: OK')

# Z. Day 16 deletion integration
assert fav(stored, 2).status_code == 200  # already favorited; idempotent
add_tags(stored, 2, ['delete-test'])
del_resp = client.delete(f'/api/videos/{stored}/prompt/history/2')
assert del_resp.status_code == 200, del_resp.status_code
assert org(stored, 2).status_code == 404, 'org for deleted version -> 404'
assert [x['version'] for x in favorites(stored)] == [3], 'deleted absent from favorites'
assert [x['version'] for x in by_tag(stored, 'delete-test')] == [], 'deleted absent from tag results'
assert org(stored, 1).json()['tags'] == ['cinematic', 'meta', 'x'], 'v1 metadata intact'
assert org(stored, 3).json()['favorite'] is True, 'v3 metadata intact'
# Day 16 numbering: versions were 1,2,3 delete 2 -> 1,3; next created -> 4
v4 = save(stored, 'fourth version prompt')
assert v4['version'] == 4, v4['version']
assert org(stored, 4).json() == {
    'video_filename': stored, 'version': 4, 'favorite': False, 'tags': [],
}
print('Z. Deletion integration: OK (v2 gone; v1/v3 intact; next version=4)')

# AA. Determinism
aa1 = add_tags(stored, 4, [' Zeta ', 'ALPHA', 'alpha'])
aa2 = add_tags(stored, 4, ['zeta', 'Alpha'])
assert aa1.json()['tags'] == aa2.json()['tags'] == ['alpha', 'zeta']
f_before = favorites(stored)
f_after = favorites(stored)
assert f_before == f_after
t_before = by_tag(stored, 'cinematic')
t_after = by_tag(stored, '  Cinematic '.strip().lower())
assert t_before == t_after
print('AA. Deterministic behavior: OK')

# Regression: Day 16 history endpoints still work
hist = client.get(f'/api/videos/{stored}/prompt/history')
assert hist.status_code == 200
assert [x['version'] for x in hist.json()['versions']] == [1, 3, 4]
assert client.get(f'/api/videos/{stored}/prompt/history/1').status_code == 200
save(stored, 'comparison prompt')
cmp_r = client.get(f'/api/videos/{stored}/prompt/history/compare/1/5')
assert cmp_r.status_code == 200 and 'added_tokens' in cmp_r.json()
assert client.delete(f'/api/videos/{stored}/prompt/history/5').status_code == 200

# Regression: Day 1-15 endpoints remain intact
assert client.get('/api/health').status_code == 200
assert client.get(f'/api/videos/{stored}/metadata').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt?style=cinematic').status_code == 200
assert client.post(f'/api/videos/{stored}/intelligence').status_code == 200
assert client.post(f'/api/videos/{stored}/advanced-prompt?style=realistic').status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/refine',
                   json={'operation': 'shorten'}).status_code == 200
assert client.post(f'/api/videos/{stored}/prompt/template',
                   json={'template': 'documentary'}).status_code == 200
print('Regression. Day 16 + Day 1-15 endpoints: OK')

if os.path.exists(tmp):
    os.remove(tmp)

print('\nALL DAY 17 MANUAL E2E VERIFICATIONS PASSED')
