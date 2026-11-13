"""Learns from its own renders so a length that keeps failing isn't made again.

Every finished short records how long its render took (story.render_stats). Every failed one says why (error).
Once a day (before the batch is planned) this looks at the last 14 days, per length:

* fails too often because it ran out of time or came out too big  -> that length gets one funny moment shorter
  (7 s) and it logs what it learned;
* its slowest renders get close to the machines' time limit           -> also one moment shorter, before it fails;
* clean for a good while and fast enough                               -> it may try one moment longer again,
  never past the 1:30 maximum.

The result (settings.len_caps) is what the planner uses as the longest "long" and "extra long" short, and the
average render minutes per length feed the daily render-time budget (trends.length_plan).
"""
from datetime import datetime, timedelta, timezone

from . import db

DEFAULT_CAP = {"long": 58, "xl": 88}       # seconds (the 1:30 maximum leaves room for the intro)
FLOOR = {"long": 38, "xl": 63}             # never shorter than this - below it the arm is just "normal" again
STEP = 7                                   # one funny moment
PART_LIMIT = 85                            # minutes one render machine may take (render3d.yml)
HARD = ("took too long", "413", "too large", "only ")   # failures caused by length (time / file size / lost frames)


def arm(n_gags):
    return "xl" if n_gags >= 9 else "long" if n_gags >= 6 else "normal"


# failures before this were caused by things fixed on 13 Nov (file-size cap, 85-min machine limit): don't learn from them
FRESH = datetime(2026, 11, 13, 22, 30, tzinfo=timezone.utc)


def _rows():
    since = max(datetime.now(timezone.utc) - timedelta(days=14), FRESH).isoformat()
    return db.select("episodes", "select=status,error,duration,story->spec->segments,story->render_stats,story->engine"
                                 f"&created_at=gte.{since}&status=in.(failed,awaiting_approval,scheduled,published,"
                                 "publishing,deleted)&order=created_at.asc&limit=2000")


def learn(rows=None):
    rows = _rows() if rows is None else rows
    st = db.settings()
    caps = dict(DEFAULT_CAP, **(st.get("len_caps") or {}))
    stats = {"normal": [], "long": [], "xl": []}
    for e in rows:
        segs = [g for g in (e.get("segments") or []) if (g or {}).get("gag") != "intro"]
        if not segs:
            continue
        a = arm(len(segs))
        err = str(e.get("error") or "")
        hard = e.get("status") in ("failed", "deleted") and any(h in err for h in HARD)
        ok = e.get("status") in ("awaiting_approval", "scheduled", "published", "publishing")
        if not (hard or ok):
            continue                               # deleted by you / other errors: say nothing about length
        rs = e.get("render_stats") or {}
        stats[a].append({"hard": hard, "mins": rs.get("part_mins") or rs.get("mins")})
    notes, minutes = [], {}
    for a in ("long", "xl"):
        s = stats[a][-30:]
        n, fails = len(s), sum(1 for x in s if x["hard"])
        mins = sorted(x["mins"] for x in s if x["mins"])
        slow = mins[int(len(mins) * 0.9)] if len(mins) >= 4 else None
        old = caps[a]
        if n >= 4 and fails / n >= 0.25:
            caps[a] = max(FLOOR[a], caps[a] - STEP)
            why = f"{fails} of the last {n} failed (too slow / too big)"
        elif slow and slow > PART_LIMIT * 0.8:
            caps[a] = max(FLOOR[a], caps[a] - STEP)
            why = f"its slowest renders took {slow:.0f} of the {PART_LIMIT} minutes allowed"
        elif n >= 10 and fails == 0 and (not slow or slow < PART_LIMIT * 0.6) and caps[a] < DEFAULT_CAP[a]:
            caps[a] = min(DEFAULT_CAP[a], caps[a] + STEP)
            why = f"the last {n} all rendered fine and fast"
        else:
            why = ""
        if caps[a] != old:
            label = "Long" if a == "long" else "Extra long"
            notes.append(f"{label} shorts: max {old} s → {caps[a]} s ({why})")
    for a, s in stats.items():
        m = [x["mins"] for x in s if x["mins"]]
        if len(m) >= 3:
            minutes[a] = round(sum(m) / len(m))
    db.upsert("settings", {"key": "len_caps", "value": caps}, "key")
    db.upsert("settings", {"key": "render_health", "value": {
        "at": datetime.now(timezone.utc).isoformat(), "caps": caps, "minutes": minutes,
        "arms": {a: {"n": len(s), "fails": sum(1 for x in s if x["hard"])} for a, s in stats.items()}}}, "key")
    for n in notes:
        db.log(f"🧠 Learned: {n}", "warning")
    return caps, minutes


def span(size):
    """min/max seconds for a long ("long") or extra long ("xl") short, inside what has proven safe to render."""
    if size not in ("long", "xl"):
        return {}
    cap = dict(DEFAULT_CAP, **(db.settings().get("len_caps") or {})).get(size, DEFAULT_CAP[size])
    lo = 45 if size == "long" else 63
    return {"min_s": min(lo, cap - STEP), "max_s": cap}
