# Prototype: a real 3D cartoon shot built + animated in code, rendered with Cycles.
# Run: blender -b --python blender/proto.py -- <outdir> [stills|part:K/N]   (env RES=percent, SAMPLES=n)
import bpy, glob, json, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "out")
MODE = argv[1] if len(argv) > 1 else "both"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
FPS = 24
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, 144


def lin(hexs):
    h = hexs.lstrip("#")
    return tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4))


MATS = {}
EVENTS = []  # (frame, sound kind) -> blender/audio.py


def sfx(f, kind):
    EVENTS.append([int(f), kind])


def mat(hexs, rough=0.45, coat=0.0, sss=0.0, emit=0.0):
    key = (hexs, rough, coat, sss, emit)
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(hexs)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(hexs), 1)
    b.inputs["Roughness"].default_value = rough
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.05
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Scale"].default_value = 0.04
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(hexs), 1)
        b.inputs["Emission Strength"].default_value = emit
    MATS[key] = m
    return m


def link(o, parent=None):
    if parent is not None:
        o.parent = parent
    return o


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    sc.collection.objects.link(o)
    link(o, parent)
    o.location = loc
    return o


def finish(o, name, m, parent, loc, scale, rot, subsurf=1):
    o.name = name
    link(o, parent)
    o.location = loc
    o.scale = scale
    o.rotation_euler = rot
    if m:
        o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    if subsurf:
        s = o.modifiers.new("s", "SUBSURF")
        s.levels, s.render_levels = 1, subsurf
    return o


def sphere(name, r, loc, m=None, parent=None, scale=(1, 1, 1), rot=(0, 0, 0), sub=1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=r)
    return finish(bpy.context.active_object, name, m, parent, loc, scale, rot, sub)


def cyl(name, r, depth, loc, m=None, parent=None, scale=(1, 1, 1), rot=(0, 0, 0), bevel=0.0, verts=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth)
    o = bpy.context.active_object
    if bevel:
        bv = o.modifiers.new("b", "BEVEL")
        bv.width, bv.segments = bevel, 4
        bpy.ops.object.modifier_apply(modifier="b")
    o = finish(o, name, m, parent, loc, scale, rot, 0)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    return o


def box(name, size, loc, m=None, parent=None, rot=(0, 0, 0), bevel=0.08):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new("b", "BEVEL")
        bv.width, bv.segments = bevel, 5
        bpy.ops.object.modifier_apply(modifier="b")
    o = finish(o, name, m, parent, loc, (1, 1, 1), rot, 0)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    return o


def cone(name, r1, r2, depth, loc, m=None, parent=None, rot=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=r1, radius2=r2, depth=depth)
    o = finish(bpy.context.active_object, name, m, parent, loc, scale, rot, 0)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    return o


def key(o, path, f, val, interp=None):
    setattr(o, path, val)
    o.keyframe_insert(data_path=path, frame=f)
    if interp and o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    if int(kp.co[0]) == f:
                        kp.interpolation = interp


# ---------------------------------------------------------------- characters
WHITE = mat("#FFFFFF", 0.25, coat=0.6)
BLACK = mat("#141018", 0.2, coat=1.0)
SHINE = mat("#FFFFFF", 0.2, emit=4.0)


def eyes(parent, y, z, dx, r, iris="#3B8BEB", brow_m=None):
    """Two big glossy Pixar-style eyes (white, coloured iris, pupil, two highlights) + optional brows.
    Returns (eye pivots, pupil pivots, brows)."""
    piv, pup, brows = [], [], []
    for side in (-1, 1):
        e = empty(f"{parent.name}_eye{side}", (side * dx, y, z), parent)
        sphere(e.name + "_w", r, (0, 0, 0), WHITE, e, scale=(1, 0.6, 1.2), sub=2)
        p = empty(e.name + "_p", (0, -r * 0.5, r * 0.04), e)
        sphere(e.name + "_iris", r * 0.6, (0, 0, 0), mat(iris, 0.15, coat=1.0), p, scale=(1, 0.32, 1.12), sub=2)
        sphere(e.name + "_pupil", r * 0.36, (0, -r * 0.08, 0), BLACK, p, scale=(1, 0.3, 1.12), sub=2)
        sphere(e.name + "_hl", r * 0.17, (r * 0.2 * -side, -r * 0.2, r * 0.26), SHINE, p, sub=0)
        sphere(e.name + "_hl2", r * 0.08, (r * 0.2 * side, -r * 0.2, -r * 0.22), SHINE, p, sub=0)
        piv.append(e)
        pup.append(p)
        if brow_m:
            b = empty(f"{parent.name}_brow{side}", (side * dx, y - 0.02, z + r * 1.45), parent)
            sphere(b.name + "_m", r * 0.55, (0, 0, 0), brow_m, b, scale=(1, 0.35, 0.28), rot=(0, side * 0.18, 0))
            brows.append(b)
    return piv, pup, brows


def make_blob(name, color, x=0.0, y=0.0):
    """Round fluffy pet creature (original design): ears, big eyes, oval mouth, little arms + feet."""
    root = empty(name, (x, y, 0))
    body_m = mat(color, 0.55)
    piv = empty(name + "_piv", (0, 0, 0), root)  # squash/stretch from the floor
    sphere(name + "_body", 0.5, (0, 0, 0.55), body_m, piv, scale=(1.0, 0.92, 1.05), sub=2)
    for side in (-1, 1):
        sphere(f"{name}_ear{side}", 0.15, (side * 0.3, 0.02, 1.0), body_m, piv, scale=(0.8, 0.6, 1.2),
               rot=(0, side * 0.5, 0))
        sphere(f"{name}_cheek{side}", 0.08, (side * 0.3, -0.4, 0.5), mat("#FF8FB1", 0.6), piv,
               scale=(1, 0.4, 0.7))
    sphere(name + "_belly", 0.3, (0, -0.33, 0.38), mat("#FFC2B8", 0.6), piv, scale=(1.0, 0.45, 0.85), sub=2)
    sphere(name + "_tuft", 0.09, (0.04, 0.0, 1.08), body_m, piv, scale=(0.7, 0.7, 1.5), rot=(0, 0.35, 0))
    sphere(name + "_tuft2", 0.07, (-0.06, 0.02, 1.06), body_m, piv, scale=(0.7, 0.7, 1.3), rot=(0, -0.4, 0))
    ev, pp, br = eyes(piv, -0.405, 0.74, 0.175, 0.165, "#3B8BEB", mat("#7A1E2A", 0.5))
    mouth = sphere(name + "_mouth", 0.1, (0, -0.465, 0.47), mat("#5A1020", 0.4), piv, scale=(1.2, 0.35, 0.4))
    sphere(name + "_tongue", 0.06, (0, -0.02, -0.04), mat("#FF5A7A", 0.5), mouth, scale=(1, 0.8, 0.5))
    arms = []
    for side in (-1, 1):
        sh = empty(f"{name}_sh{side}", (side * 0.45, -0.05, 0.55), piv)
        sphere(f"{name}_arm{side}", 0.08, (side * 0.06, 0, -0.14), body_m, sh, scale=(0.9, 0.9, 2.0))
        arms.append(sh)
    feet = []
    for side in (-1, 1):
        f = sphere(f"{name}_foot{side}", 0.14, (side * 0.2, -0.08, 0.06), mat("#FFD27A", 0.5), root,
                   scale=(1.0, 1.35, 0.55))
        feet.append(f)
    return dict(root=root, piv=piv, eyes=ev, pupils=pp, brows=br, mouth=mouth, arms=arms, feet=feet)


def make_chick(name, x=0.0, y=0.0):
    root = empty(name, (x, y, 0))
    yel = mat("#FFD53D", 0.5)
    piv = empty(name + "_piv", (0, 0, 0), root)
    sphere(name + "_body", 0.34, (0, 0, 0.38), yel, piv, scale=(1, 0.95, 1.08), sub=2)
    sphere(name + "_tuft", 0.07, (0, 0, 0.76), yel, piv, scale=(0.6, 0.6, 1.6), rot=(0.3, 0, 0))
    ev, pp, br = eyes(piv, -0.285, 0.5, 0.12, 0.11, "#6B3E1F")
    cone(name + "_beak", 0.07, 0.0, 0.14, (0, -0.33, 0.37), mat("#FF8A1F", 0.4), piv, rot=(math.radians(90), 0, 0))
    arms = []
    for side in (-1, 1):
        sh = empty(f"{name}_wing{side}", (side * 0.32, 0, 0.4), piv)
        sphere(f"{name}_w{side}", 0.1, (side * 0.04, 0, -0.06), yel, sh, scale=(0.5, 0.9, 1.4), rot=(0, side * 0.3, 0))
        arms.append(sh)
    feet = [sphere(f"{name}_foot{s}", 0.07, (s * 0.12, -0.06, 0.03), mat("#FF8A1F", 0.4), root, scale=(1, 1.6, 0.5))
            for s in (-1, 1)]
    return dict(root=root, piv=piv, eyes=ev, pupils=pp, brows=br, arms=arms, feet=feet)


# ---------------------------------------------------------------- set
def make_set():
    grass = mat("#6CCB5F", 0.8)
    box("ground", (40, 40, 0.2), (0, 6, -0.1), grass, bevel=0)
    box("path", (40, 2.4, 0.02), (0, 0.4, 0.005), mat("#F2D7A6", 0.85), bevel=0)
    houses = [("#FF9EC4", -3.2), ("#8FD3FF", -0.6), ("#FFE27A", 2.2), ("#B7A6FF", 4.8), ("#9EF0C0", -5.8)]
    for i, (c, hx) in enumerate(houses):
        h = 2.2 + (i % 2) * 0.6
        box(f"house{i}", (2.2, 1.8, h), (hx, 5.0, h / 2), mat(c, 0.6), bevel=0.12)
        cone(f"roof{i}", 1.65, 0.0, 1.2, (hx, 5.0, h + 0.55), mat("#E8574F" if i % 2 else "#4F7BE8", 0.5),
             rot=(0, 0, math.radians(45)), scale=(1, 0.85, 1))
        for wx in (-0.5, 0.5):
            box(f"wf{i}{wx}", (0.62, 0.08, 0.67), (hx + wx, 4.1, h * 0.62), WHITE, bevel=0.04)
            box(f"win{i}{wx}", (0.5, 0.1, 0.55), (hx + wx, 4.07, h * 0.62), mat("#2F4A7A", 0.1, coat=1), bevel=0.05)
            box(f"fb{i}{wx}", (0.6, 0.18, 0.12), (hx + wx, 4.0, h * 0.62 - 0.38), mat("#B5683C", 0.6), bevel=0.03)
            for j in range(4):
                sphere(f"fl{i}{wx}{j}", 0.06, (hx + wx - 0.21 + j * 0.14, 3.98, h * 0.62 - 0.28),
                       mat(("#FF5D8F", "#FFFFFF", "#FFD23F", "#FF8A3D")[(i + j) % 4], 0.5), sub=0)
        box(f"door{i}", (0.55, 0.1, 0.9), (hx, 4.08, 0.45), mat("#8A5A3C", 0.5), bevel=0.08)
        sphere(f"knob{i}", 0.035, (hx + 0.17, 4.02, 0.45), mat("#FFD23F", 0.2, coat=1), sub=0)
        for bx in (-0.85, 0.85):
            for j, (ox, oz, rr) in enumerate(((0, 0.2, 0.28), (0.22, 0.15, 0.22), (-0.2, 0.14, 0.2))):
                sphere(f"bush{i}{bx}{j}", rr, (hx + bx + ox, 3.85, oz), mat("#45B85A", 0.75), sub=1)
    fence = mat("#FFFFFF", 0.5)
    for i in range(-14, 15):
        box(f"picket{i}", (0.09, 0.05, 0.55), (i * 0.4, 2.55, 0.27), fence, bevel=0.025)
    box("rail", (12, 0.04, 0.07), (0, 2.58, 0.35), fence, bevel=0.015)
    cloud = mat("#FFFFFF", 0.9)
    for i, (cx, cz) in enumerate(((-3.5, 5.5), (1.5, 6.4), (5.5, 5.2))):
        for j, (ox, oz, rr) in enumerate(((0, 0, 0.7), (0.7, -0.15, 0.5), (-0.7, -0.15, 0.5), (0.3, 0.35, 0.5))):
            sphere(f"cloud{i}{j}", rr, (cx + ox, 14, cz + oz), cloud, scale=(1.2, 0.6, 1), sub=1)
    cyl("lamp", 0.05, 2.2, (-1.6, 1.9, 1.1), mat("#2E3A59", 0.4))
    sphere("lampbulb", 0.16, (-1.6, 1.9, 2.25), mat("#FFF2B3", 0.3, emit=1.5), sub=1)
    for i, tx in enumerate((-4.5, -1.9, 1.0, 3.6, 6.2)):
        cyl(f"trunk{i}", 0.09, 0.9, (tx, 3.2, 0.45), mat("#9A6A43", 0.7))
        sphere(f"crown{i}", 0.55, (tx, 3.2, 1.25), mat("#3FB64E", 0.7), sub=1)
    for i, (fx, fc) in enumerate(((-2.4, "#FF6B8B"), (-1.7, "#FFFFFF"), (2.6, "#FFD53D"), (3.1, "#FF6B8B"))):
        sphere(f"flower{i}", 0.07, (fx, 1.9, 0.12), mat(fc, 0.5), sub=0)
    # table + cake
    table = empty("table", (0.55, 0.2, 0))
    cyl("leg", 0.06, 0.62, (0, 0, 0.31), mat("#FFFFFF", 0.4), table)
    cyl("top", 0.42, 0.06, (0, 0, 0.64), mat("#FF7AA8", 0.35, coat=0.3), table, bevel=0.02)
    cake = empty("cake", (0, 0, 0.67), table)
    cyl("plate", 0.24, 0.02, (0, 0, 0.01), WHITE, cake, bevel=0.008)
    cyl("cake1", 0.19, 0.16, (0, 0, 0.1), mat("#FFB3CF", 0.5), cake, bevel=0.03)
    cyl("icing", 0.2, 0.05, (0, 0, 0.19), mat("#FFFFFF", 0.3, coat=0.5), cake, bevel=0.025)
    for i in range(10):
        a = i / 10 * math.tau
        sphere(f"drip{i}", 0.03, (math.cos(a) * 0.195, math.sin(a) * 0.195, 0.155), mat("#FFFFFF", 0.3, coat=0.5),
               cake, scale=(1, 1, 1.6), sub=0)
    sphere("cherry", 0.045, (0, 0, 0.255), mat("#E0102F", 0.2, coat=1), cake, sub=1)
    return cake


# ---------------------------------------------------------------- world, light, camera
def make_world():
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexGradient")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapn = nt.nodes.new("ShaderNodeMapping")
    mapn.inputs["Rotation"].default_value = (0, math.radians(90), 0)
    nt.links.new(coord.outputs["Generated"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], sky.inputs["Vector"])
    nt.links.new(sky.outputs["Fac"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = (*lin("#D8F1FF"), 1)
    ramp.color_ramp.elements[1].color = (*lin("#5EB8FF"), 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0

    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy, sun_d.angle, sun_d.color = 3.6, math.radians(4), (1, 0.93, 0.82)
    sun = bpy.data.objects.new("sun", sun_d)
    sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
    fill_d = bpy.data.lights.new("fill", "AREA")
    fill_d.energy, fill_d.size, fill_d.color = 300, 6, (0.9, 0.95, 1)
    fill = bpy.data.objects.new("fill", fill_d)
    sc.collection.objects.link(fill)
    fill.location = (-2, -5, 3)
    fill.rotation_euler = (math.radians(60), 0, math.radians(-25))
    rim_d = bpy.data.lights.new("rim", "AREA")
    rim_d.energy, rim_d.size, rim_d.color = 500, 2.5, (0.85, 0.92, 1)
    rim = bpy.data.objects.new("rim", rim_d)
    sc.collection.objects.link(rim)
    rim.location = (2.5, 3.0, 2.6)
    tr = rim.constraints.new("TRACK_TO")
    tr.target, tr.track_axis, tr.up_axis = empty("rim_t", (0, 0.2, 0.6)), "TRACK_NEGATIVE_Z", "UP_Y"

    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 50
    cam_d.dof.use_dof = True
    cam_d.dof.aperture_fstop = 2.8
    cam = bpy.data.objects.new("cam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = empty("cam_target", (0, 0.2, 0.6))
    c = cam.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    cam_d.dof.focus_object = tgt
    return cam, tgt


# ---------------------------------------------------------------- animation helpers
def blink(ch, f):
    for e in ch["eyes"]:
        for ff, z in ((f - 1, 1.0), (f + 1, 0.08), (f + 3, 1.0)):
            key(e, "scale", ff, (1, 1, z))


def eyes_big(ch, f, s=1.25, d=4, sound="sparkle"):
    if sound:
        sfx(f - d, sound)
    for e in ch["eyes"]:
        key(e, "scale", f - d, (1, 1, 1))
        key(e, "scale", f, (s, s, s))


def eyes_norm(ch, f, d=4):
    for e in ch["eyes"]:
        key(e, "scale", f - d, tuple(e.scale))
        key(e, "scale", f, (1, 1, 1))


def brows(ch, f, up=0.0, d=4):
    for b in ch.get("brows", []):
        z0 = b.get("z0", b.location[2])
        b["z0"] = z0
        key(b, "location", f - d, tuple(b.location))
        key(b, "location", f, (b.location[0], b.location[1], z0 + up))


def look(ch, f, dx, dz=0.0):
    for p in ch["pupils"]:
        key(p, "location", f, (dx, p.location[1], dz))


def hop(ch, f0, x0, x1, h=0.45, n=12):
    r, p = ch["root"], ch["piv"]
    sfx(f0 + 2, "boing")
    sfx(f0 + n, "land")
    key(p, "scale", f0, (1, 1, 1))
    key(p, "scale", f0 + 2, (1.12, 1.12, 0.82))  # anticipation squash
    key(r, "location", f0 + 2, (x0, r.location[1], 0))
    key(p, "scale", f0 + 5, (0.92, 0.92, 1.15))  # stretch on take-off
    key(r, "location", f0 + n // 2 + 1, ((x0 + x1) / 2, r.location[1], h))
    key(p, "scale", f0 + n - 1, (0.95, 0.95, 1.08))
    key(r, "location", f0 + n, (x1, r.location[1], 0))
    key(p, "scale", f0 + n + 1, (1.15, 1.15, 0.8))  # landing squash
    key(p, "scale", f0 + n + 5, (1, 1, 1))
    for a in ch["arms"]:
        side = 1 if a.location[0] > 0 else -1
        key(a, "rotation_euler", f0 + 2, (0, 0, 0))
        key(a, "rotation_euler", f0 + 6, (0, side * 1.6, 0))
        key(a, "rotation_euler", f0 + n + 2, (0, 0, 0))


def idle_breathe(ch, f0, f1, period=24, amt=0.03):
    p = ch["piv"]
    f = f0
    while f < f1:
        key(p, "scale", f, (1, 1, 1))
        key(p, "scale", f + period // 2, (1 + amt * 0.5, 1 + amt * 0.5, 1 - amt))
        f += period


def mouth(ch, f, open_z, w=1.0):
    key(ch["mouth"], "scale", f, (w, 0.35, open_z))


# ---------------------------------------------------------------- the gag
cake = make_set()
cam, tgt = make_world()
pip = make_blob("pip", "#FF4D5E", x=-1.25, y=0.15)
chick = make_chick("chick", x=0.55, y=0.75)
chick["root"].location = (0.55, 0.75, -0.9)  # hidden behind the table

# camera: gentle push-in, then a quick reframe for the payoff
# shot A (1-28): close-up, Pip notices the cake
key(cam, "location", 1, (-1.3, -2.75, 0.82))
key(tgt, "location", 1, (-1.25, 0.15, 0.68))
key(cam.data, "lens", 1, 50)
key(cam, "location", 28, (-1.22, -2.5, 0.8), "CONSTANT")
key(tgt, "location", 28, (-1.2, 0.15, 0.68), "CONSTANT")
key(cam.data, "lens", 28, 50, "CONSTANT")
# shot B (29-60): wider, the camera follows the hops
key(cam, "location", 29, (-1.05, -3.7, 0.9))
key(tgt, "location", 29, (-1.05, 0.2, 0.6))
key(cam.data, "lens", 29, 40)
key(cam, "location", 60, (-0.15, -3.5, 0.88), "CONSTANT")
key(tgt, "location", 60, (-0.15, 0.2, 0.6), "CONSTANT")
key(cam.data, "lens", 60, 40, "CONSTANT")
# shot C (61-144): two-shot at the table, slow push-in
key(cam, "location", 61, (0.12, -2.6, 0.8))
key(tgt, "location", 61, (0.12, 0.2, 0.62))
key(cam.data, "lens", 61, 35)
key(cam, "location", 144, (0.1, -2.35, 0.78))

# pip: idle, blink, spots the cake (eyes big, looks right), hops x3 to the table
idle_breathe(pip, 1, 18)
blink(pip, 10)
look(pip, 1, 0.0)
look(pip, 18, 0.05)
eyes_big(pip, 22)
brows(pip, 22, 0.05)
brows(pip, 34, 0.0)
mouth(pip, 18, 0.35)
mouth(pip, 24, 0.9, 1.1)  # "oooh"
eyes_norm(pip, 30)
hop(pip, 28, -1.25, -0.95, 0.35)
hop(pip, 42, -0.95, -0.6, 0.35)
hop(pip, 56, -0.6, -0.22, 0.3)
mouth(pip, 40, 0.5)
# lean in for a bite
p = pip["piv"]
key(p, "rotation_euler", 72, (0, 0, 0))
key(p, "rotation_euler", 82, (0, math.radians(18), 0))
mouth(pip, 76, 0.4)
mouth(pip, 84, 1.6, 1.25)  # big open mouth
look(pip, 74, 0.04, -0.03)
blink(pip, 70)

# chick pops up behind the table and slides the cake away
r = chick["root"]
key(r, "location", 70, (0.55, 0.75, -0.9))
key(r, "location", 78, (0.62, 0.62, 0.12))
sfx(75, "pop")
sfx(83, "swish")
sfx(87, "chomp")
sfx(95, "zip")
look(chick, 78, -0.05)
for a in chick["arms"]:
    key(a, "rotation_euler", 78, (0, 0, 0))
    key(a, "rotation_euler", 84, (0, (1 if a.location[0] > 0 else -1) * -1.2, 0))
key(cake, "location", 82, (0, 0, 0.67))
key(cake, "location", 92, (0.42, 0.25, 0.67))
key(r, "location", 92, (0.95, 0.75, 0.12))
key(r, "location", 102, (1.05, 0.8, -0.9))  # ducks away with it
key(cake, "location", 102, (0.5, 0.6, 0.0))
key(cake, "scale", 101, (1, 1, 1))
key(cake, "scale", 103, (0.01, 0.01, 0.01), "CONSTANT")

# chomp on nothing -> surprise -> looks at the viewer, arms up
mouth(pip, 90, 0.15, 0.8)
key(p, "rotation_euler", 92, (0, math.radians(18), 0))
key(p, "rotation_euler", 100, (0, math.radians(-4), 0))
key(p, "rotation_euler", 106, (0, 0, 0))
eyes_big(pip, 100, 1.4, 5, sound="doink")
brows(pip, 100, 0.08)
brows(pip, 136, 0.0, 8)
brows(chick, 80, 0.0)
sfx(101, "slide_down")
mouth(pip, 100, 1.3, 0.9)
look(pip, 100, 0.0, 0.0)
for a in pip["arms"]:
    side = 1 if a.location[0] > 0 else -1
    key(a, "rotation_euler", 98, (0, 0, 0))
    key(a, "rotation_euler", 104, (0, side * 2.4, 0))
key(p, "scale", 98, (1, 1, 1))
key(p, "scale", 101, (0.9, 0.9, 1.18))
key(p, "scale", 106, (1, 1, 1))
blink(pip, 116)
look(pip, 120, -0.04)
look(pip, 132, 0.04)
mouth(pip, 126, 0.45)
eyes_norm(pip, 136, 8)
for a in pip["arms"]:
    key(a, "rotation_euler", 130, tuple(a.rotation_euler))
    key(a, "rotation_euler", 140, (0, 0, 0))

# ---------------------------------------------------------------- render
R = sc.render
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.04
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 4
sc.cycles.diffuse_bounces = 2
sc.cycles.glossy_bounces = 2
sc.cycles.transmission_bounces = 2
sc.cycles.transparent_max_bounces = 2
sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.view_settings.exposure = 0.15
R.resolution_x, R.resolution_y = 1080, 1920
R.resolution_percentage = int(os.environ.get("RES", "100"))
R.use_persistent_data = True
sc.cycles.samples = int(os.environ.get("SAMPLES", "20"))
R.image_settings.file_format = "PNG"
R.image_settings.color_mode = "RGB"
json.dump({"fps": FPS, "frames": sc.frame_end, "events": sorted(EVENTS)}, open(f"{OUT}/events.json", "w"))

if MODE == "stills":
    frames = [12, 26, 50, 66, 86, 104]
else:  # "part:K/N" -> every Nth frame starting at K+1 (lets many machines share one short)
    k, n = (int(v) for v in MODE.split(":")[1].split("/")) if MODE.startswith("part:") else (0, 1)
    frames = list(range(sc.frame_start + k, sc.frame_end + 1, n))
os.makedirs(f"{OUT}/frames", exist_ok=True)
import time
for f in frames:
    t0 = time.time()
    sc.frame_set(f)
    R.filepath = f"{OUT}/frames/f_{f:04d}.png"
    bpy.ops.render.render(write_still=True)
    print(f"frame {f} in {time.time() - t0:.1f}s", flush=True)
print("done", len(frames), "frames", flush=True)
