"""Render slots: GitHub's free plan has 20 machines. Instead of starting every short at once (each one then
waits hours in one big queue), shorts render one after another, each getting 18 machines (~12 min).
The next short starts as soon as the previous one's frames are done.

    python -m pipeline.slots <finished_episode_id>   # called by the render workflow
"""
import os
import sys
from datetime import datetime, timedelta, timezone

from . import db

GH_REPO = os.environ.get("GITHUB_REPOSITORY", "foodculture90-gif/shorts-pipeline")
CPU_SLOTS = 1


def now():
    return datetime.now(timezone.utc)


def dispatch(ep_id, gpu=False):
    import requests
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not tok:
        raise RuntimeError("GH_TOKEN missing - can't start the 3D render")
    r = requests.post(f"https://api.github.com/repos/{GH_REPO}/actions/workflows/render3d.yml/dispatches",
                      headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"},
                      json={"ref": "main", "inputs": {"episode_id": ep_id, "gpu": "yes" if gpu else "no"}}, timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"could not start the 3D render: {r.status_code} {r.text[:200]}")


def kick(done=None):
    """Start waiting shorts while a CPU slot is free. `done` = a short whose frames just finished."""
    stuck = (now() - timedelta(hours=3)).isoformat()   # a render that never came back -> failed (retried once)
    for r in db.select("episodes", f"select=id&status=eq.generating&story->>render=eq.cpu&updated_at=lt.{stuck}"):
        db.update("episodes", f"id=eq.{r['id']}&status=eq.generating",
                  {"status": "failed", "error": "3D render stopped (took too long)", "updated_at": now().isoformat()})
    since = (now() - timedelta(hours=2)).isoformat()
    busy = [r for r in db.select("episodes", f"select=id&status=eq.generating&story->>render=eq.cpu&updated_at=gt.{since}")
            if r["id"] != done]
    free = CPU_SLOTS - len(busy)
    if free <= 0:
        return 0
    started = 0
    for e in db.select("episodes", "select=id,title,story&status=eq.generating&story->>render=eq.wait"
                                   f"&order=created_at.asc&limit={free}"):
        st = e.get("story") or {}
        st["render"] = "cpu"
        if not db.update("episodes", f"id=eq.{e['id']}&story->>render=eq.wait", {"story": st, "updated_at": now().isoformat()}):
            continue  # someone else started it
        try:
            dispatch(e["id"])
            started += 1
            print("started render:", e.get("title"))
        except Exception as ex:  # noqa: BLE001
            db.update("episodes", f"id=eq.{e['id']}", {"status": "failed", "error": f"3D render failed: {ex}"[:400]})
    return started


if __name__ == "__main__":
    try:
        kick(sys.argv[1] if len(sys.argv) > 1 else None)
    except Exception as ex:  # noqa: BLE001  never break the render because of this
        print("could not start the next short:", ex)
