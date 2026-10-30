"""Background life: the world keeps moving behind the characters (like a TV cartoon, never a frozen set).

street      toy cars, a bus and an ice-cream van drive by on a little road behind the fence
park        ducks paddle around the pond
outdoors    a small plane or helicopter flies over; trees sway in the wind
beach       sailboats glide along the sea
snow        snow keeps falling
underwater  fish swim past, bubbles rise
space       a rocket zooms across the sky
rooms       a wind-up toy car rolls along the back of the room

add(set_kind, sky, end, rnd) after the set and the story are built."""
import math
import random

import bpy

import toon as T

OUTDOOR_SKY = ("park", "street", "playground", "farm", "camping", "castle", "market", "jungle", "desert", "candy",
               "beach", "pirate")
ROOMS = ("kitchen", "bedroom", "livingroom")


def _lin(o, path, idx, frames_vals):
    for f, v in frames_vals:
        vec = list(getattr(o, path))
        vec[idx] = v
        setattr(o, path, vec)
        o.keyframe_insert(path, index=idx, frame=f)
    fc = o.animation_data.action.fcurves.find(path, index=idx)
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"
    return fc


def _cycle(o, path, idx):
    fc = o.animation_data.action.fcurves.find(path, index=idx)
    if fc and not fc.modifiers:
        fc.modifiers.new("CYCLES")
        fc.extrapolation = "LINEAR"


# ------------------------------------------------------------------ vehicles
def _car(name, color, kind="car"):
    root = T.empty(name, (0, 0, 0))
    paint, glass, black = T.mat(color, 0.35, coat=0.6), T.mat("#2F4A7A", 0.1, coat=1.0), T.mat("#1E1E26", 0.6)
    hub = T.mat("#FFFFFF", 0.3)
    wheels = []
    if kind == "bus":
        T.box(name + "_b", (1.9, 0.52, 0.5), (0, 0, 0.36), paint, root, bevel=0.1)
        T.box(name + "_win", (1.6, 0.54, 0.16), (-0.05, 0, 0.47), glass, root, bevel=0.04)
        T.box(name + "_wsh", (0.06, 0.44, 0.2), (0.93, 0, 0.47), glass, root, bevel=0.02)
        xs = (-0.6, 0.6)
    elif kind == "van":
        T.box(name + "_b", (1.15, 0.48, 0.3), (0, 0, 0.24), paint, root, bevel=0.08)
        T.box(name + "_box", (0.7, 0.5, 0.42), (-0.2, 0, 0.55), T.mat("#FFFFFF", 0.4), root, bevel=0.06)
        T.box(name + "_wsh", (0.3, 0.44, 0.2), (0.33, 0, 0.47), glass, root, bevel=0.05)
        T.sphere(name + "_cone", 0.1, (-0.2, 0, 0.86), T.mat("#FF9EC4", 0.4), root, sub=1)
        T.cone(name + "_wafer", 0.08, 0.0, 0.18, (-0.2, 0, 0.72), T.mat("#E8B36A", 0.6), root, rot=(math.pi, 0, 0))
        xs = (-0.38, 0.38)
    else:
        T.box(name + "_b", (0.95, 0.46, 0.24), (0, 0, 0.21), paint, root, bevel=0.1)
        T.box(name + "_cab", (0.52, 0.42, 0.2), (-0.06, 0, 0.4), glass, root, bevel=0.08)
        T.box(name + "_roof", (0.46, 0.43, 0.05), (-0.06, 0, 0.5), paint, root, bevel=0.025)
        xs = (-0.3, 0.3)
    T.sphere(name + "_hl", 0.045, (xs[1] + (0.6 if kind == "bus" else 0.2), 0.14, 0.24), T.mat("#FFF3B0", 0.2, emit=2.0), root, sub=0)
    for x in xs:
        for y in (-0.22, 0.22):
            w = T.cyl(f"{name}_w{x}{y}", 0.11, 0.08, (x, y, 0.11), black, root, rot=(math.pi / 2, 0, 0))
            T.cyl(f"{name}_hub{x}{y}", 0.05, 0.085, (0, 0, 0), hub, w)
            T.box(f"{name}_sp{x}{y}", (0.02, 0.15, 0.09), (0, 0, 0), T.mat("#C9C9D6", 0.4), w, bevel=0)  # spoke shows the spin
            wheels.append(w)
    return root, wheels


def _drive(root, wheels, f0, f1, x0, x1, y, bump=0.012):
    """Drive along x from x0 (frame f0) to x1 (frame f1); wheels roll, the body bounces a touch."""
    root.location = (x0, y, 0)
    root.rotation_euler = (0, 0, 0 if x1 > x0 else math.pi)
    _lin(root, "location", 0, ((f0, x0), (f1, x1)))
    turns = abs(x1 - x0) / (2 * math.pi * 0.11)
    for w in wheels:
        w.rotation_euler = (math.pi / 2, 0, 0)
        _lin(w, "rotation_euler", 1, ((f0, 0.0), (f1, turns * math.tau)))
    for f in range(int(f0), int(f1), 6):
        root.location.z = bump if (f // 6) % 2 else 0.0
        root.keyframe_insert("location", index=2, frame=f)


def _street(end, rnd):
    road = T.mat("#5D6270", 0.8)
    T.box("road", (40, 0.95, 0.02), (0, 3.05, 0.008), road, bevel=0)
    for i in range(-20, 21):
        T.box(f"roadline{i}", (0.45, 0.04, 0.005), (i * 1.0, 3.05, 0.02), T.mat("#FFFFFF", 0.5), bevel=0)
    cols = ["#FF4D5E", "#4DA6FF", "#FFD23F", "#5CCB6B", "#B57BFF", "#FF8A3D"]
    kinds = ["car", "car", "bus", "car", "van", "car"]
    rnd.shuffle(kinds)
    f, i = rnd.randint(-60, 10), 0
    while f < end - 20 and i < 6:
        k = kinds[i % len(kinds)]
        root, wheels = _car(f"car{i}", rnd.choice(cols) if k != "bus" else "#FFC23D", k)
        right = i % 2 == 0
        speed = rnd.uniform(0.07, 0.1) if k == "bus" else rnd.uniform(0.09, 0.13)
        x0, x1 = (-8.5, 8.5) if right else (8.5, -8.5)
        _drive(root, wheels, f, f + 17 / speed, x0, x1, 2.85 if right else 3.25)
        f += rnd.randint(55, 110)
        i += 1


def _plane(end, rnd):
    kind = rnd.choice(["plane", "plane", "heli"])
    root = T.empty("flyer_v", (0, 0, 0))
    c = T.mat(rnd.choice(["#FF4D5E", "#FFD23F", "#4DA6FF", "#FFFFFF"]), 0.3, coat=0.5)
    blades = T.empty("flyer_prop", (0.55, 0, 0) if kind == "plane" else (0, 0, 0.32), root)
    if kind == "plane":
        T.cyl("pl_body", 0.13, 1.1, (0, 0, 0), c, root, rot=(0, math.pi / 2, 0))
        T.sphere("pl_nose", 0.13, (0.55, 0, 0), c, root, sub=1)
        T.box("pl_wing", (0.32, 1.5, 0.04), (0.05, 0, 0.02), T.mat("#FFFFFF", 0.3), root, bevel=0.02)
        T.box("pl_tail", (0.2, 0.5, 0.03), (-0.5, 0, 0.05), T.mat("#FFFFFF", 0.3), root, bevel=0.01)
        T.box("pl_fin", (0.2, 0.03, 0.22), (-0.5, 0, 0.15), c, root, bevel=0.01)
        T.box("pl_blade", (0.02, 0.5, 0.05), (0.05, 0, 0), T.mat("#2E3A59", 0.4), blades, bevel=0)
        axis = 0
    else:
        T.sphere("he_body", 0.28, (0, 0, 0), c, root, scale=(1.2, 0.9, 0.9), sub=1)
        T.box("he_win", (0.2, 0.42, 0.2), (0.22, 0, 0.05), T.mat("#2F4A7A", 0.1, coat=1.0), root, bevel=0.06)
        T.cyl("he_tail", 0.05, 0.6, (-0.5, 0, 0.05), c, root, rot=(0, math.pi / 2, 0))
        T.box("he_blade", (1.6, 0.06, 0.02), (0, 0, 0), T.mat("#2E3A59", 0.4), blades, bevel=0)
        T.box("he_blade2", (0.06, 1.6, 0.02), (0, 0, 0), T.mat("#2E3A59", 0.4), blades, bevel=0)
        axis = 2
    _lin(blades, "rotation_euler", axis, ((1, 0.0), (5, math.tau)))
    _cycle(blades, "rotation_euler", axis)
    y, z = rnd.uniform(16, 24), rnd.uniform(5.0, 7.0)
    f0 = rnd.randint(-40, max(-39, end // 3))
    right = rnd.random() < 0.5
    x0, x1 = (-16, 16) if right else (16, -16)
    root.location = (x0, y, z)
    root.rotation_euler = (0, 0, 0 if right else math.pi)
    root.scale = (1.4, 1.4, 1.4)
    _lin(root, "location", 0, ((f0, x0), (f0 + 260, x1)))
    for k in range(0, 260, 40):  # gentle up/down drift
        root.location.z = z + (0.25 if (k // 40) % 2 else 0)
        root.keyframe_insert("location", index=2, frame=f0 + k)


def _ducks(end, rnd):
    pond = bpy.data.objects.get("pond")
    if pond is None:
        return
    cx, cy = pond.location.x, pond.location.y
    for i in range(2):
        d = T.empty(f"duck{i}", (0, 0, 0))
        yel = T.mat("#FFD53D" if i == 0 else "#FFFFFF", 0.5)
        T.sphere(f"duck{i}_b", 0.12, (0, 0, 0.07), yel, d, scale=(1.35, 0.95, 0.75), sub=1)
        T.sphere(f"duck{i}_h", 0.07, (0.11, 0, 0.17), yel, d, sub=1)
        T.cone(f"duck{i}_bk", 0.035, 0.0, 0.07, (0.19, 0, 0.16), T.mat("#FF8A1F", 0.4), d, rot=(0, math.pi / 2, 0))
        for s in (-1, 1):
            T.sphere(f"duck{i}_e{s}", 0.012, (0.15, s * 0.04, 0.19), T.mat("#141018", 0.2), d, sub=0)
        ph, sp = rnd.uniform(0, math.tau), rnd.uniform(0.012, 0.018) * (1 if i == 0 else -1)
        for f in range(-6, end + 8, 6):
            a = ph + f * sp
            d.location = (cx + math.cos(a) * 1.25, cy + math.sin(a) * 0.45, 0.01 + 0.012 * math.sin(f * 0.3 + i))
            d.rotation_euler = (0, 0, a + (math.pi / 2 if sp > 0 else -math.pi / 2))
            d.keyframe_insert("location", frame=f)
            d.keyframe_insert("rotation_euler", frame=f)


def _boats(end, rnd):
    for i in range(2):
        b = T.empty(f"boat{i}", (0, 0, 0))
        T.box(f"boat{i}_hull", (0.9, 0.3, 0.18), (0, 0, 0.05), T.mat(rnd.choice(["#FF4D5E", "#4DA6FF", "#FFFFFF"]), 0.4), b,
              bevel=0.08)
        T.cyl(f"boat{i}_mast", 0.02, 1.0, (0, 0, 0.6), T.mat("#8A5A3C", 0.6), b)
        me = bpy.data.meshes.new(f"boat{i}_sail")
        me.from_pydata([(0.02, 0, 0.2), (0.02, 0, 1.05), (0.42, 0, 0.22)], [], [(0, 1, 2)])
        s = bpy.data.objects.new(f"boat{i}_sail", me)
        T.sc.collection.objects.link(s)
        s.parent = b
        s.data.materials.append(T.mat(rnd.choice(["#FFFFFF", "#FFD23F", "#FF9EC4"]), 0.5))
        y = rnd.uniform(11, 17) + i * 3
        right = i % 2 == 0
        x0, x1 = (-12, 12) if right else (12, -12)
        b.location = (x0, y, 0)
        b.rotation_euler = (0, 0, 0 if right else math.pi)
        b.scale = (1.6, 1.6, 1.6)
        f0 = rnd.randint(-200, 0)
        _lin(b, "location", 0, ((f0, x0), (f0 + 520, x1)))
        for f in range(-10, end + 10, 10):  # rocking on the waves
            b.rotation_euler[0] = 0.06 * math.sin(f * 0.15 + i)
            b.keyframe_insert("rotation_euler", index=0, frame=f)


def _falling(name, n, size, col, emit, area, height, period, up=False, rnd=None):
    """A sheet of little flakes/bubbles that falls (or rises) forever: two stacked copies, looped."""
    import numpy as np
    rnd = rnd or random.Random(3)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1)
    ico = bpy.context.active_object
    base = np.array([v.co[:] for v in ico.data.vertices])
    faces = [tuple(p.vertices) for p in ico.data.polygons]
    bpy.data.objects.remove(ico)
    V, F = [], []
    for copy in (0, 1):
        for _ in range(n):
            c = np.array((rnd.uniform(*area[0]), rnd.uniform(*area[1]), rnd.uniform(0, height) + copy * height))
            r = size * rnd.uniform(0.6, 1.3)
            off = len(V)
            V += (base * r + c).tolist()
            F += [tuple(off + i for i in f) for f in faces]
    me = bpy.data.meshes.new(name)
    me.from_pydata(V, [], F)
    o = bpy.data.objects.new(name, me)
    T.sc.collection.objects.link(o)
    o.data.materials.append(T.mat(col, 0.4, emit=emit))
    z0, z1 = (-height, 0.0) if up else (0.0, -height)
    _lin(o, "location", 2, ((1, z0), (1 + period, z1)))
    _cycle(o, "location", 2)
    return o


def _fish(end, rnd):
    cols = ["#FF8A3D", "#FFD23F", "#FF6FA8", "#4DE0C8", "#B57BFF"]
    for i in range(5):
        f_ = T.empty(f"fish{i}", (0, 0, 0))
        c = T.mat(rnd.choice(cols), 0.35, coat=0.5)
        T.sphere(f"fish{i}_b", 0.12, (0, 0, 0), c, f_, scale=(1.5, 0.6, 1.0), sub=1)
        tail = T.empty(f"fish{i}_tp", (-0.17, 0, 0), f_)
        T.cone(f"fish{i}_t", 0.09, 0.0, 0.14, (-0.07, 0, 0), c, tail, rot=(0, -math.pi / 2, 0), scale=(1, 0.3, 1))
        for s in (-1, 1):
            T.sphere(f"fish{i}_e{s}", 0.02, (0.11, s * 0.05, 0.03), T.mat("#141018", 0.2), f_, sub=0)
        _lin(tail, "rotation_euler", 2, ((1, -0.4), (6, 0.4), (11, -0.4)))
        _cycle(tail, "rotation_euler", 2)
        y, z = rnd.uniform(2.5, 8), rnd.uniform(0.8, 3.2)
        right = rnd.random() < 0.5
        x0, x1 = (-7, 7) if right else (7, -7)
        f_.location = (x0, y, z)
        f_.rotation_euler = (0, 0, 0 if right else math.pi)
        f0 = rnd.randint(-120, end - 40)
        _lin(f_, "location", 0, ((f0, x0), (f0 + rnd.randint(180, 260), x1)))


def _rocket(end, rnd):
    r = T.empty("rocket", (0, 0, 0))
    T.cyl("rk_body", 0.14, 0.6, (0, 0, 0), T.mat("#FFFFFF", 0.3, coat=0.5), r, rot=(0, math.pi / 2, 0))
    T.cone("rk_nose", 0.14, 0.0, 0.25, (0.42, 0, 0), T.mat("#FF4D5E", 0.3), r, rot=(0, math.pi / 2, 0))
    T.sphere("rk_win", 0.06, (0.12, -0.12, 0.03), T.mat("#4DA6FF", 0.1, coat=1.0), r, sub=0)
    fl = T.cone("rk_flame", 0.1, 0.0, 0.35, (-0.45, 0, 0), T.mat("#FFB347", 0.3, emit=6.0), r, rot=(0, -math.pi / 2, 0))
    _lin(fl, "scale", 2, ((1, 0.8), (3, 1.3), (5, 0.8)))
    _cycle(fl, "scale", 2)
    f0 = rnd.randint(0, max(1, end // 2))
    r.location = (-12, 14, 3)
    r.rotation_euler = (0, -0.25, 0)
    r.scale = (1.5, 1.5, 1.5)
    _lin(r, "location", 0, ((f0, -12), (f0 + 120, 12)))
    _lin(r, "location", 2, ((f0, 3), (f0 + 120, 8)))


def _toy_car(end, rnd):
    root, wheels = _car("toycar", rnd.choice(["#FF4D5E", "#4DA6FF", "#5CCB6B"]))
    root.scale = (0.45, 0.45, 0.45)
    f0 = rnd.randint(10, max(11, end - 120))
    _drive(root, wheels, f0, f0 + 150, -5.5, 5.5, 2.75, bump=0.004)


def _sway_trees(end):
    """Leafy crowns and palm leaves sway a little in the wind."""
    for o in bpy.data.objects:
        n = o.name
        if not (n.startswith("crown") or (n.startswith("palm") and "_l" in n)):
            continue
        ph = o.matrix_world.translation.x * 0.7
        for idx, amp in ((0, 0.035), (1, 0.015)):
            T._wave(o, "location", idx, amp, 110 + (hash(n) % 30), ph + idx)


def add(set_kind, sky, end, rnd=None):
    rnd = rnd or random.Random(5)
    jobs = []
    if set_kind == "street":
        jobs.append(_street)
    if set_kind in ("park",):
        jobs.append(_ducks)
    if set_kind in OUTDOOR_SKY and rnd.random() < 0.8:
        jobs.append(_plane)
    if set_kind in ("beach", "pirate"):
        jobs.append(_boats)
    if set_kind in ("snow", "christmas"):
        jobs.append(lambda e, r: _falling("snowfall", 260, 0.025, "#FFFFFF", 0.4, ((-6, 6), (-1.5, 9)), 5.0, 140, rnd=r))
    if set_kind == "underwater":
        jobs.append(_fish)
        jobs.append(lambda e, r: _falling("bubbles", 70, 0.03, "#E8FBFF", 0.6, ((-5, 5), (0.5, 7)), 4.0, 110, up=True, rnd=r))
    if set_kind == "space":
        jobs.append(_rocket)
    if set_kind in ROOMS:
        jobs.append(_toy_car)
    for job in jobs:
        try:
            job(end, rnd)
        except Exception as e:  # noqa: BLE001 - the short works without it
            print("background life skipped:", getattr(job, "__name__", "job"), e)
    try:
        _sway_trees(end)
    except Exception as e:  # noqa: BLE001
        print("tree sway skipped:", e)
