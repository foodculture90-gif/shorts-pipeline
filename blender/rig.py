"""Soft rig + secondary animation, so the characters move like a TV cartoon (Paw Patrol / Bluey) instead of
stiff toys:

- the HEAD is its own part: it tilts, nods and turns (curious head tilts, moods: sad droops, proud lifts,
  surprised pulls back) and lags a little behind big body moves (follow-through)
- EARS, TAILS and TUFTS flop and bounce: a damped spring driven by how the body accelerates (take-off, landing,
  quick turns), so they keep moving for a moment after the body stops
- poses change "pose to pose": hold, then an eased move to the next pose (no constant floaty drift)

build(ch)   right after a character is made: head pivot + hooks into the sculpted body (the body is one smooth
            mesh, so the head and the floppy parts bend it softly where they join)
animate(end) after the whole story is animated: bakes the head acting + springs into keyframes"""
import json
import math
import random

import bpy
from mathutils import Matrix, Vector

HEAD_POSE = {  # mood -> head (pitch forward +, roll sideways, yaw) in degrees
    "neutral": (0, 0, 0), "happy": (-3, 7, 0), "sad": (13, -4, 0), "angry": (7, 0, 0), "surprised": (-9, 0, 0),
    "scared": (-6, 0, 0), "sleepy": (16, 9, 0), "sly": (5, -9, 6), "proud": (-11, 3, 0),
}


def _empty(name, loc, parent):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.matrix_parent_inverse = Matrix.Identity(4)
    o.location = loc
    o.empty_display_size = 0.05
    return o


def _hook(body, emp, group, name):
    bpy.context.view_layer.update()
    md = body.modifiers.new(name, "HOOK")
    md.object = emp
    md.vertex_group = group
    md.falloff_type = "NONE"
    md.matrix_inverse = emp.matrix_world.inverted() @ body.matrix_world   # no change at rest
    return md


def build(ch):
    piv = ch["piv"]
    head_z = float(ch.get("head") or 0.8)
    neck = max(0.3, head_z - 0.3)
    arms, feet = set(ch.get("arms") or []), set(ch.get("feet") or [])
    skins = [o for o in piv.children if o.type == "MESH" and o.name.endswith("_skin")]
    hd_act = _empty(ch["name"] + "_hdact", (0, 0, neck), piv)     # mood poses (keyed by feel)
    hd = _empty(ch["name"] + "_hd", (0, 0, 0), hd_act)            # idle acting + follow-through (baked)
    ch["hd_act"], ch["hd"], ch["neck"] = hd_act, hd, neck
    bpy.context.view_layer.update()
    # everything stuck on the head (eyes, brows, mouth, nose, hair, hats, whiskers...) rides on it
    for o in list(piv.children):
        if o in (hd_act, hd) or o in skins or o in arms or o in feet or o.type in ("CURVES", "LIGHT", "CAMERA"):
            continue
        if o.location.z > neck + 0.04:
            mw, old = o.matrix_world.copy(), o.location.copy()
            o.parent = hd
            o.matrix_parent_inverse = Matrix.Identity(4)
            o.matrix_world = mw
            bpy.context.view_layer.update()
            d = o.location - old            # rest positions remembered by the acting code move along
            if "z0" in o:
                o["z0"] = float(o["z0"]) + d.z
            if "home" in o:
                o["home"] = tuple(float(v) + dv for v, dv in zip(o["home"], d))
    ch["flex"] = []
    for body in skins:
        me = body.data
        flex = json.loads(body.get("flex", "[]"))
        # floppy parts first (rest space), then the head carries them along
        for fx in flex:
            p = Vector(fx["pivot"])
            emp = _empty(f"{body.name}_{fx['group']}", p, piv)
            _hook(body, emp, fx["group"], fx["group"])
            tip = Vector(fx["tip"])
            ch["flex"].append({"obj": emp, "kind": fx["kind"], "side": (1 if p.x > 0.02 else -1 if p.x < -0.02 else 0),
                               "len": max(0.05, (tip - p).length)})
        # the head region of the body: soft blend across the neck
        n = len(me.vertices)
        co = [0.0] * (n * 3)
        me.vertices.foreach_get("co", co)
        vg = body.vertex_groups.new(name="head")
        levels = {}
        for i in range(n):
            t = (co[i * 3 + 2] - (neck - 0.07)) / 0.17
            if t <= 0:
                continue
            t = 1.0 if t >= 1 else t * t * (3 - 2 * t)
            levels.setdefault(round(t * 24), []).append(i)
        for lv, idx in levels.items():
            vg.add(idx, lv / 24.0, "REPLACE")
        _hook(body, hd, "head", "head")


def head_pose(ch, f, mood, d=5):
    """Head part of an expression (called from toon.feel)."""
    h = ch.get("hd_act")
    if h is None:
        return
    p, r, y = HEAD_POSE.get(mood, HEAD_POSE["neutral"])
    h.keyframe_insert("rotation_euler", frame=f - d)
    h.rotation_euler = (math.radians(p), math.radians(r), math.radians(y))
    h.keyframe_insert("rotation_euler", frame=f)


# ------------------------------------------------------------------ motion sampling (no depsgraph: fast)
def _ev(o, path, idx, f):
    ad = o.animation_data
    fc = ad.action.fcurves.find(path, index=idx) if ad and ad.action else None
    return fc.evaluate(f) if fc else getattr(o, path)[idx]


def _track(ch, f):
    """Where the head is (world-ish) and which way the character faces, at frame f."""
    r, p = ch["root"], ch["piv"]
    rz = _ev(r, "rotation_euler", 2, f)
    s = r.scale[0]
    sz = _ev(p, "scale", 2, f)
    px, py, pz = (_ev(p, "location", i, f) for i in range(3))
    lx = _ev(p, "rotation_euler", 0, f)   # lean forward/back
    ly = _ev(p, "rotation_euler", 1, f)   # lean sideways
    hz = ch.get("neck", 0.5) + 0.25
    hx, hy, hzz = px + math.sin(ly) * hz * sz, py - math.sin(lx) * hz * sz, pz + hz * sz
    c, sn = math.cos(rz), math.sin(rz)
    x = _ev(r, "location", 0, f) + s * (c * hx - sn * hy)
    y = _ev(r, "location", 1, f) + s * (sn * hx + c * hy)
    z = _ev(r, "location", 2, f) + s * hzz
    return Vector((x, y, z)), rz


def _spring(drive, w, zeta, lim):
    """Damped spring pushed by `drive` (one value per frame); returns the angle per frame."""
    th = v = 0.0
    out = []
    for a in drive:
        acc = a - w * w * th - 2 * zeta * w * v
        v += acc
        th += v
        th = max(-lim, min(lim, th))
        out.append(th)
    return out


def _bake(o, idx, f0, vals, base=0.0, step=2):
    for k in range(0, len(vals), step):
        o.rotation_euler[idx] = base + vals[k]
        o.keyframe_insert("rotation_euler", index=idx, frame=f0 + k)


def _idle_acting(rnd, n):
    """Pose-to-pose head acting: hold, then an eased move to a new small tilt/nod/turn (every 1.5-3 s)."""
    P, R, Y = [0.0] * n, [0.0] * n, [0.0] * n
    cur, f = (0.0, 0.0, 0.0), rnd.randint(10, 30)
    while f < n:
        nxt = (math.radians(rnd.uniform(-4, 6)), math.radians(rnd.choice((-1, 1)) * rnd.uniform(3, 10)),
               math.radians(rnd.uniform(-12, 12)))
        if rnd.random() < 0.3:   # sometimes back to straight
            nxt = (0.0, 0.0, 0.0)
        dur = rnd.randint(8, 13)
        for k in range(dur):
            if f + k >= n:
                break
            t = (k + 1) / dur
            t = t * t * (3 - 2 * t)
            for arr, a, b in ((P, cur[0], nxt[0]), (R, cur[1], nxt[1]), (Y, cur[2], nxt[2])):
                arr[f + k] = a + (b - a) * t
        hold = rnd.randint(28, 62)
        for k in range(dur, dur + hold):
            if f + k < n:
                P[f + k], R[f + k], Y[f + k] = nxt
        cur, f = nxt, f + dur + hold
    return P, R, Y


def _eye_darts(ch, others, end, rnd):
    """Real actors' eyes never freeze: quick darts to the friend, back to the camera, a glance away - held in
    between. Only where the story isn't already moving the eyes (look() keys win)."""
    import toon as T
    pups = ch.get("pupils") or []
    if not pups:
        return
    busy = set()
    for p in pups:
        ad = p.animation_data
        fc = ad.action.fcurves.find("location", index=0) if ad and ad.action else None
        if fc:
            busy |= {int(round(k.co[0])) for k in fc.keyframe_points}
    x0 = ch["root"].location.x
    friend = min(others, key=lambda o: abs(o["root"].location.x - x0), default=None)
    toward = (1 if friend["root"].location.x > x0 else -1) if friend else 0
    f = rnd.randint(12, 30)
    while f < end - 6:
        hold = rnd.randint(18, 55)
        if any(abs(b - f) < 14 or f <= b <= f + hold for b in busy):
            f += 10
            continue
        r = rnd.random()
        if r < 0.5 and toward:
            dx, dz = toward * rnd.uniform(0.03, 0.045), rnd.uniform(-0.006, 0.008)
        elif r < 0.8:
            dx, dz = rnd.uniform(-0.008, 0.008), rnd.uniform(-0.004, 0.006)
        else:
            dx, dz = rnd.choice((-1, 1)) * rnd.uniform(0.025, 0.045), rnd.uniform(-0.015, 0.02)
        for p in pups:   # hold the current spot until the dart (a quick 2-frame move)
            ad = p.animation_data
            for i in (0, 2):
                fc = ad.action.fcurves.find("location", index=i) if ad and ad.action else None
                p.location[i] = fc.evaluate(f - 2) if fc else p.location[i]
            p.keyframe_insert("location", frame=f - 2)
        T.look(ch, f, dx, dz)
        f += hold


def animate(end):
    import toon as T
    n = end + 2
    for i, ch in enumerate(T.CHARS):
        try:
            _eye_darts(ch, [o for o in T.CHARS if o is not ch and o.get("pupils")], end,
                       random.Random(sum(map(ord, ch["name"])) * 5 + i))
        except Exception as ex:  # noqa: BLE001
            print("eye darts skipped:", ch["name"], ex)
    for i, ch in enumerate(T.CHARS):
        if ch.get("hd") is None:
            continue
        rnd = random.Random(sum(map(ord, ch["name"])) * 11 + i)
        pts = [_track(ch, f) for f in range(0, n + 2)]
        acc_f, acc_s, acc_z, turn = [], [], [], []
        for f in range(1, n + 1):
            (p0, r0), (p1, r1), (p2, r2) = pts[f - 1], pts[f], pts[f + 1]
            a = p2 - 2 * p1 + p0
            c, s = math.cos(-r1), math.sin(-r1)
            ax, ay = c * a.x - s * a.y, s * a.x + c * a.y    # in the character's own frame
            acc_s.append(ax)
            acc_f.append(ay)
            acc_z.append(a.z)
            turn.append((r2 - 2 * r1 + r0))
        # head: idle acting + a little lag behind body moves
        P, R, Y = _idle_acting(rnd, n)
        lag_p = _spring([2.2 * z + 1.6 * y for z, y in zip(acc_z, acc_f)], 0.75, 0.55, 0.3)
        lag_r = _spring([-2.0 * x for x in acc_s], 0.75, 0.55, 0.25)
        hd = ch["hd"]
        _bake(hd, 0, 1, [p + q for p, q in zip(P, lag_p)])
        _bake(hd, 1, 1, [r + q for r, q in zip(R, lag_r)])
        _bake(hd, 2, 1, Y)
        # floppy parts: springs (ears flop down on landing, swing back on take-off, lag on turns)
        for fx in ch.get("flex") or []:
            o, side, kind = fx["obj"], fx["side"], fx["kind"]
            soft = min(2.0, 0.6 + fx["len"] * 4)      # long ears swing more, slower
            w = 0.62 / math.sqrt(soft)
            if kind == "tail":
                pitch = _spring([-6 * z * soft for z in acc_z], w, 0.22, 0.6)
                wag_ph = rnd.uniform(0, math.tau)
                yaw = _spring([5 * x * soft - 3 * t for x, t in zip(acc_s, turn)], w, 0.22, 0.7)
                yaw = [y_ + math.radians(9) * math.sin(f * math.tau / 16 + wag_ph) for f, y_ in enumerate(yaw)]
                _bake(o, 0, 1, pitch)
                _bake(o, 2, 1, yaw)
                continue
            stiff = 0.5 if kind == "tuft" else 1.0
            pitch = _spring([(4 * z + 3.2 * y) * soft * stiff for z, y in zip(acc_z, acc_f)], w, 0.22, 0.55)
            roll = _spring([(side * 4.8 * z - 4 * x - 2 * t) * soft * stiff for z, x, t in zip(acc_z, acc_s, turn)],
                           w, 0.22, 0.55)
            f = rnd.randint(30, 90)   # little ear twitches every few seconds (alive, like a real pup)
            arr = [0.0] * n
            while kind == "ear" and f < n - 8:
                for k, v in enumerate((0.0, 0.16, 0.22, 0.1, -0.04, 0.0)):
                    arr[f + k] = v * side
                f += rnd.randint(70, 150)
            twitch = arr
            _bake(o, 0, 1, pitch)
            _bake(o, 1, 1, [r + t for r, t in zip(roll, twitch)])
