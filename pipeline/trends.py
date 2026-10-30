"""What's working: learns from our own published shorts which stories, places, characters, title styles,
lengths and short types get more views, so new shorts lean towards them (and the app can show it).

How a short is judged (fair to every short):
- views after its first day (v24; older shorts: their views one day in, from the daily history),
- minus the publish-time effect (schedule.py already learns that, so a good slot doesn't count as a good story),
- compared with the shorts published around the same days (the channel growing doesn't flatter newer shorts).
Every feature gets a cautious score: few shorts behind it -> pulled towards "average" (no knee-jerk changes),
and choices only lean (x0.55 ... x1.8), never lock in, so new things keep getting a fair test."""
import math
import re
from datetime import datetime, timedelta, timezone

K = 3.0              # shorts it takes before a feature's own result counts half
CLAMP = 0.6          # strongest lean: e^0.6 = x1.8 (and x0.55 the other way)
MIN_SHORTS = 8       # below this, no learning yet
KINDS = {"tag": "Hashtags", "story": "Stories", "type": "Funny vs lesson", "place": "Places", "char": "Characters",
         "title": "Title styles", "length": "Length", "sky": "Time of day in the short"}
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
    return "20-25 s" if seconds < 26 else "26-35 s" if seconds < 36 else "36-60 s"


def features(spec, title, duration=None):
    """(kind, value, weight) for one short."""
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
    mid_all = ys[len(ys) // 2]
    table, scored = {}, []
    for pub, y, e in pts:
        near = sorted(q[1] for q in pts if abs((q[0] - pub).total_seconds()) <= 3 * 86400)
        base = near[len(near) // 2] if len(near) >= 5 else mid_all
        r = y - base
        st = e.get("story") or {}
        scored.append((r, e.get("title") or "", int(e.get("views") or 0), st.get("hashtags") or []))
        feats = features(st.get("spec"), e.get("title"), e.get("duration"))
        tags = [str(h).lower().lstrip("#") for h in (st.get("hashtags") or []) if h]
        feats += [("tag", h, 1.0) for h in tags]
        for kind, val, w in feats:
            t = table.setdefault(kind, {}).setdefault(val, [0.0, 0.0, 0, 0.0])
            t[0] += w * r
            t[1] += w
            t[2] += 1
            t[3] += float(e.get("views") or 0)
    kinds = {}
    for kind, vals in table.items():
        kinds[kind] = {val: {"effect": round(s / (wsum + K), 3), "n": n, "avg_views": round(tot / max(1, n))}
                       for val, (s, wsum, n, tot) in vals.items()}
    scored.sort(key=lambda x: -x[0])
    best = [{"title": t, "views": v} for r, t, v, _h in scored[:8] if r > 0 and t]
    worst = [{"title": t, "views": v} for r, t, v, _h in scored[::-1][:6] if r < 0 and t]
    return {"n": len(pts), "at": now.isoformat(), "kinds": kinds, "best_titles": best, "worst_titles": worst}


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
    tags = sorted(((v["effect"], k) for k, v in (t["kinds"].get("tag") or {}).items() if v["n"] >= 3), reverse=True)
    good = [k for e, k in tags if e > 0.03][:8]
    bad = [k for e, k in tags if e < -0.1][-5:]
    if good:
        lines.append("Hashtags that bring views here (use 2-3 of them when they fit): " + ", ".join(good))
    if bad:
        lines.append("Hashtags that did badly (avoid): " + ", ".join(bad))
    return "\n".join(lines)


LONG_BUCKET = "36-60 s"


def long_plan(funny, test=10):
    """How many of today's funny shorts should be LONG (45-58 s). Testing phase: `test` a day. Once enough long and
    normal shorts have a day of views, it follows the result: clearly better -> more long ones, clearly worse -> just
    a few (so it keeps checking), about the same -> a fair mix."""
    t = current()
    L = (t.get("kinds") or {}).get("length") or {}
    lo = L.get(LONG_BUCKET)
    others = [v for k, v in L.items() if k != LONG_BUCKET and v["n"] >= 5]
    if not lo or lo["n"] < 15 or not others:
        return min(funny, test), "testing long shorts"
    base = sum(v["effect"] * v["n"] for v in others) / sum(v["n"] for v in others)
    diff = lo["effect"] - base
    if diff > 0.08:
        n, why = round(funny * 0.75), f"long shorts win (+{round((math.exp(diff) - 1) * 100)}%)"
    elif diff < -0.08:
        n, why = min(funny, 3), f"long shorts do worse ({round((math.exp(diff) - 1) * 100)}%), keeping a few to re-check"
    else:
        n, why = min(funny, max(3, round(funny * 0.4))), "long and normal shorts do about the same"
    return max(0, min(funny, n)), why


def lean(kind, value):
    """How much to favour `value` when choosing (1.0 = no data / average)."""
    t = current()
    e = ((t.get("kinds") or {}).get(kind) or {}).get(value)
    if not e:
        return 1.0
    return math.exp(max(-CLAMP, min(CLAMP, e["effect"])))


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
        vals = [(v["effect"], k) for k, v in (t["kinds"].get(kind) or {}).items() if v["n"] >= 2]
        if len(vals) < 2:
            continue
        vals.sort(reverse=True)
        best = ", ".join(f"{_label(kind, k)} (x{math.exp(e):.1f})" for e, k in vals[:2] if e > 0.05)
        worst = _label(kind, vals[-1][1]) if vals[-1][0] < -0.05 else ""
        if best or worst:
            parts.append(f"{KINDS[kind]}: " + (best or "–") + (f"; weakest {worst}" if worst else ""))
    return f"📈 What's working ({t['n']} shorts): " + (" · ".join(parts) or "no clear winners yet")


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
