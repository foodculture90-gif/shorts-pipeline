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


def run(job: dict, outdir: Path, timeout_min=110, log=print):
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


ACTION_WORDS = {
    "bounce": "bounces up and down happily", "hop": "hops forward", "sway": "sways gently side to side",
    "dance": "dances joyfully, waving its arms", "jump": "jumps up in surprise", "walk": "walks forward",
    "idle": "breathes, blinks and looks around", "nod": "nods and smiles", "wiggle": "wiggles excitedly",
}


def video_prompt(story, shot):
    """Describes the motion for the image-to-video model."""
    act = ACTION_WORDS.get(shot.get("action", ""), "moves naturally")
    return (f"{shot['prompt']} The character {act}, expressive face, natural smooth cartoon animation, "
            f"gentle camera movement. 3D animated preschool TV cartoon, bright colours, high quality.")[:900]


if __name__ == "__main__":
    if sys.argv[1] == "test":
        test(*sys.argv[2:])
