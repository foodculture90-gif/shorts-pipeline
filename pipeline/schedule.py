"""Auto-publishing: every finished short gets the next free "best time" slot and is scheduled on YouTube.

Kids' shorts are watched most before school/daycare, at lunch, after school until bedtime, and on weekend
mornings. The audience is English-speaking, so the day is built from US (Eastern + Pacific) and UK/Ireland
peak times - 20 slots a day, never two within 30 minutes of each other (bursts get less reach).

    python -m pipeline.schedule        # print the next 24 slots (UTC + Irish time)
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

GAP = timedelta(minutes=30)          # minimum time between two shorts
LEAD = timedelta(minutes=20)         # a slot must be at least this far away when the short is uploaded
HORIZON_DAYS = 4                     # never schedule further ahead than this

# (time zone, weekday times, weekend times)
PEAKS = [
    ("Europe/London", ["07:05", "12:10", "15:40", "16:40", "17:40", "18:40"],
                      ["08:05", "10:10", "13:10", "16:40", "17:40", "18:40"]),
    ("America/New_York", ["06:50", "07:40", "12:20", "15:10", "16:00", "16:50", "17:40", "18:30", "19:20"],
                         ["07:50", "08:40", "09:30", "10:20", "15:10", "16:50", "17:40", "18:30", "19:20"]),
    ("America/Chicago", ["17:10"], ["11:10"]),
    ("America/Los_Angeles", ["07:20", "16:20", "17:50", "18:50"], ["08:20", "11:50", "16:20", "18:50"]),
]


def _utc(d, hhmm, tz):
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(d, time(h, m), ZoneInfo(tz)).astimezone(timezone.utc)


def day_slots(d: date, per_day=20):
    """The best `per_day` publish times (UTC) for the UTC day `d`, at least GAP apart."""
    cand = []
    for off in (-1, 0, 1):   # a UTC day overlaps two local days in the US
        ld = d + timedelta(days=off)
        weekend = ld.weekday() >= 5
        for tz, wk, we in PEAKS:
            cand += [_utc(ld, t, tz) for t in (we if weekend else wk)]
    start = datetime.combine(d, time(0), timezone.utc)
    cand = sorted(t for t in cand if start <= t < start + timedelta(days=1))
    out = []
    for t in cand:                       # push clashing slots later so they're GAP apart
        if out and t - out[-1] < GAP:
            t = out[-1] + GAP
        if t < start + timedelta(days=1):
            out.append(t)
    while len(out) < per_day:            # not enough peaks -> add one in the middle of the biggest daytime gap
        pts = [start + timedelta(hours=6)] + [t for t in out if t >= start + timedelta(hours=6)] + [start + timedelta(days=1)]
        a, b = max(zip(pts, pts[1:]), key=lambda ab: ab[1] - ab[0])
        if b - a < 2 * GAP:
            break
        out = sorted(out + [a + (b - a) / 2])
    if len(out) > per_day:               # fewer per day -> keep an even spread of the best ones
        step = len(out) / per_day
        out = [out[int(i * step)] for i in range(per_day)]
    return out


def next_slot(taken, after=None, per_day=20):
    """First slot after `after` that is GAP away from every time in `taken` (UTC datetimes)."""
    after = after or datetime.now(timezone.utc) + LEAD
    d = after.date()
    for _ in range(HORIZON_DAYS + 1):
        for t in day_slots(d, per_day):
            if t >= after and all(abs(t - x) >= GAP for x in taken):
                return t
        d += timedelta(days=1)
    return None


def _parse(v):
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def taken_times(exclude=None):
    """Publish times already used: scheduled/just-published shorts + publish orders not uploaded yet."""
    from . import db
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    out = []
    for e in db.select("episodes", f"select=id,publish_at&publish_at=gte.{since}"
                                   "&status=in.(scheduled,published,publishing)"):
        if e["id"] != exclude and _parse(e["publish_at"]):
            out.append(_parse(e["publish_at"]))
    for c in db.select("commands", "select=payload&type=eq.publish&status=in.(queued,running)"):
        p = c.get("payload") or {}
        if p.get("episode_id") != exclude and _parse(p.get("publish_at")):
            out.append(_parse(p["publish_at"]))
    return out


def enabled():
    from . import db
    return str(db.settings().get("auto_publish", "true")).strip('"').lower() not in ("false", "0", "no", "off")


def per_day():
    from . import db
    try:
        return max(1, sum(int(c["per_day"]) for c in db.select("channels", "select=per_day&auto_daily=eq.true")) or 20)
    except Exception:  # noqa: BLE001
        return 20


def book(ep_ids):
    """Give each ready short the next free slot (a 'publish' order; the worker uploads it scheduled)."""
    from . import db
    if not ep_ids:
        return []
    taken, n, rows = taken_times(), per_day(), []
    for ep_id in ep_ids:
        t = next_slot(taken, per_day=n)
        if not t:
            break
        taken.append(t)
        rows.append({"type": "publish", "payload": {"episode_id": ep_id, "publish_at": t.isoformat(), "auto": True}})
    if rows:
        db.insert_many("commands", rows)
        db.log(f"📅 Auto-publish: {len(rows)} short{'s' if len(rows) > 1 else ''} scheduled, next at "
               f"{_parse(rows[0]['payload']['publish_at']).astimezone(ZoneInfo('Europe/Dublin')):%a %H:%M}")
    return rows


def book_ready():
    """Every finished short that is waiting for approval and has no publish order yet gets a slot."""
    from . import db
    if not enabled():
        return []
    ready = db.select("episodes", "select=id,story&status=eq.awaiting_approval&order=created_at.asc&limit=60")
    ordered = {(c.get("payload") or {}).get("episode_id")
               for c in db.select("commands", "select=payload&type=eq.publish&status=in.(queued,running)")}
    ids = [e["id"] for e in ready if (e.get("story") or {}).get("engine") == "3d" and e["id"] not in ordered]
    return book(ids)


if __name__ == "__main__":
    dub = ZoneInfo("Europe/Dublin")
    taken = []
    for _ in range(24):
        t = next_slot(taken)
        taken.append(t)
        print(t.strftime("%a %H:%M UTC"), "|", t.astimezone(dub).strftime("%H:%M Dublin"), "|",
              t.astimezone(ZoneInfo("America/New_York")).strftime("%H:%M New York"))
