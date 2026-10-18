"""Finishes a 3D short after the render machines are done:
frames -> video, + sound effects & music -> app storage -> "To approve".

  python -m pipeline.finish3d <episode_id> <dir containing frames/ and events.json>
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import db


def _run(cmd):
    print("$", " ".join(str(c) for c in cmd)[:300], flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def main(ep_id, d):
    d = Path(d)
    base = f"episodes/{ep_id}"
    try:
        ep = db.select("episodes", f"id=eq.{ep_id}&select=id,title,story,channel_id")[0]
        st = ep.get("story") or {}
        ev = json.loads((d / "events.json").read_text())
        fps, total = ev.get("fps", 24), ev["frames"]
        frames = sorted((d / "frames").glob("f_*.png"))
        if len(frames) < total:
            raise RuntimeError(f"only {len(frames)} of {total} frames were rendered")
        secs = total / fps
        _run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", fps, "-i", d / "frames/f_%04d.png",
              "-c:v", "libx264", "-crf", 18, "-preset", "slow", "-pix_fmt", "yuv420p", d / "video.mp4"])
        seed = (st.get("spec") or {}).get("seed", 0)
        _run([sys.executable, "blender/audio.py", d / "events.json", d / "sound.wav", secs, seed])
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", d / "video.mp4", "-i", d / "sound.wav", "-c:v", "copy",
              "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
              "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", d / "final.mp4"])
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", d / "final.mp4", "-vf", "scale=720:1280", "-c:v", "libx264",
              "-crf", 24, "-preset", "medium", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
              d / "preview.mp4"])
        tf = ev.get("thumb") or total // 2
        thumb_src = d / f"frames/f_{tf:04d}.png"
        if not thumb_src.exists():
            thumb_src = frames[len(frames) // 2]
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", thumb_src, "-q:v", 3, d / "thumb.jpg"])
        db.upload(d / "final.mp4", f"{base}/final.mp4", "video/mp4")
        db.upload(d / "preview.mp4", f"{base}/preview.mp4", "video/mp4")
        db.upload(d / "thumb.jpg", f"{base}/thumb.jpg", "image/jpeg")
        db.update("episodes", f"id=eq.{ep_id}", {
            "status": "awaiting_approval", "preview_path": f"{base}/preview.mp4", "thumb_path": f"{base}/thumb.jpg",
            "duration": round(secs, 1), "error": None, "updated_at": datetime.now(timezone.utc).isoformat()})
        db.log(f"🎬 Ready: {ep.get('title') or 'new short'}", "success")
    except Exception as e:
        db.update("episodes", f"id=eq.{ep_id}", {"status": "failed", "error": f"3D render failed: {e}"[:400],
                                                 "updated_at": datetime.now(timezone.utc).isoformat()})
        db.log(f"⚠️ 3D render failed: {e}"[:400], "error")
        raise


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
