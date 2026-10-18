"""Gag templates: short, wordless slapstick stories (~7s) acted by the recurring cast.

Each gag builds its own staging, acting, camera cuts and sound cues with the toon kit and returns
(last_frame, thumbnail_frame). The spec picks who plays which part, the set and the prop.
"""
import math

import toon as T


def _two(xs, lens, zc=0.85, margin=0.4, cam_z=None):
    return T.fit(xs, lens=lens, zc=zc, margin=margin, cam_z=cam_z)


def _sneak_z(ch):
    return 0.22 if T.CAST[ch["name"]]["kind"] == "bird" else 0.0


# --------------------------------------------------------------------------- 1. somebody steals the treat
def steal_treat(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -1.25, 0.15)
    table = T.make_table((0.55, 0.2, 0), spec.get("table_color", "#FF7AA8"))
    treat = T.make_prop(spec.get("prop", "cake"), (0, 0, 0.67), table, name="treat")
    sn = T.make_character(spec["friend"], 0.6, 0.62, -1.3)
    sz = _sneak_z(sn)

    # shots
    T.shot(cam, tgt, 1, 28, (-1.3, -2.75, 0.82), (-1.25, 0.15, 0.68), 50, (-1.22, -2.5, 0.8), (-1.2, 0.15, 0.68))
    T.shot(cam, tgt, 29, 60, (-1.05, -3.7, 0.62), (-1.05, 0.2, 0.72), 40, (-0.2, -3.5, 0.62), (-0.2, 0.2, 0.72))
    p0, t0 = _two([-0.35, 1.0], 32)
    T.shot(cam, tgt, 61, 168, p0, t0, 32, (p0[0], p0[1] + 0.3, p0[2]), t0)

    # hero spots the treat
    T.idle(hero, 1, 18)
    T.blink(hero, 10)
    T.look(hero, 1, 0.0)
    T.look(hero, 18, 0.05)
    T.eyes_big(hero, 22)
    T.brows(hero, 22, 0.05)
    T.mouth_set(hero, 19, 0.0)
    T.mouth_set(hero, 20, 0.3)
    T.mouth_set(hero, 24, 0.9, 1.1)
    T.eyes_norm(hero, 30)
    T.brows(hero, 34, 0.0)
    T.hop(hero, 28, -1.25, -0.98, 0.35)
    T.hop(hero, 42, -0.98, -0.66, 0.35)
    T.hop(hero, 56, -0.66, -0.35, 0.3)
    T.mouth_set(hero, 40, 0.0)
    T.turn(hero, 68, 28, 8)
    # lean in for a bite
    T.lean(hero, 82, 16, 10)
    T.blink(hero, 70)
    T.look(hero, 74, 0.04, -0.03)
    T.mouth_set(hero, 74, 0.0)
    T.mouth_set(hero, 77, 0.4)
    T.mouth_set(hero, 84, 1.6, 1.25)
    # the sneak pops up and slides the treat away
    r = sn["root"]
    T.key(r, "location", 70, (0.6, 0.62, -1.3))
    T.key(r, "location", 76, (0.6, 0.62, sz + 0.12))
    T.key(r, "location", 79, (0.6, 0.62, sz))
    T.look(sn, 79, -0.05)
    T.sfx(75, "pop")
    T.sfx(83, "swish")
    T.arms(sn, 84, 0.3, fwd=-1.4, d=6)
    T.key(treat, "location", 82, (0, 0, 0.67))
    T.key(treat, "location", 92, (0.42, 0.25, 0.67))
    T.key(r, "location", 92, (0.95, 0.62, sz))
    T.key(r, "location", 102, (1.1, 0.85, -1.3))
    T.key(treat, "location", 102, (0.55, 0.65, -0.3))
    T.key(treat, "scale", 101, (1, 1, 1))
    T.key(treat, "scale", 103, (0.01, 0.01, 0.01), "CONSTANT")
    T.sfx(95, "zip")
    # chomp on nothing -> surprise
    T.sfx(87, "chomp")
    T.mouth_set(hero, 90, 0.0)
    T.lean(hero, 100, -4, 8)
    T.lean(hero, 106, 0, 6)
    T.turn(hero, 104, 0, 6)
    T.eyes_big(hero, 100, 1.4, 5, sound="doink")
    T.sfx(101, "slide_down")
    T.brows(hero, 100, 0.08)
    T.mouth_set(hero, 100, 1.3, 0.9)
    T.look(hero, 100, 0.0, 0.0)
    T.arms(hero, 104, 2.4, d=6)
    T.stretch(hero, 101)
    T.blink(hero, 116)
    T.look(hero, 120, -0.04)
    T.look(hero, 132, 0.04)
    T.mouth_set(hero, 126, 0.0)
    T.eyes_norm(hero, 136, 8)
    T.brows(hero, 136, 0.0, 8)
    T.arms(hero, 140, 0.0, d=10)
    # ...the sneak peeks back up with crumbs and giggles
    T.key(r, "location", 140, (1.1, 0.85, -1.3))
    T.key(r, "location", 148, (0.85, 0.75, sz))
    T.sfx(146, "pop")
    T.laugh(sn, 150, 166)
    T.look(hero, 150, 0.05)
    T.eyes_big(hero, 152, 1.2, 4, sound=None)
    return 168, 100


# --------------------------------------------------------------------------- 2. ball bonk
def ball_bonk(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.75, 0.15)
    fr = T.make_character(spec["friend"], 0.85, 0.25)
    T.turn(hero, 1, 12, 1)
    T.turn(fr, 1, -15, 1)
    ball = T.make_prop("ball", (-0.3, 0.05, 0), name="ball")

    p, t = _two([-0.75, -0.3], 45, 0.5)
    T.shot(cam, tgt, 1, 30, p, t, 45, (p[0] + 0.05, p[1] + 0.25, p[2]), t)
    p, t = _two([-0.75, 0.85], 30)
    T.shot(cam, tgt, 31, 72, p, t, 30)
    p, t = _two([-0.6, 0.85], 34)
    T.shot(cam, tgt, 73, 168, p, t, 34, (p[0], p[1] + 0.35, p[2]), t)

    T.idle(hero, 1, 24)
    T.idle(fr, 1, 168)
    T.look(hero, 6, 0.04, -0.03)
    T.eyes_big(hero, 14)
    T.mouth_set(hero, 14, 0.5)
    T.mouth_set(hero, 22, 0.0)
    T.eyes_norm(hero, 24)
    T.squash(hero, 30, 0.2, 5, 4)
    # kick!
    T.place(hero, 31, -0.75)
    T.place(hero, 35, -0.55)
    T.stretch(hero, 35)
    T.sfx(34, "pop")
    T.sfx(35, "boing")
    b = ball
    T.key(b, "location", 34, (-0.3, 0.05, 0))
    T.key(b, "location", 40, (0.25, 0.12, 1.35))
    top = fr["top"] * fr["size"] + 0.02
    T.key(b, "location", 46, (0.8, 0.25, top))
    T.key(b, "location", 54, (1.35, 0.35, top + 0.35))
    T.key(b, "location", 62, (1.95, 0.55, 0))
    T.key(b, "location", 72, (2.7, 0.8, 0))
    T.key(b, "rotation_euler", 34, (0, 0, 0))
    T.key(b, "rotation_euler", 72, (math.radians(900), 0, 0))
    T.sfx(46, "doink")
    T.sfx(62, "boing")
    T.look(hero, 40, 0.05, 0.02)
    T.look(fr, 36, -0.05, 0.0)
    T.eyes_big(fr, 44, 1.3, 4, sound=None)
    # bonk -> dizzy
    T.squash(fr, 47, 0.25, 1, 6)
    T.brows(fr, 48, 0.08)
    T.mouth_set(fr, 48, 0.9)
    T.wobble(fr["piv"], 50, 104, 7, 4, 1, sound=None)
    T.dizzy_stars(fr, 50, 112)
    for i, f in enumerate(range(52, 104, 6)):
        T.look(fr, f, 0.05 * math.cos(i * 1.6), 0.04 * math.sin(i * 1.6))
    T.mouth_set(fr, 70, 0.0)
    # hero giggles, friend recovers and gives a look... then both laugh
    T.arms(hero, 76, 0.4, fwd=-1.7)
    T.laugh(hero, 76, 104)
    T.arms(hero, 106, 0.0)
    T.eyes_norm(fr, 108)
    T.blink(fr, 112)
    T.look(fr, 114, -0.05)
    T.brows(fr, 116, -0.03)
    T.look(hero, 118, 0.05)
    T.eyes_big(hero, 120, 1.15, 3, sound=None)
    T.brows(fr, 128, 0.0)
    T.jump_joy(fr, 130)
    T.jump_joy(hero, 132, sound=None)
    return 168, 47


# --------------------------------------------------------------------------- 3. balloon float
def balloon_float(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.2, 0.15)
    fr = T.make_character(spec["friend"], 1.05, 0.3)
    T.turn(fr, 1, -18, 1)
    bal = T.make_prop("balloon", (0.62, -0.02, 1.65), hero["root"], name="balloon")
    T.show(bal, 1, True)
    hand = [a for a in hero["arms"] if a.location[0] > 0][0]
    T.key(hand, "rotation_euler", 1, (0, -2.3, 0))
    T.key(bal, "rotation_euler", 1, (0, math.radians(-4), 0))
    for f in range(12, 168, 12):
        T.key(bal, "rotation_euler", f, (0, math.radians(4 if (f // 12) % 2 else -4), 0))

    p, t = _two([-0.5, 0.6], 40, 0.9)
    T.shot(cam, tgt, 1, 36, p, t, 40, (p[0], p[1] + 0.3, p[2]), t)
    p, t = _two([-0.6, 1.2], 28, 0.9)
    T.shot(cam, tgt, 37, 96, p, t, 28, (p[0], p[1], p[2] + 1.1), (t[0], t[1], t[2] + 1.2))
    p, t = _two([-0.6, 1.2], 28, 1.2)
    T.shot(cam, tgt, 97, 168, (p[0], p[1], 1.9), (t[0], t[1], 1.3), 28, (p[0], p[1] + 0.3, 1.0), (t[0], t[1], 0.75))

    T.idle(fr, 1, 168)
    T.eyes_happy(hero, 4)
    T.mouth_set(hero, 4, 0.6)
    x = -0.2
    T.hop(hero, 6, x, x, 0.25, 10)
    T.hop(hero, 20, x, x, 0.25, 10)
    T.eyes_norm(hero, 34)
    T.mouth_set(hero, 34, 0.0)
    # up, up and away
    r = hero["root"]
    T.key(r, "location", 40, (x, 0.15, 0))
    T.key(r, "location", 52, (x, 0.15, 0.35))
    T.key(r, "location", 92, (x + 0.1, 0.15, 1.7))
    T.sfx(42, "slide_up")
    T.sfx(70, "sparkle")
    T.look(hero, 52, 0.0, -0.05)
    T.eyes_big(hero, 56, 1.3, 4, sound=None)
    T.mouth_set(hero, 56, 0.8)
    T.brows(hero, 56, 0.07)
    T.look(fr, 50, -0.03, 0.05)
    T.eyes_big(fr, 58, 1.25, 4, sound=None)
    T.mouth_set(fr, 58, 0.9)
    T.key(hand, "rotation_euler", 99, (0, -2.3, 0))
    T.arms(hero, 104, 2.2, d=3, hold=False)
    # POP! hang... fall
    T.sfx(100, "pop")
    T.key(bal, "scale", 99, (1, 1, 1))
    T.key(bal, "scale", 101, (1.4, 1.4, 1.4))
    T.key(bal, "scale", 102, (0.01, 0.01, 0.01), "CONSTANT")
    T.show(bal, 102, False)
    T.eyes_big(hero, 101, 1.5, 1, sound=None)
    T.key(r, "location", 104, (x + 0.1, 0.15, 1.7))
    T.key(r, "location", 115, (x + 0.1, 0.15, 0.0))
    T.sfx(103, "slide_down")
    T.stretch(hero, 110, 0.25, 4, 5)
    T.sfx(115, "thud")
    T.squash(hero, 116, 0.32, 1, 8)
    T.arms(hero, 116, 0.2)
    T.dizzy_stars(hero, 117, 150)
    T.eyes_norm(hero, 124)
    T.look(fr, 116, -0.04, -0.02)
    T.mouth_set(fr, 120, 0.0)
    T.laugh(fr, 124, 146)
    T.blink(hero, 140)
    T.laugh(hero, 146, 160, sound=False)
    T.jump_joy(fr, 150, sound="ding")
    return 168, 78


# --------------------------------------------------------------------------- 4. surprise in the gift box
def gift_surprise(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -1.0, 0.15)
    gift = T.make_prop("gift", (0.45, 0.3, 0), name="gift")
    gift.scale = (1.25, 1.25, 1.25)
    lid = T.bpy.data.objects[gift["lid"]]
    fr = T.make_character(spec["friend"], 0.45, 0.3, -1.4)
    fr["root"].scale = tuple(v * 0.7 for v in fr["root"].scale)

    p, t = _two([0.0, 0.9], 40, 0.5)
    T.shot(cam, tgt, 1, 30, p, t, 40, (p[0], p[1] + 0.3, p[2]), t)
    p, t = _two([-1.0, 0.9], 30)
    T.shot(cam, tgt, 31, 70, p, t, 30)
    p, t = _two([-0.75, 0.9], 34)
    T.shot(cam, tgt, 71, 168, p, t, 34, (p[0], p[1] + 0.3, p[2]), t)

    T.wobble(gift, 6, 28, 5, 3)
    T.idle(hero, 1, 30)
    T.look(hero, 32, 0.05)
    T.eyes_big(hero, 36)
    T.mouth_set(hero, 36, 0.6)
    T.mouth_set(hero, 44, 0.0)
    T.eyes_norm(hero, 46)
    T.hop(hero, 42, -1.0, -0.78, 0.3)
    T.hop(hero, 56, -0.78, -0.56, 0.3)
    T.lean(hero, 68, 14, 6)
    T.wobble(gift, 72, 82, 7, 2)
    # POP - lid flies, friend springs out
    T.sfx(82, "pop")
    T.key(lid, "location", 82, (0, 0, 0.62))
    T.key(lid, "location", 90, (0.2, 0, 1.4))
    T.key(lid, "location", 102, (0.75, 0.3, -0.02))
    T.key(lid, "rotation_euler", 82, (0, 0, 0))
    T.key(lid, "rotation_euler", 102, (0, math.radians(400), 0))
    T.sfx(102, "thud")
    r = fr["root"]
    T.key(r, "location", 82, (0.45, 0.3, -1.4))
    T.key(r, "location", 89, (0.45, 0.3, 1.05))
    T.key(r, "location", 97, (0.45, 0.3, 0.58))
    T.sfx(84, "boing")
    T.stretch(fr, 88, 0.25, 3, 6)
    T.squash(fr, 98, 0.2, 1, 6)
    T.arms(fr, 88, 2.4, d=4)
    T.eyes_happy(fr, 88)
    T.mouth_set(fr, 88, 1.0, 1.1)
    T.sfx(90, "sparkle")
    # hero jumps back startled
    T.lean(hero, 84, 0, 2)
    T.hop(hero, 84, -0.56, -0.8, 0.35, 10, sound=False)
    T.sfx(85, "slide_up")
    T.eyes_big(hero, 88, 1.45, 3, sound=None)
    T.brows(hero, 88, 0.08)
    T.mouth_set(hero, 88, 1.2, 0.9)
    T.arms(hero, 88, 2.2)
    T.eyes_norm(hero, 110, 6)
    T.brows(hero, 110, 0.0)
    T.arms(hero, 110, 0.0, d=8)
    T.arms(fr, 108, 0.6, d=8)
    T.laugh(fr, 104, 128)
    T.laugh(hero, 114, 134, sound=False)
    T.hop(hero, 138, -0.8, -0.6, 0.3)
    T.jump_joy(hero, 152)
    return 168, 92


# --------------------------------------------------------------------------- 5. hide and seek
def hide_seek(spec, cam, tgt):
    seek = T.make_character(spec["friend"], -0.75, 0.2)
    hero = T.make_character(spec["hero"], -0.15, 0.15)
    bush = T.make_prop("bush", (0.55, 0.45, 0), name="hidebush")

    p, t = _two([-0.75, -0.1], 38)
    T.shot(cam, tgt, 1, 40, p, t, 38, (p[0] + 0.3, p[1] + 0.2, p[2]), (t[0] + 0.3, t[1], t[2]))
    p, t = _two([-0.75, 0.6], 32)
    T.shot(cam, tgt, 41, 96, p, t, 32)
    p, t = _two([-0.3, 0.75], 36)
    T.shot(cam, tgt, 97, 168, p, t, 36, (p[0], p[1] + 0.3, p[2]), t)

    # seeker counts with eyes covered
    T.arms(seek, 6, -0.35, fwd=-2.1, d=5)
    T.eyes_happy(seek, 6)
    for f in range(8, 42, 8):
        T.sfx(f, "tick")
        T.squash(seek, f + 2, 0.05, 2, 3)
    # hero tiptoes behind the bush and crouches
    T.look(hero, 4, 0.05)
    T.mouth_set(hero, 4, 0.0)
    T.hop(hero, 10, -0.15, 0.2, 0.15, 10, 0.15, 0.6, sound=False)
    T.hop(hero, 24, 0.2, 0.5, 0.15, 10, 0.6, 0.95, sound=False)
    T.sfx(12, "swish")
    T.sfx(26, "swish")
    p = hero["piv"]
    T.key(p, "scale", 36, (1, 1, 1))
    T.key(p, "scale", 40, (1.2, 1.2, 0.55))
    T.key(p, "scale", 98, (1.2, 1.2, 0.55))
    # seeker looks around
    T.arms(seek, 46, 0.0)
    T.eyes_norm(seek, 46)
    T.look(seek, 52, -0.05)
    T.turn(seek, 54, -20)
    T.look(seek, 64, 0.05)
    T.turn(seek, 66, 25)
    T.brows(seek, 64, -0.02)
    T.hop(seek, 70, -0.75, -0.25, 0.3)
    T.wobble(bush, 78, 92, 4, 3, 1, sound=None)
    T.sfx(78, "swish")
    T.look(seek, 84, 0.05, 0.01)
    T.lean(seek, 92, 10, 6)
    # BOO!
    T.sfx(99, "pop")
    T.key(p, "scale", 100, (0.9, 0.9, 1.25))
    T.key(p, "scale", 106, (1, 1, 1))
    r = hero["root"]
    T.key(r, "location", 99, (0.5, 0.95, 0))
    T.key(r, "location", 104, (0.5, 0.95, 0.35))
    T.key(r, "location", 110, (0.5, 0.95, 0.0))
    T.sfx(101, "boing")
    T.arms(hero, 102, 2.4)
    T.mouth_set(hero, 102, 1.0, 1.1)
    T.eyes_big(hero, 102, 1.25, 3, sound=None)
    T.look(hero, 102, -0.04)
    T.lean(seek, 104, -8, 3)
    T.squash(seek, 104, 0.25, 2, 6)
    T.eyes_big(seek, 104, 1.45, 3, sound="doink")
    T.brows(seek, 104, 0.09)
    T.mouth_set(seek, 104, 1.2, 0.9)
    T.hop(seek, 106, -0.25, -0.45, 0.25, 10, sound=False)
    T.arms(hero, 120, 0.0, d=8)
    T.eyes_norm(hero, 118)
    T.eyes_norm(seek, 120, 6)
    T.brows(seek, 122, 0.0)
    T.lean(seek, 120, 0, 6)
    T.laugh(seek, 124, 146)
    T.laugh(hero, 126, 146, sound=False)
    T.jump_joy(seek, 148)
    T.jump_joy(hero, 150, sound=None)
    return 168, 104


# --------------------------------------------------------------------------- 6. banana peel slip
def slip_peel(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -1.3, 0.15)
    fr = T.make_character(spec["friend"], 1.4, 0.35)
    T.turn(fr, 1, -20, 1)
    peel = T.make_prop("peel", (-0.05, 0.12, 0), name="peel")

    T.shot(cam, tgt, 1, 32, (-1.15, -2.9, 0.8), (-1.15, 0.15, 0.6), 40, (-0.75, -2.9, 0.8), (-0.75, 0.15, 0.6))
    p, t = _two([-0.8, 1.2], 30)
    T.shot(cam, tgt, 33, 80, p, t, 30)
    p, t = _two([0.2, 1.45], 34)
    T.shot(cam, tgt, 81, 168, p, t, 38, (p[0], p[1] + 0.3, p[2]), t)

    T.idle(fr, 1, 168)
    T.eyes_happy(hero, 2)
    T.mouth_set(hero, 2, 0.6)
    T.hop(hero, 2, -1.3, -0.95, 0.35)
    T.hop(hero, 17, -0.95, -0.6, 0.35)
    T.eyes_norm(hero, 32)
    T.mouth_set(hero, 32, 0.0)
    T.hop(hero, 32, -0.6, -0.08, 0.35)
    # whoops!
    r, pv = hero["root"], hero["piv"]
    T.sfx(45, "slide_up")
    T.sfx(45, "swish")
    T.key(r, "location", 44, (-0.08, 0.15, 0))
    T.key(r, "location", 52, (0.2, 0.15, 0.95))
    T.key(r, "location", 61, (0.42, 0.15, 0.0))
    T.key(pv, "rotation_euler", 44, (0, 0, 0))
    T.key(pv, "rotation_euler", 60, (0, math.radians(-360), 0))
    T.key(pv, "rotation_euler", 61, (0, 0, 0), "CONSTANT")
    T.eyes_big(hero, 48, 1.45, 3, sound=None)
    T.brows(hero, 48, 0.08)
    T.mouth_set(hero, 48, 1.2, 0.9)
    T.arms(hero, 48, 2.4, d=3)
    T.key(peel, "location", 44, (-0.05, 0.12, 0))
    T.key(peel, "location", 54, (-0.75, 0.3, 0))
    T.key(peel, "rotation_euler", 44, (0, 0, 0))
    T.key(peel, "rotation_euler", 54, (0, 0, math.radians(540)))
    T.sfx(61, "thud")
    T.squash(hero, 62, 0.33, 1, 8)
    T.arms(hero, 64, 0.3)
    T.look(fr, 46, -0.05, 0.03)
    T.eyes_big(fr, 50, 1.3, 3, sound=None)
    T.mouth_set(fr, 50, 1.0)
    # dizzy, then everybody laughs
    T.dizzy_stars(hero, 64, 126)
    T.wobble(pv, 64, 120, 6, 4, 1, sound=None)
    T.mouth_set(hero, 66, 0.0)
    T.eyes_norm(hero, 68)
    T.brows(hero, 70, 0.0)
    for i, f in enumerate(range(68, 120, 6)):
        T.look(hero, f, 0.05 * math.cos(i * 1.7), 0.04 * math.sin(i * 1.7))
    T.mouth_set(fr, 70, 0.0)
    T.laugh(fr, 96, 126)
    T.blink(hero, 128)
    T.look(hero, 132, 0.0, 0.0)
    T.laugh(hero, 136, 156, sound=False)
    T.jump_joy(fr, 140)
    return 168, 52


GAGS = {"steal_treat": steal_treat, "ball_bonk": ball_bonk, "balloon_float": balloon_float,
        "gift_surprise": gift_surprise, "hide_seek": hide_seek, "slip_peel": slip_peel}
