# Prototype: a real 3D cartoon shot built + animated in code, rendered with Cycles.
# Run: blender -b --python blender/proto.py -- <outdir> [stills|video|both]
import bpy, math, os, sys, glob

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


def eyes(parent, y, z, dx, r, look=(0, 0)):
    """Two big glossy cartoon eyes. Returns (eye pivots, pupils)."""
    piv, pup = [], []
    for side in (-1, 1):
        e = empty(f"{parent.name}_eye{side}", (side * dx, y, z), parent)
        sphere(e.name + "_w", r, (0, 0, 0), WHITE, e, scale=(1, 0.55, 1.18), sub=2)
        p = empty(e.name + "_p", (0, -r * 0.42, 0), e)
        sphere(e.name + "_iris", r * 0.62, (0, 0, -r * 0.05), BLACK, p, scale=(1, 0.45, 1.1), sub=2)
        sphere(e.name + "_hl", r * 0.2, (r * 0.22, -r * 0.3, r * 0.25), SHINE, p, sub=0)
        sphere(e.name + "_hl2", r * 0.09, (-r * 0.18, -r * 0.3, -r * 0.22), SHINE, p, sub=0)
        piv.append(e)
        pup.append(p)
    return piv, pup


def make_blob(name, color, x=0.0, y=0.0):
    """Round fluffy pet creature (original design): ears, big eyes, oval mouth, little arms + feet."""
    root = empty(name, (x, y, 0))
    body_m = mat(color, 0.55, sss=0.15)
    piv = empty(name + "_piv", (0, 0, 0), root)  # squash/stretch from the floor
    sphere(name + "_body", 0.5, (0, 0, 0.55), body_m, piv, scale=(1.0, 0.92, 1.05), sub=2)
    for side in (-1, 1):
        sphere(f"{name}_ear{side}", 0.15, (side * 0.3, 0.02, 1.0), body_m, piv, scale=(0.8, 0.6, 1.2),
               rot=(0, side * 0.5, 0))
        sphere(f"{name}_cheek{side}", 0.08, (side * 0.3, -0.4, 0.5), mat("#FF8FB1", 0.6), piv,
               scale=(1, 0.4, 0.7))
    ev, pp = eyes(piv, -0.4, 0.72, 0.17, 0.15)
    mouth = sphere(name + "_mouth", 0.1, (0, -0.46, 0.42), mat("#5A1020", 0.4), piv, scale=(1.0, 0.35, 0.35))
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
    return dict(root=root, piv=piv, eyes=ev, pupils=pp, mouth=mouth, arms=arms, feet=feet)


def make_chick(name, x=0.0, y=0.0):
    root = empty(name, (x, y, 0))
    yel = mat("#FFD53D", 0.5, sss=0.1)
    piv = empty(name + "_piv", (0, 0, 0), root)
    sphere(name + "_body", 0.34, (0, 0, 0.38), yel, piv, scale=(1, 0.95, 1.08), sub=2)
    sphere(name + "_tuft", 0.07, (0, 0, 0.76), yel, piv, scale=(0.6, 0.6, 1.6), rot=(0.3, 0, 0))
    ev, pp = eyes(piv, -0.29, 0.48, 0.12, 0.1)
    cone(name + "_beak", 0.07, 0.0, 0.14, (0, -0.33, 0.37), mat("#FF8A1F", 0.4), piv, rot=(math.radians(90), 0, 0))
    arms = []
    for side in (-1, 1):
        sh = empty(f"{name}_wing{side}", (side * 0.32, 0, 0.4), piv)
        sphere(f"{name}_w{side}", 0.1, (side * 0.04, 0, -0.06), yel, sh, scale=(0.5, 0.9, 1.4), rot=(0, side * 0.3, 0))
        arms.append(sh)
    feet = [sphere(f"{name}_foot{s}", 0.07, (s * 0.12, -0.06, 0.03), mat("#FF8A1F", 0.4), root, scale=(1, 1.6, 0.5))
            for s in (-1, 1)]
    return dict(root=root, piv=piv, eyes=ev, pupils=pp, arms=arms, feet=feet)


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
            box(f"win{i}{wx}", (0.5, 0.1, 0.55), (hx + wx, 4.08, h * 0.62), mat("#2F4A7A", 0.15, coat=1), bevel=0.06)
        box(f"door{i}", (0.55, 0.1, 0.9), (hx, 4.08, 0.45), mat("#8A5A3C", 0.5), bevel=0.08)
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
    sun_d.energy, sun_d.angle, sun_d.color = 3.2, math.radians(8), (1, 0.95, 0.86)
    sun = bpy.data.objects.new("sun", sun_d)
    sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
    fill_d = bpy.data.lights.new("fill", "AREA")
    fill_d.energy, fill_d.size, fill_d.color = 400, 6, (0.9, 0.95, 1)
    fill = bpy.data.objects.new("fill", fill_d)
    sc.collection.objects.link(fill)
    fill.location = (-2, -5, 3)
    fill.rotation_euler = (math.radians(60), 0, math.radians(-25))

    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 38
    cam_d.dof.use_dof = True
    cam_d.dof.aperture_fstop = 4.0
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


def eyes_big(ch, f, s=1.25, d=4):
    for e in ch["eyes"]:
        key(e, "scale", f - d, (1, 1, 1))
        key(e, "scale", f, (s, s, s))


def eyes_norm(ch, f, d=4):
    for e in ch["eyes"]:
        key(e, "scale", f - d, tuple(e.scale))
        key(e, "scale", f, (1, 1, 1))


def look(ch, f, dx, dz=0.0):
    for p in ch["pupils"]:
        key(p, "location", f, (dx, p.location[1], dz))


def hop(ch, f0, x0, x1, h=0.45, n=12):
    r, p = ch["root"], ch["piv"]
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
key(cam, "location", 1, (-0.3, -4.6, 1.25))
key(cam, "location", 60, (-0.1, -4.0, 1.15), "CONSTANT")
key(tgt, "location", 1, (-0.3, 0.2, 0.6))
key(tgt, "location", 60, (0.0, 0.2, 0.62), "CONSTANT")
key(cam, "location", 61, (0.2, -2.6, 0.95), "CONSTANT")
key(tgt, "location", 61, (0.2, 0.2, 0.72), "CONSTANT")
key(cam, "location", 144, (0.25, -2.35, 0.95))
key(cam.data, "lens", 1, 38)

# pip: idle, blink, spots the cake (eyes big, looks right), hops x3 to the table
idle_breathe(pip, 1, 18)
blink(pip, 10)
look(pip, 1, 0.0)
look(pip, 18, 0.05)
eyes_big(pip, 22)
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
eyes_big(pip, 100, 1.4, 5)
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
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.view_settings.exposure = 0.15
R.resolution_x, R.resolution_y = 1080, 1920
R.use_persistent_data = True

if MODE in ("stills", "both"):
    sc.cycles.samples = 96
    R.resolution_percentage = 100
    R.image_settings.file_format = "JPEG"
    R.image_settings.quality = 92
    for f in (12, 26, 50, 66, 86, 104):
        sc.frame_set(f)
        R.filepath = f"{OUT}/still_{f:03d}.jpg"
        bpy.ops.render.render(write_still=True)
        print("still", f, flush=True)

if MODE in ("video", "both"):
    sc.cycles.samples = 24
    R.resolution_percentage = 50
    R.image_settings.file_format = "FFMPEG"
    R.ffmpeg.format = "MPEG4"
    R.ffmpeg.codec = "H264"
    R.ffmpeg.constant_rate_factor = "HIGH"
    R.filepath = f"{OUT}/proto_"
    bpy.ops.render.render(animation=True)
    for f in glob.glob(f"{OUT}/proto_*.mp4"):
        os.replace(f, f"{OUT}/proto.mp4")
print("done", os.listdir(OUT), flush=True)
