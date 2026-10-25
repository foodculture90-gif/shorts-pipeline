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
    T.sfx(66, "tiptoe")
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
    T.sfx(112, "wahwah")
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
    T.sfx(48, "honk")
    T.sfx(62, "boing")
    T.sfx(68, "rattle")
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
    T.sfx(122, "squeak")
    T.jump_joy(fr, 130)
    T.jump_joy(hero, 132, sound=None)
    T.sfx(150, "tada")
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
    T.sfx(56, "bubble")
    T.sfx(70, "sparkle")
    T.sfx(84, "twinkle")
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
    T.sfx(100, "crash")
    T.key(bal, "scale", 99, (1, 1, 1))
    T.key(bal, "scale", 101, (1.4, 1.4, 1.4))
    T.key(bal, "scale", 102, (0.01, 0.01, 0.01), "CONSTANT")
    T.show(bal, 102, False)
    T.eyes_big(hero, 101, 1.5, 1, sound=None)
    T.key(r, "location", 104, (x + 0.1, 0.15, 1.7))
    T.key(r, "location", 115, (x + 0.1, 0.15, 0.0))
    T.sfx(103, "xylo_down")
    T.stretch(hero, 110, 0.25, 4, 5)
    T.sfx(115, "thud")
    T.sfx(116, "splat")
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
    p, t = _two([-0.85, 0.9], 28)
    T.shot(cam, tgt, 71, 168, p, t, 28, (p[0], p[1] + 0.3, p[2]), t)

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
    T.wobble(gift, 72, 82, 7, 2, sound="rattle")
    T.sfx(60, "drumroll")
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
    T.sfx(90, "tada")
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
    T.sfx(97, "squeak")
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
    T.sfx(11, "tiptoe")
    T.sfx(25, "tiptoe")
    T.sfx(38, "squeak")
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
    T.sfx(78, "rattle")
    T.sfx(86, "rattle")
    T.look(seek, 84, 0.05, 0.01)
    T.lean(seek, 92, 10, 6)
    # BOO!
    T.sfx(99, "pop")
    T.sfx(100, "honk")
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
    T.sfx(43, "squeak")
    T.sfx(45, "slide_up")
    T.sfx(45, "swish")
    T.sfx(53, "xylo_down")
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
    T.sfx(61, "crash")
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
    T.sfx(156, "tada")
    return 168, 52


# --------------------------------------------------------------------------- little helpers for the new gags
def _arm(ch, side, f, angle, fwd=0.0, d=4):
    """One arm only (side -1 = left, 1 = right)."""
    for a in ch["arms"]:
        if (1 if a.location[0] > 0 else -1) == side:
            T.key(a, "rotation_euler", f - d, tuple(a.rotation_euler))
            T.key(a, "rotation_euler", f, (fwd, -side * angle, 0))


def _spin(ch, f0, n=12, turns=1):
    r = ch["root"]
    T.key(r, "rotation_euler", f0, tuple(r.rotation_euler))
    T.key(r, "rotation_euler", f0 + n, (0, 0, math.radians(360 * turns)), "LINEAR")
    T.key(r, "rotation_euler", f0 + n + 1, (0, 0, 0), "CONSTANT")
    r.rotation_euler = (0, 0, 0)


def _confetti(name, f0, loc, n=26, spread=1.4):
    rnd = T.random.Random(f0 + n)
    cols = ["#FF4D6D", "#FFD23F", "#4DA6FF", "#5CCB6B", "#B57BFF", "#FF8A3D", "#FFFFFF"]
    root = T.empty(name, loc)
    T.show(root, 1, False)
    for i in range(n):
        c = T.box(f"{name}{i}", (0.05, 0.012, 0.08), (0, 0, 0), T.mat(rnd.choice(cols), 0.5), root, bevel=0.003)
        dx, dy = rnd.uniform(-spread, spread), rnd.uniform(-0.4, 0.6)
        T.key(c, "location", f0, (0, 0, 0))
        T.key(c, "location", f0 + 8, (dx * 0.5, dy * 0.5, rnd.uniform(0.9, 1.6)))
        T.key(c, "location", f0 + 46, (dx, dy, 0.0))
        T.key(c, "rotation_euler", f0, (0, 0, 0))
        T.key(c, "rotation_euler", f0 + 46, (rnd.uniform(-9, 9), rnd.uniform(-9, 9), rnd.uniform(-9, 9)))
    T.show(root, f0, True)
    T.sfx(f0, "pop")
    T.sfx(f0 + 2, "sparkle")
    return root


def _bubble_mat():
    m = T.bpy.data.materials.new("bubble")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    for k, v in (("Base Color", (0.85, 0.95, 1.0, 1)), ("Roughness", 0.02), ("IOR", 1.05), ("Transmission Weight", 1.0),
                 ("Coat Weight", 1.0), ("Alpha", 0.55), ("Specular IOR Level", 0.8)):
        try:
            b.inputs[k].default_value = v
        except Exception:  # noqa: BLE001
            pass
    try:
        m.blend_method = "BLEND"
    except Exception:  # noqa: BLE001
        pass
    return m


def _flower(name, loc, color):
    root = T.empty(name, loc)
    T.cyl(name + "_stem", 0.018, 0.55, (0, 0, 0.275), T.mat("#3FA64E", 0.6), root)
    T.sphere(name + "_leaf", 0.07, (0.06, 0, 0.22), T.mat("#3FA64E", 0.6), root, scale=(1.4, 0.4, 0.6), rot=(0, 0.5, 0))
    head = T.empty(name + "_head", (0, -0.02, 0.6), root)
    petals = []
    for i in range(7):
        a = i / 7 * math.tau
        petals.append(T.sphere(f"{name}_p{i}", 0.06, (math.cos(a) * 0.09, 0, math.sin(a) * 0.09), T.mat(color, 0.5), head,
                               scale=(1.2, 0.4, 0.8), rot=(0, -a, 0), sub=1))
    T.sphere(name + "_mid", 0.055, (0, -0.02, 0), T.mat("#FFD23F", 0.4), head, scale=(1, 0.6, 1))
    return root, head, petals


# --------------------------------------------------------------------------- 7. big sneeze
def sneeze(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.75, 0.15)
    fr = T.make_character(spec["friend"], 0.55, 0.25)
    T.turn(hero, 1, 14, 1)
    T.turn(fr, 1, -16, 1)
    col = T.PROP_COLOR or T.VAR.choice(["#FF6B8B", "#B57BFF", "#FF8A3D", "#4DA6FF", "#FFFFFF"])
    fl, head, petals = _flower("bigflower", (-0.38, -0.05, 0), col)

    p, t = _two([-0.75, -0.3], 46, 0.65)
    T.shot(cam, tgt, 1, 34, p, t, 46, (p[0] + 0.05, p[1] + 0.25, p[2]), t)
    T.shot(cam, tgt, 35, 76, (-0.65, -2.2, 0.78), (-0.7, 0.15, 0.72), 52, (-0.68, -1.95, 0.76), (-0.7, 0.15, 0.72))
    p, t = _two([-0.8, 1.5], 30)
    T.shot(cam, tgt, 77, 168, p, t, 30, (p[0], p[1] + 0.3, p[2]), t)

    T.idle(fr, 1, 76)
    # hero sniffs the flower
    T.look(hero, 4, 0.04, -0.02)
    T.lean(hero, 14, 14, 8)
    T.sfx(14, "sniff")
    T.eyes_happy(hero, 18)
    T.mouth_set(hero, 18, 0.0)
    T.sfx(20, "sparkle")
    T.wobble(head, 16, 30, 6, 3, 1, sound=None)
    # ah... ah... AH...
    T.eyes_norm(hero, 34)
    T.brows(hero, 36, 0.06)
    for k, f in enumerate((38, 50, 62)):
        T.lean(hero, f, -6 - 7 * k, 6)
        T.mouth_set(hero, f, 0.4 + 0.3 * k, 0.9)
        for e in hero["eyes"]:
            T.key(e, "scale", f, (1.05, 1, 0.45))
        T.sfx(f - 2, "squeak")
    T.sfx(40, "drumroll")
    T.look(fr, 50, -0.05)
    T.eyes_big(fr, 60, 1.2, 4, sound=None)
    # ACHOO!
    T.sfx(72, "achoo")
    T.lean(hero, 76, 26, 3)
    T.squash(hero, 77, 0.22, 1, 6)
    T.eyes_happy(hero, 76, 1)
    T.mouth_set(hero, 76, 1.1, 1.1)
    T.sfx(77, "swish")
    T.sfx(78, "whoosh")
    for i, pt in enumerate(petals):  # the petals fly off
        a = i / len(petals) * math.tau
        T.key(pt, "location", 76, tuple(pt.location))
        T.key(pt, "location", 96, (1.4 + 0.5 * math.cos(a), 0.3 * math.sin(a), -0.6 + 0.2 * math.sin(a * 2)))
        T.show(pt, 96, False)
    r = fr["root"]  # the friend is blown away
    T.key(r, "location", 77, (0.55, 0.25, 0))
    T.key(r, "location", 86, (1.05, 0.3, 0.75))
    T.key(r, "location", 95, (1.45, 0.35, 0))
    T.key(fr["piv"], "rotation_euler", 77, (0, 0, 0))
    T.key(fr["piv"], "rotation_euler", 94, (0, math.radians(360), 0))
    T.key(fr["piv"], "rotation_euler", 95, (0, 0, 0), "CONSTANT")
    T.eyes_big(fr, 79, 1.45, 2, sound=None)
    T.mouth_set(fr, 79, 1.2, 0.9)
    T.arms(fr, 80, 2.4, d=2)
    T.sfx(95, "thud")
    T.squash(fr, 96, 0.3, 1, 8)
    T.arms(fr, 98, 0.3)
    T.dizzy_stars(fr, 97, 134)
    T.wobble(fr["piv"], 98, 128, 6, 4, 1, sound=None)
    # oops! hero covers mouth, looks at the bald flower
    T.lean(hero, 90, 0, 8)
    T.eyes_norm(hero, 90)
    T.mouth_set(hero, 92, 0.6, 0.6)
    T.arms(hero, 94, 0.5, fwd=-1.9, d=6)
    T.eyes_big(hero, 96, 1.3, 4, sound="doink")
    T.look(hero, 104, -0.05, -0.03)
    T.sfx(108, "wahwah")
    T.look(hero, 120, 0.05)
    T.arms(hero, 124, 0.0, d=6)
    T.mouth_set(fr, 112, 0.0)
    T.eyes_norm(fr, 132)
    T.laugh(fr, 136, 158)
    T.laugh(hero, 134, 156, sound=False)
    T.jump_joy(hero, 154, sound="ding")
    return 168, 78


# --------------------------------------------------------------------------- 8. dance party
def dance_party(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.55, 0.15)
    fr = T.make_character(spec["friend"], 0.6, 0.25)
    T.turn(fr, 1, -12, 1)
    p, t = _two([-0.55, 0.6], 34, 0.8)
    T.shot(cam, tgt, 1, 62, p, t, 34, (p[0] - 0.2, p[1] + 0.25, p[2]), t)
    p, t = _two([-0.55, 0.6], 40, 0.75)
    T.shot(cam, tgt, 63, 116, (p[0] + 0.5, p[1], p[2] - 0.15), (t[0] + 0.5, t[1], t[2]), 46, (p[0] + 0.3, p[1] + 0.2, p[2]), t)
    p, t = _two([-0.7, 0.75], 30, 0.9)
    T.shot(cam, tgt, 117, 168, p, t, 30, (p[0], p[1] + 0.35, p[2] + 0.1), t)

    T.idle(fr, 1, 60)
    # hero starts grooving: side sways on the beat, arms up and down
    T.eyes_happy(hero, 6)
    T.mouth_set(hero, 6, 0.6, 1.1)
    for k, f in enumerate(range(8, 56, 8)):
        T.lean(hero, f, 12 if k % 2 else -12, 4, axis=1)
        _arm(hero, 1 if k % 2 else -1, f, 2.5, d=4)
        _arm(hero, -1 if k % 2 else 1, f, 0.3, d=4)
        T.sfx(f, "clap" if k % 2 else "tick")
    T.hop(hero, 30, -0.55, -0.55, 0.3, 10, sound=False)
    T.sfx(32, "boing")
    _spin(hero, 56, 10)
    T.sfx(56, "whoosh")
    T.lean(hero, 58, 0, 4, axis=1)
    T.arms(hero, 66, 2.2, d=4)
    T.sfx(66, "ding")
    # friend watches, then copies... with a too-big spin
    T.look(fr, 20, -0.05)
    T.eyes_big(fr, 30, 1.2, 4, sound=None)
    T.mouth_set(fr, 36, 0.5)
    T.eyes_happy(fr, 66)
    T.mouth_set(fr, 66, 0.7, 1.1)
    for k, f in enumerate(range(70, 98, 7)):
        T.lean(fr, f, 16 if k % 2 else -16, 4, axis=1)
        _arm(fr, 1 if k % 2 else -1, f, 2.6, d=3)
        _arm(fr, -1 if k % 2 else 1, f, 0.2, d=3)
        T.sfx(f, "clap" if k % 2 else "tick")
    T.lean(fr, 100, 0, 3, axis=1)
    _spin(fr, 100, 14, 3)
    T.sfx(100, "slide_up")
    T.sfx(108, "whoosh")
    T.arms(fr, 104, 2.4, d=3)
    T.eyes_norm(fr, 112)
    T.wobble(fr["piv"], 116, 136, 10, 3, 1, sound=None)
    T.dizzy_stars(fr, 116, 140)
    T.sfx(118, "honk")
    T.squash(fr, 136, 0.28, 2, 6)
    T.sfx(136, "thud")
    T.arms(hero, 100, 0.0, d=6)
    T.eyes_norm(hero, 100)
    T.look(hero, 104, 0.05)
    T.eyes_big(hero, 118, 1.3, 4, sound=None)
    T.mouth_set(hero, 118, 1.0)
    # then they dance together + confetti
    T.laugh(hero, 126, 142)
    T.laugh(fr, 142, 150, sound=False)
    _confetti("confetti", 144, (0.05, 0.3, 1.6))
    T.jump_joy(hero, 146, sound=None)
    T.jump_joy(fr, 148, sound=None)
    T.sfx(148, "tada")
    return 168, 108


# --------------------------------------------------------------------------- 9. bubbles
def bubbles(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.85, 0.15)
    fr = T.make_character(spec["friend"], 0.7, 0.3)
    T.turn(hero, 1, 18, 1)
    T.turn(fr, 1, -14, 1)
    bm = _bubble_mat()
    wand = T.empty("wand", (0.42, -0.25, 0.62), hero["root"])
    T.cyl("wand_stick", 0.015, 0.32, (0, 0, -0.14), T.mat("#FF8FC8", 0.4), wand)
    ring = [(math.cos(a) * 0.08, 0, 0.08 + math.sin(a) * 0.08) for a in [i / 12 * math.tau for i in range(13)]]
    T.curve_line("wand_ring", ring, 0.012, T.mat("#FF8FC8", 0.4), wand)
    wx, wz = -0.45, 0.85

    p, t = _two([-0.85, 0.7], 34, 0.95)
    T.shot(cam, tgt, 1, 70, p, t, 34, (p[0], p[1] + 0.25, p[2]), t)
    p, t = _two([-0.7, 0.9], 30, 1.25)
    T.shot(cam, tgt, 71, 132, p, t, 30, (p[0], p[1], p[2] + 0.5), (t[0], t[1], t[2] + 0.55))
    p, t = _two([-0.85, 0.9], 32, 0.8)
    T.shot(cam, tgt, 133, 168, p, t, 32, (p[0], p[1] + 0.3, p[2]), t)

    T.idle(fr, 1, 60)
    # three little bubbles - the friend hops to pop them
    pops = []
    for k, (f, x1, z1) in enumerate(((14, 0.35, 1.25), (30, 0.75, 1.45), (46, 0.15, 1.15))):
        T.lean(hero, f - 4, -6, 4)
        T.mouth_set(hero, f - 4, 0.5, 0.5)
        T.lean(hero, f, 4, 3)
        T.sfx(f, "bubble")
        b = T.sphere(f"bub{k}", 0.11, (wx, 0.1, wz), bm, sub=2)
        T.show(b, 1, False)
        T.show(b, f, True)
        T.key(b, "scale", f, (0.2, 0.2, 0.2))
        T.key(b, "scale", f + 6, (1, 1, 1))
        T.key(b, "location", f, (wx, 0.1, wz))
        pf = f + 22
        T.key(b, "location", pf, (x1, 0.28, z1))
        T.key(b, "scale", pf, (1, 1, 1))
        T.key(b, "scale", pf + 2, (1.5, 1.5, 1.5))
        T.show(b, pf + 2, False)
        pops.append((pf, x1))
    T.mouth_set(hero, 50, 0.0)
    for k, (pf, x1) in enumerate(pops):
        x0 = fr["root"].location[0]
        T.hop(fr, pf - 7, x0, x1 * 0.5 + 0.45, 0.55, 8, sound=False)
        T.arms(fr, pf - 2, 2.5, d=3)
        T.sfx(pf + 1, "pop")
        T.eyes_happy(fr, pf + 2)
        T.mouth_set(fr, pf + 2, 0.7)
    T.arms(fr, 76, 0.2, d=4)
    T.eyes_norm(fr, 78)
    fx = fr["root"].location[0]
    # the GIANT bubble
    T.lean(hero, 80, -8, 6)
    T.sfx(80, "sniff")
    T.lean(hero, 86, 6, 4)
    T.mouth_set(hero, 86, 0.6, 0.6)
    T.sfx(86, "slide_up")
    g = T.sphere("bigbub", 0.62, (wx, 0.1, wz), bm, sub=2)
    T.show(g, 1, False)
    T.show(g, 86, True)
    T.key(g, "scale", 86, (0.15, 0.15, 0.15))
    T.key(g, "scale", 100, (1, 1, 1))
    T.key(g, "location", 86, (wx, 0.1, wz))
    T.key(g, "location", 104, (fx, 0.3, 0.6))
    T.sfx(104, "bubble")
    r = fr["root"]  # friend trapped - floats up
    T.key(r, "location", 104, (fx, 0.3, 0))
    T.key(r, "location", 130, (fx, 0.3, 1.05))
    T.key(g, "location", 130, (fx, 0.3, 1.65))
    T.eyes_big(fr, 108, 1.35, 4, sound="sparkle")
    T.mouth_set(fr, 108, 0.9)
    for k, f in enumerate(range(110, 130, 5)):
        T.arms(fr, f, 1.6 if k % 2 else 0.6, d=3)
    T.sfx(112, "twinkle")
    T.mouth_set(hero, 100, 0.0)
    T.look(hero, 110, 0.05, 0.05)
    T.eyes_big(hero, 112, 1.25, 4, sound=None)
    # POP - and down
    T.sfx(131, "pop")
    T.key(g, "scale", 130, (1, 1, 1))
    T.key(g, "scale", 132, (1.25, 1.25, 1.25))
    T.show(g, 132, False)
    T.key(r, "location", 132, (fx, 0.3, 1.05))
    T.key(r, "location", 140, (fx, 0.3, 0.0))
    T.sfx(133, "xylo_down")
    T.sfx(140, "splat")
    T.squash(fr, 141, 0.3, 1, 8)
    T.dizzy_stars(fr, 142, 166)
    T.laugh(hero, 140, 162)
    T.laugh(fr, 154, 166, sound=False)
    return 168, 112


# --------------------------------------------------------------------------- 10. wake-up surprise
def wake_up(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -2.2, 0.15)
    fr = T.make_character(spec["friend"], 0.65, 0.3)
    T.turn(fr, 1, -10, 1)
    T.lean(fr, 2, 10, 1, axis=1)
    T.eyes_happy(fr, 2, 1)  # asleep
    T.mouth_set(fr, 2, 0.0)
    T.brows(fr, 2, -0.02, 1)
    snot = T.sphere("snot", 0.07, (0.06, -0.52, 0.56), _bubble_mat(), fr["piv"], sub=2)
    for k, f in enumerate(range(4, 84, 20)):  # breathing + bubble in and out
        T.key(fr["piv"], "scale", f, (1, 1, 1))
        T.key(fr["piv"], "scale", f + 10, (1.05, 1.05, 0.95))
        T.key(snot, "scale", f, (0.3, 0.3, 0.3))
        T.key(snot, "scale", f + 10, (1.3, 1.3, 1.3))
        T.sfx(f + 2, "snore")
    horn = T.empty("horn", (0.0, -0.5, 0.45), hero["piv"])
    T.cone("horn_cone", 0.05, 0.015, 0.2, (0, -0.1, 0), T.mat("#FF4D6D", 0.4), horn, rot=(math.radians(90), 0, 0))
    curl = T.cyl("horn_curl", 0.035, 0.36, (0, -0.38, 0), T.mat("#FFD23F", 0.4), horn, rot=(math.radians(90), 0, 0))
    T.show(horn, 1, False)
    T.key(curl, "scale", 1, (1, 1, 0.05))

    p, t = _two([-2.2, 0.65], 30, 0.7)
    T.shot(cam, tgt, 1, 60, p, t, 30, (p[0] + 0.6, p[1], p[2]), (t[0] + 0.6, t[1], t[2]))
    T.shot(cam, tgt, 61, 82, (-0.55, -2.3, 0.85), (-0.45, 0.15, 0.72), 50, (-0.55, -2.1, 0.85), (-0.45, 0.15, 0.72))
    p, t = _two([-0.55, 0.75], 28, 1.0)
    T.shot(cam, tgt, 83, 168, p, t, 28, (p[0], p[1] + 0.3, p[2]), t)

    # hero tiptoes in
    T.look(hero, 4, 0.05)
    T.mouth_set(hero, 4, 0.0)
    x = -2.2
    for k, f in enumerate(range(8, 56, 12)):
        T.hop(hero, f, x, x + 0.43, 0.12, 10, sound=False)
        T.sfx(f + 2, "tiptoe")
        x += 0.43
    _arm(hero, 1, 10, 0.4, fwd=-2.2, d=4)  # shh!
    _arm(hero, 1, 56, 0.0, d=4)
    # cheeky look at the camera, out comes the party horn
    T.turn(hero, 62, -10, 4)
    T.look(hero, 62, 0.0, -0.02)
    T.eyes_happy(hero, 64)
    T.mouth_set(hero, 64, 0.0)
    T.sfx(64, "giggle")
    T.turn(hero, 72, 20, 4)
    T.eyes_norm(hero, 72)
    T.show(horn, 74, True)
    T.sfx(74, "pop")
    T.lean(hero, 78, -10, 4)
    # PARP!
    T.lean(hero, 84, 10, 2)
    T.key(curl, "scale", 83, (1, 1, 0.05))
    T.key(curl, "scale", 86, (1, 1, 1))
    T.key(curl, "scale", 100, (1, 1, 1))
    T.key(curl, "scale", 104, (1, 1, 0.05))
    T.sfx(84, "partyhorn")
    T.key(snot, "scale", 84, (1.3, 1.3, 1.3))
    T.key(snot, "scale", 86, (1.8, 1.8, 1.8))
    T.show(snot, 86, False)
    T.sfx(86, "pop")
    r = fr["root"]  # friend jumps sky high
    T.key(r, "location", 86, (0.65, 0.3, 0))
    T.key(r, "location", 96, (0.65, 0.3, 1.3))
    T.key(r, "location", 108, (0.65, 0.3, 0))
    T.sfx(87, "slide_up")
    T.sfx(87, "boing")
    T.lean(fr, 88, 0, 2, axis=1)
    T.eyes_big(fr, 89, 1.5, 3, sound=None)
    T.brows(fr, 89, 0.1, 2)
    T.mouth_set(fr, 89, 1.2, 0.9)
    T.arms(fr, 90, 2.5, d=3)
    T.stretch(fr, 92, 0.25, 3, 6)
    T.sfx(108, "thud")
    T.squash(fr, 109, 0.28, 1, 7)
    T.arms(fr, 112, 0.2, d=4)
    # grumpy look... then friend takes the horn and blows it back!
    T.eyes_norm(fr, 116)
    T.brows(fr, 118, -0.05)
    T.mouth_set(fr, 116, 0.0)
    T.look(fr, 118, -0.05)
    T.turn(fr, 118, -25, 6)
    T.laugh(hero, 106, 122)
    T.show(horn, 124, False)
    T.sfx(124, "swish")
    horn2 = T.empty("horn2", (0.0, -0.5, 0.45), fr["piv"])
    T.cone("horn2_cone", 0.05, 0.015, 0.2, (0, -0.1, 0), T.mat("#FF4D6D", 0.4), horn2, rot=(math.radians(90), 0, 0))
    curl2 = T.cyl("horn2_curl", 0.035, 0.36, (0, -0.38, 0), T.mat("#FFD23F", 0.4), horn2, rot=(math.radians(90), 0, 0))
    T.show(horn2, 1, False)
    T.show(horn2, 124, True)
    T.key(curl2, "scale", 1, (1, 1, 0.05))
    T.key(curl2, "scale", 131, (1, 1, 0.05))
    T.key(curl2, "scale", 134, (1, 1, 1))
    T.key(curl2, "scale", 146, (1, 1, 1))
    T.key(curl2, "scale", 149, (1, 1, 0.05))
    T.sfx(132, "partyhorn")
    T.eyes_big(hero, 134, 1.45, 2, sound=None)
    T.hop(hero, 133, hero["root"].location[0], hero["root"].location[0] - 0.3, 0.45, 10, sound=False)
    T.sfx(134, "boing")
    T.brows(fr, 136, 0.0)
    T.laugh(fr, 146, 166)
    T.laugh(hero, 148, 166, sound=False)
    return 168, 92


# --------------------------------------------------------------------------- 11. the race
def race(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -2.3, 0.0)
    fr = T.make_character(spec["friend"], -2.3, 0.55)
    for ch in (hero, fr):
        T.turn(ch, 1, 50, 1)
    fin = T.empty("finish", (1.9, 1.15, 0))  # finish arch just behind the line
    stripes = T.checker("#FFFFFF", "#2E3A59", 6.0, 0.5)
    for i, x in enumerate((-0.75, 0.75)):
        T.cyl(f"fin_pole{i}", 0.05, 1.7, (x, 0, 0.85), T.mat("#FF4D6D", 0.4), fin)
    T.box("fin_banner", (1.6, 0.06, 0.32), (0, 0, 1.6), stripes, fin, bevel=0.01)
    tape = [T.box(f"fin_tape{i}", (0.75, 0.03, 0.05), (-0.37 + i * 0.75, 0, 0.5), T.mat("#FFD23F", 0.4), fin, bevel=0.005)
            for i in range(2)]

    p, t = _two([-2.3, -1.5], 32, 0.65)
    T.shot(cam, tgt, 1, 28, (p[0] + 0.3, p[1], p[2]), t, 32, (p[0] + 0.4, p[1] + 0.2, p[2]), t)
    T.shot(cam, tgt, 29, 104, (-2.0, -3.6, 0.95), (-2.0, 0.3, 0.55), 26, (1.1, -3.6, 0.95), (1.1, 0.3, 0.55))
    p, t = _two([1.2, 2.4], 30, 0.85)
    T.shot(cam, tgt, 105, 168, p, t, 30, (p[0], p[1] + 0.3, p[2]), t)

    # ready... set...
    T.sfx(4, "drumroll")
    for ch in (hero, fr):
        T.key(ch["piv"], "scale", 6, (1, 1, 1))
        T.key(ch["piv"], "scale", 16, (1.12, 1.12, 0.82))
        T.brows(ch, 14, -0.04)
        T.look(ch, 14, 0.05)
    T.sfx(26, "whistle")
    # GO! the friend zooms ahead
    xf, xh = -2.3, -2.3
    for k, f in enumerate(range(28, 92, 9)):
        T.hop(fr, f, xf, xf + 0.42, 0.25, 8, sound=False)
        xf += 0.42
        if k % 2 == 0:
            T.sfx(f + 2, "boing")
    for k, f in enumerate(range(30, 74, 11)):
        T.hop(hero, f, xh, xh + 0.32, 0.22, 10, sound=False)
        xh += 0.32
    T.mouth_set(fr, 34, 0.6)
    T.eyes_happy(fr, 60)
    T.mouth_set(hero, 60, 0.9)
    T.brows(hero, 60, 0.06)
    # hero takes a deep breath... SUPER LEAP over the friend!
    T.key(hero["piv"], "scale", 78, (1, 1, 1))
    T.key(hero["piv"], "scale", 84, (1.2, 1.2, 0.7))
    T.sfx(82, "sniff")
    T.sfx(86, "slide_up")
    r = hero["root"]
    T.key(r, "location", 86, (xh, 0.0, 0))
    T.key(r, "location", 98, ((xh + 2.2) / 2, 0.2, 1.3))
    T.key(r, "location", 108, (2.2, 0.3, 0))
    T.stretch(hero, 90, 0.25, 3, 6)
    T.arms(hero, 90, 2.5, d=3)
    T.eyes_big(fr, 96, 1.35, 3, sound="doink")
    T.mouth_set(fr, 96, 1.0)
    T.key(fr["root"], "location", 100, (xf, 0.55, 0))
    for i, tp in enumerate(tape):  # the tape snaps
        T.key(tp, "rotation_euler", 104, (0, 0, 0))
        T.key(tp, "rotation_euler", 112, (0, math.radians(-70 if i else 70), 0))
    T.sfx(105, "zip")
    T.sfx(108, "land")
    T.squash(hero, 109, 0.25, 1, 6)
    T.turn(hero, 112, 0, 6)
    _confetti("winconfetti", 110, (2.1, 0.4, 1.2))
    T.sfx(112, "tada")
    T.jump_joy(hero, 114, sound=None)
    # friend arrives puffed out, then laughs along
    T.hop(fr, 104, xf, 1.35, 0.25, 10, sound=False)
    T.turn(fr, 116, 0, 6)
    T.eyes_norm(fr, 118)
    T.mouth_set(fr, 118, 0.5, 0.7)
    T.sfx(120, "wahwah")
    T.laugh(fr, 136, 160)
    T.laugh(hero, 144, 162, sound=False)
    T.jump_joy(fr, 150, sound="ding")
    return 168, 98


# --------------------------------------------------------------------------- 12. magic trick
def _poof(name, f, loc, size=0.22, parent=None):
    """A puff of magic smoke + sparkles."""
    root = T.empty(name, loc, parent)
    m = T.mat("#FFFFFF", 0.9)
    for i in range(7):
        a = i / 7 * math.tau
        b = T.sphere(f"{name}{i}", size * (0.7 + 0.1 * (i % 3)), (math.cos(a) * size * 0.8, -0.05, math.sin(a) * size * 0.6),
                     m, root, sub=1, seg=20)
        T.key(b, "scale", f, (0.05, 0.05, 0.05))
        T.key(b, "scale", f + 4, (1.2, 1.2, 1.2))
        T.key(b, "scale", f + 12, (0.05, 0.05, 0.05))
    T.show(root, 1, False)
    T.show(root, f, True)
    T.show(root, f + 13, False)
    T.sfx(f, "pop")
    T.sfx(f + 1, "twinkle")
    return root


def _wand(name, ch, side=1):
    w = T.empty(name, (side * 0.42, -0.25, 0.6), ch["root"])
    w.rotation_euler = (0.3, side * -0.5, 0)
    T.cyl(name + "_stick", 0.018, 0.34, (0, 0, 0.1), T.mat("#1E1A26", 0.3, coat=0.6), w)
    T.cyl(name + "_tip", 0.02, 0.07, (0, 0, 0.29), T.mat("#FFFFFF", 0.3), w)
    T.star(name + "_star", 0.06, (0, 0, 0.36), T.mat("#FFD23F", 0.3, emit=1.5), w)
    return w


def _tap(ch, f, side=1):
    _arm(ch, side, f, 0.9, fwd=-1.2, d=3)
    _arm(ch, side, f + 3, 0.5, fwd=-0.6, d=3)
    T.sfx(f + 2, "tick")


def magic_trick(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.72, 0.15)
    fr = T.make_character(spec["friend"], 0.85, 0.3)
    T.turn(hero, 1, 22, 1)
    T.turn(fr, 1, -18, 1)
    table = T.make_table((0.08, 0.25, 0), spec.get("table_color", "#B7A6FF"))
    hat = T.empty("tophat", (0, 0, 0.67), table)
    black, band = T.mat("#1E1A26", 0.35, coat=0.4), T.mat(T.PROP_COLOR or "#FF4D6D", 0.4)
    T.cyl("hat_brim", 0.25, 0.025, (0, 0, 0.012), black, hat, bevel=0.008)
    T.cyl("hat_crown", 0.16, 0.26, (0, 0, 0.15), black, hat, bevel=0.01)
    T.cyl("hat_band", 0.163, 0.05, (0, 0, 0.06), band, hat)
    w1 = _wand("wand", hero, 1)
    w2 = _wand("wand2", fr, -1)
    T.show(w2, 1, False)

    p, t = _two([-0.75, 0.9], 34, 0.95)
    T.shot(cam, tgt, 1, 56, p, t, 34, (p[0], p[1] + 0.25, p[2]), t)
    T.shot(cam, tgt, 57, 92, (0.25, -2.6, 0.95), (0.25, 0.25, 0.8), 40, (0.15, -2.4, 0.9), (0.15, 0.25, 0.8))
    T.shot(cam, tgt, 93, 122, (-0.65, -2.0, 0.55), (-0.72, 0.15, 0.4), 45, (-0.65, -1.85, 0.5), (-0.72, 0.15, 0.4))
    p, t = _two([-0.75, 0.9], 32, 0.9)
    T.shot(cam, tgt, 123, 168, p, t, 32, (p[0], p[1] + 0.3, p[2]), t)

    T.idle(fr, 1, 56)
    # tap, tap, tap... POOF! flowers
    T.sfx(4, "drumroll")
    T.eyes_happy(hero, 6)
    for f in (10, 18, 26):
        _tap(hero, f)
        T.wobble(hat, f + 2, f + 6, 6, 2, 1, sound=None)
    T.eyes_norm(hero, 30)
    _poof("poof1", 32, (0.08, 0.2, 1.05))
    bunch = T.empty("bunch", (0.08, 0.25, 0.9))
    cols = ["#FF6B8B", "#FFD23F", "#B57BFF", "#4DA6FF", "#FF8A3D"]
    for i in range(5):
        a = (i - 2) * 0.35
        T.cyl(f"bstem{i}", 0.01, 0.3, (math.sin(a) * 0.12, 0, 0.12), T.mat("#3FA64E", 0.6), bunch, rot=(0, a, 0))
        T.sphere(f"bflw{i}", 0.06, (math.sin(a) * 0.24, -0.02, 0.28 + math.cos(a) * 0.02), T.mat(cols[i], 0.5), bunch,
                 scale=(1, 0.6, 1), sub=1)
    T.key(bunch, "scale", 33, (0.05, 0.05, 0.05))
    T.key(bunch, "scale", 38, (1.15, 1.15, 1.15))
    T.key(bunch, "scale", 42, (1, 1, 1))
    T.show(bunch, 1, False)
    T.show(bunch, 33, True)
    T.sfx(36, "tada")
    T.jump_joy(hero, 40, h=0.25, n=10, times=1, sound=None)
    T.eyes_big(fr, 36, 1.3, 3, sound=None)
    T.mouth_set(fr, 36, 0.8)
    for k, f in enumerate(range(42, 56, 4)):  # friend claps
        T.arms(fr, f, 0.2 if k % 2 else 0.9, fwd=-1.3, d=2)
        T.sfx(f, "clap")
    T.mouth_set(fr, 56, 0.0)
    # the friend borrows the wand - POOF! the hero turns tiny
    T.show(bunch, 58, False)
    T.show(w1, 60, False)
    T.show(w2, 60, True)
    T.sfx(60, "zip")
    T.look(fr, 60, -0.05)
    T.eyes_happy(fr, 62)
    for f in (66, 74):
        _tap(fr, f, -1)
    T.eyes_norm(fr, 80)
    _poof("poof2", 84, (-0.72, 0.15, 0.55), 0.3)
    r, sz = hero["root"], hero["size"]
    T.key(r, "scale", 85, (sz, sz, sz))
    T.key(r, "scale", 89, (sz * 0.35, sz * 0.35, sz * 0.35))
    T.sfx(88, "slide_down")
    T.eyes_big(hero, 94, 1.45, 3, sound=None)
    T.mouth_set(hero, 94, 0.9, 0.8)
    for k, f in enumerate(range(96, 120, 4)):
        T.arms(hero, f, 2.4 if k % 2 else 1.2, d=2)
        T.sfx(f, "squeak")
    T.hop(hero, 104, -0.72, -0.72, 0.15, 8, sound=False)
    T.eyes_big(fr, 92, 1.35, 3, sound="doink")
    T.mouth_set(fr, 92, 0.9, 0.7)
    T.arms(fr, 96, 0.5, fwd=-1.9, d=4)  # oops - hands over mouth
    # one more tap - back to normal
    T.arms(fr, 118, 0.2, d=4)
    _tap(fr, 120, -1)
    _poof("poof3", 124, (-0.72, 0.15, 0.6), 0.32)
    T.key(r, "scale", 125, (sz * 0.35, sz * 0.35, sz * 0.35))
    T.key(r, "scale", 129, (sz * 1.12, sz * 1.12, sz * 1.12))
    T.key(r, "scale", 133, (sz, sz, sz))
    T.sfx(126, "slide_up")
    T.arms(hero, 126, 0.0, d=3)
    T.eyes_norm(hero, 128)
    T.mouth_set(hero, 130, 0.0)
    T.laugh(fr, 134, 158)
    T.laugh(hero, 136, 156, sound=False)
    T.jump_joy(hero, 154, sound="ding")
    return 168, 100


# --------------------------------------------------------------------------- 13. seesaw launch
def seesaw(spec, cam, tgt):
    col = T.PROP_COLOR or T.VAR.choice(["#FF4D6D", "#4DA6FF", "#FFD23F", "#5CCB6B", "#B57BFF"])
    base = T.empty("seesaw", (0.3, 0.3, 0))
    T.box("ss_block", (0.3, 0.42, 0.26), (0, 0, 0.13), T.mat("#8A5A3C", 0.6), base, bevel=0.05)
    T.cyl("ss_axle", 0.07, 0.5, (0, 0, 0.3), T.mat("#C9C9D1", 0.3, metal=0.6), base, rot=(math.pi / 2, 0, 0))
    plank = T.empty("ss_pivot", (0, 0, 0.32), base)
    T.box("ss_plank", (2.5, 0.34, 0.07), (0, 0, 0.05), T.mat(col, 0.4, coat=0.3), plank, bevel=0.03)
    for sx in (-1, 1):
        T.cyl(f"ss_handle{sx}", 0.025, 0.24, (sx * 0.95, 0, 0.18), T.mat("#FFFFFF", 0.4), plank)
    L = 1.05  # where each friend sits from the middle

    def end_z(a, side):  # height of a plank end for tilt a
        return 0.32 + 0.04 - side * L * math.sin(a)

    hero = T.make_character(spec["hero"], 0.3 - L, 0.3, end_z(-0.22, -1))
    fr = T.make_character(spec["friend"], 2.0, 0.3)
    T.turn(hero, 1, 25, 1)
    T.turn(fr, 1, -30, 1)
    T.key(plank, "rotation_euler", 1, (0, -0.22, 0))

    p, t = _two([-0.8, 2.0], 26, 0.8)
    T.shot(cam, tgt, 1, 62, p, t, 26, (p[0], p[1] + 0.3, p[2]), t)
    T.shot(cam, tgt, 63, 96, (-0.6, -3.6, 1.1), (-0.75, 0.3, 1.2), 30, (-0.6, -3.6, 1.4), (-0.75, 0.3, 1.7))
    p, t = _two([-0.8, 2.0], 26, 0.85)
    T.shot(cam, tgt, 97, 168, p, t, 26, (p[0] + 0.2, p[1] + 0.2, p[2]), t)

    T.idle(hero, 1, 40)
    T.look(hero, 6, 0.05)
    T.eyes_happy(hero, 8)
    T.mouth_set(hero, 8, 0.0)
    # friend hops onto the high end, then a BIG stomp jump
    xf = 0.3 + L
    T.hop(fr, 14, 2.0, xf, 0.85, 14, sound=True)
    r = fr["root"]
    T.key(r, "location", 28, (xf, 0.3, end_z(-0.22, 1)))
    T.look(fr, 32, -0.05)
    T.eyes_happy(fr, 34)
    T.sfx(34, "giggle")
    T.squash(fr, 42, 0.2, 3, 3)
    T.key(r, "location", 44, (xf, 0.3, end_z(-0.22, 1)))
    T.key(r, "location", 52, (xf, 0.3, 1.5))
    T.sfx(44, "boing")
    T.arms(fr, 46, 2.4, d=3)
    T.key(r, "location", 60, (xf, 0.3, end_z(0.22, 1)))
    T.key(plank, "rotation_euler", 59, (0, -0.22, 0))
    T.key(plank, "rotation_euler", 62, (0, 0.22, 0))
    T.sfx(60, "thud")
    T.squash(fr, 61, 0.3, 1, 6)
    # the hero is launched sky high with a flip
    h = hero["root"]
    T.key(h, "location", 60, (0.3 - L, 0.3, end_z(-0.22, -1)))
    T.key(h, "location", 78, (0.3 - L - 0.1, 0.3, 2.3))
    T.key(h, "location", 96, (0.3 - L, 0.3, end_z(0.22, -1)))
    T.sfx(61, "slide_up")
    T.sfx(62, "whoosh")
    T.eyes_big(hero, 63, 1.45, 2, sound=None)
    T.mouth_set(hero, 63, 1.1, 0.9)
    T.key(hero["piv"], "rotation_euler", 64, (0, 0, 0))
    T.key(hero["piv"], "rotation_euler", 90, (0, math.radians(-360), 0))
    T.key(hero["piv"], "rotation_euler", 91, (0, 0, 0), "CONSTANT")
    for k, f in enumerate(range(64, 92, 4)):
        T.arms(hero, f, 2.6 if k % 2 else 1.4, d=2)
    T.sfx(80, "xylo_down")
    T.eyes_happy(fr, 66)
    T.mouth_set(fr, 66, 0.8)
    # hero lands - and launches the friend!
    T.key(plank, "rotation_euler", 95, (0, 0.22, 0))
    T.key(plank, "rotation_euler", 98, (0, -0.22, 0))
    T.sfx(96, "thud")
    T.squash(hero, 97, 0.3, 1, 6)
    T.key(h, "location", 98, (0.3 - L, 0.3, end_z(-0.22, -1)))
    T.key(r, "location", 96, (xf, 0.3, end_z(0.22, 1)))
    T.key(r, "location", 112, (xf + 0.5, 0.3, 2.0))
    T.key(r, "location", 126, (xf + 0.9, 0.3, 0.0))
    T.sfx(97, "slide_up")
    T.eyes_big(fr, 98, 1.45, 2, sound=None)
    T.mouth_set(fr, 98, 1.1, 0.9)
    T.arms(fr, 100, 2.6, d=2)
    T.sfx(126, "land")
    T.squash(fr, 127, 0.32, 1, 8)
    T.arms(fr, 128, 0.3)
    T.dizzy_stars(fr, 128, 152)
    T.eyes_big(hero, 108, 1.3, 3, sound=None)
    T.mouth_set(hero, 110, 0.7)
    T.laugh(hero, 130, 160)
    T.laugh(fr, 146, 164, sound=False)
    T.eyes_norm(fr, 150)
    return 168, 80


# --------------------------------------------------------------------------- 14. paint splat
def _splats(ch, f, cols, name):
    """Paint dots on a face (placed around the eyes, so they fit every kind of character)."""
    spots = []
    ex = [e.location for e in ch["eyes"]]
    if not ex:
        return spots
    x0, y0, z0 = sum(v[0] for v in ex) / len(ex), sum(v[1] for v in ex) / len(ex), sum(v[2] for v in ex) / len(ex)
    dx = abs(ex[0][0] - x0) or 0.15
    for i, (ox, oz, rr) in enumerate(((-1.5, -0.95, 0.07), (1.6, -0.8, 0.06), (0.1, 1.15, 0.065), (0.0, -1.7, 0.05))):
        sp = T.sphere(f"{name}{i}", rr, (x0 + ox * dx, y0 - 0.03, z0 + oz * dx), T.mat(cols[i % len(cols)], 0.3, coat=0.6),
                      ch["piv"], scale=(1, 0.35, 0.9), sub=1, seg=20)
        T.show(sp, 1, False)
        T.show(sp, f + i, True)
        T.key(sp, "scale", f + i, (0.2, 0.1, 0.2))
        T.key(sp, "scale", f + i + 3, (1.15, 0.35, 1.0))
        spots.append(sp)
    return spots


def _brush(name, ch, color, side=1):
    b = T.empty(name, (side * 0.42, -0.25, 0.6), ch["root"])
    b.rotation_euler = (0.4, side * -0.6, 0)
    T.cyl(name + "_h", 0.018, 0.32, (0, 0, 0.1), T.mat("#C98A4A", 0.5), b)
    T.cone(name + "_tip", 0.035, 0.0, 0.1, (0, 0, 0.3), T.mat(color, 0.3, coat=0.6), b)
    return b


def paint_splat(spec, cam, tgt):
    hero = T.make_character(spec["hero"], -0.85, 0.1)
    fr = T.make_character(spec["friend"], 0.95, 0.3)
    T.turn(hero, 1, 30, 1)
    T.turn(fr, 1, -20, 1)
    cols = ["#FF4D6D", "#FFD23F", "#4DA6FF", "#5CCB6B", "#B57BFF", "#FF8A3D"]
    T.VAR.shuffle(cols)
    easel = T.empty("easel", (-0.1, 0.35, 0))
    wood = T.mat("#C98A4A", 0.6)
    for i, (lx, ly, rot) in enumerate(((-0.28, -0.05, (0.08, -0.18, 0)), (0.28, -0.05, (0.08, 0.18, 0)), (0, 0.3, (-0.35, 0, 0)))):
        T.cyl(f"easel_leg{i}", 0.025, 1.3, (lx, ly, 0.62), wood, easel, rot=rot)
    T.box("easel_shelf", (0.72, 0.1, 0.04), (0, -0.12, 0.58), wood, easel, bevel=0.01)
    T.box("canvas", (0.68, 0.04, 0.54), (0, -0.14, 0.88), T.mat("#FFFDF5", 0.8), easel, bevel=0.01)
    pal = T.empty("palette", (-0.55, 0.0, 0), hero["root"])
    T.sphere("pal_board", 0.16, (0, -0.3, 0.42), T.mat("#E2B27A", 0.6), pal, scale=(1.2, 0.3, 0.9), rot=(0.4, 0, 0))
    for i in range(5):
        a = i / 5 * math.pi + 0.3
        T.sphere(f"pal_dab{i}", 0.03, (math.cos(a) * 0.11, -0.34, 0.42 + math.sin(a) * 0.07), T.mat(cols[i], 0.3, coat=0.5),
                 pal, scale=(1, 0.5, 1), sub=0)
    b1 = _brush("brush", hero, cols[0], 1)
    b2 = _brush("brush2", fr, cols[2], -1)
    T.show(b2, 1, False)

    p, t = _two([-0.85, 0.95], 34, 0.9)
    T.shot(cam, tgt, 1, 52, p, t, 34, (p[0] + 0.1, p[1] + 0.25, p[2]), t)
    T.shot(cam, tgt, 53, 96, (0.7, -2.3, 0.8), (0.75, 0.3, 0.74), 46, (0.7, -2.1, 0.8), (0.75, 0.3, 0.74))
    p, t = _two([-0.85, 0.95], 32, 0.85)
    T.shot(cam, tgt, 97, 168, p, t, 32, (p[0], p[1] + 0.3, p[2]), t)

    # the hero paints a little picture, dab by dab
    T.idle(fr, 1, 40)
    T.look(hero, 4, 0.05, 0.03)
    T.mouth_set(hero, 4, 0.0)
    pic = [(-0.18, 0.12, 0.09, 0), (0.12, -0.05, 0.07, 1), (0.0, -0.12, 0.06, 3), (-0.15, -0.14, 0.05, 4),
           (0.2, 0.15, 0.05, 2)]
    for k, (px, pz, rr, ci) in enumerate(pic):
        f = 8 + k * 7
        _arm(hero, 1, f, 0.6, fwd=-1.5, d=3)
        _arm(hero, 1, f + 3, 0.3, fwd=-0.8, d=3)
        dab = T.sphere(f"dab{k}", rr, (px, -0.17, 0.88 + pz), T.mat(cols[ci], 0.35, coat=0.4), easel, scale=(1, 0.2, 1),
                       sub=1, seg=20)
        T.show(dab, 1, False)
        T.show(dab, f + 2, True)
        T.sfx(f + 2, "squeak" if k % 2 else "tick")
    T.eyes_happy(hero, 46)
    T.sfx(46, "sparkle")
    # the friend comes to look - very close...
    T.hop(fr, 40, 0.95, 0.45, 0.2, 10, sound=False)
    T.sfx(42, "tiptoe")
    T.look(fr, 52, -0.06, 0.02)
    T.lean(fr, 56, -14, 6)
    T.eyes_big(fr, 58, 1.2, 4, sound=None)
    T.mouth_set(fr, 58, 0.5, 0.6)
    # ...the hero swings for a big stroke - SPLAT!
    T.eyes_norm(hero, 60)
    _arm(hero, 1, 64, 2.4, fwd=0.6, d=4)
    T.lean(hero, 64, 10, 4)
    _arm(hero, 1, 70, 0.4, fwd=-1.6, d=3)
    T.lean(hero, 70, -8, 3)
    T.sfx(69, "whoosh")
    T.sfx(71, "splat")
    _splats(fr, 71, cols, "splat")
    T.eyes_happy(fr, 72, 1)
    T.squash(fr, 72, 0.15, 1, 5)
    T.sfx(78, "drumroll")
    T.blink(fr, 84)
    T.eyes_big(fr, 90, 1.3, 3, sound="doink")
    T.mouth_set(fr, 90, 0.0)
    T.lean(fr, 90, 0, 4)
    T.eyes_big(hero, 76, 1.35, 3, sound=None)
    T.mouth_set(hero, 76, 0.9, 0.7)
    T.arms(hero, 80, 0.5, fwd=-1.9, d=4)  # oops!
    # the friend grabs a brush and paints the hero back - then they laugh
    T.show(b2, 98, True)
    T.sfx(98, "zip")
    T.eyes_happy(fr, 100)
    T.sfx(100, "giggle")
    T.hop(fr, 102, 0.45, -0.25, 0.25, 10, sound=False)
    for f in (114, 120, 126):
        _arm(fr, -1, f, 0.8, fwd=-1.4, d=3)
        _arm(fr, -1, f + 3, 0.3, fwd=-0.6, d=3)
    T.sfx(116, "splat")
    _splats(hero, 116, cols[2:] + cols[:2], "splat2")
    T.arms(hero, 112, 0.0, d=4)
    T.eyes_happy(hero, 118, 1)
    T.laugh(hero, 132, 160)
    T.laugh(fr, 134, 160, sound=False)
    T.jump_joy(fr, 152, sound="ding")
    return 168, 74


GAGS = {"steal_treat": steal_treat, "ball_bonk": ball_bonk, "balloon_float": balloon_float,
        "gift_surprise": gift_surprise, "hide_seek": hide_seek, "slip_peel": slip_peel,
        "sneeze": sneeze, "dance_party": dance_party, "bubbles": bubbles, "wake_up": wake_up, "race": race,
        "magic_trick": magic_trick, "seesaw": seesaw, "paint_splat": paint_splat}
