"""Phase 2 manual E2E verification (P2-01 .. P2-13).

Progressive script: each Phase 2 feature appends its section here.
Run from the backend directory:  python phase2_e2e.py
"""
import json
import os
import shutil
import subprocess
import tempfile

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)
BASE = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE, "storage", "uploads")
FRAME_DIR = os.path.join(BASE, "storage", "frames")
TMP_VIDEO = os.path.join(tempfile.gettempdir(), "phase2_e2e.mp4")
UPLOADED = []
PASSED = []


def ok(label, condition=True, detail=""):
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    print(f"  {label}: OK")


def make_video(path=TMP_VIDEO):
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-f", "lavfi", "-i", "color=c=navy:s=320x240:d=3",
         "-y", path],
        capture_output=True, timeout=15,
    )
    assert os.path.exists(path) and os.path.getsize(path) > 0
    return path


def upload(path=TMP_VIDEO, extract=True):
    with open(path, "rb") as f:
        r = client.post("/api/videos/upload",
                        files={"file": ("test.mp4", f, "video/mp4")})
    assert r.status_code == 200, r.text
    stored = r.json()["video"]["stored_filename"]
    UPLOADED.append(stored)
    if extract:
        r = client.post(f"/api/videos/{stored}/frames/extract"
                        f"?interval_seconds=1")
        assert r.status_code == 200, r.text
    return stored


def walk_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(k)
            yield from walk_strings(v)
    elif isinstance(node, list):
        for item in node:
            yield from walk_strings(item)


def cleanup():
    for stored in UPLOADED:
        p = os.path.join(UPLOADS_DIR, stored)
        if os.path.exists(p):
            os.remove(p)
    UPLOADED.clear()
    if os.path.exists(TMP_VIDEO):
        os.remove(TMP_VIDEO)
    if os.path.exists(FRAME_DIR):
        for d in os.listdir(FRAME_DIR):
            full = os.path.join(FRAME_DIR, d)
            if os.path.isdir(full):
                shutil.rmtree(full, ignore_errors=True)


ANALYSIS_DOMAINS = [
    "shots", "subjects", "actions", "environment", "camera", "lens",
    "lighting", "color", "composition", "visual_style", "audio",
    "characters",
]


def mvp_regression():
    """Core MVP (Day 1-30) endpoints keep working."""
    print("MVP regression (Day 1-30):")
    stored = upload()
    ok("health", client.get("/api/health").status_code == 200)
    ok("metadata",
       client.get(f"/api/videos/{stored}/metadata").status_code == 200)
    ok("intelligence",
       client.post(f"/api/videos/{stored}/intelligence").status_code == 200)
    ok("advanced-prompt",
       client.post(f"/api/videos/{stored}/advanced-prompt").status_code == 200)
    ok("scenes/detect",
       client.post(f"/api/videos/{stored}/scenes/detect").status_code == 200)
    ok("subjects/analyze",
       client.post(f"/api/videos/{stored}/subjects/analyze").status_code == 200)
    ok("audio/analyze",
       client.post(f"/api/videos/{stored}/audio/analyze").status_code == 200)
    ok("prompt/quality", client.post(
        f"/api/videos/{stored}/prompt/quality",
        json={"prompt": "A person walks through a city street at noon."}
    ).status_code == 200)
    ok("prompt/readiness", client.post(
        f"/api/videos/{stored}/prompt/readiness",
        json={"prompt": "A person walks through a city street at noon."}
    ).status_code == 200)
    hist = client.post(
        f"/api/videos/{stored}/prompt/history",
        json={"prompt": "A person walks through a city street at noon.",
              "negative_prompt": "", "source": "custom", "operation": ""},
    )
    ok("history POST", hist.status_code == 200)
    listing = client.get(f"/api/videos/{stored}/prompt/history")
    ok("history GET", listing.status_code == 200
       and len(listing.json()["versions"]) == 1)
    ok("readiness report", client.get(
        f"/api/videos/{stored}/prompt/history/readiness/report"
    ).status_code == 200)
    ok("readiness report export", client.get(
        f"/api/videos/{stored}/prompt/history/readiness/report/export",
        params={"format": "json"},
    ).status_code == 200)
    ok("favorites", client.get(
        f"/api/videos/{stored}/prompt/history/favorites"
    ).status_code == 200)
    ok("export", client.get(
        f"/api/videos/{stored}/prompt/history/1/export",
        params={"format": "markdown"},
    ).status_code == 200)
    PASSED.append("MVP")


# ==================== P2-01 Video-to-Video Prompt Reconstruction ==========
def p2_01():
    print("P2-01 reconstruction:")
    stored = upload()

    r = client.post(f"/api/videos/{stored}/prompt/reconstruct")
    ok("default request", r.status_code == 200, r.text)
    data = r.json()
    ok("success envelope",
       data["success"] is True
       and data["message"] == "Prompt reconstruction completed successfully")
    ok("identity", data["video_filename"] == stored
       and data["depth"] == "standard" and data["style"] == "cinematic")

    ok("video_information observed",
       data["video_information"]["availability"] == "observed"
       and data["video_information"]["value"]["duration_seconds"] > 0)
    ok("analysis domains", list(data["analysis"].keys()) == ANALYSIS_DOMAINS)
    for domain in ANALYSIS_DOMAINS:
        block = data["analysis"][domain]
        ok(f"block shape [{domain}]",
           list(block.keys())
           == ["availability", "source", "value", "confidence", "note"]
           and block["availability"] in {"observed", "estimated",
                                         "unavailable"})
    conf = data["confidence"]
    combined = (conf["observed_domains"] + conf["estimated_domains"]
                + conf["unavailable_domains"])
    ok("confidence partition",
       sorted(combined) == sorted(ANALYSIS_DOMAINS)
       and len(combined) == len(set(combined))
       and conf["overall"] in {"high", "medium", "low"})
    ok("prompt block",
       data["prompt"]["production_prompt"].strip()
       and data["prompt"]["negative_prompt"].strip()
       and len(data["prompt"]["sections"]) == 9)
    ok("quality block", 0 <= data["quality"]["overall_score"] <= 100)
    ok("readiness block",
       data["readiness"]["status"] in {"ready", "needs_attention"}
       and len(data["readiness"]["checklist"]) == 9)

    if settings.vision_provider == "mock":
        ok("honest unavailable domains",
           all(data["analysis"][d]["availability"] == "unavailable"
               and data["analysis"][d]["note"].strip()
               for d in ("environment", "lighting", "visual_style",
                         "camera")))
        ok("mock provider note",
           "local mock" in data["provider_status"]["note"])
    ok("shots observed from frames",
       data["analysis"]["shots"]["availability"] == "observed"
       and data["analysis"]["shots"]["value"]["scenes_detected"] >= 1)
    ok("optional domains unavailable",
       data["analysis"]["lens"]["availability"] == "unavailable"
       and data["analysis"]["characters"]["availability"] == "unavailable")

    for depth in ("quick", "standard", "deep"):
        rr = client.post(f"/api/videos/{stored}/prompt/reconstruct",
                         params={"depth": depth})
        ok(f"depth={depth}", rr.status_code == 200
           and rr.json()["depth"] == depth)
    bad = client.post(f"/api/videos/{stored}/prompt/reconstruct",
                      params={"depth": "turbo"})
    ok("invalid depth 400", bad.status_code == 400
       and bad.json()["detail"]
       == "Invalid depth. Must be one of: deep, quick, standard")
    bad = client.post(f"/api/videos/{stored}/prompt/reconstruct",
                      params={"style": "gritty"})
    ok("invalid style 400", bad.status_code == 400
       and bad.json()["detail"]
       == "Invalid style. Must be one of: cinematic, commercial, realistic")
    ok("invalid filename 400",
       client.post("/api/videos/notavideo/prompt/reconstruct"
                   ).status_code == 400)
    ok("missing video 404",
       client.post("/api/videos/ghost_xyz.mp4/prompt/reconstruct"
                   ).status_code == 404)
    ok("traversal 404",
       client.post("/api/videos/../../../etc/passwd.mp4"
                   "/prompt/reconstruct").status_code == 404)

    ok("style realistic", client.post(
        f"/api/videos/{stored}/prompt/reconstruct",
        params={"style": "realistic"}).json()["prompt"][
            "production_prompt"].find("realistic presentation") >= 0)
    ok("style commercial", client.post(
        f"/api/videos/{stored}/prompt/reconstruct",
        params={"style": "commercial"}).json()["prompt"][
            "production_prompt"].find("commercial presentation") >= 0)

    first = client.post(
        f"/api/videos/{stored}/prompt/reconstruct").json()
    second = client.post(
        f"/api/videos/{stored}/prompt/reconstruct").json()
    ok("deterministic",
       json.dumps(first, sort_keys=True) == json.dumps(second,
                                                       sort_keys=True))
    leaks = []
    for text in walk_strings(first):
        for bad_s in ("C:\\", "C:/", "/home", "/Users", "storage/uploads",
                      "storage/frames", "test_assets", "app.services",
                      "Traceback"):
            if bad_s in text:
                leaks.append(bad_s)
    ok("no path/internal leaks", not leaks, str(leaks))

    history_before = client.get(
        f"/api/videos/{stored}/prompt/history").json()
    uploads_before = sorted(os.listdir(UPLOADS_DIR))
    frames_before = sorted(os.listdir(FRAME_DIR))
    client.post(f"/api/videos/{stored}/prompt/reconstruct")
    ok("read-only (history)",
       client.get(f"/api/videos/{stored}/prompt/history").json()
       == history_before)
    ok("read-only (storage)",
       sorted(os.listdir(UPLOADS_DIR)) == uploads_before
       and sorted(os.listdir(FRAME_DIR)) == frames_before)

    other = upload()
    data_other = client.post(
        f"/api/videos/{other}/prompt/reconstruct").json()
    ok("multi-video isolation",
       data_other["video_filename"] == other
       and data_other["video_filename"] != stored)
    PASSED.append("P2-01")


def main():
    make_video()
    try:
        mvp_regression()
        p2_01()
        print(f"PHASE 2 E2E PROGRESS — sections passed: "
              f"{', '.join(PASSED)}")
        print("ALL PHASE 2 E2E VERIFICATIONS PASSED SO FAR")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
