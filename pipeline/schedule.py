"""Auto-publishing: every finished short gets the next free "best time" slot and is scheduled on YouTube.

Each day's times come from research on when kids watch (before school, lunch, after school, weekend mornings;
US + UK/Ireland audience) multiplied by what the channel's own shorts show: views in the first day by the
time they went out. The 20 slots are spread over the whole day, closer together at the best times, never two
within 30 minutes of each other (bursts get less reach).

    python -m pipeline.schedule        # print the next 24 slots (UTC + Irish time)
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
import math

GAP = timedelta(minutes=30)          # usual time between two shorts
MIN_GAP = timedelta(minutes=14)      # never closer than this (very full days squeeze to 15-25 min)
LEAD = timedelta(minutes=20)         # a slot must be at least this far away when the short is uploaded
HORIZON_DAYS = 4                     # never schedule further ahead than this

# ---- research: when do kids (and their parents' phones) watch? (local time -> 0..1)
# Kids: before school/daycare, lunch, after school until bedtime; weekend mornings + afternoons.
# General Shorts data (2026 studies): weekdays ~12-3 pm and 6-10 pm, weekends 12-6 pm.
WEEKDAY = {6: .3, 7: .75, 8: .45, 9: .15, 10: .15, 11: .3, 12: .6, 13: .5, 14: .4, 15: .7, 16: .95, 17: 1., 18: 1.,
           19: .85, 20: .55, 21: .25, 22: .1}
WEEKEND = {7: .45, 8: .8, 9: .95, 10: .95, 11: .8, 12: .75, 13: .7, 14: .75, 15: .85, 16: .95, 17: 1., 18: .9,
           19: .7, 20: .4, 21: .2}
# where the viewers are (English-speaking kids' shorts)
AUDIENCE = [("America/New_York", .36), ("America/Chicago", .12), ("America/Los_Angeles", .17), ("Europe/London", .35)]
EARLY = timedelta(minutes=40)        # publish a little before a peak so the short is out when kids arrive
FLOOR = 0.06                         # quiet hours still get the odd short (keeps testing new times)
PRIOR_N = 6.0                        # how many shorts of our own data it takes to outweigh the research


def _research(t):
    """How good publishing at UTC time t is, from the research above (0..1)."""
    v = 0.0
    for tz, share in AUDIENCE:
        lt = (t + EARLY).astimezone(ZoneInfo(tz))
        table = WEEKEND if lt.weekday() >= 5 else WEEKDAY
        h, f = lt.hour, lt.minute / 60
        v += share * ((1 - f) * table.get(h, 0.0) + f * table.get((h + 1) % 24, 0.0))
    return v


_LEARNED = None


def learned():
    """What our own shorts teach us: views in their first day by publish time of day (UTC, 30-min bins).
    Returns (lift per bin, how many shorts behind each bin)."""
    global _LEARNED
    if _LEARNED is not None:
        return _LEARNED
    import math
    lift, weight = [0.0] * 48, [0.0] * 48
    try:
        from . import db
        since = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        rows = db.select("episodes", f"select=publish_at,story&status=eq.published&publish_at=gte.{since}&limit=2000")
        pts, when = [], [_parse(e.get("publish_at")) for e in rows]
        now = datetime.now(timezone.utc)
        for e, t in zip(rows, when):
            yt = (e.get("story") or {}).get("yt") or {}
            if not t or yt.get("privacy", "public") != "public":
                continue
            v = yt.get("v24")
            if v is None and now - t > timedelta(hours=30):  # missed the day-1 count: read it off the daily history
                try:
                    from .trends import _day1_views
                    v = _day1_views(e, t)
                except Exception:  # noqa: BLE001
                    v = None
            if v is None:
                continue
            if sum(1 for u in when if u and abs(u - t) <= GAP) > 3:
                continue  # part of a burst (many at once) - says nothing about the time of day
            pts.append(((t.hour * 60 + t.minute) / 30.0, math.log1p(float(v)), t))
        if len(pts) >= 10:
            # compare each short with the shorts published around the same days (the channel grows, so a
            # plain average would just reward whatever times we happened to use most recently)
            res = []
            for x, y, t in pts:
                near = sorted(y2 for _x, y2, t2 in pts if abs(t2 - t) <= timedelta(days=3))
                res.append((x, y - near[len(near) // 2]))
            for b in range(48):  # smooth over neighbouring times (circular, ~1.5 h wide)
                num = den = 0.0
                for x, y in res:
                    dx = min(abs(x - b - 0.5), 48 - abs(x - b - 0.5))
                    k = math.exp(-0.5 * (dx / 3.0) ** 2)
                    num += k * y
                    den += k
                lift[b], weight[b] = (num / den if den else 0.0), den
    except Exception as ex:  # noqa: BLE001 - no data yet: research only
        print("learning skipped:", ex)
    _LEARNED = (lift, weight)
    return _LEARNED


def score(t):
    """Research x our own results for a UTC time."""
    import math
    lift, weight = learned()
    b = (t.hour * 60 + t.minute) // 30
    trust = weight[b] / (weight[b] + PRIOR_N)
    return max(FLOOR, _research(t)) * math.exp(trust * max(-1.5, min(1.5, lift[b])))


_DAY = {}
_TESTS = {}


TEST_SHARE = 0.15                    # ~1 in 6 slots tests a time we know little about (then the data decides)


def _test_times(d, start, k):
    """k test times for day d: plausible viewing times (research) where our own data is thinnest."""
    import random
    if k <= 0:
        return []
    lift, weight = learned()
    rnd = random.Random(d.toordinal() * 7 + 3)
    bins = []
    for b in range(48):
        t = start + timedelta(minutes=30 * b + 5)
        r = _research(t)
        if r < 0.2:      # not in the middle of the night
            continue
        bins.append((weight[b] + rnd.random() * 0.3, t))
    bins.sort(key=lambda x: x[0])
    picked = []
    for _w, t in bins:
        if all(abs(t - p) >= timedelta(minutes=90) for p in picked):
            picked.append(t)
        if len(picked) >= k:
            break
    return picked


def day_slots(d: date, per_day=20):
    """`per_day` publish times (UTC) for the UTC day `d`, spread over the whole day but packed closer
    together where kids watch most (each slot sits at an equal share of the day's total 'score'),
    never two within GAP of each other."""
    key = (d, per_day)
    if key in _DAY:
        return _DAY[key]
    start = datetime.combine(d, time(0), timezone.utc)
    mins = [start + timedelta(minutes=5 * i) for i in range(288)]
    w = [score(t) ** 1.3 for t in mins]
    tests = _test_times(d, start, round(per_day * TEST_SHARE)) if per_day >= 6 else []
    main = per_day - len(tests)
    tot, acc, out, k = sum(w), 0.0, [], 0
    for t, x in zip(mins, w):
        acc += x
        while k < main and acc >= (k + 0.5) / main * tot:
            out.append(t + timedelta(minutes=5))   # :05 / :10 ... never exactly on the hour
            k += 1
    out = sorted([(t, False) for t in out] + [(t, True) for t in tests])
    for gap in (GAP, timedelta(minutes=25), timedelta(minutes=20), timedelta(minutes=15)):
        fixed, flags = [], []
        for t, is_test in out:                        # keep them `gap` apart (30 min, a bit less on very full days)
            if fixed and t - fixed[-1] < gap:
                t = fixed[-1] + gap
            if t < start + timedelta(days=1):
                fixed.append(t)
                flags.append(is_test)
        if len(fixed) >= len(out):
            break
    _DAY[key] = fixed
    _TESTS[d] = [t for t, f in zip(fixed, flags) if f]
    return fixed


def plan_today():
    """Daily 'research' step: today's publish plan from research + our own results, written to the log."""
    from . import db
    lift, weight = learned()
    n = sum(1 for x in weight if x > 0)
    d = datetime.now(timezone.utc).date()
    slots = day_slots(d, per_day())
    dub = ZoneInfo("Europe/Dublin")
    trust = [weight[b] / (weight[b] + PRIOR_N) for b in range(48)]
    best = sorted(range(48), key=lambda b: lift[b] * trust[b], reverse=True)[:3]
    start = datetime.combine(d, time(0), timezone.utc)
    hm = lambda b: (start + timedelta(minutes=30 * b)).astimezone(dub).strftime("%H:%M")  # noqa: E731
    learned_txt = ("own data: best around " + ", ".join(hm(b) for b in best) + " Irish time"
                   if n else "own data: not enough yet, using research")
    times = ", ".join(t.astimezone(dub).strftime("%H:%M") for t in slots)
    tests = _TESTS.get(d) or []
    test_txt = (" · testing " + ", ".join(t.astimezone(dub).strftime("%H:%M") for t in tests)) if tests else ""
    # per Irish hour: how much better/worse our own shorts did there (x1.0 = average), and how sure we are
    hours = []
    for h in range(24):
        bs = [b for b in range(48) if (start + timedelta(minutes=30 * b)).astimezone(dub).hour == h]
        lf = sum(lift[b] * trust[b] for b in bs) / max(1, len(bs))
        hours.append({"h": h, "x": round(math.exp(max(-1.5, min(1.5, lf))), 2),
                      "sure": round(sum(trust[b] for b in bs) / max(1, len(bs)), 2),
                      "research": round(sum(_research(start + timedelta(minutes=30 * b)) for b in bs) / max(1, len(bs)), 2)})
    db.upsert("settings", {"key": "publish_plan", "value": {
        "date": d.isoformat(), "times": [t.isoformat() for t in slots], "tests": [t.isoformat() for t in tests],
        "note": learned_txt, "hours": hours}}, "key")
    db.log(f"📊 Publish times today (Irish time): {times} — {learned_txt}{test_txt}")
    return slots


def next_slot(taken, after=None, per_day=20):
    """First slot after `after` that is GAP away from every time in `taken` (UTC datetimes)."""
    after = after or datetime.now(timezone.utc) + LEAD
    d = after.date()
    for _ in range(HORIZON_DAYS + 1):
        for t in day_slots(d, per_day):
            if t >= after and all(abs(t - x) >= MIN_GAP for x in taken):
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
