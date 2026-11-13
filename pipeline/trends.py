"""What's working: learns from our own published shorts which stories, places, characters, title styles,
lengths and short types get more views, so new shorts lean towards them (and the app can show it).

How a short is judged (fair to every short):
- views after its first day (v24; older shorts: their views one day in, from the daily history),
- minus the publish-time effect (schedule.py already learns that, so a good slot doesn't count as a good story),
- compared with the shorts published around the same days (the channel growing doesn't flatter newer shorts).
Every feature gets a cautious score AND an error bar (how much of it could be luck). Only the part of an effect
that is bigger than its error bar is used ("proven"); everything else stays a fair 50/50 test, and things with
very few shorts get a small bonus so they are tried. Choices only lean (x0.55 ... x1.8), never lock in."""
import math
import re
from datetime import datetime, timedelta, timezone

K = 3.0              # shorts it takes before a feature's own result counts half
Z = 1.28             # error bars: ~80 % one-sided - an effect must clear this to be used
TRY_BONUS = 0.15     # options with < 3 shorts get tried a bit more (x1.16)
CLAMP = 0.6          # strongest lean: e^0.6 = x1.8 (and x0.55 the other way)
MIN_SHORTS = 8       # below this, no learning yet
KINDS = {"tag": "Hashtags", "story": "Stories", "type": "Funny vs lesson", "place": "Places", "char": "Characters",
         "title": "Title styles", "length": "Length", "sky": "Time of day in the short", "when": "Publish time",
         "when_char": "Time × character", "when_story": "Time × story", "when_place": "Time × place",
         "when_type": "Time × funny/lesson", "when_length": "Time × length"}
COMBOS = ("char", "story", "place", "type", "length")   # what can fit some times of day better than others
BANDS = (("night", 0, 6), ("morning", 6, 12), ("afternoon", 12, 17), ("evening", 17, 24))   # Irish time


def band(t):
    """Part of the day (Irish time) a publish time falls in."""
    from zoneinfo import ZoneInfo
    h = t.astimezone(ZoneInfo("Europe/Dublin")).hour
    return next(name for name, a, b in BANDS if a <= h < b)
TITLE_STYLES = ["how", "dont", "question", "name", "exclaim", "the", "challenge"]  # = plan3d.TITLE_FORMATS order
TITLE_NAMES = {"how": "“How To …”", "dont": "“Don't …”", "question": "Questions", "name": "Name + action",
               "exclaim": "Exclamations", "the": "“The …”", "challenge": "Challenges", "other": "Other"}

_CACHE = None


def _parse(v):
    try:
        t = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def title_style(title):
    from .plan3d import NAMES
    t = re.sub(r"[^\w\s'?!]", "", str(title or "")).strip().lower()
    if re.match(r"(try not|can you|warning|challenge|dont blink|only \d)", t):
        return "challenge"
    if t.startswith("how to"):
        return "how"
    if re.match(r"(don'?t|do not|never) ", t):
        return "dont"
    if "?" in t:
        return "question"
    if t.startswith("the "):
        return "the"
    if t.split(" ")[0].split("'")[0] in {n.lower() for n in NAMES.values()}:
        return "name"
    if "!" in t:
        return "exclaim"
    return "other"


def length_bucket(seconds):
    return "20-25 s" if seconds < 26 else "26-35 s" if seconds < 36 else "36-60 s" if seconds < 61 else "61-90 s"


def features(spec, title, duration=None, pub=None):
    """(kind, value, weight) for one short. With its publish time also: part of day, and part of day x
    character / story / place / funny-or-lesson / length (so it can learn e.g. "Bolt does best in the evening")."""
    spec = spec or {}
    segs = [g for g in (spec.get("segments") or [spec]) if g.get("gag") != "intro"]
    out = []
    for i, s in enumerate(segs):
        if s.get("gag"):
            out.append(("story", s["gag"], 1.0 if i == 0 else 0.5))  # the first moment is the hook
    out.append(("type", "lesson" if spec.get("moral") else "funny", 1.0))
    if spec.get("set"):
        out.append(("place", spec["set"], 1.0))
    for c in {spec.get("hero"), spec.get("friend")} - {None}:
        out.append(("char", c, 1.0))
    out.append(("title", title_style(title), 1.0))
    d = duration or (len(segs) * 7 if not spec.get("moral") else None)
    if d:
        out.append(("length", length_bucket(d), 1.0))
    sky = (spec.get("theme") or {}).get("sky")
    if sky:
        out.append(("sky", sky, 1.0))
    if pub:
        w = band(pub)
        out.append(("when", w, 1.0))
        out += [(f"when_{k}", f"{w}|{v}", wt) for k, v, wt in list(out) if k in COMBOS and (k != "story" or wt == 1.0)]
    return out


def _day1_views(e, pub):
    """Views about one day after publishing: v24, else the daily history, else None."""
    yt = (e.get("story") or {}).get("yt") or {}
    if yt.get("v24") is not None:
        return float(yt["v24"])
    want = (pub + timedelta(days=1)).date()
    best = None
    for d, v in yt.get("hist") or []:
        try:
            gap = abs((datetime.fromisoformat(d).date() - want).days)
        except (TypeError, ValueError):
            continue
        if gap <= 1 and (best is None or gap < best[0]):
            best = (gap, float(v))
    return best[1] if best else None


def learn(rows, now=None):
    """rows: episodes (publish_at, views, duration, title, story). Returns the trends table."""
    from . import schedule
    now = now or datetime.now(timezone.utc)
    pts = []
    for e in rows:
        st = e.get("story") or {}
        pub = _parse(e.get("publish_at"))
        if not pub or not st.get("spec") or (st.get("yt") or {}).get("privacy", "public") != "public":
            continue
        if now - pub < timedelta(hours=24):
            continue
        v = _day1_views(e, pub)
        if v is None:  # no early count: total views, gently discounted for age
            v = float(e.get("views") or 0) / max(1.0, ((now - pub).total_seconds() / 86400) ** 0.35)
        y = math.log1p(v)
        likes = float(e.get("likes") or 0)  # liked = kids/parents loved it -> a small bonus (likes lead to subscribers)
        y += 0.3 * math.log1p(likes)
        try:  # take out the publish-time effect
            lift, weight = schedule.learned()
            b = (pub.hour * 60 + pub.minute) // 30
            y -= weight[b] / (weight[b] + schedule.PRIOR_N) * max(-1.5, min(1.5, lift[b]))
        except Exception:  # noqa: BLE001
            pass
        pts.append((pub, y, e))
    if len(pts) < MIN_SHORTS:
        return {"n": len(pts), "at": now.isoformat(), "kinds": {}, "note": "not enough shorts with views yet"}
    ys = sorted(p[1] for p in pts)
    mid_all = sum(ys) / len(ys)
    table, scored = {}, []
    for pub, y, e in pts:
        near = [q[1] for q in pts if abs((q[0] - pub).total_seconds()) <= 3 * 86400]
        # the average (not the median: most shorts get 0 views, and a median of 0 made everything look "better")
        base = sum(near) / len(near) if len(near) >= 5 else mid_all
        r = y - base
        st = e.get("story") or {}
        scored.append((r, e.get("title") or "", int(e.get("views") or 0), st.get("hashtags") or []))
        feats = features(st.get("spec"), e.get("title"), e.get("duration"), pub)
        tags = [str(h).lower().lstrip("#") for h in (st.get("hashtags") or []) if h]
        feats += [("tag", h, 1.0) for h in tags]
        for kind, val, w in feats:
            t = table.setdefault(kind, {}).setdefault(val, [0.0, 0.0, 0, 0.0])
            t[0] += w * r
            t[1] += w
            t[2] += 1
            t[3] += float(e.get("views") or 0)
    rs = [r for r, *_ in scored]
    mu = sum(rs) / len(rs)
    sd = max(0.15, (sum((r - mu) ** 2 for r in rs) / max(1, len(rs) - 1)) ** 0.5)   # how noisy one short is
    kinds = {}
    for kind, vals in table.items():
        kinds[kind] = {}
        for val, (s_, wsum, n, tot) in vals.items():
            eff = s_ / (wsum + K)
            se = sd / math.sqrt(wsum + K)
            sure = 0.5 * (1 + math.erf(eff / se / math.sqrt(2)))           # chance it really is better than average
            used = math.copysign(max(0.0, abs(eff) - Z * se), eff)         # the part that is not luck
            verdict = "better" if used > 0.05 else "worse" if used < -0.05 else ("new" if n < 3 else "testing")
            kinds[kind][val] = {"effect": round(eff, 3), "se": round(se, 3), "used": round(used, 3),
                                "sure": round(sure, 2), "verdict": verdict, "n": n, "avg_views": round(tot / max(1, n), 1)}
    scored.sort(key=lambda x: -x[0])
    best = [{"title": t, "views": v} for r, t, v, _h in scored[:8] if r > 0 and t and v >= 3]  # one lucky view isn't a lesson
    worst = [{"title": t, "views": v} for r, t, v, _h in scored[::-1][:6] if r < 0 and t]
    zero = sum(1 for _p, _y, e in pts if not (e.get("views") or 0)) / len(pts)
    signal = "weak" if zero > 0.6 or sd > 1.5 else "ok"
    return {"n": len(pts), "at": now.isoformat(), "kinds": kinds, "best_titles": best, "worst_titles": worst,
            "noise": round(sd, 2), "zero_share": round(zero, 2), "signal": signal}


def writer_notes():
    """What the title writer should copy and avoid, learned from this channel (empty until there is data)."""
    t = current()
    if not t.get("kinds"):
        return ""
    lines = []
    if t.get("best_titles"):
        lines.append("Titles that got the MOST views on this channel (write in a similar style, never copy them):")
        lines += [f"- {b['title']}" for b in t["best_titles"][:6]]
    if t.get("worst_titles"):
        lines.append("Titles that got the FEWEST views (avoid this style):")
        lines += [f"- {b['title']}" for b in t["worst_titles"][:4]]
    tags = sorted(((v.get("used", v["effect"]), k) for k, v in (t["kinds"].get("tag") or {}).items() if v["n"] >= 3),
                  reverse=True)
    good = [k for e, k in tags if e > 0.02][:8]
    bad = [k for e, k in tags if e < -0.02][-5:]
    if good:
        lines.append("Hashtags that bring views here (use 2-3 of them when they fit): " + ", ".join(good))
    if bad:
        lines.append("Hashtags that did badly (avoid): " + ", ".join(bad))
    return "\n".join(lines)


LONG_BUCKET = "36-60 s"
XL_BUCKET = "61-90 s"
# minutes of render time a short takes (18 cloud machines in parallel) - the day has room for ~1,100
COST = {"normal": 20, "long": 50, "xl": 75}
BUDGET = 1250     # renders run around the clock now (next day's batch starts the day before): 24 h minus ~15 %


def length_plan(funny, test_long=8, test_xl=4, others=0):
    """How many of today's funny shorts are normal (20-35 s), long (45-58 s) and extra long (63-88 s).
    Each length keeps a fair test until the views PROVE one better or worse (error bars, like everything else);
    then the winner gets most shorts and the others keep a few so it can change its mind. The cloud render time
    caps how many long ones fit in a day."""
    t = current()
    L = (t.get("kinds") or {}).get("length") or {}
    norm = [v for k, v in L.items() if k not in (LONG_BUCKET, XL_BUCKET) and v["n"] >= 5]
    base = sum(v["effect"] * v["n"] for v in norm) / sum(v["n"] for v in norm) if norm else 0.0
    plan, why = {"long": test_long, "xl": test_xl}, []
    for arm, key, label in (("long", LONG_BUCKET, "45-58 s"), ("xl", XL_BUCKET, "63-88 s")):
        v = L.get(key)
        if not v or v["n"] < 12 or not norm:
            why.append(f"{label}: testing ({v['n'] if v else 0} so far)")
            continue
        diff, se = v["effect"] - base, (v.get("se") or 0.3) * 1.15
        pct = round((math.exp(diff) - 1) * 100)
        if diff - Z * se > 0.02:
            plan[arm] = round(funny * 0.6)
            why.append(f"{label}: proven better (+{pct}%)")
        elif diff + Z * se < -0.02:
            plan[arm] = 2
            why.append(f"{label}: proven worse ({pct}%), a few to re-check")
        else:
            why.append(f"{label}: no proven difference yet ({pct:+d}%)")
    n_long, n_xl = plan["long"], plan["xl"]
    if n_long + n_xl > funny:                      # both proven better: share the funny shorts
        n_xl = min(n_xl, funny // 2)
        n_long = funny - n_xl
    # keep the day's render time inside the budget (the `others` = lesson shorts are normal length);
    # real average render minutes per length (renderlearn) replace the estimates once there are enough
    try:
        from . import db
        c = dict(COST, **((db.settings().get("render_health") or {}).get("minutes") or {}))
    except Exception:  # noqa: BLE001
        c = dict(COST)

    def cost(a, b):
        return a * c["long"] + b * c["xl"] + (funny - a - b + others) * c["normal"]
    while cost(n_long, n_xl) > BUDGET and n_xl > 1:
        n_xl -= 1
    while cost(n_long, n_xl) > BUDGET and n_long > 1:
        n_long -= 1
    return {"long": max(0, n_long), "xl": max(0, n_xl)}, " · ".join(why)


def long_plan(funny, test=10):
    """Old name, kept for callers: number of long (45-58 s) shorts."""
    p, why = length_plan(funny)
    return p["long"], why


def fit(spec, title, duration, t):
    """How well a finished short suits publish time t: only PROVEN time x character/story/place/... effects
    count (1.0 = no difference known)."""
    tab = current()
    if not tab.get("kinds"):
        return 1.0
    x = 0.0
    for k, v, w in features(spec, title, duration, t):
        if not k.startswith("when_"):
            continue
        e = (tab["kinds"].get(k) or {}).get(v)
        if e and e.get("n", 0) >= 3:
            x += w * e.get("used", 0.0)
    return math.exp(max(-CLAMP, min(CLAMP, x)))


def lean(kind, value):
    """How much to favour `value` when choosing (1.0 = no data / average)."""
    t = current()
    vals = (t.get("kinds") or {}).get(kind) or {}
    e = vals.get(value)
    if not e:
        return math.exp(TRY_BONUS) if vals else 1.0      # never tried yet: give it a go
    if "used" not in e:                                   # older table (before error bars)
        return math.exp(max(-CLAMP, min(CLAMP, e["effect"] * 0.5)))
    if e["n"] < 3:
        return math.exp(TRY_BONUS)
    return math.exp(max(-CLAMP, min(CLAMP, e["used"])))


def pick(rnd, options, kind, extra=None):
    """Weighted random choice that leans towards what works (extra: optional per-option multiplier)."""
    options = list(options)
    if not options:
        return None
    ws = [lean(kind, o) * (extra(o) if extra else 1.0) for o in options]
    return rnd.choices(options, weights=ws, k=1)[0]


def order(rnd, options, kind):
    """Shuffle where better things tend to come first (weighted random order)."""
    keyed = [(rnd.random() ** (1.0 / max(1e-6, lean(kind, o))), o) for o in options]
    return [o for _, o in sorted(keyed, reverse=True)]


def current():
    """Latest trends (saved by update(); one read per run)."""
    global _CACHE
    if _CACHE is None:
        try:
            from . import db
            _CACHE = db.settings().get("trends") or {}
            if isinstance(_CACHE, str):
                import json
                _CACHE = json.loads(_CACHE)
        except Exception:  # noqa: BLE001 - no data: plain variety
            _CACHE = {}
    return _CACHE


def _label(kind, val):
    from .plan3d import NAMES
    if kind == "char":
        return NAMES.get(val, val)
    if kind == "title":
        return TITLE_NAMES.get(val, val)
    return str(val).replace("_", " ")


def summary(t):
    """One line for the activity log."""
    if not t.get("kinds"):
        return f"📈 What's working: {t.get('note', 'not enough data yet')} ({t.get('n', 0)} shorts so far)"
    parts = []
    for kind in ("story", "place", "char", "title", "type", "length", "tag"):
        vals = [(v.get("used", v["effect"]), k) for k, v in (t["kinds"].get(kind) or {}).items() if v["n"] >= 3]
        if len(vals) < 2:
            continue
        vals.sort(reverse=True)
        best = ", ".join(f"{_label(kind, k)} (x{math.exp(e):.1f})" for e, k in vals[:2] if e > 0.05)
        worst = _label(kind, vals[-1][1]) if vals[-1][0] < -0.05 else ""
        if best or worst:
            parts.append(f"{KINDS[kind]}: " + (best or "–") + (f"; proven weak {worst}" if worst else ""))
    weak = " · views too low to tell much apart yet, so everything keeps being tested" if t.get("signal") == "weak" else ""
    return f"📈 What's working ({t['n']} shorts): " + (" · ".join(parts) or "nothing proven yet") + weak


def update():
    """Re-learn from every published short, save it for the planner + app, log the headline."""
    global _CACHE
    from . import db
    since = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    rows = db.select("episodes", "select=publish_at,views,likes,duration,title,story&status=eq.published"
                                 f"&youtube_id=not.is.null&publish_at=gte.{since}&limit=2000")
    t = learn(rows)
    old = current()
    _CACHE = t
    db.upsert("settings", {"key": "trends", "value": t}, "key")
    if (old.get("at") or "")[:10] != t["at"][:10]:  # the headline once a day
        db.log(summary(t)[:500])
    return t


if __name__ == "__main__":
    import json
    t = update()
    print(json.dumps(t, indent=1)[:4000])
    print(summary(t))
