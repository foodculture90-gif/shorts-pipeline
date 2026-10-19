"""Renders a 3D short on Kaggle's free GPU (full 1080x1920, more light bounces, motion blur).

  python -m pipeline.kaggle_render <episode_id> <outdir>
Exit code 0 = outdir has gpu.mp4 + events.json + thumb.png; anything else = use the free CPU machines instead.
Needs KAGGLE_KEY (same secret as the picture animation).
"""
import json
import os
import sys
from pathlib import Path

from . import db
from .kaggle_video import ROOT, KaggleBusy, run

SCRIPT = ROOT / "kaggle" / "render_job.py"


def main(ep_id, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    ep = db.select("episodes", f"id=eq.{ep_id}&select=title,story")[0]
    job = {"spec": ep["story"]["spec"], "repo": os.environ.get("GITHUB_REPOSITORY", "foodculture90-gif/shorts-pipeline"),
           "sha": os.environ.get("GITHUB_SHA", "main"), "samples": int(os.environ.get("GPU_SAMPLES", "48"))}
    print("GPU render:", ep.get("title"), flush=True)
    try:
        logs, res, status = run(job, out, timeout_min=200, max_queue_min=20, script=SCRIPT,
                                slug=f"mc-render-{ep_id[:8]}")
    except KaggleBusy as e:
        print("kaggle busy:", e)
        return 2
    print("===== kaggle log (end) =====")
    print(logs[-6000:])
    print("===== result:", status, res)
    ok = res.get("done") and (out / "gpu.mp4").exists() and (out / "events.json").exists()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
