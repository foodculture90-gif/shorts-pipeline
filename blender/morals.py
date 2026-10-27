"""Moral stories: longer wordless shorts (~22-26 s) with a gentle lesson kids can SEE - no text, no talking.

Each story builds its own staging, acting, camera and sound cues with the toon kit, like the gags, and returns
(last_frame, thumbnail_frame). The planner uses one moral story as the whole short.
"""
import math
import random

import toon as T
from gags import _arm, _confetti, _flower, _two


# --------------------------------------------------------------------------- little acting helpers
def _sad(ch, f, d=6, sound=True):
    T.brows(ch, f, -0.035, d)
    for e in ch["eyes"]:
        T.key(e, "scale", f - d, tuple(e.scale))
        T.key(e, "scale", f, (1, 1, 0.62))
    T.mouth_set(ch, f, 0.0)
    T.lean(ch, f, 9, d, axis=0)
    if sound:
        T.sfx(f, "wahwah")


def _cheer_up(ch, f, d=6):
    T.brows(ch, f, 0.0, d)
    T.eyes_norm(ch, f, d)
    T.lean(ch, f, 0, d, axis=0)


def _determined(ch, f, d=5):
    T.brows(ch, f, -0.03, d)
    for e in ch["eyes"]:
        T.key(e, "scale", f - d, tuple(e.scale))
        T.key(e, "scale", f, (1.05, 1, 0.8))
    T.mouth_set(ch, f, 0.0)


def _nod(ch, f0, times=2):
    for k in range(times):
        T.lean(ch, f0 + k * 8 + 4, 12, 4, axis=0)
        T.lean(ch, f0 + k * 8 + 8, 0, 4, axis=0)


def _shake_head(ch, f0, times=2):
    r = ch["root"]
    base = r.rotation_euler[2]
    for k in range(times * 2):
        T.key(r, "rotation_euler", f0 + k * 5, (0, 0, base + (0.35 if k % 2 else -0.35)))
    T.key(r, "rotation_euler", f0 + times * 10 + 4, (0, 0, base))


def _tears(ch, f0, f1, name):
    m = T.mat("#7FD3FF", 0.05, coat=1.0)
    n = 0
    for f in range(f0, f1, 12):
        for k, e in enumerate(ch["eyes"]):
            ex, ey, ez = e.location
            dr = T.sphere(f"{name}{n}", 0.03, (ex * 1.05, ey - 0.03, ez - 0.12), m, ch["piv"], scale=(0.8, 0.8, 1.25),
                          sub=0, seg=16)
            n += 1
            T.show(dr, 1, False)
            T.show(dr, f + k * 3, True)
            T.key(dr, "location", f + k * 3, (ex * 1.05, ey - 0.03, ez - 0.12))
            T.key(dr, "location", f + k * 3 + 10, (ex * 1.2, ey - 0.04, ez - 0.48))
            T.show(dr, f + k * 3 + 11, False)
        T.sfx(f, "squeak")


def _heart(name, loc, size, m, parent=None):
    h = T.empty(name, loc, parent)
    for s in (-1, 1):
        T.sphere(f"{name}_l{s}", size * 0.56, (s * size * 0.36, 0, size * 0.22), m, h, sub=1, seg=20)
    T.cone(f"{name}_c", size * 0.8, 0.0, size * 0.95, (0, 0, -size * 0.3), m, h, rot=(math.pi, 0, 0), scale=(1, 0.55, 1))
    return h


def _hearts(name, f, loc, n=5):
    m = T.mat("#FF4D8D", 0.3, coat=0.6, emit=0.5)
    rnd = random.Random(f * 7 + n)
    for i in range(n):
        x0 = loc[0] + rnd.uniform(-0.4, 0.4)
        z0 = loc[2] + rnd.uniform(-0.1, 0.15)
        h = _heart(f"{name}{i}", (x0, loc[1] - 0.15, z0), 0.09, m)
        st = f + i * 4
        T.show(h, 1, False)
        T.show(h, st, True)
        T.key(h, "scale", st, (0.1, 0.1, 0.1))
        T.key(h, "scale", st + 5, (1.25, 1.25, 1.25))
        T.key(h, "scale", st + 9, (1, 1, 1))
        T.key(h, "location", st, (x0, loc[1] - 0.15, z0))
        T.key(h, "location", st + 34, (x0 + rnd.uniform(-0.25, 0.25), loc[1] - 0.15, z0 + 0.9))
        T.key(h, "scale", st + 34, (0.4, 0.4, 0.4))
        T.show(h, st + 35, False)
    T.sfx(f, "sparkle")
    T.sfx(f + 3, "twinkle")


def _hug(a, b, f, xa, xb, y=None):
    """The two walk together and squeeze."""
    T.hop(a, f, a["root"].location[0], xa, 0.15, 8, y0=y, y1=y, sound=False)
    T.hop(b, f, b["root"].location[0], xb, 0.15, 8, y0=y, y1=y, sound=False)
    for ch in (a, b):
        T.arms(ch, f + 10, 1.0, fwd=-1.2, d=4)
        T.eyes_happy(ch, f + 11)
        T.squash(ch, f + 14, 0.12, 3, 8)
        T.arms(ch, f + 30, 0.0, d=5)
    T.sfx(f + 12, "squeak")
    _hearts(f"hug{f}", f + 12, ((xa + xb) / 2, 0.2, 1.1))


def _night(f_dusk, f_dark, f_dawn, f_day, name="night"):
    """Day -> starry night -> morning: the sky and every light fade down and back up (shows time passing)."""
    sc = T.sc
    marks = ((f_dusk, 1.0), (f_dark, 0.13), (f_dawn, 0.13), (f_day, 1.0))
    try:
        for n in sc.world.node_tree.nodes:
            if n.type == "BACKGROUND":
                inp = n.inputs["Strength"]
                s0 = inp.default_value
                for f, k in marks:
                    inp.default_value = s0 * k
                    inp.keyframe_insert("default_value", frame=f)
                inp.default_value = s0
    except Exception as e:  # noqa: BLE001
        print("night sky:", e)
    for ob in list(sc.objects):
        if ob.type == "LIGHT":
            e0 = ob.data.energy
            for f, k in marks:
                ob.data.energy = e0 * k
                ob.data.keyframe_insert("energy", frame=f)
            ob.data.energy = e0
    sky = T.empty(name, (0, 12.5, 0))
    T.sphere(name + "_moon", 0.55, (2.6, 0, 6.2), T.mat("#FFF4C2", 0.5, emit=3.0), sky, sub=1)
    rnd = random.Random(f_dark)
    sm = T.mat("#FFF3A8", 0.3, emit=4.0)
    for i in range(16):
        T.star(f"{name}_st{i}", rnd.uniform(0.07, 0.14), (rnd.uniform(-5.5, 5.5), -0.2, rnd.uniform(3.0, 8.5)), sm, sky)
    T.show(sky, 1, False)
    T.show(sky, (f_dusk + f_dark) // 2, True)
    T.show(sky, (f_dawn + f_day) // 2, False)
    T.sfx(f_dark, "twinkle")
    T.sfx(f_day, "tweet")


def _sleep(ch, f0, f1):
    T.eyes_happy(ch, f0)
    T.mouth_set(ch, f0, 0.0)
    T.lean(ch, f0, 10, 6, axis=1)
    for f in range(f0 + 6, f1 - 10, 24):
        T.key(ch["piv"], "scale", f, (1, 1, 1))
        T.key(ch["piv"], "scale", f + 12, (1.04, 1.04, 0.96))
        T.sfx(f + 4, "snore")
    T.lean(ch, f1, 0, 6, axis=1)
    T.eyes_norm(ch, f1 + 2)


def _water(name, ch, f, target_x, side=1):
    """A watering can appears in the hand and pours drops on target_x."""
    can = T.empty(name, (side * 0.45, -0.25, 0.55), ch["root"])
    T.cyl(name + "_body", 0.1, 0.16, (0, 0, 0), T.mat("#4DA6FF", 0.35, coat=0.4), can, bevel=0.01)
    T.cone(name + "_spout", 0.025, 0.012, 0.18, (side * 0.15, 0, 0.04), T.mat("#4DA6FF", 0.35, coat=0.4), can,
           rot=(0, side * 1.1, 0))
    T.show(can, 1, False)
    T.show(can, f, True)
    T.key(can, "rotation_euler", f, (0, 0, 0))
    T.key(can, "rotation_euler", f + 6, (0, side * 0.7, 0))
    T.key(can, "rotation_euler", f + 30, (0, side * 0.7, 0))
    T.key(can, "rotation_euler", f + 34, (0, 0, 0))
    T.show(can, f + 36, False)
    dm = T.mat("#7FD3FF", 0.05, coat=1.0)
    for i in range(6):
        d = T.sphere(f"{name}_drop{i}", 0.025, (target_x - 0.05 + 0.02 * i, -0.05, 0.6), dm, sub=0, seg=16)
        st = f + 6 + i * 4
        T.show(d, 1, False)
        T.show(d, st, True)
        T.key(d, "location", st, (target_x - 0.06 + 0.025 * i, -0.05, 0.62))
        T.key(d, "location", st + 8, (target_x - 0.06 + 0.025 * i, -0.05, 0.05))
        T.show(d, st + 9, False)
    T.sfx(f + 8, "bubble")
    T.sfx(f + 18, "bubble")


# --------------------------------------------------------------------------- 1. good things take time
def patience(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.62, 0.15)
    fr = T.make_character(spec["friend"], 2.1, 0.25)
    T.turn(hero, 1, 25, 1)
    T.turn(fr, 1, -25, 1)
    mx = 0.12
    T.sphere("mound", 0.2, (mx, -0.02, 0.0), T.mat("#8A5A3C", 0.95), scale=(1.3, 1.1, 0.35), sub=1)
    col = T.PROP_COLOR or T.VAR.choice(["#FF6B8B", "#FFD23F", "#B57BFF", "#FF8A3D"])
    plant, head, petals = _flower("plant", (mx, -0.02, 0.04), col)
    T.key(plant, "scale", 1, (0.001, 0.001, 0.001))
    T.show(head, 1, False)
    seed = T.sphere("seed", 0.04, (-0.2, -0.3, 0.55), T.mat("#7A4A22", 0.6), hero["root"], scale=(1, 1, 1.3), sub=0)

    p, t = _two([-0.75, 0.8], 26, 0.8, margin=0.5)
    T.shot(cam, tgt, 1, 140, p, t, 26, (p[0], p[1] + 0.25, p[2]), t)
    T.shot(cam, tgt, 141, 214, (0.0, -2.4, 0.6), (0.0, 0.1, 0.45), 34, (0.0, -2.2, 0.6), (0.0, 0.1, 0.45))
    p, t = _two([-0.75, 0.85], 24, 0.95, margin=0.5)
    T.shot(cam, tgt, 215, 480, p, t, 24, (p[0], p[1] + 0.3, p[2]), t)
    p2, t2 = _two([-0.8, 0.9], 24, 1.15, margin=0.5)
    T.shot(cam, tgt, 481, 620, p2, t2, 24, (p2[0], p2[1] + 0.3, p2[2] + 0.1), t2)

    # plant the seed, water it
    T.look(hero, 4, 0.04, -0.03)
    T.eyes_happy(hero, 8)
    T.sfx(8, "giggle")
    T.lean(hero, 22, 18, 6, axis=0)
    T.key(seed, "location", 22, (-0.2, -0.3, 0.55))
    T.key(seed, "location", 30, (0.75, 0.05, 0.05))
    T.show(seed, 31, False)
    T.sfx(30, "pop")
    for f in (34, 40, 46):
        _arm(hero, 1, f, 0.4, fwd=-1.2, d=3)
        _arm(hero, 1, f + 3, 0.2, fwd=-0.4, d=3)
        T.sfx(f + 2, "tick")
    T.lean(hero, 50, 0, 6, axis=0)
    T.eyes_norm(hero, 52)
    _water("can1", hero, 58, mx)
    # waiting... and waiting (tick tock)
    T.idle(hero, 96, 150)
    for k, f in enumerate(range(100, 150, 10)):
        T.sfx(f, "tick")
        T.look(hero, f, 0.05 if k % 2 else -0.02, -0.03)
    T.brows(hero, 112, -0.03)
    T.arms(hero, 116, 0.6, fwd=-0.6, d=4)  # arms crossed-ish: impatient
    T.turn(hero, 124, 0, 6)  # looks at the camera
    T.mouth_set(hero, 126, 0.3, 0.6)
    T.sfx(128, "wahwah")
    T.turn(hero, 140, 25, 6)
    T.arms(hero, 142, 0.0, d=4)
    T.brows(hero, 146, 0.0)
    # a tiny sprout!
    T.key(plant, "scale", 150, (0.001, 0.001, 0.001))
    T.key(plant, "scale", 158, (0.18, 0.18, 0.18))
    T.sfx(152, "sparkle")
    T.eyes_big(hero, 160, 1.35, 4, sound=None)
    T.mouth_set(hero, 160, 0.8)
    T.jump_joy(hero, 164, h=0.25, n=10, times=1, sound="ding")
    # hero tries to PULL it up to make it grow faster...
    T.lean(hero, 182, 22, 5, axis=0)
    T.arms(hero, 184, 0.6, fwd=-1.5, d=3)
    for k, f in enumerate(range(186, 206, 4)):
        T.lean(hero, f, -10 if k % 2 else 4, 2, axis=0)
        T.key(plant, "scale", f, (0.18, 0.18, 0.24 if k % 2 else 0.18))
        T.sfx(f, "squeak")
    # ...the friend hops in: "No no - wait!"
    T.hop(fr, 176, 2.1, 1.3, 0.3, 10, sound=True)
    T.hop(fr, 190, 1.3, 0.62, 0.3, 10, sound=True)
    T.eyes_big(fr, 202, 1.2, 3, sound=None)
    _shake_head(fr, 206, 2)
    T.arms(hero, 208, 0.0, d=4)
    T.lean(hero, 208, 0, 4, axis=0)
    T.key(plant, "scale", 208, (0.18, 0.18, 0.18))
    _arm(fr, -1, 228, 1.1, fwd=-0.9, d=5)  # gentle hand on the shoulder
    T.mouth_set(fr, 226, 0.0)
    T.eyes_happy(fr, 230)
    _nod(hero, 236, 2)
    _arm(fr, -1, 252, 0.0, d=5)
    T.eyes_norm(fr, 254)
    # night 1: they sit and sleep, the plant grows
    _night(262, 288, 336, 360, "night1")
    for ch in (hero, fr):
        T.squash(ch, 266, 0.12, 4, 100)
        _sleep(ch, 286, 340)
    T.key(plant, "scale", 290, (0.18, 0.18, 0.18))
    T.key(plant, "scale", 336, (0.55, 0.55, 0.55))
    T.sfx(320, "slide_up")
    # morning: a bigger plant - water it again
    T.eyes_big(hero, 352, 1.3, 4, sound="doink")
    T.mouth_set(hero, 352, 0.6)
    T.jump_joy(hero, 356, h=0.2, n=10, times=1, sound=None)
    _water("can2", hero, 376, mx)
    T.mouth_set(hero, 376, 0.0)
    # night 2: even bigger
    _night(414, 436, 480, 500, "night2")
    for ch in (hero, fr):
        _sleep(ch, 434, 484)
    T.key(plant, "scale", 438, (0.55, 0.55, 0.55))
    T.key(plant, "scale", 480, (1.2, 1.2, 1.2))
    T.sfx(462, "slide_up")
    # the big bloom!
    T.wobble(plant, 500, 512, 5, 2, 1, sound="rattle")
    T.show(head, 514, True)
    T.key(plant, "scale", 512, (1.2, 1.2, 1.2))
    T.key(plant, "scale", 518, (1.65, 1.65, 1.65))
    T.key(plant, "scale", 524, (1.55, 1.55, 1.55))
    T.sfx(514, "tada")
    rnd = random.Random(spec.get("seed", 1))
    cols = ["#FF6B8B", "#FFD23F", "#B57BFF", "#4DA6FF", "#FFFFFF"]
    for i, (fx, fy) in enumerate(((-1.2, 0.6), (1.3, 0.7), (-0.3, 0.8), (0.6, 0.9), (1.7, 0.4), (-1.6, 0.4))):
        b, _, _ = _flower(f"bloom{i}", (fx + rnd.uniform(-0.1, 0.1), fy, 0), cols[i % len(cols)])
        T.key(b, "scale", 1, (0.001, 0.001, 0.001))
        T.key(b, "scale", 520 + i * 3, (0.001, 0.001, 0.001))
        T.key(b, "scale", 526 + i * 3, (0.9, 0.9, 0.9))
        T.sfx(520 + i * 3, "pop")
    for ch in (hero, fr):
        T.eyes_big(ch, 518, 1.4, 3, sound=None)
        T.mouth_set(ch, 518, 0.9)
    T.jump_joy(hero, 532, sound="ding")
    T.jump_joy(fr, 536, sound=None)
    _hug(hero, fr, 568, -0.42, 0.62)
    T.laugh(hero, 600, 618, sound=True)
    T.laugh(fr, 600, 618, sound=False)
    return 624, 520


# --------------------------------------------------------------------------- 2. sharing makes us happy
def sharing(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.72, 0.15)
    fr = T.make_character(spec["friend"], 2.1, 0.3)
    T.turn(hero, 1, 22, 1)
    T.turn(fr, 1, -25, 1)
    table = T.make_table((0.05, 0.25, 0), spec.get("table_color", "#FFD23F"))
    kind = spec.get("prop") if spec.get("prop") in ("cupcake", "apple") else "cupcake"  # tall treats read from the side
    TX, TY = 0.05, 0.25

    def loc(x, y, z):  # world -> table-local (the treats sit on the table)
        return (x - TX, y - TY, z)

    hm, fm = (-0.58, -0.35, 0.45 * hero["size"]), (0.6, -0.35, 0.45 * fr["size"])
    treats = []
    for i, (tx, ty) in enumerate(((-0.17, -0.05), (0.0, 0.08), (0.17, -0.05))):
        tr = T.make_prop(kind, (tx, ty, 0.67), table, name=f"treat{i}")
        tr.scale = (1.15, 1.15, 1.15)
        treats.append(tr)

    p, t = _two([-0.8, 0.85], 26, 0.65, margin=0.5, cam_z=1.6)
    T.shot(cam, tgt, 1, 190, p, t, 26, (p[0], p[1] + 0.25, p[2]), t)
    T.shot(cam, tgt, 191, 250, (-0.45, -2.5, 1.45), (-0.5, 0.2, 0.75), 38, (-0.45, -2.3, 1.45), (-0.5, 0.2, 0.75))
    p, t = _two([-0.8, 0.8], 26, 0.65, margin=0.5, cam_z=1.6)
    T.shot(cam, tgt, 251, 540, p, t, 26, (p[0], p[1] + 0.3, p[2]), t)

    def eat(ch, f, tr, local_to, side=1):
        """A treat hops from the table to the mouth and is munched."""
        _arm(ch, side, f, 0.5, fwd=-1.5, d=4)
        T.key(tr, "location", f, tuple(tr.location))
        T.key(tr, "location", f + 8, local_to)
        T.key(tr, "scale", f + 8, (1.15, 1.15, 1.15))
        for k in range(3):
            T.mouth_set(ch, f + 10 + k * 6, 0.6, 0.8)
            T.mouth_set(ch, f + 13 + k * 6, 0.0)
            T.sfx(f + 10 + k * 6, "chomp")
            T.key(tr, "scale", f + 10 + k * 6, (1.15 - k * 0.35,) * 3)
        T.show(tr, f + 28, False)
        _arm(ch, side, f + 28, 0.0, d=4)
        T.eyes_happy(ch, f + 30)
        T.sfx(f + 32, "sparkle")

    # the hero munches one treat - yum!
    T.look(hero, 4, 0.05, -0.02)
    T.eyes_big(hero, 10, 1.25, 4, sound="sparkle")
    eat(hero, 20, treats[0], loc(*hm))
    T.eyes_norm(hero, 60)
    # a friend arrives, hungry and sad
    T.hop(fr, 64, 2.1, 1.4, 0.3, 10, sound=True)
    T.hop(fr, 78, 1.4, 0.75, 0.3, 10, sound=True)
    T.look(fr, 92, -0.06, -0.02)
    T.eyes_big(fr, 94, 1.2, 4, sound=None)
    T.sfx(104, "honk")  # tummy rumble
    T.squash(fr, 104, 0.1, 2, 4)
    _sad(fr, 116)
    _tears(fr, 124, 160, "ftear")
    # the hero hugs the plate... looks at the sad friend... and has an idea
    T.look(hero, 100, 0.06)
    T.arms(hero, 128, 1.0, fwd=-1.3, d=5)
    for tr in treats[1:]:
        T.key(tr, "location", 128, tuple(tr.location))
    T.key(treats[1], "location", 136, (-0.28, 0.0, 0.67))
    T.key(treats[2], "location", 136, (-0.2, -0.14, 0.67))
    T.brows(hero, 140, -0.02)
    T.look(hero, 150, 0.07, -0.03)
    T.brows(hero, 162, 0.03)
    T.look(hero, 176, 0.0, 0.07)  # thinks...
    T.sfx(186, "ding")
    T.star("idea", 0.1, (-0.72, 0.1, 1.45), T.mat("#FFD23F", 0.3, emit=2.0))
    idea = T.bpy.data.objects["idea"]
    T.show(idea, 1, False)
    T.show(idea, 186, True)
    T.key(idea, "scale", 186, (0.1, 0.1, 0.1))
    T.key(idea, "scale", 191, (1.3, 1.3, 1.3))
    T.show(idea, 212, False)
    T.eyes_happy(hero, 190)
    T.mouth_set(hero, 190, 0.6)
    T.arms(hero, 200, 0.0, d=5)
    # here, have one!
    T.mouth_set(hero, 214, 0.0)
    T.eyes_norm(hero, 214)
    T.look(hero, 214, 0.06)
    _arm(hero, 1, 220, 0.6, fwd=-1.6, d=5)
    T.key(treats[1], "location", 222, (-0.28, 0.0, 0.67))
    T.key(treats[1], "location", 236, loc(0.48, -0.25, 0.72))
    T.sfx(228, "zip")
    _arm(hero, 1, 244, 0.0, d=5)
    _cheer_up(fr, 240)
    T.eyes_big(fr, 244, 1.35, 3, sound="sparkle")
    T.mouth_set(fr, 244, 0.8)
    T.jump_joy(fr, 252, h=0.3, n=10, times=1, sound="ding")
    T.key(treats[1], "location", 252, loc(0.48, -0.25, 0.72))
    eat(fr, 282, treats[1], loc(*fm), side=-1)
    T.eyes_norm(fr, 320)
    # the last one: split in half - one for you, one for me
    tr = treats[2]
    T.key(tr, "location", 326, (-0.2, -0.14, 0.67))
    T.key(tr, "location", 338, (0.05, -0.1, 0.72))
    T.sfx(340, "crash")
    T.show(tr, 342, False)
    halves = []
    for s, x in ((-1, -0.45), (1, 0.48)):
        hv = T.make_prop(kind, (0.05, -0.1, 0.72), None, name=f"half{s}")
        hv.scale = (0.75, 0.75, 0.75)
        T.show(hv, 1, False)
        T.show(hv, 342, True)
        T.key(hv, "location", 342, (0.05 + s * 0.06, -0.1, 0.72))
        T.key(hv, "location", 354, (x, -0.2, 0.62))
        T.key(hv, "location", 380, (x, -0.2, 0.62))
        T.key(hv, "location", 386, (x * 0.95, -0.35, 0.42))
        T.show(hv, 400, False)
        halves.append(hv)
    for ch, side in ((hero, 1), (fr, -1)):
        _arm(ch, side, 352, 0.6, fwd=-1.4, d=5)
        T.eyes_happy(ch, 356)
        for k in range(3):
            T.mouth_set(ch, 386 + k * 5, 0.6, 0.8)
            T.mouth_set(ch, 388 + k * 5, 0.0)
        _arm(ch, side, 402, 0.0, d=5)
    T.sfx(386, "chomp")
    T.sfx(396, "chomp")
    T.laugh(hero, 404, 430)
    T.laugh(fr, 406, 430, sound=False)
    _hug(hero, fr, 440, -0.3, 0.45)
    T.jump_joy(hero, 494, sound="ding")
    T.jump_joy(fr, 498, sound=None)
    return 540, 252


# --------------------------------------------------------------------------- 3. help a friend
def helping(spec, cam, tgt):
    fr = T.make_character(spec["friend"], -2.3, 0.3)
    hero = T.make_character(spec["hero"], 1.05, 0.15)
    T.turn(hero, 1, -15, 1)
    sz = fr["size"]
    cols = ["#FF6B6B", "#4DA6FF", "#FFD23F", "#5CCB6B"]
    T.VAR.shuffle(cols)
    boxes = []
    for i in range(4):  # a wobbly stack of boxes, held in front (parented to the friend)
        b = T.box(f"crate{i}", (0.3, 0.26, 0.2), (0.02 * (-1) ** i, -0.42, 0.55 + i * 0.2), T.mat(cols[i], 0.5), fr["root"],
                  bevel=0.03)
        boxes.append(b)
    fall_x = -0.25

    p, t = _two([-1.2, 1.1], 22, 0.85, margin=0.5)
    T.shot(cam, tgt, 1, 150, p, t, 22, (p[0], p[1] + 0.2, p[2]), t)
    p, t = _two([-0.7, 0.9], 28, 0.75, margin=0.5)
    T.shot(cam, tgt, 151, 330, p, t, 28, (p[0], p[1] + 0.25, p[2]), t)
    p, t = _two([-0.9, 1.35], 22, 0.9, margin=0.5)
    T.shot(cam, tgt, 331, 560, p, t, 22, (p[0] + 0.2, p[1] + 0.2, p[2]), t)

    # the friend wobbles in with a tall stack
    T.idle(hero, 1, 90)
    T.look(hero, 10, -0.05)
    x = -2.3
    for k, f in enumerate(range(6, 62, 14)):
        T.hop(fr, f, x, x + 0.52, 0.12, 12, sound=False)
        T.sfx(f + 2, "tiptoe")
        x += 0.52
    for i, b in enumerate(boxes):
        T.wobble(b, 6 + i, 62, 4 + i * 2, 4, 1, sound=None)
    T.sfx(40, "rattle")
    # trip!
    r = fr["root"]
    T.key(r, "location", 62, (x, 0.3, 0))
    T.key(r, "location", 70, (fall_x, 0.25, 0))
    T.lean(fr, 66, 30, 4, axis=0)
    T.eyes_big(fr, 66, 1.4, 2, sound=None)
    T.mouth_set(fr, 66, 0.9)
    T.sfx(66, "whoosh")
    T.lean(fr, 74, 0, 4, axis=0)
    T.squash(fr, 75, 0.3, 1, 8)
    T.sfx(74, "thud")
    spots = [(-0.55, 0.0), (0.25, -0.12), (-0.95, 0.35), (0.45, 0.45)]
    for i, (b, (bx, by)) in enumerate(zip(boxes, spots)):
        T.key(b, "location", 66, tuple(b.location))
        lx, ly = (bx - fall_x) / sz, (by - 0.25) / sz
        T.key(b, "location", 72 + i * 2, (lx * 0.6, ly * 0.6 - 0.2, 0.9))
        T.key(b, "location", 80 + i * 2, (lx, ly, 0.1 / sz))
        T.key(b, "rotation_euler", 66, (0, 0, 0))
        T.key(b, "rotation_euler", 80 + i * 2, (0, 0, (i - 1.5) * 0.6))
        T.sfx(80 + i * 2, "thud")
    T.dizzy_stars(fr, 80, 110)
    _sad(fr, 114)
    _tears(fr, 120, 168, "tear")
    # the hero sees it and comes to help
    T.eyes_big(hero, 76, 1.35, 3, sound="doink")
    T.mouth_set(hero, 76, 0.7)
    T.mouth_set(hero, 100, 0.0)
    T.hop(hero, 120, 1.05, 0.55, 0.25, 10, sound=True)
    T.hop(hero, 134, 0.55, 0.25, 0.2, 10, sound=True)
    T.turn(hero, 146, -30, 5)
    hx = 0.25
    # picks the boxes up one by one into a neat pile
    pile_x, pile_y = 0.65, 0.55
    for i, (b, (bx, by)) in enumerate(zip(boxes, spots)):
        f = 156 + i * 26
        T.hop(hero, f, hx, bx + 0.32, 0.15, 8, sound=False)
        hx = bx + 0.32
        T.lean(hero, f + 10, 16, 3, axis=0)
        T.lean(hero, f + 16, 0, 3, axis=0)
        T.key(b, "location", f + 12, ((bx - fall_x) / sz, (by - 0.25) / sz, 0.1 / sz))
        T.key(b, "location", f + 22, ((pile_x - fall_x) / sz, (pile_y - 0.25) / sz, (0.1 + i * 0.2) / sz))
        T.key(b, "rotation_euler", f + 12, (0, 0, (i - 1.5) * 0.6))
        T.key(b, "rotation_euler", f + 22, (0, 0, 0))
        T.sfx(f + 14, "tick" if i % 2 else "pop")
    T.sfx(262, "tada")
    # a hand up
    T.hop(hero, 268, hx, 0.3, 0.15, 8, sound=False)
    T.turn(hero, 280, -60, 5)
    _arm(hero, -1, 286, 1.0, fwd=-1.0, d=5)
    _arm(fr, 1, 292, 1.0, fwd=-1.0, d=5)
    T.sfx(296, "slide_up")
    T.stretch(fr, 300, 0.2, 4, 6)
    _cheer_up(fr, 300)
    T.eyes_happy(fr, 306)
    T.mouth_set(fr, 306, 0.6)
    _arm(hero, -1, 312, 0.0, d=5)
    _arm(fr, 1, 312, 0.0, d=5)
    T.turn(hero, 316, -15, 5)
    _hug(fr, hero, 326, -0.05, 0.42)
    # carry them together: two boxes each
    for i, b in enumerate(boxes):
        T.show(b, 372, False)
    carry = []
    for ch, idxs, nm in ((fr, (0, 1), "ca"), (hero, (2, 3), "cb")):
        for j, i in enumerate(idxs):
            b = T.box(f"{nm}{j}", (0.28, 0.24, 0.18), (0, -0.48, 0.28 + j * 0.18), T.mat(cols[i], 0.5), ch["root"], bevel=0.03)
            T.show(b, 1, False)
            T.show(b, 372, True)
            carry.append(b)
    T.sfx(372, "pop")
    for ch in (fr, hero):
        T.turn(ch, 376, 0, 5)
    T.eyes_norm(fr, 380)
    xs = {id(fr): -0.05, id(hero): 0.42}
    for k, f in enumerate(range(390, 470, 16)):  # a little walk together, staying in the shot
        for ch in (fr, hero):
            x0 = xs[id(ch)]
            T.hop(ch, f + (4 if ch is hero else 0), x0, x0 + 0.12, 0.14, 12, sound=False)
            xs[id(ch)] = x0 + 0.12
        T.sfx(f + 2, "tiptoe")
    for ch in (fr, hero):
        T.turn(ch, 480, 0, 5)
        T.eyes_happy(ch, 484)
    T.laugh(fr, 490, 520)
    T.laugh(hero, 492, 520, sound=False)
    _hearts("thanks", 520, ((xs[id(fr)] + xs[id(hero)]) / 2, 0.2, 1.2), 4)
    return 560, 300


# --------------------------------------------------------------------------- 4. say sorry and make it right
def _block(name, loc, color, parent=None):
    return T.box(name, (0.22, 0.22, 0.2), loc, T.mat(color, 0.45, coat=0.3), parent, bevel=0.03)


def sorry(spec, cam, tgt):
    fr = T.make_character(spec["friend"], 0.85, 0.3)
    hero = T.make_character(spec["hero"], -2.0, 0.15)
    T.turn(fr, 1, -30, 1)
    cols = ["#FF6B6B", "#FFD23F", "#4DA6FF", "#5CCB6B", "#B57BFF", "#FF8A3D", "#FF8FC8"]
    tx, ty = 0.2, 0.3
    blocks = []
    for i in range(5):  # the friend builds a tower, block by block
        b = _block(f"blk{i}", (tx + 0.02 * ((-1) ** i), ty, 0.1 + i * 0.2), cols[i])
        T.show(b, 1, False)
        f = 8 + i * 12
        T.show(b, f, True)
        T.key(b, "location", f, (tx, ty, 0.1 + i * 0.2 + 0.35))
        T.key(b, "location", f + 5, (tx + 0.02 * ((-1) ** i), ty, 0.1 + i * 0.2))
        T.sfx(f + 5, "tick")
        blocks.append(b)
    ball = T.make_prop("ball", (-2.0, -0.1, 0.18), name="ball")

    p, t = _two([-0.9, 0.95], 26, 0.85, margin=0.5)
    T.shot(cam, tgt, 1, 160, p, t, 26, (p[0], p[1] + 0.2, p[2]), t)
    T.shot(cam, tgt, 161, 250, (-0.45, -2.6, 0.8), (-0.45, 0.2, 0.72), 36, (-0.45, -2.4, 0.8), (-0.45, 0.2, 0.72))
    p, t = _two([-0.85, 0.95], 26, 0.95, margin=0.5)
    T.shot(cam, tgt, 251, 560, p, t, 26, (p[0], p[1] + 0.3, p[2]), t)

    for f in range(10, 70, 12):
        _arm(fr, -1, f, 0.9, fwd=-1.2, d=4)
        _arm(fr, -1, f + 5, 0.3, fwd=-0.5, d=4)
    T.eyes_happy(fr, 72)
    T.sfx(72, "tada")
    T.jump_joy(fr, 76, h=0.2, n=10, times=1, sound=None)
    # the hero kicks a ball in from the side... BONK
    T.hop(hero, 60, -2.0, -1.2, 0.25, 10, sound=True)
    T.key(ball, "location", 60, (-2.0, -0.1, 0.18))
    T.key(ball, "location", 70, (-1.0, -0.1, 0.18))
    T.lean(hero, 80, -10, 4)
    T.lean(hero, 84, 12, 2)
    T.sfx(84, "doink")
    T.key(ball, "location", 84, (-1.0, -0.1, 0.18))
    T.key(ball, "location", 96, (tx - 0.2, ty - 0.1, 0.5))
    T.key(ball, "location", 108, (tx + 0.9, ty + 0.4, 0.18))
    T.key(ball, "rotation_euler", 84, (0, 0, 0))
    T.key(ball, "rotation_euler", 108, (0, 9, 0))
    T.sfx(96, "crash")
    rnd = random.Random(spec.get("seed", 3))
    for i, b in enumerate(blocks):  # the tower crashes down
        T.key(b, "location", 96, tuple(b.location))
        T.key(b, "rotation_euler", 96, (0, 0, 0))
        land = (tx + rnd.uniform(-0.6, 0.6), ty + rnd.uniform(-0.35, 0.2), 0.1)
        T.key(b, "location", 100 + i * 2, (land[0] * 0.5 + tx * 0.5, land[1], 0.6 + i * 0.12))
        T.key(b, "location", 110 + i * 2, land)
        T.key(b, "rotation_euler", 110 + i * 2, (rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        T.sfx(110 + i * 2, "thud")
    T.eyes_big(fr, 98, 1.4, 2, sound=None)
    T.mouth_set(fr, 98, 1.0)
    _sad(fr, 126)
    _tears(fr, 132, 200, "tear")
    T.eyes_big(hero, 100, 1.35, 3, sound=None)
    T.mouth_set(hero, 100, 0.8, 0.6)
    T.arms(hero, 104, 0.5, fwd=-1.9, d=4)  # oops! hands over mouth
    # the hero feels bad... walks over and says sorry
    T.arms(hero, 140, 0.0, d=5)
    _sad(hero, 146, sound=False)
    T.look(hero, 150, 0.03, -0.05)
    T.hop(hero, 168, -1.2, -0.75, 0.12, 12, sound=False)
    T.sfx(170, "tiptoe")
    T.hop(hero, 186, -0.75, -0.3, 0.12, 12, sound=False)
    T.sfx(188, "tiptoe")
    T.turn(hero, 202, 30, 5)
    T.lean(hero, 212, 24, 8, axis=0)  # a little bow: sorry
    T.arms(hero, 212, 0.4, fwd=-1.0, d=6)
    T.sfx(212, "xylo_down")
    T.lean(hero, 236, 0, 6, axis=0)
    # ...and offers a flower
    fl, fh, _ = _flower("sorryflower", (0.42, -0.25, 0.35), "#FF6BD6", )
    fl.parent = hero["root"]
    fl.scale = (0.6, 0.6, 0.6)
    T.show(fl, 1, False)
    T.show(fl, 240, True)
    T.sfx(240, "sparkle")
    _arm(hero, 1, 242, 0.6, fwd=-1.4, d=5)
    T.key(fl, "location", 242, (0.42, -0.25, 0.35))
    T.key(fl, "location", 252, (0.6, -0.3, 0.42))
    T.look(fr, 248, -0.06)
    _cheer_up(fr, 256)
    T.eyes_big(fr, 262, 1.25, 4, sound="sparkle")
    T.mouth_set(fr, 262, 0.6)
    T.eyes_happy(fr, 274)
    T.show(fl, 286, False)
    _arm(hero, 1, 286, 0.0, d=5)
    _cheer_up(hero, 290)
    _hug(hero, fr, 292, -0.05, 0.62)
    # rebuild it together - even taller, with a star on top
    T.hop(hero, 330, -0.05, -0.45, 0.15, 8, sound=False)
    T.hop(fr, 330, 0.62, 0.9, 0.15, 8, sound=False)
    T.turn(hero, 340, 25, 5)
    T.turn(fr, 340, -25, 5)
    for i in range(7):
        f = 344 + i * 13
        b = _block(f"new{i}", (tx, ty, 0.1 + i * 0.2), cols[i % len(cols)])
        T.show(b, 1, False)
        T.show(b, f, True)
        T.key(b, "location", f, (tx + (-0.5 if i % 2 else 0.5), ty, 0.1 + i * 0.2 + 0.3))
        T.key(b, "location", f + 6, (tx, ty, 0.1 + i * 0.2))
        T.sfx(f + 6, "tick")
        ch, side = (hero, 1) if i % 2 else (fr, -1)
        _arm(ch, side, f, 1.3, fwd=-1.0, d=4)
        _arm(ch, side, f + 6, 0.2, d=4)
    for b in blocks:
        T.show(b, 344, False)
    st = T.star("topstar", 0.13, (tx, ty - 0.02, 1.62), T.mat("#FFD23F", 0.3, emit=1.5))
    T.show(st, 1, False)
    T.show(st, 440, True)
    T.key(st, "scale", 440, (0.1, 0.1, 0.1))
    T.key(st, "scale", 446, (1.3, 1.3, 1.3))
    T.key(st, "scale", 450, (1, 1, 1))
    T.sfx(440, "tada")
    # high five!
    for ch, side in ((hero, 1), (fr, -1)):
        _arm(ch, side, 466, 2.6, d=5)
        T.eyes_happy(ch, 466)
        T.mouth_set(ch, 466, 0.7)
    T.sfx(472, "clap")
    _confetti("confetti", 474, (tx, ty, 1.2))
    T.jump_joy(hero, 490, sound="ding")
    T.jump_joy(fr, 494, sound=None)
    return 560, 452


# --------------------------------------------------------------------------- 5. together we can do it
def teamwork(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.75, 0.15)
    fr = T.make_character(spec["friend"], -2.6, 0.2)
    T.turn(hero, 1, 60, 1)  # facing the big rock on the right
    rock = T.empty("rock", (0.15, 0.25, 0.62))
    rm = T.mat(T.VAR.choice(["#9AA0A8", "#A89A8A", "#8FA0B0"]), 0.85)
    T.sphere("rock_s", 0.62, (0, 0, 0), rm, rock, scale=(1.1, 0.9, 1.0), sub=2)
    for i in range(3):
        a = i * 2.1
        T.sphere(f"rock_spot{i}", 0.12, (math.cos(a) * 0.45, -0.5, math.sin(a) * 0.35), T.mat("#7D838C", 0.9), rock,
                 scale=(1, 0.3, 0.8), sub=0)
    prize = T.make_table((1.55, 0.35, 0), spec.get("table_color", "#FF7AA8"))
    cake = T.make_prop("cake", (0, 0, 0.67), prize, name="cake")

    p, t = _two([-0.8, 0.9], 26, 0.85, margin=0.5)
    T.shot(cam, tgt, 1, 190, p, t, 26, (p[0], p[1] + 0.2, p[2]), t)
    p, t = _two([-1.6, 0.6], 24, 0.85, margin=0.5)
    T.shot(cam, tgt, 191, 330, p, t, 24, (p[0] + 0.3, p[1] + 0.2, p[2]), t)
    p, t = _two([-0.5, 1.8], 24, 0.85, margin=0.5)
    T.shot(cam, tgt, 331, 540, p, t, 24, (p[0], p[1] + 0.3, p[2]), t)

    def push(ch, f0, f1, side=1):
        """Strain against the rock: lean in, little shakes, puffing."""
        T.lean(ch, f0, 18, 5, axis=0)
        T.arms(ch, f0, 1.2, fwd=-1.3, d=4)
        T.brows(ch, f0, -0.04)
        T.mouth_set(ch, f0, 0.3, 1.2)
        for k, f in enumerate(range(f0 + 4, f1, 4)):
            T.key(ch["piv"], "scale", f, (1.04, 1.04, 0.96) if k % 2 else (0.98, 0.98, 1.02))
            if k % 3 == 0:
                T.sfx(f, "squeak")
        T.key(ch["piv"], "scale", f1, (1, 1, 1))

    # the hero spots the yummy cake behind the big rock... and pushes. It won't move.
    T.look(hero, 6, 0.06, 0.04)
    T.eyes_big(hero, 14, 1.25, 4, sound="sparkle")
    T.mouth_set(hero, 14, 0.6)
    T.hop(hero, 30, -0.75, -0.62, 0.1, 8, sound=False)
    push(hero, 44, 92)
    T.wobble(rock, 50, 90, 2, 4, 1, sound=None)
    T.lean(hero, 96, 0, 5, axis=0)
    T.arms(hero, 96, 0.0, d=4)
    T.squash(hero, 98, 0.2, 2, 6)
    _sad(hero, 106)
    T.brows(hero, 120, 0.0)
    push(hero, 126, 156)
    T.lean(hero, 160, 0, 4, axis=0)
    T.arms(hero, 160, 0.0, d=4)
    T.hop(hero, 164, -0.62, -0.8, 0.1, 8, sound=False)
    T.squash(hero, 174, 0.28, 2, 10)  # flops down, tired
    T.sfx(174, "thud")
    _sad(hero, 180, sound=False)
    # a friend comes by
    T.hop(fr, 190, -2.6, -2.0, 0.3, 10, sound=True)
    T.hop(fr, 204, -2.0, -1.45, 0.3, 10, sound=True)
    T.turn(fr, 214, 20, 4)
    T.look(fr, 216, 0.05)
    T.eyes_big(fr, 220, 1.2, 4, sound=None)
    T.look(hero, 222, -0.06)
    T.sfx(232, "ding")
    T.eyes_happy(fr, 234)
    T.mouth_set(fr, 234, 0.6)
    _nod(fr, 240, 2)
    _cheer_up(hero, 252)
    T.mouth_set(hero, 256, 0.6)
    # together: 1, 2, 3 - PUSH!
    T.turn(fr, 262, 60, 5)
    T.hop(hero, 266, -0.8, -0.62, 0.15, 8, sound=False)
    T.hop(fr, 268, -1.45, -1.05, 0.15, 8, sound=False)
    for k, f in enumerate((284, 294, 304)):
        T.sfx(f, "ding" if k < 2 else "tada")
        for ch in (hero, fr):
            T.squash(ch, f, 0.12, 2, 4)
    push(hero, 312, 344)
    push(fr, 312, 344)
    T.key(rock, "location", 316, (0.15, 0.25, 0.62))
    T.key(rock, "location", 348, (0.75, 0.25, 0.62))
    T.key(rock, "rotation_euler", 316, (0, 0, 0))
    T.key(rock, "rotation_euler", 348, (0, 1.2, 0))
    T.sfx(320, "rattle")
    # it rolls away - the way is open!
    T.key(rock, "location", 380, (3.6, 0.9, 0.62))
    T.key(rock, "rotation_euler", 380, (0, 6.5, 0))
    T.sfx(350, "whoosh")
    T.sfx(362, "xylo_down")
    T.key(rock, "location", 381, (3.6, 0.9, 0.62))
    T.show(rock, 384, False)
    for ch in (hero, fr):
        T.lean(ch, 352, 0, 4, axis=0)
        T.arms(ch, 352, 0.0, d=4)
        T.brows(ch, 352, 0.0)
        T.turn(ch, 364, 0, 6)
    T.sfx(366, "tada")
    T.jump_joy(hero, 370, sound="ding")
    T.jump_joy(fr, 374, sound=None)
    # share the cake
    T.hop(hero, 404, -0.62, 1.05, 0.3, 12, sound=True)
    T.hop(fr, 408, -1.05, 1.95, 0.3, 14, sound=True)
    T.turn(hero, 422, 30, 5)
    T.turn(fr, 424, -30, 5)
    for ch in (hero, fr):
        T.eyes_happy(ch, 430)
        for k in range(3):
            T.mouth_set(ch, 434 + k * 8, 0.6, 0.8)
            T.mouth_set(ch, 438 + k * 8, 0.0)
            T.sfx(434 + k * 8, "chomp")
    T.key(cake, "scale", 430, (1, 1, 1))
    T.key(cake, "scale", 458, (0.55, 0.55, 0.55))
    T.laugh(hero, 466, 496)
    T.laugh(fr, 468, 496, sound=False)
    _hearts("team", 500, (1.5, 0.3, 1.3), 5)
    return 540, 352


# --------------------------------------------------------------------------- 6. never give up
def try_again(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.95, 0.15)
    fr = T.make_character(spec["friend"], -1.75, 0.45)
    T.turn(hero, 1, 55, 1)
    T.turn(fr, 1, 40, 1)
    col = T.VAR.choice(["#FF8A3D", "#4DA6FF", "#B57BFF", "#FF6B8B"])
    px, ph = 0.55, 0.9
    T.box("ledge", (0.75, 0.6, ph), (px, 0.3, ph / 2), T.mat(col, 0.5, coat=0.2), bevel=0.06)
    T.box("ledge_top", (0.8, 0.65, 0.06), (px, 0.3, ph + 0.03), T.mat("#FFFFFF", 0.4), bevel=0.02)
    star = T.star("prize", 0.18, (px, 0.2, ph + 0.4), T.mat("#FFD23F", 0.25, emit=1.2))
    for f in range(1, 330, 24):
        T.key(star, "location", f, (px, 0.2, ph + 0.4))
        T.key(star, "location", f + 12, (px, 0.2, ph + 0.5))
    hz = ph + 0.06  # standing height on the ledge

    p, t = _two([-1.3, 0.8], 24, 1.0, margin=0.5)
    T.shot(cam, tgt, 1, 210, p, t, 24, (p[0] + 0.2, p[1] + 0.2, p[2]), t)
    T.shot(cam, tgt, 211, 300, (-0.9, -2.5, 0.75), (-1.0, 0.2, 0.7), 36, (-0.9, -2.3, 0.75), (-1.0, 0.2, 0.7))
    p, t = _two([-1.3, 0.9], 24, 1.15, margin=0.5)
    T.shot(cam, tgt, 301, 540, p, t, 24, (p[0], p[1] + 0.3, p[2] + 0.1), t)

    def jump_fail(f0, x0, top, back_to, bonk=True):
        r = hero["root"]
        T.squash(hero, f0, 0.2, 3, 2)
        T.sfx(f0 + 2, "boing")
        T.key(r, "location", f0 + 2, (x0, 0.15, 0))
        T.key(r, "location", f0 + 9, ((x0 + px - 0.45) / 2, 0.15, top))
        T.key(r, "location", f0 + 13, (px - 0.62, 0.15, top * 0.8))
        T.arms(hero, f0 + 4, 2.4, d=2)
        if bonk:
            T.sfx(f0 + 13, "doink")
            T.eyes_big(hero, f0 + 14, 1.4, 1, sound=None)
        T.key(r, "location", f0 + 22, (back_to, 0.15, 0))
        T.sfx(f0 + 22, "thud")
        T.squash(hero, f0 + 23, 0.3, 1, 8)
        T.arms(hero, f0 + 24, 0.0, d=3)

    # the hero wants the shiny star up there
    T.look(hero, 6, 0.06, 0.08)
    T.eyes_big(hero, 12, 1.3, 4, sound="sparkle")
    T.mouth_set(hero, 12, 0.6)
    T.idle(fr, 1, 200)
    # try 1: bonk!
    T.mouth_set(hero, 30, 0.0)
    jump_fail(34, -0.95, 0.45, -0.8)
    T.dizzy_stars(hero, 58, 84)
    # try 2: almost... slides back down
    T.hop(hero, 90, -0.8, -0.95, 0.1, 8, sound=False)
    _determined(hero, 100)
    jump_fail(106, -0.95, 0.75, -0.75, bonk=False)
    T.sfx(122, "slide_down")
    T.sfx(132, "wahwah")
    # give up?
    T.turn(hero, 140, 0, 6)
    _sad(hero, 146, sound=False)
    T.squash(hero, 150, 0.18, 4, 40)
    T.mouth_set(hero, 154, 0.0)
    # the friend cheers: you can do it!
    T.hop(fr, 160, -1.75, -1.4, 0.2, 10, sound=True)
    T.turn(fr, 172, 30, 5)
    for k, f in enumerate(range(176, 212, 6)):
        T.arms(fr, f, 2.5 if k % 2 else 1.2, d=3)
        T.sfx(f, "clap")
    T.eyes_happy(fr, 178)
    T.mouth_set(fr, 178, 0.8)
    T.jump_joy(fr, 214, h=0.3, n=10, times=1, sound="ding")
    T.look(hero, 196, -0.06, 0.02)
    _cheer_up(hero, 222)
    _determined(hero, 236)
    _nod(hero, 240, 2)
    T.sfx(250, "drumroll")
    T.turn(hero, 256, 55, 5)
    # back up... run... SUPER JUMP
    T.hop(hero, 262, -0.75, -1.15, 0.12, 8, sound=False)
    T.squash(hero, 280, 0.25, 6, 2)
    r = hero["root"]
    T.key(r, "location", 282, (-1.15, 0.15, 0))
    T.key(r, "location", 290, (-0.6, 0.15, 0.25))
    T.key(r, "location", 300, (-0.1, 0.15, 1.45))
    T.key(r, "location", 310, (px - 0.05, 0.25, hz))
    T.sfx(284, "slide_up")
    T.sfx(286, "whoosh")
    T.key(hero["piv"], "rotation_euler", 290, (0, 0, 0))
    T.key(hero["piv"], "rotation_euler", 306, (0, math.radians(360), 0))
    T.key(hero["piv"], "rotation_euler", 307, (0, 0, 0), "CONSTANT")
    T.arms(hero, 292, 2.6, d=3)
    T.sfx(310, "land")
    T.squash(hero, 311, 0.25, 1, 7)
    T.arms(hero, 316, 0.0, d=3)
    T.brows(hero, 316, 0.0)
    T.eyes_norm(hero, 318)
    # got it!
    T.turn(hero, 322, 0, 5)
    _arm(hero, 1, 330, 2.6, d=5)
    T.key(star, "location", 330, (px, 0.2, ph + 0.4))
    T.key(star, "location", 338, (px + 0.2, 0.05, ph + 1.15))
    T.key(star, "scale", 334, (1, 1, 1))
    T.key(star, "scale", 342, (1.6, 1.6, 1.6))
    T.key(star, "scale", 348, (1.3, 1.3, 1.3))
    T.sfx(336, "tada")
    T.eyes_happy(hero, 338)
    T.mouth_set(hero, 338, 0.9)
    _confetti("yay", 344, (px, 0.3, ph + 0.6))
    T.eyes_big(fr, 336, 1.35, 3, sound=None)
    T.mouth_set(fr, 336, 0.9)
    T.jump_joy(fr, 350, sound=None)
    T.jump_joy(fr, 380, sound=None)
    # hop down and share the star with the friend who believed
    _arm(hero, 1, 392, 0.0, d=4)
    T.key(star, "location", 392, (px + 0.2, 0.05, ph + 1.15))
    T.key(star, "location", 420, (-0.55, 0.0, 1.45))
    T.key(r, "location", 400, (px - 0.05, 0.25, hz))
    T.key(r, "location", 408, (0.0, 0.2, hz + 0.3))
    T.key(r, "location", 416, (-0.35, 0.2, 0))
    T.sfx(416, "land")
    T.squash(hero, 417, 0.2, 1, 6)
    T.hop(fr, 412, -1.4, -0.95, 0.2, 10, sound=False)
    T.turn(hero, 424, -30, 5)
    T.turn(fr, 424, 30, 5)
    _hearts("proud", 432, (-0.65, 0.2, 1.2), 5)
    for ch in (hero, fr):
        _arm(ch, 1 if ch is fr else -1, 434, 2.4, d=4)
    T.sfx(438, "clap")
    T.laugh(hero, 452, 490)
    T.laugh(fr, 454, 490, sound=False)
    T.jump_joy(hero, 494, sound="ding")
    T.jump_joy(fr, 498, sound=None)
    return 540, 338


MORALS = {"patience": patience, "sharing": sharing, "helping": helping, "sorry": sorry, "teamwork": teamwork,
          "try_again": try_again}
