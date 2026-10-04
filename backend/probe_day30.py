"""Temp Day 30 probe - deleted after use."""
import json
import os
import subprocess
import tempfile

import imageio_ffmpeg
from fastapi.testclient import TestClient

from app.main import app
from app.services.prompt_quality_service import PromptQualityService
from app.services.prompt_history_service import PromptHistoryService
from app.services.prompt_organization_service import PromptOrganizationService
from app.services.prompt_readiness_service import PromptReadinessService
from app.services.prompt_readiness_change_service import (
    PromptReadinessChangeService,
)
from app.services.prompt_readiness_timeline_service import (
    PromptReadinessTimelineService,
)
from app.services.prompt_readiness_snapshot_service import (
    PromptReadinessSnapshotService,
)
from app.services.prompt_readiness_report_service import (
    PromptReadinessReportService,
)
from app.services.prompt_readiness_export_service import (
    PromptReadinessExportService,
)

FULL = ("Cinematic film grain style portrait of a person, the subject "
        "walking, looking around and gesturing in an outdoor forest "
        "street, camera tracking with shallow depth of field, soft "
        "lighting with rim light and golden hour glow, vibrant teal and "
        "orange palette with warm tones, layered foreground and rule of "
        "thirds composition, ambient sound with quiet music score.")
CITY = "A person walks through a city street."
MINIMAL = "nothing specific at all"
VIDEO = "sample.mp4"

history = PromptHistoryService()
history.create_version(VIDEO, FULL, source="advanced_prompt",
                       operation="generate")
history.create_version(VIDEO, CITY, source="refinement", operation="expand")
history.create_version(VIDEO, MINIMAL, source="custom", operation="draft")
org = PromptOrganizationService(history)
org.favorite_version(VIDEO, 1)
org.add_tags(VIDEO, 1, ["ai", "cinematic"])

readiness = PromptReadinessService(PromptQualityService())
change = PromptReadinessChangeService(history, readiness)
timeline_svc = PromptReadinessTimelineService(history, change)
snapshot_svc = PromptReadinessSnapshotService(history, readiness, org)
report_svc = PromptReadinessReportService(timeline_svc, snapshot_svc)
export_svc = PromptReadinessExportService(report_svc)

assert export_svc.report_service is report_svc
assert set(vars(export_svc).keys()) == {"report_service"}

# --- service level ---
report = report_svc.generate_report(VIDEO)
j = export_svc.export_report(VIDEO, format="json")
assert set(j.keys()) == {"format", "content", "media_type", "filename"}
assert j["format"] == "json"
assert j["media_type"] == "application/json"
assert j["filename"] == "visionprompt_readiness_report.json"
assert json.loads(j["content"]) == report, "JSON semantically equals report"
assert j["content"] == json.dumps(report, indent=2, ensure_ascii=False) + "\n"
assert j["content"] == export_svc.export_report(
    VIDEO, format="json")["content"], "json deterministic"

m = export_svc.export_report(VIDEO, format="markdown")
assert m["media_type"] == "text/markdown"
assert m["filename"] == "visionprompt_readiness_report.md"
assert m["content"].startswith("# Prompt Readiness Report\n")
for needle in ("## Report", "## Version Readiness", "## Timeline",
               "## Summary", "### Version 1", "### Version 3",
               "#### Required Dimensions", "#### Supporting Dimensions",
               "### Step 1: Version 1 \u2192 Version 2",
               "### Timeline Summary", "### Dimension Summary",
               "### Organization", "| subject |", "prompt_readiness_report",
               VIDEO):
    assert needle in m["content"], needle
assert m["content"] == export_svc.export_report(
    VIDEO, format="markdown")["content"], "markdown deterministic"

t = export_svc.export_report(VIDEO, format="txt")
assert t["media_type"] == "text/plain"
assert t["filename"] == "visionprompt_readiness_report.txt"
assert t["content"].startswith("PROMPT READINESS REPORT\n")
for needle in ("REPORT\n------", "VERSION READINESS\n---------",
               "TIMELINE\n--------", "SUMMARY\n-------",
               "VERSION 1", "REQUIRED DIMENSIONS", "SUPPORTING DIMENSIONS",
               "Step 1: Version 1 -> Version 2", "STEP DIMENSIONS",
               "TRANSITION SUMMARY", "TIMELINE SUMMARY", "DIMENSION SUMMARY",
               "ORGANIZATION", "subject: present (100)", VIDEO):
    assert needle in t["content"], needle
assert t["content"] == export_svc.export_report(
    VIDEO, format="txt")["content"], "txt deterministic"

# every JSON leaf value appears in markdown + txt
def leaves(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from leaves(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from leaves(v)
    else:
        yield obj

def fmt(v):
    if v is None:
        return "none"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)

for leaf in leaves(report):
    s = fmt(leaf)
    assert s in m["content"], ("md missing", s)
    assert s in t["content"], ("txt missing", s)

# no prompt text / ranking words
assert FULL not in m["content"] and FULL not in t["content"]
for word in ("best", "worst", "winner", "loser", "superior", "inferior",
             "better", "worse", "improved", "degraded", "recommended",
             "preferred", "optimal"):
    assert word not in m["content"].lower(), word
    assert word not in t["content"].lower(), word

# selection + reverse
sub = export_svc.export_report(VIDEO, [3, 1], format="json")
assert json.loads(sub["content"])["versions_analyzed"] == [3, 1]
assert sub["content"] == json.dumps(report_svc.generate_report(
    VIDEO, [3, 1]), indent=2, ensure_ascii=False) + "\n"

# single version
single = export_svc.export_report(VIDEO, [2], format="markdown")
assert single["content"].count("### Version ") == 1
assert "No timeline steps." in single["content"]
assert json.loads(export_svc.export_report(
    VIDEO, [2], format="json")["content"])["timeline"][
        "required_coverage_delta"] == 0

# empty history (video "none.mp4" has no saved versions anywhere)
empty_j = export_svc.export_report("none.mp4", format="json")
empty_report = json.loads(empty_j["content"])
assert empty_report["versions_analyzed"] == []
assert empty_report["timeline"]["required_coverage_delta"] is None
empty_m = export_svc.export_report("none.mp4", format="markdown")
assert "No saved versions." in empty_m["content"]
assert "No timeline steps." in empty_m["content"]
empty_t = export_svc.export_report("none.mp4", format="txt")
assert "No saved versions." in empty_t["content"]

# validation
for bad in ("json ", "xml", "", None, 123, "JSON"):
    try:
        export_svc.export_report(VIDEO, format=bad)
        raise AssertionError(f"expected ValueError for {bad!r}")
    except ValueError as e:
        assert "Invalid format. Must be one of: json, markdown, txt" == str(e)

for bad_versions in ([0], [-1], [1, 1], ["1"], []):
    try:
        export_svc.export_report(VIDEO, bad_versions, format="json")
        raise AssertionError(f"expected ValueError for {bad_versions!r}")
    except ValueError:
        pass
try:
    export_svc.export_report(VIDEO, [99], format="json")
    raise AssertionError("expected ValueError for missing version")
except ValueError as e:
    assert "99" in str(e)

print("SERVICE LEVEL OK")

# --- route level ---
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
tmp = os.path.join(tempfile.gettempdir(), "day30_probe.mp4")
subprocess.run(
    [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=160x120:d=2",
     "-c:v", "libx264", "-y", tmp],
    capture_output=True, timeout=30,
)
client = TestClient(app)
with open(tmp, "rb") as f:
    up = client.post("/api/videos/upload",
                     files={"file": ("probe.mp4", f, "video/mp4")})
assert up.status_code == 200, up.text
stored = up.json()["video"]["stored_filename"]
for i, (p, s, o) in enumerate([(FULL, "advanced_prompt", "generate"),
                               (CITY, "refinement", "expand"),
                               (MINIMAL, "custom", "draft")], start=1):
    r = client.post(f"/api/videos/{stored}/prompt/history",
                    json={"prompt": p, "negative_prompt": "", "source": s,
                          "operation": o})
    assert r.status_code == 200, r.text

base = f"/api/videos/{stored}/prompt/history/readiness/report"
rj = client.get(base + "/export", params={"format": "json"})
assert rj.status_code == 200, (rj.status_code, rj.text)
assert rj.headers["content-type"].startswith("application/json")
assert rj.headers["content-disposition"] == \
    'attachment; filename="visionprompt_readiness_report.json"'
direct = client.get(base).json()
assert json.loads(rj.content) == direct, "export == report endpoint"
assert rj.content == client.get(base + "/export",
                                params={"format": "json"}).content, \
    "byte-identical repeat"

rm = client.get(base + "/export", params={"format": "markdown"})
assert rm.status_code == 200
assert rm.headers["content-type"].startswith("text/markdown")
assert rm.headers["content-disposition"] == \
    'attachment; filename="visionprompt_readiness_report.md"'
assert rm.text == client.get(base + "/export",
                             params={"format": "markdown"}).text

rt = client.get(base + "/export", params={"format": "txt"})
assert rt.status_code == 200
assert rt.headers["content-type"].startswith("text/plain")
assert rt.headers["content-disposition"] == \
    'attachment; filename="visionprompt_readiness_report.txt"'

# selected / repeated / whitespace
rs = client.get(base + "/export", params={"format": "json",
                                          "versions": "3,1"})
assert rs.status_code == 200
assert json.loads(rs.content)["versions_analyzed"] == [3, 1]
rr = client.get(base + "/export", params=[("format", "json"),
                                          ("versions", "1"),
                                          ("versions", "3")])
assert rr.status_code == 200
assert json.loads(rr.content)["versions_analyzed"] == [1, 3]
rw = client.get(base + "/export", params={"format": "json",
                                          "versions": "1 , 3"})
assert rw.status_code == 200
assert json.loads(rw.content)["versions_analyzed"] == [1, 3]
assert rw.content == rr.content, "whitespace == repeated result"

# validation
for bad in ("xml", "", "JSON", "Json"):
    rb = client.get(base + "/export", params={"format": bad})
    assert rb.status_code == 422, (bad, rb.status_code)
for bad in ("", "0", "-1", "abc", "1,,2", "1,1", "1.5", ",", " "):
    rb = client.get(base + "/export", params={"format": "json",
                                              "versions": bad})
    assert rb.status_code == 422, (bad, rb.status_code)
rb = client.get(base + "/export", params={"format": "json",
                                          "versions": "1,99"})
assert rb.status_code == 404, rb.status_code
rb = client.get(base + "/export")
assert rb.status_code == 422, "missing format -> 422"

# nonexistent / traversal / bad extension
rn = client.get("/api/videos/missing.mp4/prompt/history/readiness/"
                "report/export", params={"format": "json"})
assert rn.status_code == 404
rtv = client.get("/api/videos/../../../etc/passwd/prompt/history/"
                 "readiness/report/export", params={"format": "json"})
assert rtv.status_code == 404
rx = client.get("/api/videos/clip.txt/prompt/history/readiness/"
                "report/export", params={"format": "json"})
assert rx.status_code == 400

# empty history video
with open(tmp, "rb") as f:
    up2 = client.post("/api/videos/upload",
                      files={"file": ("probe2.mp4", f, "video/mp4")})
stored2 = up2.json()["video"]["stored_filename"]
re_ = client.get(f"/api/videos/{stored2}/prompt/history/readiness/"
                 f"report/export", params={"format": "json"})
assert re_.status_code == 200
assert json.loads(re_.content)["versions_analyzed"] == []
rm2 = client.get(f"/api/videos/{stored2}/prompt/history/readiness/"
                 f"report/export", params={"format": "markdown"})
assert "No saved versions." in rm2.text

# route collision: numeric history route untouched
rv = client.get(f"/api/videos/{stored}/prompt/history/1")
assert rv.status_code == 200 and "prompt" in rv.json()
r29 = client.get(base)
assert r29.status_code == 200 and set(r29.json().keys()) == {
    "video_filename", "versions_analyzed", "report", "timeline", "summary"}
rd19 = client.get(f"/api/videos/{stored}/prompt/history/1/export",
                  params={"format": "json"})
assert rd19.status_code == 200

# read-only: history listing unchanged after exports
listing = [x["version"] for x in client.get(
    f"/api/videos/{stored}/prompt/history").json()["versions"]]
for fmt in ("json", "markdown", "txt"):
    client.get(base + "/export", params={"format": fmt})
assert [x["version"] for x in client.get(
    f"/api/videos/{stored}/prompt/history").json()["versions"]] == listing

# no storage files created by export
uploads = os.listdir(os.path.join("storage", "uploads"))
assert not any(name.startswith("visionprompt") for name in uploads), uploads

os.remove(tmp)
print("ROUTE LEVEL OK")
print("DAY 30 PROBE VERIFIED")
