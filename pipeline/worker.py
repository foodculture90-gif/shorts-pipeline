"""Cloud worker: does what you asked for in the app. Several run in parallel.

    python -m pipeline.worker queue   # process queued commands (started instantly by the app)
    python -m pipeline.worker daily   # queue each channel's daily shorts + a stats refresh
"""
import json
import os
import shutil
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, db, notify, render
from .generate import asset_files, make_assets
from .images import QuotaExceeded
from .llm import Busy

WORK = config.OUTPUT
CAPACITY = config.DAILY_NEURONS // config.NEURONS_PER_IMAGE        # pictures per day (free)
PICS = config.SCENES * config.SHOTS_PER_SCENE                        # pictures per short
WORKER_ID = os.environ.get("WORKER_ID", "1")
GH_REPO = os.environ.get("GITHUB_REPOSITORY", "foodculture90-gif/shorts-pipeline")


def _engine():
    """'3d' = real 3D cartoons rendered in Blender (default); 'ai' = the older AI-picture pipeline."""
    try:
        return (os.environ.get("ENGINE") or db.settings().get("engine") or "3d").lower()
    except Exception:  # noqa: BLE001
        return "3d"
USE_KAGGLE = bool(os.environ.get("KAGGLE_KEY"))   # free GPU turns pictures into real animation
ANIMATE_BATCH = 10                                 # shorts per Kaggle run (start-up costs ~5 min)


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
    if (ep.get("story") or {}).get("engine") == "3d":
        paths += [f"episodes/{ep['id']}/assets/story.json", f"episodes/{ep['id']}/final.mp4"]
    elif ep.get("assets_path"):
        st = ep.get("story") or {"scenes": [{"shots": [{}, {}]}] * 4}
        paths += [f"{ep['assets_path']}/{f}" for f in set(asset_files(st, False) + asset_files(st, True))]
    if ep.get("preview_path"):
        paths.append(ep["preview_path"])
    if ep.get("thumb_path") and not keep_thumb:
        paths.append(ep["thumb_path"])
    db.remove(paths)


def _refund(n):
    if n > 0:
        try:
            db.rpc("reserve_images", n=-n, cap=CAPACITY)
        except Exception as e:  # noqa: BLE001
            print("  could not refund picture allowance:", e)


# ---- commands ------------------------------------------------------------------------
def _dispatch_render(ep_id, gpu=None):
    from .slots import dispatch
    dispatch(ep_id, bool(gpu))


def _generate_3d(payload, ch, ep_id, slot=None):
    """Plan a 3D gag (cast, set, prop) + title/description, then hand it to the Blender render machines."""
    from . import plan3d
    _set(ep_id, status="generating", error=None)
    rows = db.select("episodes", f"select=title,story&channel_id=eq.{ch['id']}&title=not.is.null"
                                 "&order=created_at.desc&limit=40")
    recent = [(r.get("story") or {}).get("spec") for r in rows]
    base = None
    if payload.get("parent_id"):  # "Change this short": start from the short being changed
        try:
            base = (_episode(payload["parent_id"]).get("story") or {}).get("spec")
        except Exception:  # noqa: BLE001
            base = None
    idea = payload.get("idea") or payload.get("feedback")
    choose = dict(payload.get("choose") or {})
    if payload.get("moral"):
        choose["moral"] = True
    span = dict(min_s=45, max_s=58) if payload.get("long") else {}   # long shorts: 7 funny moments (~52 s)
    spec = plan3d.plan(recent, idea=idea, slot=slot, base=base, choose=choose, **span)
    if idea:
        note = (spec.get("wish") or {}).get("note") or plan3d.describe(spec)[:160]
        db.log(f"💡 Your idea “{idea[:80]}”: {note}"[:400])
    m = plan3d.meta(spec, [r["title"] for r in rows], slot=slot)
    st = dict(m, engine="3d", spec=spec, summary=plan3d.describe(spec))
    work = WORK / ep_id
    work.mkdir(parents=True, exist_ok=True)
    (work / "story.json").write_text(json.dumps(st))
    base = f"episodes/{ep_id}"
    db.upload(work / "story.json", f"{base}/assets/story.json", "application/json")
    shutil.rmtree(work, ignore_errors=True)
    _set(ep_id, title=st["title"], takeaway=st.get("takeaway"), story=st, style=f"3D {spec['set']}",
         assets_path=f"{base}/assets")
    gpu = payload.get("gpu")
    if gpu is None:  # setting gpu_render = true: Kaggle's free GPU takes up to 2 shorts at a time, the rest go to
        gpu = str(db.settings().get("gpu_render", "false")).lower() in ("1", "true", "yes")  # the normal machines
        if gpu:
            since = (now() - timedelta(hours=3)).isoformat()
            busy = db.select("episodes", f"select=id&status=eq.generating&story->>render=eq.gpu&updated_at=gt.{since}")
            gpu = len(busy) < 2
    if gpu:
        st["render"] = "gpu"
        _set(ep_id, story=st)
        _dispatch_render(ep_id, gpu)
        db.log(f"🎬 Rendering in 3D on the GPU: {st['title']} ({ch['name']})")
        return ep_id
    st["render"] = "wait"   # CPU machines: one short at a time gets all of them (see slots.py)
    _set(ep_id, story=st)
    from . import slots
    slots.kick()
    db.log(f"🎬 In line to render: {st['title']} ({ch['name']})")
    return ep_id


def cmd_generate(payload, cmd):
    ch = _channel(payload["channel_id"])
    ep_id = payload.get("episode_id")
    if not ep_id:
        ep_id = db.insert("episodes", {"channel_id": ch["id"], "status": "queued", "idea": payload.get("idea"),
                                       "feedback": payload.get("feedback"), "parent_id": payload.get("parent_id")})["id"]
        payload["episode_id"] = ep_id
        db.update("commands", f"id=eq.{cmd['id']}", {"payload": payload})
    if _engine() == "3d":
        try:
            return _generate_3d(payload, ch, ep_id, slot=int(cmd["id"]) if cmd and cmd.get("id") else None)
        except Exception as e:
            _set(ep_id, status="failed", error=str(e)[:400])
            raise
    # with the Kaggle GPU on, pictures are drawn there (better 3D-cartoon model, no daily picture limit)
    reserved = (not USE_KAGGLE) and bool(db.rpc("reserve_images", n=PICS, cap=CAPACITY))
    if not reserved and not USE_KAGGLE:
        _set(ep_id, status="queued", error=None)
        raise Wait(tomorrow_utc(), "Today's free pictures are used up — continues after midnight UTC")
    _set(ep_id, status="generating", error=None)
    work = WORK / ep_id
    drawn = [0 if reserved else PICS]  # pictures actually made; unused reservations are given back if this fails
    try:
        previous = None
        if payload.get("parent_id"):
            previous = _episode(payload["parent_id"]).get("story")
        past = [r["title"] for r in db.select(
            "episodes", f"select=title&channel_id=eq.{ch['id']}&title=not.is.null&order=created_at.desc&limit=60")]
        silent = payload.get("silent")
        if silent is None and previous is not None:
            silent = bool(previous.get("silent"))
        st = make_assets(work, ch, past_titles=past, idea=payload.get("idea"), feedback=payload.get("feedback"),
                         previous=previous, log=lambda m: print("  ·", m), silent=bool(silent),
                         on_image=lambda: drawn.__setitem__(0, drawn[0] + 1),
                         cloud_pictures=reserved, kaggle_fallback=USE_KAGGLE)
        if st.get("pics_needed") and reserved:
            _refund(PICS - drawn[0])
            drawn[0] = PICS
        base = f"episodes/{ep_id}"
        for f in asset_files(st):
            db.upload(work / f, f"{base}/assets/{f}", _mime(f))
        _set(ep_id, title=st["title"], story=st, assets_path=f"{base}/assets")
        if USE_KAGGLE:  # pictures → real animation on Kaggle's free GPU (batched by worker 1)
            db.log(f"🎨 Animating: {st['title']}")
            db.insert("commands", {"type": "animate", "payload": {"episode_id": ep_id}})
        else:
            _finish(ep_id, work, st, ch)
        return ep_id
    except QuotaExceeded:
        _refund(PICS - drawn[0])
        _set(ep_id, status="queued")
        raise Wait(min(tomorrow_utc(), now() + timedelta(hours=3)),
                   "Cloudflare's free picture limit was reached — retrying in a few hours")
    except Busy:
        _refund(PICS - drawn[0])
        _set(ep_id, status="queued", error=None)
        raise Wait(now() + timedelta(minutes=30), "The free script writer is busy — trying again in 30 minutes")
    except Exception as e:
        _refund(PICS - drawn[0])
        _set(ep_id, status="failed", error=str(e)[:400])
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _mime(f):
    return {"json": "application/json", "jpg": "image/jpeg", "mp3": "audio/mpeg", "mp4": "video/mp4"}[f.rsplit(".", 1)[1]]


def _finish(ep_id, work, st, ch=None):
    """Renders the preview from the files in work/ and puts the short up for approval."""
    preview = render.render(work, st, work / "preview", config.PREVIEW_SIZE,
                            music_volume=float(db.settings().get("music_volume") or 0.12))
    thumb = render.thumbnail(work / "s1_1.jpg", st["title"], work / "thumb.jpg")
    base = f"episodes/{ep_id}"
    db.upload(preview, f"{base}/preview.mp4", "video/mp4")
    db.upload(thumb, f"{base}/thumb.jpg", "image/jpeg")
    _set(ep_id, status="awaiting_approval", title=st["title"], takeaway=st.get("takeaway"), story=st,
         style=st.get("style", "")[:80], assets_path=f"{base}/assets", preview_path=f"{base}/preview.mp4",
         thumb_path=f"{base}/thumb.jpg", duration=round(render.duration(preview), 1), error=None)
    db.log(f"🎬 Ready: {st['title']}" + (f" ({ch['name']})" if ch else ""), "success")


def _download(ep, work, clips=None):
    work.mkdir(parents=True, exist_ok=True)
    if not db.download(f"{ep['assets_path']}/story.json", work / "story.json"):
        raise RuntimeError("missing story.json")
    st = json.loads((work / "story.json").read_text())
    for f in asset_files(st, clips):
        if f != "story.json" and not db.download(f"{ep['assets_path']}/{f}", work / f):
            raise RuntimeError(f"missing file {f}")
    return st


def cmd_animate(payload, cmd):
    """Worker 1 only: animates up to ANIMATE_BATCH waiting shorts in ONE Kaggle GPU run, then renders them.
    If Kaggle fails, the shorts are still finished with the built-in puppet animation."""
    from . import kaggle_video
    import time
    for _ in range(30):  # wait (max ~10 min) for shorts other workers are still making, to batch them
        if not db.select("commands", "select=id&type=eq.generate&status=eq.running&limit=1"):
            break
        time.sleep(20)
    others = db.select("commands", f"type=eq.animate&status=eq.queued&id=neq.{cmd['id']}"
                                   f"&order=created_at.asc&limit={ANIMATE_BATCH - 1}")
    taken = [c for c in others if db.update("commands", f"id=eq.{c['id']}&status=eq.queued",
                                             {"status": "running", "note": "animating with another short"})]
    jobs = [cmd] + taken
    eps = []
    for c in jobs:
        try:
            ep = _episode(c["payload"]["episode_id"])
            if ep["status"] == "generating" and ep.get("assets_path") and ep["id"] not in [x["id"] for x in eps]:
                eps.append(ep)
        except Exception as e:  # noqa: BLE001
            print("  skip", c["payload"], e)
    work = WORK / f"anim-{cmd['id']}"
    clips = {}
    try:
        if eps:
            clips = kaggle_video.animate_batch([(e["id"], e["story"], e["assets_path"]) for e in eps], work,
                                               log=lambda m: print(m))
    except kaggle_video.KaggleBusy as e:  # no free GPU right now: put the whole batch back and retry later
        later = (now() + timedelta(minutes=60)).isoformat()
        for c in taken:
            db.update("commands", f"id=eq.{c['id']}", {"status": "queued", "run_after": later,
                                                       "note": "waiting for a free Kaggle GPU"})
        shutil.rmtree(work, ignore_errors=True)
        db.log(f"⏳ {e} — trying again in an hour", "warning")
        raise Wait(now() + timedelta(minutes=60), "Waiting for a free Kaggle GPU — trying again in an hour")
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        db.log(f"⚠️ AI animation failed, using built-in animation: {e}"[:300], "warning")
    try:
        for ep in eps:
            ew = work / ep["id"]
            try:
                st = _download(ep, ew, clips=False)
                got = clips.get(ep["id"], {})
                pics = st.get("pics_needed") or []
                if pics:  # pictures drawn on the Kaggle GPU (Cloudflare limit was reached)
                    if not all(p in got for p in pics):
                        raise RuntimeError("the pictures couldn't be drawn on the free GPU — try Retry later")
                    for p in pics:
                        shutil.copy(got[p], ew / p)
                        db.upload(ew / p, f"{ep['assets_path']}/{p}", "image/jpeg")
                    st["pics_needed"] = []
                    (ew / "story.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
                    db.upload(ew / "story.json", f"{ep['assets_path']}/story.json", "application/json")
                need = [f for f in asset_files(st, True) if f.startswith("c")]
                if got and all(f in got for f in need):
                    for f in need:
                        shutil.copy(got[f], ew / f)
                        db.upload(ew / f, f"{ep['assets_path']}/{f}", "video/mp4")
                    st["clips"] = True
                    (ew / "story.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
                    db.upload(ew / "story.json", f"{ep['assets_path']}/story.json", "application/json")
                _finish(ep["id"], ew, st)
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                _set(ep["id"], status="failed", error=str(e)[:400])
    finally:
        shutil.rmtree(work, ignore_errors=True)
        for c in taken:
            db.update("commands", f"id=eq.{c['id']}", {"status": "done", "finished_at": now().isoformat()})


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
        if (ep.get("story") or {}).get("engine") == "3d":  # already rendered at full quality by Blender
            st = ep["story"]
            video = work / "final.mp4"
            if not db.download(f"episodes/{ep['id']}/final.mp4", video):
                raise RuntimeError("the finished 3D video is missing - press Retry")
        else:
            st = _download(ep, work)
            video = render.render(work, st, work / "final", config.FINAL_SIZE,
                                  music_volume=float(db.settings().get("music_volume") or 0.12))
        publish_at = payload.get("publish_at")
        if payload.get("auto") and publish_at:  # auto-publish: the slot passed while waiting -> take the next free one
            from . import schedule
            if datetime.fromisoformat(publish_at.replace("Z", "+00:00")) < now() + timedelta(minutes=10):
                t = schedule.next_slot(schedule.taken_times(exclude=ep["id"]), per_day=schedule.per_day())
                publish_at = t.isoformat() if t else None
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
    """Views, likes and comments of every short on YouTube (+ a daily history for the app's chart)."""
    from . import youtube

    eps = db.select("episodes", "select=id,channel_id,youtube_id,status,thumb_path,title,story,publish_at"
                                "&youtube_id=not.is.null&status=in.(published,scheduled)")
    by_ch = {}
    for e in eps:
        by_ch.setdefault(e["channel_id"], []).append(e)
    today = now().date().isoformat()
    for ch_id in {c["id"] for c in db.select("channels", "select=id&connected=is.true")} | set(by_ch):
        try:
            cs = youtube.channel_stats(_token(ch_id))
            if cs:
                db.upsert("settings", {"key": f"yt_{ch_id}", "value": dict(cs, at=now().isoformat())}, "key")
                from . import notify
                notify.snapshot(ch_id, cs)   # end-of-day totals -> subscribers gained per day
        except Exception as ex:  # noqa: BLE001
            print("channel stats skipped:", ex)
    for ch_id, items in by_ch.items():
        try:
            data = youtube.stats(_token(ch_id), [e["youtube_id"] for e in items])
        except Exception as ex:  # noqa: BLE001
            print("stats skipped:", ex)
            continue
        for e in items:
            s = data.get(e["youtube_id"])
            if not s:  # removed on YouTube -> remove it here too
                if e.get("thumb_path"):
                    db.remove([e["thumb_path"]])
                _set(e["id"], status="deleted", thumb_path=None)
                db.log(f"🗑️ “{e.get('title')}” was deleted on YouTube — removed from the app")
                continue
            st = e.get("story") or {}
            yt = st.get("yt") or {}
            hist = [h for h in (yt.get("hist") or []) if h[0] != today][-29:] + [[today, s["views"]]]
            st["yt"] = {"privacy": s.get("privacy"), "comments": s.get("comments", 0), "hist": hist}
            for k in ("v24",):  # views after its first day -> teaches the scheduler which times work best
                if k in yt:
                    st["yt"][k] = yt[k]
            v = {"views": s["views"], "likes": s["likes"], "stats_at": now().isoformat(), "story": st}
            try:
                pub = datetime.fromisoformat(str(e.get("publish_at")).replace("Z", "+00:00"))
            except ValueError:
                pub = None
            if e["status"] == "scheduled" and s["privacy"] == "public":
                v["status"] = "published"
                if pub and pub > now():  # made public early by hand -> it went out now
                    pub = now()
                    v["publish_at"] = pub.isoformat()
            if pub and s["privacy"] == "public" and "v24" not in st["yt"] and now() - pub >= timedelta(hours=24):
                st["yt"]["v24"] = s["views"] if now() - pub <= timedelta(hours=36) else None
            db.update("episodes", f"id=eq.{e['id']}", v)
    db.upsert("settings", {"key": "stats_at", "value": now().isoformat()}, "key")
    try:  # what's working: stories/places/characters/titles that get more views -> new shorts lean towards them
        from . import trends
        trends.update()
    except Exception:  # noqa: BLE001
        traceback.print_exc()


def maybe_stats():
    """Keep the views fresh: every ~2 hours, whenever a worker runs."""
    try:
        last = db.settings().get("stats_at")
        if last and now() - datetime.fromisoformat(str(last).replace("Z", "+00:00")) < timedelta(hours=2):
            return
        cmd_stats()
    except Exception:  # noqa: BLE001
        traceback.print_exc()


def cmd_notify_test(payload=None, cmd=None):
    """The app's 'Send me today's report' button: the daily report, right now."""
    from . import notify
    notify.daily_report(force=True)


HANDLERS = {"generate": cmd_generate, "animate": cmd_animate, "revise": cmd_revise, "publish": cmd_publish, "delete": cmd_delete,
            "stats": cmd_stats, "connect_channel": cmd_connect, "notify_test": cmd_notify_test}


def retry_failed_renders():
    """A 3D short whose render machines hiccuped gets one more try instead of staying failed."""
    for e in db.select("episodes", "select=id,title,story,idea,feedback,parent_id,channel_id,error&status=eq.failed"
                                   "&error=like.*3D*&story->>retries=is.null&limit=12"):
        st = e.get("story") or {}
        if st.get("engine") != "3d" or not st.get("spec"):
            continue
        if (e.get("idea") or e.get("feedback")) and str(e.get("error", "")).startswith("could not start"):
            # never rendered: plan it again so the idea is read by the newest planner
            st["retries"] = 1
            if db.update("episodes", f"id=eq.{e['id']}&status=eq.failed", {"status": "queued", "error": None, "story": st}):
                db.insert("commands", {"type": "generate", "payload": {
                    "channel_id": e["channel_id"], "episode_id": e["id"], "idea": e.get("idea"),
                    "feedback": e.get("feedback"), "parent_id": e.get("parent_id"), "silent": True}})
                db.log(f"🔁 Making your idea again: {e.get('idea') or e.get('feedback')}"[:300])
            continue
        st["retries"] = 1
        st["render"] = "wait"
        if db.update("episodes", f"id=eq.{e['id']}&status=eq.failed",
                     {"status": "generating", "error": None, "story": st, "updated_at": now().isoformat()}):
            db.log(f"🔁 Rendering again: {e.get('title') or 'a short'}")
    from . import slots
    slots.kick()


def clear_stale_failed():
    """Failed shorts that already had their retry and are 2+ days old just clutter the app: tidy them away."""
    old = (now() - timedelta(days=2)).isoformat()
    rows = db.select("episodes", f"select=id,title,thumb_path,story&status=eq.failed&updated_at=lt.{old}&limit=50")
    gone = 0
    for e in rows:
        if not (e.get("story") or {}).get("retries") and (e.get("story") or {}).get("engine") == "3d":
            continue  # not retried yet: retry_failed_renders gets it first
        if e.get("thumb_path"):
            try:
                db.remove([e["thumb_path"]])
            except Exception:  # noqa: BLE001
                pass
        if db.update("episodes", f"id=eq.{e['id']}&status=eq.failed", {"status": "deleted", "thumb_path": None}):
            gone += 1
    if gone:
        db.log(f"🧹 Cleared {gone} old failed short{'s' if gone > 1 else ''} (they had already been retried)")


def retry_failed_plans():
    """A short that failed before it was even planned (e.g. a planner bug) is made again once."""
    since = (now() - timedelta(hours=36)).isoformat()
    for e in db.select("episodes", "select=id,channel_id,idea,feedback,parent_id,error,story&status=eq.failed"
                                   f"&story=is.null&created_at=gt.{since}&limit=25"):
        if "3D" in str(e.get("error") or "") or "retried" in str(e.get("error") or ""):
            continue
        if db.update("episodes", f"id=eq.{e['id']}&status=eq.failed", {"status": "queued", "error": None,
                                                                        "story": {"retries": 1}}):
            db.insert("commands", {"type": "generate", "payload": {
                "channel_id": e["channel_id"], "episode_id": e["id"], "idea": e.get("idea"), "auto": True,
                "feedback": e.get("feedback"), "parent_id": e.get("parent_id"), "silent": True}})


def process_queue():
    if WORKER_ID == "1":
        for job in (retry_failed_plans, retry_failed_renders, clear_stale_failed):
            try:
                job()
            except Exception:  # noqa: BLE001
                traceback.print_exc()
        try:
            from . import schedule
            schedule.book_ready()   # finished shorts -> next best publish time
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        maybe_stats()
        from . import notify
        notify.maybe_report()    # morning push: yesterday's views + subscribers vs the day before
    stale = (now() - timedelta(minutes=50)).isoformat()
    db.update("commands", f"status=eq.running&created_at=lt.{stale}&finished_at=is.null",
              {"status": "queued", "note": "retrying after a stopped run"})
    failures = 0
    while True:
        only = "" if WORKER_ID == "1" else "&type=neq.animate"   # one Kaggle GPU job at a time
        rows = db.select("commands", f"status=eq.queued&run_after=lte.{now().isoformat()}{only}"
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
        silent = str(db.settings().get("silent", "true")).lower() not in ("false", "0", "no")
        # shorts already waiting (ready, or scheduled beyond tomorrow) count towards today's batch
        later = (now() + timedelta(hours=30)).isoformat()
        waiting = len(db.select("episodes", f"select=id&channel_id=eq.{ch['id']}&status=eq.scheduled&publish_at=gt.{later}"))
        waiting += len(db.select("episodes", f"select=id&channel_id=eq.{ch['id']}&status=in.(awaiting_approval,queued)"))
        n = max(0, int(ch["per_day"]) - len(done) - max(0, waiting - 2))
        try:  # half of the daily shorts are moral stories (setting moral_share, 0..1)
            share = float(str(db.settings().get("moral_share", "0.5")).strip('"'))
        except ValueError:
            share = 0.5
        morals = round(n * max(0.0, min(1.0, share)))
        flags = [i * morals // max(1, n) != (i + 1) * morals // max(1, n) for i in range(n)]
        # a share of the funny shorts are LONG (45-58 s): 10 a day while testing, then whatever the views say
        try:
            from . import trends
            n_long, why = trends.long_plan(flags.count(False))
        except Exception:  # noqa: BLE001
            n_long, why = min(10, flags.count(False)), "testing long shorts"
        funny = [i for i, m in enumerate(flags) if not m]
        long_ids = set(funny[::max(1, len(funny) // max(1, n_long))][:n_long]) if n_long else set()
        if n:
            db.log(f"📏 Today: {n} shorts, {len(long_ids)} of them long (45-58 s) — {why}")
        batch += [{"type": "generate", "payload": {"channel_id": ch["id"], "auto": True, "silent": silent,
                                                   "moral": flags[i], "long": i in long_ids}}
                  for i in range(n)]
    batch.append({"type": "stats", "payload": {}})
    try:  # daily research: today's best publish times (research + what our own shorts showed)
        from . import schedule
        schedule.plan_today()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    db.insert_many("commands", batch)  # one insert = one wake-up of the workers
    if len(batch) > 1:
        notify.send(f"🎬 Making {len(batch) - 1} new shorts — they'll appear in the app for approval.")
    return 0


def test3d():
    """One test short on the first channel, rendered on the GPU (Actions -> Worker -> Run workflow -> test3d)."""
    ch = (db.select("channels", "select=id&auto_daily=eq.true&limit=1") or db.select("channels", "select=id&limit=1"))[0]
    payload = {"channel_id": ch["id"], "gpu": True, "silent": True}
    if os.environ.get("TEST_IDEA"):
        payload["idea"] = os.environ["TEST_IDEA"]
    db.insert("commands", {"type": "generate", "payload": payload})
    return process_queue()


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "queue"
    if mode == "test3d":
        sys.exit(1 if test3d() else 0)
    sys.exit(1 if (daily() if mode == "daily" else process_queue()) else 0)
