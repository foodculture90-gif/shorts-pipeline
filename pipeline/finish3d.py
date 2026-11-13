"""Finishes a 3D short after the render machines are done:
frames -> video, + sound effects & music -> app storage -> "To approve".

  python -m pipeline.finish3d <episode_id> <dir containing frames/ and events.json>
"""
import json
import os
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
    t0 = datetime.now(timezone.utc)   # the render machines are done now: start -> here = the render time
    try:
        ep = db.select("episodes", f"id=eq.{ep_id}&select=id,title,story,channel_id")[0]
        st = ep.get("story") or {}
        ev = json.loads((d / "events.json").read_text())
        fps, total = ev.get("fps", 24), ev["frames"]
        gpu = (d / "gpu.mp4").exists()  # rendered in one go on Kaggle's GPU (full resolution)
        have = {int(p.stem[2:]) for p in (d / "frames").glob("f_*.png")}
        missing = [] if gpu else [g for g in range(1, total + 1) if g not in have]
        if missing:  # a render machine failed: draw its frames here instead of losing the short
            if len(missing) > total * 0.35 or not os.environ.get("BLENDER"):
                raise RuntimeError(f"only {len(have)} of {total} frames were rendered")
            print(f"re-rendering {len(missing)} missing frames", flush=True)
            spec_path = d / "spec.json"
            spec_path.write_text(json.dumps(st["spec"]))
            _run([os.environ["BLENDER"], "-b", "--python", "blender/scene.py", "--", spec_path, d,
                  "list:" + ",".join(map(str, missing))])
        frames = sorted((d / "frames").glob("f_*.png"))
        if not gpu and len(frames) < total:
            raise RuntimeError(f"only {len(frames)} of {total} frames were rendered")
        secs = total / fps
        # Supabase's free storage takes files up to 50 MB: give the video a bitrate ceiling that keeps it under ~44 MB
        vk = max(2500, min(12000, int(44e6 * 8 / secs / 1000) - 260))
        cap = ["-maxrate", f"{vk}k", "-bufsize", f"{vk * 2}k"]
        if gpu:
            _run(["ffmpeg", "-y", "-loglevel", "error", "-i", d / "gpu.mp4", "-c:v", "libx264", "-crf", 17, *cap, "-preset", "slow",
                  "-pix_fmt", "yuv420p", d / "video.mp4"])
        else:
            _run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", fps, "-i", d / "frames/f_%04d.png",
                  "-vf", "scale=1080:1920:flags=lanczos,setsar=1", "-c:v", "libx264", "-crf", 18, *cap, "-preset", "slow",
                  "-tune", "animation", "-pix_fmt", "yuv420p", d / "video.mp4"])
        seed = (st.get("spec") or {}).get("seed", 0)
        _run([sys.executable, "blender/audio.py", d / "events.json", d / "sound.wav", secs, seed])
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", d / "video.mp4", "-i", d / "sound.wav", "-c:v", "copy",
              "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
              "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", d / "final.mp4"])
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", d / "final.mp4", "-vf", "scale=720:1280", "-c:v", "libx264",
              "-crf", 24, "-preset", "medium", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
              d / "preview.mp4"])
        crf = 21
        while (d / "final.mp4").stat().st_size > 47e6 and crf <= 33:   # still too big for storage: squeeze harder
            print(f"final.mp4 is {(d / 'final.mp4').stat().st_size / 1e6:.0f} MB - re-encoding at crf {crf}", flush=True)
            _run(["ffmpeg", "-y", "-loglevel", "error", "-i", d / "final.mp4", "-c:v", "libx264", "-crf", crf, "-preset", "slow",
                  "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", d / "final2.mp4"])
            (d / "final2.mp4").replace(d / "final.mp4")
            crf += 4
        tf = ev.get("thumb") or total // 2
        thumb_src = d / f"frames/f_{tf:04d}.png"
        if gpu and (d / "thumb.png").exists():
            thumb_src = d / "thumb.png"
        elif not thumb_src.exists():
            thumb_src = frames[len(frames) // 2]
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", thumb_src, "-q:v", 3, d / "thumb.jpg"])
        db.upload(d / "final.mp4", f"{base}/final.mp4", "video/mp4")
        db.upload(d / "preview.mp4", f"{base}/preview.mp4", "video/mp4")
        db.upload(d / "thumb.jpg", f"{base}/thumb.jpg", "image/jpeg")
        stats = {"frames": total, "secs": round(secs, 1), "mb": round((d / "final.mp4").stat().st_size / 1e6, 1),
                 "gpu": gpu}
        try:   # how long the render machines took (renderlearn keeps long shorts inside what renders safely)
            start = datetime.fromisoformat(str(st.get("render_at")).replace("Z", "+00:00"))
            stats["part_mins"] = round((t0 - start).total_seconds() / 60, 1)
            stats["mins"] = round((datetime.now(timezone.utc) - start).total_seconds() / 60, 1)
        except (TypeError, ValueError):
            pass
        st["render_stats"] = stats
        db.update("episodes", f"id=eq.{ep_id}", {
            "status": "awaiting_approval", "preview_path": f"{base}/preview.mp4", "thumb_path": f"{base}/thumb.jpg",
            "duration": round(secs, 1), "error": None, "story": st, "updated_at": datetime.now(timezone.utc).isoformat()})
        db.log(f"🎬 Ready: {ep.get('title') or 'new short'}", "success")
        try:  # auto-publish: straight into the next best time slot
            from . import schedule
            if schedule.enabled():
                schedule.book([ep_id])
        except Exception as ex:  # noqa: BLE001  (the worker books it later instead)
            print("auto-publish booking skipped:", ex)
    except Exception as e:
        db.update("episodes", f"id=eq.{ep_id}", {"status": "failed", "error": f"3D render failed: {e}"[:400],
                                                 "updated_at": datetime.now(timezone.utc).isoformat()})
        db.log(f"⚠️ 3D render failed: {e}"[:400], "error")
        raise


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
