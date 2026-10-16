"""Sends pictures to Kaggle's free GPU, which turns them into moving clips (image-to-video AI).

Needs GitHub secrets KAGGLE_KEY (+ username in KAGGLE_USERNAME, default storytimeeditor).
Usage (test):  python -m pipeline.kaggle_video test '<json list of {image, prompt}>'
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "kaggle" / "animate_job.py"
SLUG = "mc-animate"


def _env():
    os.environ.setdefault("KAGGLE_USERNAME", "storytimeeditor")
    key = os.environ.get("KAGGLE_KEY", "")
    if key.startswith("KGAT_"):  # new-style token
        os.environ.setdefault("KAGGLE_API_TOKEN", key)
    return os.environ["KAGGLE_USERNAME"]


def _kaggle(*args, check=True):
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if check and r.returncode:
        raise RuntimeError(f"kaggle {' '.join(args[:2])} failed: {out[-600:]}")
    return out


def run(job: dict, outdir: Path, timeout_min=170, log=print):
    """Pushes the job, waits for it, downloads clips into outdir. Returns (log_text, result)."""
    user = _env()
    work = outdir / "_kernel"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    code = SCRIPT.read_text().replace("JOB = {}", "JOB = __import__('json').loads(" + repr(json.dumps(job)) + ")", 1)
    (work / "animate_job.py").write_text(code)
    (work / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{user}/{SLUG}", "title": SLUG, "code_file": "animate_job.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "dataset_sources": [], "competition_sources": [], "kernel_sources": []}))
    log("  pushing job to Kaggle GPU…")
    log("  " + _kaggle("kernels", "push", "-p", str(work)).splitlines()[-1])
    t0, status = time.time(), ""
    while time.time() - t0 < timeout_min * 60:
        time.sleep(30)
        out = _kaggle("kernels", "status", f"{user}/{SLUG}", check=False)
        st = out.split('"')[-2] if '"' in out else out
        if st != status:
            log(f"  kaggle: {st} ({time.time() - t0:.0f}s)")
            status = st
        if any(x in st.lower() for x in ("complete", "error", "cancel")):
            break
    outdir.mkdir(parents=True, exist_ok=True)
    _kaggle("kernels", "output", f"{user}/{SLUG}", "-p", str(outdir), "--force", check=False)
    logs = ""
    for f in outdir.glob("*.log"):
        try:
            logs += "".join(e.get("data", "") for e in json.loads(f.read_text()))
        except Exception:  # noqa: BLE001
            logs += f.read_text(errors="ignore")
    res = {}
    if (outdir / "result.json").exists():
        res = json.loads((outdir / "result.json").read_text())
    return logs, res, status


def test(title_prefix, count="3"):
    """Animates the first pictures of an existing short (found by title) and uploads the clips."""
    from . import db
    ep = db.select("episodes", f"select=title,assets_path,story&title=like.{title_prefix}*&limit=1")[0]
    st = ep["story"]
    shots = []
    for i, sc in enumerate(st["scenes"]):
        for k, sh in enumerate(sc["shots"]):
            if len(shots) >= int(count):
                break
            shots.append({"image": db.signed_url(f"{ep['assets_path']}/s{i + 1}_{k + 1}.jpg"),
                          "prompt": video_prompt(st, sh), "name": f"s{i + 1}_{k + 1}", "seed": 7 + len(shots)})
    job = {"shots": shots, "list_models": True}
    job.update(json.loads(os.environ.get("JOB_EXTRA", "") or "{}"))
    print("testing on", ep["title"], "with", len(shots), "shots", {k: v for k, v in job.items() if k != "shots"})
    out = ROOT / "output" / "kaggle-test"
    logs, res, status = run(job, out)
    print("===== kaggle log =====")
    print(logs[-15000:])
    print("===== result:", status, res)
    stamp = time.strftime("%H%M%S")
    for f in sorted(out.glob("*.mp4")):
        db.upload(f, f"tests/{stamp}-{f.name}", "video/mp4")
        print("uploaded", f"tests/{stamp}-{f.name}")


DEFAULTS = {"guidance": 3.0, "steps": 30, "frames": 73, "end_strength": 0.0}  # g3 = lively motion


def animate_batch(episodes, workdir: Path, log=print):
    """episodes: [(ep_id, story, assets_path)]. One Kaggle run for all of them.
    Returns {ep_id: {"c1_1.mp4": Path, ...}} for the clips that came back."""
    from . import db
    shots = []
    for ep_id, st, assets in episodes:
        for i, sc in enumerate(st["scenes"]):
            for k, sh in enumerate(sc["shots"]):
                shots.append({"image": db.signed_url(f"{assets}/s{i + 1}_{k + 1}.jpg"),
                              "prompt": video_prompt(st, sh), "name": f"{ep_id[:8]}__c{i + 1}_{k + 1}",
                              "seed": int(st.get("seed", 1)) + len(shots)})
    job = dict(DEFAULTS, shots=shots)
    job.update(json.loads(os.environ.get("KAGGLE_JOB_EXTRA", "") or "{}"))
    out = workdir / "kaggle-out"
    shutil.rmtree(out, ignore_errors=True)
    log(f"  animating {len(shots)} shots for {len(episodes)} shorts on Kaggle")
    logs, res, status = run(job, out, log=log)
    log(f"  kaggle {status}: {res}")
    if not res.get("done"):
        log(logs[-3000:])
    clips = {}
    for ep_id, _, _ in episodes:
        got = {f.name.split("__", 1)[1]: f for f in out.glob(f"{ep_id[:8]}__c*.mp4") if f.stat().st_size > 1000}
        clips[ep_id] = got
    return clips


ACTION_WORDS = {
    "bounce": "bounces up and down happily", "hop": "hops forward", "sway": "sways gently side to side",
    "dance": "dances joyfully, waving its arms", "jump": "jumps up in surprise", "walk": "walks forward",
    "idle": "breathes, blinks and looks around", "nod": "nods and smiles", "wiggle": "wiggles excitedly",
}


def video_prompt(story, shot):
    """Describes the motion for the image-to-video model."""
    act = shot.get("motion") or "The character " + ACTION_WORDS.get(shot.get("action", ""), "moves naturally")
    return (f"{shot['prompt']} {act.rstrip('.')}, lively expressive cartoon acting, big clear movement, staying in the frame, "
            f"keeping exactly the same look, expressive face, smooth cartoon animation, steady camera. "
            f"3D animated preschool TV cartoon, bright colours, high quality.")[:900]


if __name__ == "__main__":
    if sys.argv[1] == "test":
        test(*sys.argv[2:])
