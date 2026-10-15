"""Cloud worker: does what you asked for in the app. Several run in parallel.

    python -m pipeline.worker queue   # process queued commands (started instantly by the app)
    python -m pipeline.worker daily   # queue each channel's daily shorts + a stats refresh
"""
import json
import shutil
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, db, notify, render
from .generate import ASSET_FILES, make_assets
from .images import QuotaExceeded

WORK = config.OUTPUT
CAPACITY = config.DAILY_NEURONS // config.NEURONS_PER_IMAGE        # pictures per day (free)
PICS = config.SCENES * config.SHOTS_PER_SCENE                        # pictures per short


class Wait(Exception):
    def __init__(self, until, note):
        super().__init__(note)
        self.until, self.note = until, note


def now():
    return datetime.now(timezone.utc)


def tomorrow_utc():
    return (now() + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)


def _set(ep_id, **values):
    values["updated_at"] = now().isoformat()
    db.update("episodes", f"id=eq.{ep_id}", values)


def _episode(ep_id):
    rows = db.select("episodes", f"id=eq.{ep_id}&select=*")
    if not rows:
        raise ValueError("short not found")
    return rows[0]


def _channel(ch_id):
    rows = db.select("channels", f"id=eq.{ch_id}&select=*")
    if not rows:
        raise ValueError("channel not found")
    return rows[0]


def _token(ch_id):
    rows = db.select("channel_tokens", f"channel_id=eq.{ch_id}&select=refresh_token")
    if not rows:
        raise ValueError("this channel isn't connected to YouTube yet (app → Channels → Connect)")
    return rows[0]["refresh_token"]


def _remove_files(ep, keep_thumb=False):
    paths = []
    if ep.get("assets_path"):
        paths += [f"{ep['assets_path']}/{f}" for f in ASSET_FILES]
    if ep.get("preview_path"):
        paths.append(ep["preview_path"])
    if ep.get("thumb_path") and not keep_thumb:
        paths.append(ep["thumb_path"])
    db.remove(paths)


# ---- commands ------------------------------------------------------------------------
def cmd_generate(payload, cmd):
    ch = _channel(payload["channel_id"])
    ep_id = payload.get("episode_id")
    if not ep_id:
        ep_id = db.insert("episodes", {"channel_id": ch["id"], "status": "queued", "idea": payload.get("idea"),
                                       "feedback": payload.get("feedback"), "parent_id": payload.get("parent_id")})["id"]
        payload["episode_id"] = ep_id
        db.update("commands", f"id=eq.{cmd['id']}", {"payload": payload})
    if not db.rpc("reserve_images", n=PICS, cap=CAPACITY):
        _set(ep_id, status="queued", error=None)
        raise Wait(tomorrow_utc(), "Today's free pictures are used up — continues after midnight UTC")
    _set(ep_id, status="generating", error=None)
    work = WORK / ep_id
    try:
        previous = None
        if payload.get("parent_id"):
            previous = _episode(payload["parent_id"]).get("story")
        past = [r["title"] for r in db.select(
            "episodes", f"select=title&channel_id=eq.{ch['id']}&title=not.is.null&order=created_at.desc&limit=60")]
        st = make_assets(work, ch, past_titles=past, idea=payload.get("idea"), feedback=payload.get("feedback"),
                         previous=previous, log=lambda m: print("  ·", m))
        preview = render.render(work, st, work / "preview", config.PREVIEW_SIZE,
                                music_volume=float(db.settings().get("music_volume") or 0.12))
        thumb = render.thumbnail(work / "s1_1.jpg", st["title"], work / "thumb.jpg")
        base = f"episodes/{ep_id}"
        for f in ASSET_FILES:
            db.upload(work / f, f"{base}/assets/{f}",
                      "application/json" if f.endswith(".json") else "image/jpeg" if f.endswith(".jpg") else "audio/mpeg")
        db.upload(preview, f"{base}/preview.mp4", "video/mp4")
        db.upload(thumb, f"{base}/thumb.jpg", "image/jpeg")
        _set(ep_id, status="awaiting_approval", title=st["title"], takeaway=st.get("takeaway"), story=st,
             style=st.get("style", "")[:80], assets_path=f"{base}/assets", preview_path=f"{base}/preview.mp4",
             thumb_path=f"{base}/thumb.jpg", duration=round(render.duration(preview), 1))
        db.log(f"🎬 Ready: {st['title']} ({ch['name']})", "success")
        return ep_id
    except QuotaExceeded:
        _set(ep_id, status="queued")
        raise Wait(tomorrow_utc(), "Cloudflare's free limit was reached — continues after midnight UTC")
    except Exception as e:
        _set(ep_id, status="failed", error=str(e)[:400])
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def cmd_revise(payload, cmd):
    parent = _episode(payload["episode_id"])
    db.insert("commands", {"type": "generate", "payload": {
        "channel_id": parent["channel_id"], "feedback": payload["feedback"], "parent_id": parent["id"]}})
    _remove_files(parent)
    _set(parent["id"], status="replaced")


def cmd_publish(payload, cmd):
    from . import youtube

    ep = _episode(payload["episode_id"])
    if ep["status"] not in ("awaiting_approval", "failed", "publishing"):
        return
    ch = _channel(ep["channel_id"])
    token = _token(ch["id"])
    _set(ep["id"], status="publishing", error=None)
    work = WORK / f"pub-{ep['id']}"
    try:
        for f in ASSET_FILES:
            if not db.download(f"{ep['assets_path']}/{f}", work / f):
                raise RuntimeError(f"missing file {f}")
        st = json.loads((work / "story.json").read_text())
        video = render.render(work, st, work / "final", config.FINAL_SIZE,
                              music_volume=float(db.settings().get("music_volume") or 0.12))
        publish_at = payload.get("publish_at")
        vid, privacy = youtube.upload(token, video, st, ch, publish_at=publish_at)
    except Exception as e:
        _set(ep["id"], status="awaiting_approval", error=f"Upload failed: {e}"[:400])
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
    _remove_files(ep, keep_thumb=True)
    _set(ep["id"], status="scheduled" if publish_at else "published", youtube_id=vid,
         youtube_url=f"https://youtube.com/shorts/{vid}", publish_at=publish_at or now().isoformat(),
         assets_path=None, preview_path=None)
    if not publish_at and privacy == "private":
        db.log(f"Uploaded “{ep['title']}” as Private (Google API review pending) — set Public in YouTube Studio.", "warning")
    else:
        db.log(f"✅ {'Scheduled' if publish_at else 'Published'}: {ep['title']} ({ch['name']})", "success")


def cmd_delete(payload, cmd):
    ep = _episode(payload["episode_id"])
    _remove_files(ep)
    _set(ep["id"], status="deleted", preview_path=None, thumb_path=None, assets_path=None)


def cmd_connect(payload, cmd):
    from . import youtube

    token, yt_id, yt_title = youtube.exchange_code(payload["code"], payload["redirect_uri"])
    db.upsert("channel_tokens", {"channel_id": payload["channel_id"], "refresh_token": token,
                                 "updated_at": now().isoformat()}, "channel_id")
    db.update("channels", f"id=eq.{payload['channel_id']}",
              {"connected": True, "youtube_channel_id": yt_id, "youtube_title": yt_title})
    db.log(f"🔗 Connected YouTube channel “{yt_title}”", "success")


def cmd_stats(payload=None, cmd=None):
    from . import youtube

    eps = db.select("episodes", "select=id,channel_id,youtube_id,status&youtube_id=not.is.null")
    by_ch = {}
    for e in eps:
        by_ch.setdefault(e["channel_id"], []).append(e)
    for ch_id, items in by_ch.items():
        try:
            data = youtube.stats(_token(ch_id), [e["youtube_id"] for e in items])
        except Exception as ex:  # noqa: BLE001
            print("stats skipped:", ex)
            continue
        for e in items:
            s = data.get(e["youtube_id"])
            if s:
                v = {"views": s["views"], "likes": s["likes"], "stats_at": now().isoformat()}
                if e["status"] == "scheduled" and s["privacy"] == "public":
                    v["status"] = "published"
                db.update("episodes", f"id=eq.{e['id']}", v)


HANDLERS = {"generate": cmd_generate, "revise": cmd_revise, "publish": cmd_publish, "delete": cmd_delete,
            "stats": cmd_stats, "connect_channel": cmd_connect}


def process_queue():
    stale = (now() - timedelta(minutes=50)).isoformat()
    db.update("commands", f"status=eq.running&created_at=lt.{stale}&finished_at=is.null",
              {"status": "queued", "note": "retrying after a stopped run"})
    failures = 0
    while True:
        rows = db.select("commands", f"status=eq.queued&run_after=lte.{now().isoformat()}"
                                     "&order=created_at.asc&limit=1")
        if not rows:
            break
        c = rows[0]
        if not db.update("commands", f"id=eq.{c['id']}&status=eq.queued", {"status": "running", "note": None}):
            continue  # another worker took it
        print(f"▶ {c['type']} {json.dumps(c['payload'])[:200]}")
        try:
            HANDLERS[c["type"]](c["payload"], c)
            db.update("commands", f"id=eq.{c['id']}", {"status": "done", "finished_at": now().isoformat()})
        except Wait as w:
            db.update("commands", f"id=eq.{c['id']}", {"status": "queued", "run_after": w.until.isoformat(),
                                                       "note": w.note})
            print("  waiting:", w.note)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            failures += 1
            db.update("commands", f"id=eq.{c['id']}", {"status": "failed", "error": str(e)[:500],
                                                       "finished_at": now().isoformat()})
            db.log(f"⚠️ {c['type']} failed: {e}"[:500], "error")
            notify.send(f"⚠️ {c['type']} failed: {e}"[:300])
    return failures


def daily():
    today = now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    batch = []
    for ch in db.select("channels", "select=*&auto_daily=eq.true"):
        done = db.select("commands", f"select=id&type=eq.generate&created_at=gte.{today}"
                                     f"&payload->>channel_id=eq.{ch['id']}&payload->>auto=eq.true")
        batch += [{"type": "generate", "payload": {"channel_id": ch["id"], "auto": True}}
                  for _ in range(max(0, int(ch["per_day"]) - len(done)))]
    batch.append({"type": "stats", "payload": {}})
    db.insert_many("commands", batch)  # one insert = one wake-up of the workers
    if len(batch) > 1:
        notify.send(f"🎬 Making {len(batch) - 1} new shorts — they'll appear in the app for approval.")
    return 0


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "queue"
    sys.exit(1 if (daily() if mode == "daily" else process_queue()) else 0)
