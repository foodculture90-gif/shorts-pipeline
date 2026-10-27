"""Toon kit: everything needed to build a little 3D cartoon in Blender from code.

Materials, shapes, the recurring cast, props, sets, lights, camera moves, animation moves and the
sound-effect cue list (EVENTS -> blender/audio.py). Used by blender/gags.py + blender/scene.py.
"""
import json, math, os, random

import bpy

FPS = 24
MATS = {}
EVENTS = []  # [frame, sound kind]
LOOKS = {}   # per short: {character: [accessory, colour]} - same outfit in every gag of the short
THEME = {}   # per short: {"sky": ..., "season": ..., "pal": seed} - colours of the set
VAR = random.Random(1)  # per gag: prop colours
PROP_COLOR = None  # a colour the title may mention (e.g. a blue balloon)
sc = None


def reset():
    global sc
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    MATS.clear()
    EVENTS.clear()
    return sc


def sfx(f, kind):
    EVENTS.append([int(f), kind])


def lin(hexs):
    h = hexs.lstrip("#")
    return tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4))


# ------------------------------------------------------------------ materials
def mat(hexs, rough=0.45, coat=0.0, emit=0.0, metal=0.0):
    key = (hexs, rough, coat, emit, metal)
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(hexs)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(hexs), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.05
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(hexs), 1)
        b.inputs["Emission Strength"].default_value = emit
    MATS[key] = m
    return m


def checker(c1, c2, scale=6.0, rough=0.4, coat=0.0):
    key = ("checker", c1, c2, scale, rough, coat)
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new("checker")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    ck = nt.nodes.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = scale
    ck.inputs["Color1"].default_value = (*lin(c1), 1)
    ck.inputs["Color2"].default_value = (*lin(c2), 1)
    nt.links.new(ck.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    MATS[key] = m
    return m


WHITE = BLACK = SHINE = None


def base_mats():
    global WHITE, BLACK, SHINE
    WHITE = mat("#FFFFFF", 0.25, coat=0.6)
    BLACK = mat("#141018", 0.2, coat=1.0)
    SHINE = mat("#FFFFFF", 0.2, emit=4.0)


# ------------------------------------------------------------------ shapes
def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    sc.collection.objects.link(o)
    if parent is not None:
        o.parent = parent
    o.location = loc
    return o


def _finish(o, name, m, parent, loc, scale, rot, subsurf=1):
    o.name = name
    if parent is not None:
        o.parent = parent
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


def sphere(name, r, loc, m=None, parent=None, scale=(1, 1, 1), rot=(0, 0, 0), sub=1, seg=40):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r)
    return _finish(bpy.context.active_object, name, m, parent, loc, scale, rot, sub)


def _bevel_apply(o, width, segments):
    bv = o.modifiers.new("b", "BEVEL")
    bv.width, bv.segments = width, segments
    bpy.ops.object.modifier_apply(modifier="b")


def cyl(name, r, depth, loc, m=None, parent=None, scale=(1, 1, 1), rot=(0, 0, 0), bevel=0.0, verts=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth)
    o = bpy.context.active_object
    if bevel:
        _bevel_apply(o, bevel, 4)
    o = _finish(o, name, m, parent, loc, scale, rot, 0)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    return o


def box(name, size, loc, m=None, parent=None, rot=(0, 0, 0), bevel=0.08):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        _bevel_apply(o, min(bevel, min(size) * 0.45), 5)
    o = _finish(o, name, m, parent, loc, (1, 1, 1), rot, 0)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    return o


def cone(name, r1, r2, depth, loc, m=None, parent=None, rot=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=r1, radius2=r2, depth=depth)
    o = _finish(bpy.context.active_object, name, m, parent, loc, scale, rot, 0)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    return o


def star(name, r, loc, m, parent=None, depth=0.04):
    """Flat 5-point cartoon star facing the camera (-Y)."""
    me = bpy.data.meshes.new(name)
    verts = [(0, 0, 0)]
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        verts.append((math.cos(a) * rr, 0, math.sin(a) * rr))
    faces = [(0, 1 + i, 1 + (i + 1) % 10) for i in range(10)]
    me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    if parent is not None:
        o.parent = parent
    o.location = loc
    me.materials.append(m)
    so = o.modifiers.new("solid", "SOLIDIFY")
    so.thickness, so.offset = depth, 0
    bv = o.modifiers.new("bev", "BEVEL")
    bv.width, bv.segments = depth * 0.4, 3
    return o


def curve_line(name, pts, radius, m, parent=None, loc=(0, 0, 0)):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth, cu.bevel_resolution = radius, 4
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, cu)
    sc.collection.objects.link(o)
    if parent is not None:
        o.parent = parent
    o.location = loc
    o.data.materials.append(m)
    return o


# ------------------------------------------------------------------ keyframes
def key(o, path, f, val, interp=None):
    setattr(o, path, val)
    o.keyframe_insert(data_path=path, frame=f)
    if interp and o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    if int(kp.co[0]) == f:
                        kp.interpolation = interp


def show(o, f, visible=True):
    """Key visibility (render) on o and all its children."""
    for x in [o] + list(o.children_recursive):
        x.hide_render = not visible
        x.keyframe_insert(data_path="hide_render", frame=f)


# ------------------------------------------------------------------ the recurring cast (original designs)
CAST = {
    "pip": dict(kind="blob", body="#FF4D5E", belly="#FFC2B8", feet="#FFD27A", iris="#3B8BEB", brow="#7A1E2A",
                ears="round", tuft=True, size=1.0),
    "bubu": dict(kind="blob", body="#4DA6FF", belly="#DDF0FF", feet="#FFFFFF", iris="#6B3E1F", brow="#1E4A7A",
                 ears="bunny", tuft=False, size=0.95),
    "mimi": dict(kind="blob", body="#B57BFF", belly="#F0E4FF", feet="#FFD27A", iris="#2FAF5A", brow="#4A2A7A",
                 ears="cat", tuft=False, tail=True, size=0.9),
    "gogo": dict(kind="blob", body="#5CCB6B", belly="#E9FFD9", feet="#FFB347", iris="#8A4B12", brow="#2A6A2A",
                 ears="none", eyes_top=True, tuft=False, size=0.95),
    "chiko": dict(kind="bird", body="#FFD53D", beak="#FF8A1F", iris="#6B3E1F", size=1.35),
    "lulu": dict(kind="blob", body="#FF8FC8", belly="#FFE6F3", feet="#FFFFFF", iris="#3B8BEB", brow="#8A2A5A",
                 ears="round", ear_in="#FFD1E6", tuft=False, size=0.9),
    "tobi": dict(kind="blob", body="#FF9A3D", belly="#FFF4E6", feet="#6B3E1F", iris="#2FAF5A", brow="#8A3E12",
                 ears="cat", ear_in="#FFF4E6", tuft=False, tail=True, tail_tip="#FFFFFF", size=0.97),
    "teo": dict(kind="blob", body="#F2D2A2", belly="#FFF6E8", feet="#FFFFFF", iris="#6B3E1F", brow="#7A4A22",
                ears="floppy", ear_col="#A0663A", patch="#A0663A", tuft=False, nose=True, size=0.95),
    "popo": dict(kind="bird", body="#2E4A7A", belly="#FFFFFF", beak="#FFA53D", iris="#3B2A1A", tuft=False,
                 size=1.3, wing="#2E4A7A"),
    "bobo": dict(kind="blob", body="#FFFFFF", belly="#F1F1F4", feet="#2B2B33", iris="#3B2A1A", brow="#2B2B33",
                 ears="round", ear_col="#2B2B33", patches="#2B2B33", tuft=False, nose=True, size=1.0),
    "zuzu": dict(kind="blob", body="#EADCFF", belly="#FFFFFF", feet="#FFB3E6", iris="#B04BD9", brow="#8A4AA8",
                 ears="cat", ear_in="#FFC2E6", tuft=False, horn="#FFD23F", mane=["#FF8FC8", "#8FD3FF", "#FFE27A", "#9EF0C0"],
                 size=0.92),
    "leo": dict(kind="blob", body="#FFC24D", belly="#FFF0C9", feet="#C9822E", iris="#6B3E1F", brow="#A0582A",
                ears="round", ear_in="#FFE0A0", tuft=False, ruff="#D9772B", tail=True, tail_tip="#D9772B", nose=True,
                size=1.0),
    "dodo": dict(kind="bird", body="#FFFFFF", beak="#FF9F1C", iris="#2A2A3A", belly="#FFF7E0", wing="#EFEFF4",
                 size=1.3),
    # ---- new kinds of characters: robot, dinosaurs, dragon, monster, octopus, elephant, pig, owl, bee, two kids
    "bolt": dict(kind="robot", body="#8FD8E8", accent="#FF6B6B", screen="#22304A", feet="#5A6B7D", iris="#2EC4F5",
                 brow="#1A2638", size=0.95, acc_top=1.05, no_cap=True),
    "rexy": dict(kind="dino", body="#6CCB5F", belly="#E6F7C8", plates="#FF9F43", feet="#58B04C", iris="#7A4A12",
                 brow="#2F6A2A", size=1.0, acc_top=1.04),
    "trixie": dict(kind="dino", body="#F59AC8", belly="#FFE3F0", frill="#B57BFF", horns="#FFF6D8", feet="#E584B6",
                   iris="#3B8BEB", brow="#8A2A5A", size=0.95, acc_top=1.04, no_cap=True),
    "drako": dict(kind="dino", body="#9B7BEA", belly="#FFE07A", plates="#7FD8FF", wings="#7FD8FF", horns="#FFE07A",
                  feet="#8668D6", iris="#E8A43A", brow="#4A2A8A", size=0.95, spade=True, acc_top=1.04, no_cap=True),
    "momo": dict(kind="monster", body="#4FC3F7", belly="#B3E5FC", fur="#38ACE6", horns="#FFB347", feet="#2F8FD8",
                 iris="#5CCB6B", brow="#1E5A8A", size=1.0, no_cap=True, acc_top=1.12),
    "ocki": dict(kind="octo", body="#FF8A65", spots="#FFC2AE", iris="#2A2A3A", brow="#A8452A", size=0.95, acc_top=1.13),
    "ellie": dict(kind="elephant", body="#A9B8D6", belly="#C9D4EA", ear_in="#FFC2D9", feet="#93A3C4", iris="#3B2A1A",
                  brow="#5A6A8A", size=1.0),
    "pinky": dict(kind="blob", body="#FFA9C6", belly="#FFD6E5", feet="#E8789F", iris="#3B8BEB", brow="#B8456E",
                  ears="pig", snout="#FF8FB5", curl_tail=True, mouth=(-0.43, 0.35), tuft=False, size=0.95),
    "hoot": dict(kind="bird", body="#A0703E", belly="#F2DDB8", beak="#F2A93B", iris="#E89B1A", wing="#8A5E32",
                 owl=True, disc="#F7E6C4", tuft=False, size=1.3, no_cap=True),
    "buzzy": dict(kind="blob", body="#FFD23F", belly="#FFE98A", feet="#2B2B33", iris="#3B2A1A", brow="#2B2B33",
                  ears="none", bee=True, tuft=False, size=0.9, no_cap=True),
    "kiki": dict(kind="kid", skin="#F5C9A0", hair="#6A3B1F", shirt="#FF6FA8", pants="#4DA6FF", shoes="#FFFFFF",
                 iris="#3B7A2A", hairdo="pigtails", ties="#FFD23F", size=1.0, acc_top=1.2),
    "nino": dict(kind="kid", skin="#8D5A3C", hair="#1E1410", shirt="#FFC93D", pants="#3B5BDB", shoes="#FF5A5F",
                 iris="#3B2A1A", hairdo="curly", size=1.0, acc_top=1.2),
}
ACCESSORIES = ["party_hat", "bow", "cap", "flower", "bowtie", "crown", "none", "none"]
ACC_COLORS = ["#FF4D6D", "#FFD23F", "#4DA6FF", "#5CCB6B", "#B57BFF", "#FF8A3D", "#FFFFFF", "#2EC4B6"]


def eyes(parent, y, z, dx, r, iris="#3B8BEB", brow_m=None):
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
            b["z0"] = b.location[2]
            brows.append(b)
    return piv, pup, brows


def torus(name, R, r, loc, m=None, parent=None, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=40, minor_segments=12)
    return _finish(bpy.context.active_object, name, m, parent, loc, scale, rot, 1)


def _face(name, piv, d, fy, ez, edx, er, my, mz, mw=1.0, cheeks=None, brow=True):
    """Eyes + an open/closed mouth + smile, same parts (and animation API) as the original cast."""
    ev, pp, br = eyes(piv, fy, ez, edx, er, d["iris"], mat(d.get("brow", "#3A2A2A"), 0.5) if brow else None)
    if cheeks:
        cx, cy, cz = cheeks
        for side in (-1, 1):
            sphere(f"{name}_cheek{side}", 0.07, (side * cx, cy, cz), mat("#FF8FB1", 0.6), piv, scale=(1, 0.4, 0.7))
    mouth = sphere(name + "_mouth", 0.1 * mw, (0, my, mz), mat("#5A1020", 0.4), piv, scale=(1.2, 0.35, 0.05))
    sphere(name + "_tongue", 0.06 * mw, (0, -0.02, -0.04), mat("#FF5A7A", 0.5), mouth, scale=(1, 0.8, 0.5))
    w = 0.085 * mw
    smile = curve_line(name + "_smile", [(-w, 0, w * 0.45), (0, 0, -w * 0.25), (w, 0, w * 0.45)], 0.014,
                       mat("#5A1020", 0.4), piv, (0, my - 0.02, mz + 0.015))
    return ev, pp, br, mouth, smile


def _limbs(name, piv, root, arm_m, foot_m, sx=0.45, sy=-0.05, sz=0.55, ar=0.08, al=2.0, hand=None, fx=0.2, fr=0.14):
    arms = []
    for side in (-1, 1):
        sh = empty(f"{name}_sh{side}", (side * sx, sy, sz), piv)
        sphere(f"{name}_arm{side}", ar, (side * 0.06, 0, -0.14), arm_m, sh, scale=(0.9, 0.9, al))
        if hand is not None:
            sphere(f"{name}_hand{side}", ar * 1.2, (side * 0.07, 0, -0.14 - ar * al * 0.95), hand, sh)
        arms.append(sh)
    feet = [sphere(f"{name}_foot{s}", fr, (s * fx, -0.08, 0.06), foot_m, root, scale=(1.0, 1.35, 0.55)) for s in (-1, 1)]
    return arms, feet


def _chain(name, pts, r0, r1, m, parent):
    """A bendy tube made of overlapping balls (tails, trunks, tentacles)."""
    n = len(pts)
    return [sphere(f"{name}{i}", r0 + (r1 - r0) * i / max(1, n - 1), p, m, parent, sub=1, seg=24) for i, p in enumerate(pts)]


def _robot(name, d, root, piv, ch):
    body = mat(d["body"], 0.3, coat=0.5, metal=0.25)
    acc = mat(d["accent"], 0.35, coat=0.4)
    box(name + "_body", (0.88, 0.76, 0.94), (0, 0, 0.6), body, piv, bevel=0.22)
    box(name + "_screen", (0.7, 0.06, 0.46), (0, -0.37, 0.74), mat(d["screen"], 0.15, coat=1.0), piv, bevel=0.1)
    box(name + "_panel", (0.42, 0.05, 0.2), (0, -0.375, 0.34), mat("#E8EEF5", 0.4), piv, bevel=0.05)
    for i, c in enumerate(("#FF5A5F", "#FFD23F", "#5CCB6B")):
        sphere(f"{name}_btn{i}", 0.035, (-0.11 + i * 0.11, -0.405, 0.34), mat(c, 0.2, coat=1.0, emit=0.8), piv, sub=0)
    for side in (-1, 1):
        cyl(f"{name}_bolt{side}", 0.1, 0.09, (side * 0.46, 0, 0.74), acc, piv, rot=(0, math.pi / 2, 0), bevel=0.02)
    cyl(name + "_ant", 0.016, 0.26, (-0.2, 0.02, 1.18), mat("#9AA5B1", 0.3, metal=0.6), piv, rot=(0, -0.3, 0))
    sphere(name + "_bulb", 0.065, (-0.24, 0.02, 1.32), mat(d["accent"], 0.2, emit=2.5), piv, sub=1)
    ev, pp, br, mouth, smile = _face(name, piv, d, -0.39, 0.82, 0.17, 0.13, -0.405, 0.6, 1.0)
    arms, feet = _limbs(name, piv, root, mat("#B8C4D0", 0.3, metal=0.5), mat(d["feet"], 0.4, coat=0.3),
                        sx=0.47, sz=0.5, ar=0.065, al=1.8, hand=acc)
    ch.update(eyes=ev, pupils=pp, brows=br, arms=arms, feet=feet, mouth=mouth, smile=smile, top=1.15, head=0.8)


def _dino(name, d, root, piv, ch):
    body_m = mat(d["body"], 0.55)
    sphere(name + "_body", 0.5, (0, 0, 0.55), body_m, piv, scale=(1.0, 0.95, 1.0), sub=2)
    sphere(name + "_belly", 0.3, (0, -0.33, 0.36), mat(d["belly"], 0.6), piv, scale=(1.0, 0.45, 0.8), sub=2)
    sphere(name + "_snout", 0.23, (0, -0.42, 0.5), body_m, piv, scale=(1.08, 0.9, 0.72), sub=2)
    for side in (-1, 1):
        sphere(f"{name}_nostril{side}", 0.025, (side * 0.065, -0.615, 0.58), mat("#2A2A2A", 0.3), piv, sub=0)
    ev, pp, br, mouth, smile = _face(name, piv, d, -0.37, 0.8, 0.18, 0.15, -0.6, 0.45, 1.1, cheeks=(0.27, -0.5, 0.55))
    if d.get("plates"):  # spikes along the back
        pm = mat(d["plates"], 0.45)
        for i, th in enumerate((0.25, 0.65, 1.05, 1.45, 1.85)):
            cone(f"{name}_plate{i}", 0.085 - i * 0.008, 0.0, 0.2 - i * 0.015,
                 (0, 0.5 * math.sin(th) * 0.95, 0.55 + 0.5 * math.cos(th)), pm, piv, rot=(-th, 0, 0))
    if d.get("frill"):  # triceratops frill + horns
        sphere(name + "_frill", 0.44, (0, 0.14, 0.92), mat(d["frill"], 0.5), piv, scale=(1.15, 0.22, 0.85), rot=(-0.35, 0, 0))
    if d.get("horns"):
        hm = mat(d["horns"], 0.35, coat=0.4)
        for side in (-1, 1):
            cone(f"{name}_horn{side}", 0.055, 0.0, 0.22, (side * 0.15, -0.22, 1.03), hm, piv, rot=(-0.5, side * 0.25, 0))
        if d.get("frill"):
            cone(name + "_nosehorn", 0.045, 0.0, 0.12, (0, -0.55, 0.66), hm, piv, rot=(0.6, 0, 0))
    if d.get("wings"):
        wm = mat(d["wings"], 0.35)
        for side in (-1, 1):
            w = empty(f"{name}_wingp{side}", (side * 0.32, 0.32, 0.82), piv)
            w.rotation_euler = (0.2, 0, side * -0.5)
            sphere(f"{name}_wing{side}", 0.3, (side * 0.18, 0, 0.05), wm, w, scale=(1.0, 0.12, 0.7), rot=(0, side * -0.4, 0))
    tail = _chain(name + "_tail", [(0, 0.42, 0.32), (0, 0.6, 0.24), (0, 0.76, 0.18), (0, 0.9, 0.16), (0.02, 1.02, 0.18)],
                  0.17, 0.06, body_m, piv)
    if d.get("spade"):
        cone(name + "_spade", 0.09, 0.0, 0.16, (0.02, 1.1, 0.2), mat(d.get("plates", d["body"]), 0.45), piv, rot=(-1.4, 0, 0))
    arms, feet = _limbs(name, piv, root, body_m, mat(d["feet"], 0.55), sx=0.42, sy=-0.18, sz=0.5, ar=0.065, al=1.5,
                        fr=0.15)
    for f in feet:
        for k in (-1, 0, 1):
            sphere(f"{f.name}_claw{k}", 0.03, (k * 0.07, -0.12, -0.01), WHITE, f, sub=0)
    ch.update(eyes=ev, pupils=pp, brows=br, arms=arms, feet=feet, mouth=mouth, smile=smile, top=1.12, head=0.8)


def _monster(name, d, root, piv, ch):
    body_m, fur = mat(d["body"], 0.75), mat(d["fur"], 0.85)
    sphere(name + "_body", 0.5, (0, 0, 0.55), body_m, piv, scale=(1.0, 0.92, 1.05), sub=2)
    sphere(name + "_belly", 0.3, (0, -0.33, 0.36), mat(d["belly"], 0.8), piv, scale=(1.0, 0.45, 0.8), sub=2)
    for i in range(20):  # shaggy fur tufts all around the outline
        a = i / 20 * math.tau
        if math.sin(a) < -0.75:
            continue
        sphere(f"{name}_tuft{i}", 0.12, (math.cos(a) * 0.48, 0.1, 0.56 + math.sin(a) * 0.5), fur if i % 2 else body_m,
               piv, scale=(1, 0.8, 1), sub=1, seg=20)
    hm = mat(d["horns"], 0.35, coat=0.5)
    for side in (-1, 1):
        h = empty(f"{name}_hornp{side}", (side * 0.22, -0.02, 1.0), piv)
        h.rotation_euler = (0, side * 0.45, 0)
        _chain(f"{name}_horn{side}_", [(0, 0, 0), (side * 0.03, 0, 0.08), (side * 0.07, 0, 0.15), (side * 0.12, 0, 0.2)],
               0.07, 0.025, hm, h)
    ev, pp, br, mouth, smile = _face(name, piv, d, -0.405, 0.76, 0.19, 0.18, -0.455, 0.42, 1.5, cheeks=(0.32, -0.38, 0.52))
    for side in (-1, 1):  # two little teeth, seen when the mouth opens
        cone(f"{name}_tooth{side}", 0.025, 0.0, 0.05, (side * 0.045, -0.03, 0.03), WHITE, mouth, rot=(math.pi, 0, 0))
    arms, feet = _limbs(name, piv, root, fur, mat(d["feet"], 0.6))
    ch.update(eyes=ev, pupils=pp, brows=br, arms=arms, feet=feet, mouth=mouth, smile=smile, top=1.12, head=0.76)


def _octo(name, d, root, piv, ch):
    body_m = mat(d["body"], 0.45, coat=0.3)
    sphere(name + "_body", 0.5, (0, 0, 0.66), body_m, piv, scale=(1.0, 0.95, 1.05), sub=2)
    sm = mat(d["spots"], 0.5)
    for i, (sx_, sz_) in enumerate(((0.3, 1.0), (-0.32, 0.98), (0.0, 1.13), (0.42, 0.78), (-0.44, 0.74))):
        sy_ = -0.95 * math.sqrt(max(0.0, 0.25 - sx_ * sx_ - ((sz_ - 0.66) / 1.05) ** 2))
        sphere(f"{name}_spot{i}", 0.055, (sx_, sy_ - 0.005, sz_), sm, piv, scale=(1, 0.45, 1), sub=0)
    for i in range(6):  # wavy legs all around the bottom
        a = math.radians(-90 + 30 + i * 60)
        if abs(math.degrees(a) + 90) < 20:
            continue
        pts = [(math.cos(a) * r, math.sin(a) * r, z) for r, z in ((0.32, 0.25), (0.45, 0.14), (0.58, 0.08), (0.68, 0.1),
                                                                     (0.74, 0.17))]
        _chain(f"{name}_leg{i}_", pts, 0.11, 0.045, body_m, piv)
    ev, pp, br, mouth, smile = _face(name, piv, d, -0.44, 0.82, 0.17, 0.16, -0.475, 0.56, 1.0, cheeks=(0.3, -0.42, 0.62))
    arms = []
    for side in (-1, 1):  # the two front legs are the arms
        sh = empty(f"{name}_sh{side}", (side * 0.36, -0.22, 0.38), piv)
        _chain(f"{name}_arm{side}_", [(side * 0.03, 0, -0.04), (side * 0.08, -0.02, -0.12), (side * 0.12, -0.04, -0.2),
                                      (side * 0.14, -0.08, -0.26)], 0.09, 0.045, body_m, sh)
        arms.append(sh)
    feet = [sphere(f"{name}_foot{s}", 0.1, (s * 0.2, -0.12, 0.06), body_m, root, scale=(1.0, 1.3, 0.5)) for s in (-1, 1)]
    ch.update(eyes=ev, pupils=pp, brows=br, arms=arms, feet=feet, mouth=mouth, smile=smile, top=1.17, head=0.82)


def _elephant(name, d, root, piv, ch):
    body_m = mat(d["body"], 0.6)
    sphere(name + "_body", 0.5, (0, 0, 0.55), body_m, piv, scale=(1.0, 0.92, 1.05), sub=2)
    sphere(name + "_belly", 0.3, (0, -0.33, 0.33), mat(d["belly"], 0.65), piv, scale=(1.0, 0.45, 0.75), sub=2)
    for side in (-1, 1):  # big flappy ears
        e = sphere(f"{name}_ear{side}", 0.34, (side * 0.56, 0.08, 0.78), body_m, piv, scale=(0.95, 0.22, 1.1),
                   rot=(0, 0, side * -0.35))
        sphere(f"{name}_earin{side}", 0.24, (0, -0.06, 0.0), mat(d["ear_in"], 0.6), e, scale=(1, 0.5, 1))
    _chain(name + "_trunk", [(0, -0.44, 0.66), (0, -0.53, 0.6), (0, -0.6, 0.55), (0, -0.66, 0.55), (0, -0.7, 0.6)],
           0.11, 0.065, body_m, piv)
    sphere(name + "_trunktip", 0.06, (0, -0.73, 0.64), mat(d["ear_in"], 0.6), piv, scale=(1, 0.6, 1), sub=0)
    ev, pp, br, mouth, smile = _face(name, piv, d, -0.39, 0.8, 0.2, 0.14, -0.43, 0.37, 0.9, cheeks=(0.3, -0.4, 0.55))
    tl = sphere(name + "_tail", 0.05, (0, 0.47, 0.3), body_m, piv, scale=(0.8, 2.0, 0.8), rot=(0.5, 0, 0))
    sphere(name + "_tailtip", 0.05, (0, 0.06, 0.0), mat("#5A6A8A", 0.8), tl, scale=(1, 0.6, 1))
    arms, feet = _limbs(name, piv, root, body_m, mat(d["feet"], 0.6), fr=0.15)
    ch.update(eyes=ev, pupils=pp, brows=br, arms=arms, feet=feet, mouth=mouth, smile=smile, top=1.15, head=0.8)


def _kid(name, d, root, piv, ch):
    skin, hair = mat(d["skin"], 0.55), mat(d["hair"], 0.7)
    shirt, pants = mat(d["shirt"], 0.6), mat(d["pants"], 0.65)
    for s in (-1, 1):
        cyl(f"{name}_leg{s}", 0.075, 0.24, (s * 0.1, 0, 0.17), pants, root)
    sphere(name + "_torso", 0.25, (0, 0, 0.44), shirt, piv, scale=(1.0, 0.82, 1.05), sub=2)
    sphere(name + "_neck", 0.08, (0, 0, 0.62), skin, piv, sub=0)
    sphere(name + "_head", 0.36, (0, 0, 0.88), skin, piv, sub=2)
    for s in (-1, 1):
        sphere(f"{name}_earh{s}", 0.07, (s * 0.355, 0.0, 0.86), skin, piv, scale=(0.6, 0.9, 1.1))
    sphere(name + "_nose", 0.04, (0, -0.365, 0.81), mat(d["skin"], 0.5), piv, scale=(1.2, 0.8, 0.9), sub=0)
    if d.get("hairdo") == "curly":
        k = 0
        for i in range(7):
            for j in range(9):
                th, ph = 0.15 + i * 0.2, j / 9 * math.tau
                x, y, z = math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)
                if y < -0.55 and z < 0.75:
                    continue  # keep the face free
                sphere(f"{name}_curl{k}", 0.1, (x * 0.36, y * 0.36 + 0.02, 0.9 + z * 0.36), hair, piv, sub=0, seg=16)
                k += 1
    else:
        sphere(name + "_hair", 0.375, (0, 0.06, 0.94), hair, piv, scale=(1.0, 1.0, 0.92), sub=1)
        sphere(name + "_bangs", 0.2, (0, -0.22, 1.14), hair, piv, scale=(1.45, 0.6, 0.45), rot=(0.4, 0, 0))
        for s in (-1, 1):
            sphere(f"{name}_tail{s}", 0.13, (s * 0.4, 0.1, 0.98), hair, piv, scale=(0.8, 0.8, 1.15), rot=(0, s * 0.5, 0))
            sphere(f"{name}_tie{s}", 0.05, (s * 0.33, 0.08, 1.04), mat(d.get("ties", "#FFD23F"), 0.4), piv, sub=0)
    ev, pp, br, mouth, smile = _face(name, piv, d | {"brow": d["hair"]}, -0.3, 0.9, 0.13, 0.1, -0.34, 0.72, 0.75,
                                     cheeks=(0.2, -0.3, 0.77))
    arms = []
    for side in (-1, 1):
        sh = empty(f"{name}_sh{side}", (side * 0.25, 0, 0.53), piv)
        sphere(f"{name}_sleeve{side}", 0.08, (side * 0.03, 0, -0.04), shirt, sh, scale=(1, 1, 1.1), sub=1)
        sphere(f"{name}_arm{side}", 0.055, (side * 0.05, 0, -0.14), skin, sh, scale=(0.9, 0.9, 1.9))
        sphere(f"{name}_hand{side}", 0.06, (side * 0.06, 0, -0.25), skin, sh, sub=1)
        arms.append(sh)
    feet = [sphere(f"{name}_foot{s}", 0.1, (s * 0.1, -0.05, 0.05), mat(d["shoes"], 0.4, coat=0.3), root,
                   scale=(1.0, 1.5, 0.6)) for s in (-1, 1)]
    ch.update(eyes=ev, pupils=pp, brows=br, arms=arms, feet=feet, mouth=mouth, smile=smile, top=1.24, head=0.88)


KINDS = {"robot": _robot, "dino": _dino, "monster": _monster, "octo": _octo, "elephant": _elephant, "kid": _kid}


def make_character(name, x=0.0, y=0.0, z=0.0):
    d = CAST[name]
    root = empty(name, (x, y, z))
    root.scale = (d["size"],) * 3
    piv = empty(name + "_piv", (0, 0, 0), root)  # squash & stretch from the floor
    ch = dict(name=name, root=root, piv=piv, mouth=None, smile=None, size=d["size"])
    if d["kind"] in KINDS:
        KINDS[d["kind"]](name, d, root, piv, ch)
        mouth_set(ch, 1, 0.0)
        accessory(ch, *LOOKS.get(name, ("none", "#FFFFFF")))
        return ch
    if d["kind"] == "bird":
        yel = mat(d["body"], 0.5)
        sphere(name + "_body", 0.34, (0, 0, 0.38), yel, piv, scale=(1, 0.95, 1.08), sub=2)
        if d.get("tuft", True):
            sphere(name + "_tuft", 0.07, (0, 0, 0.76), yel, piv, scale=(0.6, 0.6, 1.6), rot=(0.3, 0, 0))
        sphere(name + "_belly", 0.2 if d.get("belly") is None else 0.25, (0, -0.19, 0.32),
               mat(d.get("belly", "#FFF1B8"), 0.6), piv, scale=(1, 0.5, 0.95), sub=2)
        if d.get("owl"):  # owl: feather discs around the eyes + ear tufts
            for side in (-1, 1):
                sphere(f"{name}_disc{side}", 0.15, (side * 0.12, -0.25, 0.5), mat(d["disc"], 0.7), piv, scale=(1, 0.3, 1))
                cone(f"{name}_etuft{side}", 0.06, 0.0, 0.17, (side * 0.18, 0.0, 0.72), yel, piv, rot=(0, side * 0.4, 0))
        ev, pp, br = eyes(piv, -0.285, 0.5, 0.12, 0.11, d["iris"])
        cone(name + "_beak", 0.07, 0.0, 0.14, (0, -0.33, 0.37), mat(d["beak"], 0.4), piv, rot=(math.radians(90), 0, 0))
        arms = []
        for side in (-1, 1):
            sh = empty(f"{name}_wing{side}", (side * 0.32, 0, 0.4), piv)
            sphere(f"{name}_w{side}", 0.1, (side * 0.04, 0, -0.06), mat(d.get("wing", d["body"]), 0.5), sh,
                   scale=(0.5, 0.9, 1.4), rot=(0, side * 0.3, 0))
            arms.append(sh)
        feet = [sphere(f"{name}_foot{s}", 0.07, (s * 0.12, -0.06, 0.03), mat(d["beak"], 0.4), root, scale=(1, 1.6, 0.5))
                for s in (-1, 1)]
        ch.update(eyes=ev, pupils=pp, brows=br, arms=arms, feet=feet, top=0.85, head=0.5)
        accessory(ch, *LOOKS.get(name, ("none", "#FFFFFF")))
        return ch
    body_m = mat(d["body"], 0.55)
    sq = 0.88 if d.get("eyes_top") else 1.05
    sphere(name + "_body", 0.5, (0, 0, 0.55), body_m, piv, scale=(1.0, 0.92, sq), sub=2)
    sphere(name + "_belly", 0.3, (0, -0.33, 0.38), mat(d["belly"], 0.6), piv, scale=(1.0, 0.45, 0.85), sub=2)
    for side in (-1, 1):
        sphere(f"{name}_cheek{side}", 0.08, (side * 0.3, -0.4, 0.5), mat("#FF8FB1", 0.6), piv, scale=(1, 0.4, 0.7))
    ears = d.get("ears", "round")
    for side in (-1, 1):
        if ears == "round":
            e = sphere(f"{name}_ear{side}", 0.15, (side * 0.3, 0.02, 1.0), mat(d["ear_col"], 0.6) if d.get("ear_col") else body_m,
                       piv, scale=(0.8, 0.6, 1.2), rot=(0, side * 0.5, 0))
            if d.get("ear_in"):
                sphere(f"{name}_earin{side}", 0.09, (0, -0.07, -0.01), mat(d["ear_in"], 0.6), e, scale=(0.8, 0.4, 0.8))
        elif ears == "floppy":
            sphere(f"{name}_ear{side}", 0.17, (side * 0.47, 0.02, 0.8), mat(d.get("ear_col", d["body"]), 0.6), piv,
                   scale=(0.45, 0.7, 1.45), rot=(0, side * -0.35, 0))
        elif ears == "bunny":
            e = sphere(f"{name}_ear{side}", 0.11, (side * 0.17, 0.05, 1.22), body_m, piv, scale=(0.75, 0.5, 2.6),
                       rot=(0, side * 0.22, 0))
            sphere(f"{name}_earin{side}", 0.07, (0, -0.05, 0.0), mat("#FFB3CF", 0.6), e, scale=(0.8, 0.4, 0.85))
        elif ears == "pig":
            cone(f"{name}_ear{side}", 0.13, 0.02, 0.22, (side * 0.3, -0.06, 1.0), mat(d["snout"], 0.6), piv,
                 rot=(-0.5, side * 0.5, 0))
        elif ears == "cat":
            cone(f"{name}_ear{side}", 0.14, 0.02, 0.28, (side * 0.27, 0.0, 1.03), body_m, piv, rot=(0, side * 0.45, 0))
            if d.get("ear_in"):
                cone(f"{name}_earin{side}", 0.08, 0.01, 0.18, (side * 0.265, -0.06, 1.01), mat(d["ear_in"], 0.6), piv,
                     rot=(0, side * 0.45, 0))
    if d.get("tuft"):
        sphere(name + "_tuft", 0.09, (0.04, 0.0, 1.08), body_m, piv, scale=(0.7, 0.7, 1.5), rot=(0, 0.35, 0))
        sphere(name + "_tuft2", 0.07, (-0.06, 0.02, 1.06), body_m, piv, scale=(0.7, 0.7, 1.3), rot=(0, -0.4, 0))
    if d.get("tail"):
        tl = sphere(name + "_tail", 0.1, (0.0, 0.45, 0.25), body_m, piv, scale=(0.8, 1.6, 0.8), rot=(0.6, 0, 0))
        if d.get("tail_tip"):
            sphere(name + "_tailtip", 0.075, (0, 0.08, 0.0), mat(d["tail_tip"], 0.6), tl, scale=(1, 0.8, 1))
    if d.get("patches"):  # panda eye patches
        for side in (-1, 1):
            sphere(f"{name}_patch{side}", 0.14, (side * 0.175, -0.36, 0.72), mat(d["patches"], 0.6), piv,
                   scale=(1.05, 0.35, 1.25), rot=(0, side * 0.35, 0))
    if d.get("ruff"):  # lion mane all around the face
        for i in range(14):
            a = i / 14 * math.tau
            sphere(f"{name}_ruff{i}", 0.17, (math.cos(a) * 0.5, 0.12, 0.6 + math.sin(a) * 0.5), mat(d["ruff"], 0.7), piv,
                   scale=(1, 0.8, 1), sub=1)
    if d.get("horn"):  # unicorn horn + rainbow mane
        cone(name + "_horn", 0.07, 0.0, 0.32, (0, -0.12, 1.15), mat(d["horn"], 0.3, coat=0.6), piv, rot=(0.35, 0, 0))
        for i, c in enumerate(d.get("mane", [])):
            sphere(f"{name}_mane{i}", 0.11, (0.0, 0.1 + i * 0.1, 1.08 - i * 0.12), mat(c, 0.5), piv, scale=(0.8, 1, 1.1))
    if d.get("snout"):  # piggy snout + curly tail
        sn = mat(d["snout"], 0.5)
        cyl(name + "_snout", 0.12, 0.09, (0, -0.47, 0.52), sn, piv, rot=(math.pi / 2, 0, 0), bevel=0.03)
        for side in (-1, 1):
            sphere(f"{name}_nost{side}", 0.025, (side * 0.045, -0.515, 0.52), mat("#B8456E", 0.4), piv, scale=(0.8, 0.5, 1.2),
                   sub=0)
    if d.get("curl_tail"):
        curve_line(name + "_curl", [(0, 0, 0), (0.05, 0.06, 0.06), (0.0, 0.1, 0.12), (-0.06, 0.07, 0.08),
                                    (-0.03, 0.02, 0.05), (0.02, 0.08, 0.02)], 0.022, body_m, piv, (0, 0.46, 0.3))
    if d.get("bee"):  # stripes, see-through wings, antennae, tiny stinger
        st = mat("#2B2B33", 0.6)
        for i, (zz, rr) in enumerate(((0.38, 0.47), (0.2, 0.37))):
            torus(f"{name}_stripe{i}", rr, 0.045, (0, 0, zz), st, piv, scale=(1, 0.92, 1))
        wm = mat("#E3F6FF", 0.05, coat=1.0)
        for side in (-1, 1):
            sphere(f"{name}_bwing{side}", 0.26, (side * 0.32, 0.38, 0.88), wm, piv, scale=(0.55, 0.18, 1.0),
                   rot=(0.3, 0, side * -0.6))
            curve_line(f"{name}_ant{side}", [(0, 0, 0), (side * 0.06, -0.04, 0.14), (side * 0.13, -0.08, 0.24)], 0.014, st,
                       piv, (side * 0.12, -0.05, 1.02))
            sphere(f"{name}_antb{side}", 0.04, (side * 0.25, -0.13, 1.26), st, piv, sub=0)
        cone(name + "_sting", 0.04, 0.0, 0.1, (0, 0.5, 0.3), st, piv, rot=(-math.pi / 2, 0, 0))
    if d.get("patch"):  # puppy eye patch
        sphere(name + "_patch", 0.15, (0.17, -0.37, 0.76), mat(d["patch"], 0.6), piv, scale=(1.1, 0.35, 1.2))
    if d.get("eyes_top"):
        ev, pp, br = eyes(piv, -0.22, 1.0, 0.2, 0.17, d["iris"], mat(d["brow"], 0.5))
        for e in ev:  # eye bumps on top (frog-ish)
            sphere(e.name + "_lid", 0.2, (0, 0.04, -0.02), body_m, e, scale=(1, 0.8, 0.9))
    else:
        ev, pp, br = eyes(piv, -0.405, 0.74, 0.175, 0.165, d["iris"], mat(d["brow"], 0.5))
    if d.get("nose"):
        sphere(name + "_nose", 0.05, (0, -0.48, 0.565), mat("#3A2A2A", 0.25, coat=1.0), piv, scale=(1.3, 0.7, 0.85))
    my, mz = d.get("mouth", (-0.455, 0.44))
    mouth = sphere(name + "_mouth", 0.1, (0, my, mz), mat("#5A1020", 0.4), piv, scale=(1.2, 0.35, 0.05))
    sphere(name + "_tongue", 0.06, (0, -0.02, -0.04), mat("#FF5A7A", 0.5), mouth, scale=(1, 0.8, 0.5))
    w = 0.085
    smile = curve_line(name + "_smile", [(-w, 0, w * 0.45), (0, 0, -w * 0.25), (w, 0, w * 0.45)], 0.014,
                       mat("#5A1020", 0.4), piv, (0, my - 0.02, mz + 0.015))
    arms = []
    for side in (-1, 1):
        sh = empty(f"{name}_sh{side}", (side * 0.45, -0.05, 0.55), piv)
        sphere(f"{name}_arm{side}", 0.08, (side * 0.06, 0, -0.14), body_m, sh, scale=(0.9, 0.9, 2.0))
        arms.append(sh)
    feet = [sphere(f"{name}_foot{s}", 0.14, (s * 0.2, -0.08, 0.06), mat(d["feet"], 0.5), root, scale=(1.0, 1.35, 0.55))
            for s in (-1, 1)]
    ch.update(eyes=ev, pupils=pp, brows=br, arms=arms, feet=feet, mouth=mouth, smile=smile, top=1.15,
              head=1.0 if d.get("eyes_top") else 0.74)
    mouth_set(ch, 1, 0.0)
    accessory(ch, *LOOKS.get(name, ("none", "#FFFFFF")))
    return ch


def accessory(ch, kind, color):
    """A little outfit piece so the same friends look a bit different from short to short."""
    if not kind or kind == "none":
        return
    name, piv, d = ch["name"], ch["piv"], CAST[ch["name"]]
    bird = d["kind"] == "bird"
    top = d.get("acc_top") or (0.72 if bird else (0.96 if d.get("eyes_top") else 1.06))
    c, m2 = mat(color, 0.4, coat=0.3), mat("#FFFFFF", 0.4)
    k = 0.75 if bird or d.get("eyes_top") else 1.0
    if kind == "party_hat":
        h = empty(name + "_hat", (0.05, 0.0, top - 0.04), piv)
        h.rotation_euler = (0, 0.22, 0)
        cone(name + "_hatc", 0.14 * k, 0.01, 0.34 * k, (0, 0, 0.17 * k), checker(color, "#FFFFFF", 5.0, 0.4), h)
        sphere(name + "_hatpom", 0.05 * k, (0, 0, 0.35 * k), m2, h, sub=1)
    elif kind == "crown":
        h = empty(name + "_crown", (0, 0.0, top - 0.03), piv)
        gold = mat("#FFD23F", 0.2, coat=1.0, metal=0.6)
        cyl(name + "_crb", 0.15 * k, 0.07 * k, (0, 0, 0.035 * k), gold, h, bevel=0.01)
        for i in range(5):
            a = i / 5 * math.tau
            cone(f"{name}_crp{i}", 0.04 * k, 0.0, 0.1 * k, (math.cos(a) * 0.13 * k, math.sin(a) * 0.13 * k, 0.11 * k), gold, h)
        sphere(name + "_crgem", 0.03 * k, (0, -0.15 * k, 0.04 * k), mat(color, 0.1, coat=1.0), h, sub=0)
    elif kind == "cap":
        if d.get("ears") in ("bunny", "cat") or d.get("eyes_top") or d.get("no_cap"):
            kind = "bow"  # a cap would hide the ears - wear a bow instead
        else:
            h = empty(name + "_cap", (0, 0.0, top - 0.12), piv)
            sphere(name + "_capd", 0.3 * k, (0, 0, 0), c, h, scale=(1, 1, 0.55), sub=2)
            cyl(name + "_capb", 0.17 * k, 0.025, (0, -0.27 * k, -0.01), c, h, scale=(1.15, 1.0, 1))
            sphere(name + "_capt", 0.035 * k, (0, 0, 0.165 * k), m2, h, sub=0)
    if kind == "bow":
        h = empty(name + "_bow", (0.2 * k, -0.05, top - 0.06), piv)
        h.rotation_euler = (0, -0.4, 0)
        for side in (-1, 1):
            sphere(f"{name}_bowl{side}", 0.075 * k, (side * 0.07 * k, 0, 0), c, h, scale=(1.2, 0.5, 0.8),
                   rot=(0, side * 0.4, 0))
        sphere(name + "_bowk", 0.035 * k, (0, -0.01, 0), c, h, sub=0)
    elif kind == "flower":
        h = empty(name + "_flw", (-0.2 * k, -0.08, top - 0.07), piv)
        h.rotation_euler = (math.radians(70), 0, 0.3)
        for i in range(5):
            a = i / 5 * math.tau
            sphere(f"{name}_pet{i}", 0.045 * k, (math.cos(a) * 0.05 * k, math.sin(a) * 0.05 * k, 0), c, h,
                   scale=(1, 1, 0.4), sub=0)
        sphere(name + "_flc", 0.03 * k, (0, 0, 0.01), mat("#FFD23F", 0.4), h, sub=0)
    elif kind == "bowtie":
        h = empty(name + "_tie", (0, -0.31, 0.2) if bird else (0, -0.22, 0.57) if d["kind"] == "kid" else (0, -0.43, 0.27), piv)
        for side in (-1, 1):
            cone(f"{name}_tie{side}", 0.06, 0.012, 0.09, (side * 0.045, 0, 0), c, h, rot=(0, side * math.pi / 2, 0),
                 scale=(1, 0.5, 1))
        sphere(name + "_tiek", 0.025, (0, -0.01, 0), c, h, sub=0)


# ------------------------------------------------------------------ props
KENNEY_FOOD = {"donut": ["donut*"], "cupcake": ["cupcake*"], "watermelon": ["watermelon*"], "pizza": ["pizza*"],
               "strawberry": ["strawberry*"], "pie": ["pie*"], "burger": ["burger*"]}
KENNEY_TREATS = {"gingerbread": ("holiday", ["gingerbread-*"])}
FOOD_H = {"gingerbread": 0.24, "donut": 0.12, "cupcake": 0.22, "watermelon": 0.16, "pizza": 0.08, "strawberry": 0.14, "pie": 0.12,
          "burger": 0.2}


def make_prop(kind, loc, parent=None, name=None):
    name = name or kind
    root = empty(name, loc, parent)
    v = VAR
    if kind in KENNEY_FOOD or kind in KENNEY_TREATS:  # toy-style food from the free Kenney kits, on a little plate
        files = kenney_find(*KENNEY_TREATS[kind]) if kind in KENNEY_TREATS else kenney_find("food", KENNEY_FOOD[kind])
        if files:
            cyl(name + "_plate", 0.2, 0.02, (0, 0, 0.01), WHITE, root, bevel=0.008)
            if kenney(v.choice(files[:3]), name + "_k", (0, 0, 0.02), FOOD_H[kind], root, rot_z=v.uniform(-0.6, 0.6)):
                return root
        kind = "cake"  # kit missing -> our own cake
    if kind == "cake":
        body, icing = v.choice([("#FFB3CF", "#FFFFFF"), ("#8A5A3C", "#FFB3CF"), ("#FFE27A", "#FFFFFF"),
                                ("#B7A6FF", "#FFF4D6"), ("#9EF0C0", "#FFFFFF"), ("#FFFFFF", "#6B3E1F")])
        cyl(name + "_plate", 0.24, 0.02, (0, 0, 0.01), WHITE, root, bevel=0.008)
        cyl(name + "_body", 0.19, 0.16, (0, 0, 0.1), mat(body, 0.5), root, bevel=0.03)
        cyl(name + "_icing", 0.2, 0.05, (0, 0, 0.19), mat(icing, 0.3, coat=0.5), root, bevel=0.025)
        for i in range(10):
            a = i / 10 * math.tau
            sphere(f"{name}_drip{i}", 0.03, (math.cos(a) * 0.195, math.sin(a) * 0.195, 0.155),
                   mat(icing, 0.3, coat=0.5), root, scale=(1, 1, 1.6), sub=0)
        for i in range(8):  # sprinkles
            a = i / 8 * math.tau + 0.3
            sphere(f"{name}_spr{i}", 0.013, (math.cos(a) * 0.12, math.sin(a) * 0.12, 0.218),
                   mat(("#FF4D6D", "#4DA6FF", "#FFD23F", "#5CCB6B")[i % 4], 0.4), root, scale=(1.8, 0.7, 0.7),
                   rot=(0, 0, a), sub=0)
        sphere(name + "_cherry", 0.045, (0, 0, 0.255), mat("#E0102F", 0.2, coat=1), root, sub=1)
    elif kind == "icecream":
        cone(name + "_cone", 0.02, 0.1, 0.26, (0, 0, 0.13), checker("#E8B36A", "#C98B3F", 14, 0.6), root)
        sc1, sc2 = v.sample(["#FF9EC4", "#FFF4D6", "#8A5A3C", "#9EF0C0", "#B7A6FF", "#FFE27A", "#8FD3FF"], 2)
        sphere(name + "_s1", 0.105, (0, 0, 0.29), mat(sc1, 0.4, coat=0.3), root)
        sphere(name + "_s2", 0.09, (0, 0, 0.42), mat(sc2, 0.4, coat=0.3), root)
        sphere(name + "_cherry", 0.035, (0, 0, 0.53), mat("#E0102F", 0.2, coat=1), root, sub=1)
    elif kind == "cookie":
        cyl(name + "_plate", 0.2, 0.02, (0, 0, 0.01), WHITE, root, bevel=0.008)
        cyl(name + "_body", 0.15, 0.04, (0, 0, 0.045), mat("#D99A4E", 0.7), root, bevel=0.015)
        for i, (cx, cy) in enumerate(((0.05, 0.03), (-0.06, 0.04), (0.0, -0.07), (-0.03, -0.02), (0.08, -0.05))):
            sphere(f"{name}_chip{i}", 0.022, (cx, cy, 0.068), mat("#4A2A12", 0.5), root, sub=0)
    elif kind == "apple":
        sphere(name + "_body", 0.13, (0, 0, 0.13), mat(v.choice(["#E8232F", "#E8232F", "#7ED957", "#FFC93D"]), 0.25, coat=1),
               root, scale=(1, 1, 0.9))
        cyl(name + "_stem", 0.012, 0.07, (0, 0, 0.27), mat("#6B4423", 0.6), root)
        sphere(name + "_leaf", 0.04, (0.04, 0, 0.27), mat("#3FB64E", 0.5), root, scale=(1.4, 0.3, 0.6), rot=(0, -0.5, 0))
    elif kind == "ball":
        c1, c2 = v.choice([("#FF3B4E", "#FFFFFF"), ("#4DA6FF", "#FFD23F"), ("#5CCB6B", "#FFFFFF"), ("#B57BFF", "#FFE27A"),
                           ("#FF8A3D", "#FFFFFF")])
        sphere(name + "_body", 0.18, (0, 0, 0.18), checker(c1, c2, 2.0, 0.3, 0.6), root, sub=2)
    elif kind == "balloon":
        bc = PROP_COLOR or v.choice(["#FF3B6E", "#4DA6FF", "#FFD23F", "#5CCB6B", "#B57BFF", "#FF8A3D"])
        root["color"] = bc
        b = sphere(name + "_body", 0.24, (0, 0, 0.0), mat(bc, 0.15, coat=1.0), root, scale=(1, 1, 1.2), sub=2)
        cone(name + "_knot", 0.035, 0.0, 0.05, (0, 0, -0.29), mat(bc, 0.2), root, rot=(math.pi, 0, 0))
        curve_line(name + "_string", [(0, 0, -0.3), (0.03, 0, -0.55), (-0.02, 0, -0.85)], 0.006, mat("#FFFFFF", 0.5), root)
    elif kind == "gift":
        wc, rc = v.choice([("#4DA6FF", "#FFD23F"), ("#FF4D6D", "#FFFFFF"), ("#5CCB6B", "#FF4D6D"), ("#B57BFF", "#FFD23F"),
                           ("#FFD23F", "#FF4D6D"), ("#FF9EC4", "#4DA6FF")])
        wall = mat(wc, 0.4, coat=0.3)
        s = 0.62
        box(name + "_bottom", (s, s, 0.04), (0, 0, 0.02), wall, root, bevel=0.01)
        for i, (px, py, sx, sy) in enumerate(((0, -s / 2, s, 0.04), (0, s / 2, s, 0.04), (-s / 2, 0, 0.04, s), (s / 2, 0, 0.04, s))):
            box(f"{name}_wall{i}", (sx, sy, s), (px, py, s / 2), wall, root, bevel=0.012)
        rib = mat(rc, 0.3, coat=0.5)
        box(name + "_rib1", (0.1, 0.05, s), (0, -s / 2 - 0.02, s / 2), rib, root, bevel=0.01)
        lid = empty(name + "_lid", (0, 0, s), root)
        box(name + "_lidbox", (s + 0.08, s + 0.08, 0.12), (0, 0, 0.06), wall, lid, bevel=0.03)
        box(name + "_lidrib", (0.1, s + 0.1, 0.13), (0, 0, 0.06), rib, lid, bevel=0.02)
        for side in (-1, 1):
            sphere(f"{name}_bow{side}", 0.1, (side * 0.09, 0, 0.19), rib, lid, scale=(1.1, 0.5, 0.7), rot=(0, side * 0.5, 0))
        root["lid"] = lid.name
    elif kind == "peel":
        y = mat("#FFE135", 0.4)
        for i, a in enumerate((0, 2.1, 4.2)):
            sphere(f"{name}_p{i}", 0.06, (math.cos(a) * 0.09, math.sin(a) * 0.09, 0.025), y, root,
                   scale=(2.2, 0.8, 0.35), rot=(0, 0, a))
        sphere(name + "_c", 0.05, (0, 0, 0.05), y, root, scale=(1, 1, 1.4))
        sphere(name + "_tip", 0.02, (0, 0, 0.12), mat("#5A3A1A", 0.6), root)
    elif kind == "bush":
        g = mat(v.choice(["#45B85A", "#3FA64E", "#5CC26A"]), 0.75)
        for j, (ox, oz, rr) in enumerate(((0, 0.32, 0.42), (0.36, 0.25, 0.32), (-0.34, 0.24, 0.3), (0.12, 0.6, 0.28))):
            sphere(f"{name}_{j}", rr, (ox, 0, oz), g, root, sub=1)
        if THEME.get("set") == "snow":
            for j, (ox, oz, rr) in enumerate(((0, 0.62, 0.3), (0.12, 0.8, 0.2))):
                sphere(f"{name}_snow{j}", rr, (ox, 0, oz), mat("#FFFFFF", 0.6), root, scale=(1.1, 1.1, 0.5), sub=1)
        for j in range(5):
            sphere(f"{name}_berry{j}", 0.035, (-0.3 + j * 0.15, -0.35, 0.3 + (j % 2) * 0.15),
                   mat(v.choice(["#FF4D6D", "#4DA6FF", "#FFD23F"]) if j == 0 else "#FF4D6D", 0.3, coat=1), root, sub=0)
    return root


def make_table(loc, color="#FF7AA8"):
    color = VAR.choice([color, "#FF7AA8", "#7FD1B9", "#FFD23F", "#8FD3FF", "#B7A6FF", "#FF8A3D"])
    t = empty("table", loc)
    cyl("table_leg", 0.06, 0.62, (0, 0, 0.31), mat("#FFFFFF", 0.4), t)
    cyl("table_foot", 0.2, 0.03, (0, 0, 0.015), mat("#FFFFFF", 0.4), t, bevel=0.01)
    cyl("table_top", 0.42, 0.06, (0, 0, 0.64), mat(color, 0.35, coat=0.3), t, bevel=0.02)
    return t


# ------------------------------------------------------------------ sets
SKY = {"day": ("#D8F1FF", "#5EB8FF"), "sunset": ("#FFD6A8", "#7A8CFF"), "indoor": ("#FFF4E6", "#FFE0C2"),
       "morning": ("#FFE9F2", "#8FD0FF"), "golden": ("#FFE8B0", "#6FB6FF"), "snow": ("#EEF6FF", "#9CC8F2"),
       "space": ("#3A2F7A", "#0A0C2A"), "underwater": ("#6FE3EC", "#0B4F96"), "candy": ("#FFC2E3", "#8E7BEF")}
SUN = {"sunset": (1, 0.78, 0.6), "golden": (1, 0.87, 0.68), "morning": (1, 0.92, 0.9), "snow": (0.95, 0.97, 1), "space": (0.92, 0.93, 1),
       "underwater": (0.72, 0.93, 1), "candy": (1, 0.93, 0.96)}
SEASON_CROWNS = {"summer": ["#3FB64E", "#47B856", "#3CA84C"], "spring": ["#FF9EC4", "#FFB8D6", "#47B856"],
                 "autumn": ["#FF8A3D", "#E8574F", "#FFC23D"]}
GRASS = ["#6CCB5F", "#73D165", "#7AD36A", "#5FC27A", "#8BD65A"]
PASTELS = ["#FF9EC4", "#8FD3FF", "#FFE27A", "#B7A6FF", "#9EF0C0", "#FFC09F", "#A0E7E5", "#FFB5E8", "#C5F27A"]


def _clouds(z0=5.5, y=14):
    cloud = mat("#FFFFFF", 0.9)
    for i, (cx, cz) in enumerate(((-3.5, z0), (1.5, z0 + 0.9), (5.5, z0 - 0.3))):
        for j, (ox, oz, rr) in enumerate(((0, 0, 0.7), (0.7, -0.15, 0.5), (-0.7, -0.15, 0.5), (0.3, 0.35, 0.5))):
            sphere(f"cloud{i}{j}", rr, (cx + ox, y, cz + oz), cloud, scale=(1.2, 0.6, 1), sub=1)


def _trees(xs, y, crown=None):
    for i, tx in enumerate(xs):
        c = crown or _crown(i)
        cyl(f"trunk{y}{i}", 0.09, 0.9, (tx, y, 0.45), mat("#9A6A43", 0.7))
        sphere(f"crown{y}{i}", 0.55, (tx, y, 1.25), mat(c, 0.7), sub=1)
        sphere(f"crownb{y}{i}", 0.38, (tx + 0.3, y + 0.1, 1.05), mat(c, 0.7), sub=1)


def _crown(i):
    cols = SEASON_CROWNS.get(THEME.get("season", "summer"), SEASON_CROWNS["summer"])
    return cols[i % len(cols)]


def _pines(xs, y, snowy=True):
    for i, tx in enumerate(xs):
        cyl(f"ptrunk{y}{i}", 0.08, 0.4, (tx, y, 0.2), mat("#8A5A3C", 0.7))
        for j, (r, z) in enumerate(((0.62, 0.55), (0.48, 1.0), (0.32, 1.4))):
            cone(f"pine{y}{i}{j}", r, 0.0, 0.7, (tx, y, z + 0.1), mat("#2E8B57", 0.7))
            if snowy:
                cone(f"psnow{y}{i}{j}", r * 0.55, 0.0, 0.32, (tx, y, z + 0.33), mat("#FFFFFF", 0.6))


def _flowers(n, y0, y1, xs=(-4, 4), rnd=None):
    rnd = rnd or random.Random(3)
    cols = ("#FF6B8B", "#FFFFFF", "#FFD53D", "#B57BFF", "#FF8A3D", "#4DA6FF", "#FF9EC4")
    for i in range(n):
        x, y = rnd.uniform(*xs), rnd.uniform(y0, y1)
        cyl(f"stem{i}", 0.008, 0.14, (x, y, 0.07), mat("#3FA64E", 0.6))
        sphere(f"flower{i}", 0.045, (x, y, 0.15), mat(cols[i % len(cols)], 0.5), sub=0, scale=(1, 1, 0.6))


DRESS = {  # free Kenney Nature Kit pieces placed behind the action (they never block the characters)
    "park": ([(-3.8, 1.9), (-1.0, 2.9), (-0.4, 3.5), (-4.6, 3.0), (5.2, 2.0), (-3.0, 3.7), (0.6, 3.9)],
             ["flower_*", "mushroom_*", "plant_bush*", "rock_small*", "stump_*", "grass*"]),
    "playground": ([(-4.3, 2.2), (-0.8, 3.0), (0.3, 2.6), (3.2, 2.2), (5.6, 3.4), (-1.6, 4.6)],
                   ["flower_*", "plant_bush*", "grass*", "mushroom_*"]),
    "street": ([(-4.4, 2.25), (-1.8, 2.25), (0.7, 2.25), (3.0, 2.25), (5.2, 2.25), (-5.6, 2.25)],
               ["flower_*", "plant_bush*", "grass*"]),
    "beach": ([(-4.2, 3.2), (4.3, 3.6), (0.4, 4.2), (-0.9, 3.8)], ["rock_small*", "rock_tall*", "plant_bush*"]),
    "snow": ([(-4.3, 2.6), (0.2, 3.0), (4.5, 2.5), (-1.0, 4.0)], ["rock_small*", "stump_*", "log*"]),
}


PETS = {  # free Kenney Cube Pets that hop around in the background
    "park": ["bunny", "chick", "deer", "fox", "hog", "cow", "pig", "dog", "cat", "koala", "beaver"],
    "playground": ["dog", "cat", "bunny", "chick", "pig"], "street": ["dog", "cat", "bunny"],
    "beach": ["crab", "parrot", "crab"], "pirate": ["parrot", "crab", "monkey"], "snow": ["penguin", "polar"],
    "christmas": ["penguin", "polar", "deer"], "space": [], "bedroom": ["cat", "dog"], "livingroom": ["cat", "dog"],
    "farm": ["cow", "pig", "chick", "hog", "bunny"], "camping": ["deer", "fox", "beaver", "bunny"],
    "castle": ["deer", "bunny", "dog"], "underwater": ["crab"], "candy": ["bunny", "chick", "pig"],
    "market": ["dog", "cat", "chick"], "desert": [], "jungle": ["monkey", "parrot", "koala", "deer"],
}
PET_SPOTS = {"bedroom": [(0.6, 3.1)], "livingroom": [(1.3, 2.7)], "beach": [(-1.6, 3.0), (3.3, 3.2)],
             "pirate": [(-1.6, 3.0), (3.3, 3.2)]}


def _pets(kind, rnd):
    names = PETS.get(kind) or []
    files = kenney_find("pets", [f"animal-{n}.glb" for n in names])
    if not files:
        return
    spots = PET_SPOTS.get(kind, [(-2.9, 3.0), (2.8, 3.3)])
    for i, (x, y) in enumerate(spots[:rnd.choice((1, 2))]):
        o = kenney(rnd.choice(files), f"pet{i}", (x + rnd.uniform(-0.3, 0.3), y, 0), 0.42 if kind in ("bedroom", "livingroom") else 0.5,
                   rot_z=rnd.uniform(-0.5, 0.5))
        if o:
            bob(o, phase=rnd.randint(0, 30), height=0.08, every=rnd.randint(36, 60))


def _dress(kind, rnd):
    try:
        _pets(kind, random.Random(rnd.random()))
    except Exception as e:  # noqa: BLE001
        print("pets skipped:", e)
    kind = {"pirate": "beach", "christmas": "snow"}.get(kind, kind)
    spots, pats = DRESS.get(kind, ([], []))
    if THEME.get("season") == "autumn" and kind in ("park", "playground", "street"):
        pats = pats + ["crop_pumpkin*", "mushroom_*"]
    files = kenney_find("nature", pats)
    if not files:
        return
    for i, (x, y) in enumerate(spots):
        f = rnd.choice(files)
        b = os.path.basename(f).lower()
        h = 0.5 if "bush" in b else 0.35 if ("stump" in b or "log" in b or "rock" in b or "pumpkin" in b) else 0.28
        kenney(f, f"dress{i}", (x + rnd.uniform(-0.2, 0.2), y + rnd.uniform(-0.15, 0.15), 0), h * rnd.uniform(0.85, 1.2),
               rot_z=rnd.uniform(0, math.tau))


# ------------------------------------------------------------------ more places (procedural + free Kenney kits)
def _hay(name, loc, r=0.32):
    cyl(name, r, 0.5, loc, mat("#F2C94C", 0.9), rot=(math.radians(90), 0, 0.3))


def _set_farm(pal, rnd, sky, grass):
    box("ground", (40, 40, 0.2), (0, 6, -0.1), mat(grass, 0.85), bevel=0)
    box("path", (1.4, 12, 0.02), (1.2, 6, 0.005), mat("#D9B27A", 0.9), bevel=0)
    barn = empty("barn", (2.8, 5.0, 0))
    red = mat(pal.choice(["#D9433B", "#E8574F", "#C93A4A"]), 0.6)
    box("barn_body", (2.4, 1.8, 1.7), (0, 0, 0.85), red, barn, bevel=0.06)
    for side in (-1, 1):
        box(f"barn_roof{side}", (2.6, 1.15, 0.12), (0, side * 0.45, 1.95), mat("#5A3A2A", 0.6), barn,
            rot=(side * math.radians(-38), 0, 0), bevel=0.03)
    box("barn_door", (0.9, 0.06, 1.1), (0, -0.92, 0.55), mat("#FFFFFF", 0.5), barn, bevel=0.02)
    box("barn_doorin", (0.75, 0.06, 0.95), (0, -0.94, 0.5), red, barn, bevel=0.02)
    for a in (-1, 1):
        box(f"barn_x{a}", (0.06, 0.04, 1.15), (0, -0.98, 0.5), mat("#FFFFFF", 0.5), barn, rot=(0, a * 0.68, 0), bevel=0.01)
    box("barn_win", (0.42, 0.06, 0.36), (0, -0.92, 1.45), mat("#FFFFFF", 0.5), barn, bevel=0.02)
    for i, (hx, hy, hz) in enumerate(((-2.9, 3.3, 0.32), (-2.3, 3.4, 0.32), (-2.6, 3.35, 0.9))):
        _hay(f"hay{i}", (hx, hy, hz))
    for i in range(-5, 5):
        if not kk("nature", ["fence_simple.glb"], f"fence{i}", (i * 1.0 + 0.5, 2.6, 0), width=1.0):
            box(f"fencep{i}", (0.08, 0.06, 0.5), (i * 1.0, 2.6, 0.25), mat("#FFFFFF", 0.5), bevel=0.02)
    for i in range(6):
        kk("nature", ["crops_cornstaged.glb", "crops_wheatstageb.glb"], f"crop{i}", (-4.4 + i * 0.6, 6.0, 0), 1.1, rnd=pal)
    for i, (px, py) in enumerate(((-1.4, 3.4), (-0.6, 3.8))):
        kk("nature", ["crop_pumpkin.glb", "crop_melon.glb"], f"pump{i}", (px, py, 0), 0.35, rnd=pal)
    kk("nature", ["tree_oak.glb", "tree_default.glb"], "otree", (-4.4, 5.2, 0), 3.0, rnd=pal)
    kk("toycar", ["vehicle-truck.glb", "vehicle-monster-truck.glb"], "tractor", (4.6, 3.4, 0), width=1.0, rot_z=-0.6, rnd=pal)
    _clouds()


def _flame(name, loc):
    root = empty(name, loc)
    for i, (r, h, c) in enumerate(((0.16, 0.42, "#FF7A1A"), (0.1, 0.32, "#FFD23F"))):
        f = cone(f"{name}{i}", r, 0.0, h, (0, 0, h / 2), mat(c, 0.5, emit=4 - i), root)
        for k, fr in enumerate(range(1, 400, 5)):
            key(f, "scale", fr, (1, 1, 0.85 + 0.3 * ((k * 7 + i * 3) % 5) / 4))
    lt = bpy.data.lights.new(name + "_l", "POINT")
    lt.energy, lt.color = 90, (1, 0.6, 0.3)
    o = bpy.data.objects.new(name + "_l", lt)
    sc.collection.objects.link(o)
    o.location = (loc[0], loc[1], loc[2] + 0.5)
    return root


def _set_camping(pal, rnd, sky, grass):
    box("ground", (40, 40, 0.2), (0, 6, -0.1), mat(pal.choice(["#5FAE57", "#64B85A", "#58A65A"]), 0.9), bevel=0)
    kk("nature", ["tent_detailedopen.glb", "tent_smallopen.glb"], "tent", (-2.5, 3.4, 0), width=1.7, rot_z=0.3, rnd=pal)
    kk("nature", ["tent_smallclosed.glb", "tent_detailedclosed.glb"], "tent2", (3.0, 4.4, 0), width=1.3, rot_z=-0.4, rnd=pal)
    if kk("nature", ["campfire_logs.glb", "campfire_stones.glb"], "fire", (0.9, 2.7, 0), width=0.7, rnd=pal):
        _flame("flame", (0.9, 2.7, 0.08))
    kk("nature", ["log.glb", "log_large.glb"], "seatlog", (1.9, 2.3, 0), width=1.0, rot_z=0.2, rnd=pal)
    for i, (tx, ty) in enumerate(((-4.3, 5.4), (-1.0, 6.2), (1.6, 6.6), (4.6, 5.8), (-3.0, 7.4), (3.2, 7.8))):
        kk("nature", ["tree_pinetall*", "tree_pineround*", "tree_pinedefault*"], f"pine{i}", (tx, ty, 0),
           rnd.uniform(2.6, 3.6), rnd=pal)
    for i in range(5):
        kk("nature", ["mushroom_*"], f"mush{i}", (rnd.uniform(-4, 4), rnd.uniform(2.4, 4.0), 0), 0.25, rnd=pal)
    kk("nature", ["canoe.glb"], "canoe", (-0.6, 4.6, 0), width=1.6, rot_z=0.3)
    _clouds()
    return "golden" if sky == "day" else sky


def _tower(prefix, parts, loc, w, rnd):
    z, last = 0.0, None
    for p in parts:
        o = kk("castle", [p], f"{prefix}_{p[:12]}", (loc[0], loc[1], z), width=w, rnd=rnd)
        if not o:
            return last
        z, last = top(o), o
    return last


def _set_castle(pal, rnd, sky, grass):
    box("ground", (40, 40, 0.2), (0, 6, -0.1), mat(grass, 0.85), bevel=0)
    box("moat", (30, 1.2, 0.02), (0, 6.2, 0.006), mat("#4FB3FF", 0.05, coat=1), bevel=0)
    hexa = ["tower-hexagon-base.glb", "tower-hexagon-mid.glb", "tower-hexagon-roof.glb"]
    sq = ["tower-square-base.glb", "tower-square-mid-windows.glb",
          pal.choice(["tower-square-top-roof-high.glb", "tower-square-top-roof.glb"])]
    _tower("tl", hexa, (-2.8, 7.4), 1.6, pal)
    _tower("tr", sq, (2.8, 7.4), 1.5, pal)
    for i, x in enumerate((-1.6, -0.55, 0.55, 1.6)):
        kk("castle", ["wall-doorway.glb" if i in (1, 2) else "wall.glb"], f"cwall{i}", (x, 7.4, 0), width=1.1)
    for i, (fx, fy) in enumerate(((-1.4, 4.0), (1.5, 4.2))):
        kk("castle", ["flag-banner-long.glb", "flag-wide.glb", "flag.glb"], f"cflag{i}", (fx, fy, 0), 1.6, rnd=pal)
    for i, (tx, ty) in enumerate(((-4.4, 4.0), (4.5, 4.4), (-0.2, 9.0))):
        kk("castle", ["tree-large.glb", "tree-small.glb"], f"ctree{i}", (tx, ty, 0), 2.2, rnd=pal)
    _flowers(18, 1.8, 3.6, rnd=rnd)
    _clouds()


def _set_underwater(pal, rnd, sky, grass):
    box("ground", (40, 40, 0.2), (0, 6, -0.1), mat(pal.choice(["#F2DDA8", "#EED6A0", "#F5E3B5"]), 0.9), bevel=0)
    for i, (hx, hr) in enumerate(((-6, 4), (1, 5.5), (7.5, 4.5))):
        sphere(f"dune{i}", hr, (hx, 14, -hr * 0.6), mat("#3E9CC2", 0.9), scale=(1.6, 1, 1), sub=1)
    coral = ["#FF7A8A", "#FFB547", "#B57BFF", "#FF8FC8", "#5CE0C8"]
    for i in range(7):
        x, y, c = rnd.uniform(-4.5, 4.5), rnd.uniform(3.0, 5.5), mat(pal.choice(coral), 0.5)
        root = empty(f"coral{i}", (x, y, 0))
        for j in range(rnd.randint(3, 5)):
            a = rnd.uniform(-0.6, 0.6)
            h = rnd.uniform(0.4, 1.0)
            cyl(f"coral{i}_{j}", 0.06, h, (math.sin(a) * h * 0.4, 0, h / 2), c, root, rot=(0, a, 0))
            sphere(f"coraltip{i}_{j}", 0.09, (math.sin(a) * h * 0.8, 0, h), c, root)
    weed = mat("#3FB64E", 0.6)
    for i in range(10):
        x, y = rnd.uniform(-4.5, 4.5), rnd.uniform(2.6, 5.0)
        w = empty(f"weed{i}", (x, y, 0))
        h = rnd.uniform(0.8, 1.6)
        cyl(f"weed{i}s", 0.05, h, (0, 0, h / 2), weed, w, scale=(1.4, 0.5, 1))
        ph = rnd.randint(0, 19)
        for k, f in enumerate(range(1 - ph, 400, 20)):
            key(w, "rotation_euler", f, (0, math.radians(8 if k % 2 else -8), 0))
    kk("pirate", ["chest.glb"], "uchest", (2.3, 3.0, 0), 0.5, rot_z=-0.4)
    for i in range(6):
        sphere(f"ushell{i}", 0.06, (rnd.uniform(-3.5, 3.5), rnd.uniform(1.0, 3.0), 0.02),
               mat(pal.choice(["#FFB3CF", "#FFFFFF", "#FFD27A"]), 0.5), scale=(1, 0.8, 0.5))
    fish = kenney_find("pets", ["animal-fish.glb"])
    cols = ["#FF8A3D", "#FFD23F", "#4DA6FF", "#FF4D8A", "#5CCB6B"]
    for i in range(4):
        y, z, d = rnd.uniform(2.5, 5.0), rnd.uniform(0.9, 2.4), rnd.choice((-1, 1))
        o = kenney(fish[0], f"fish{i}", (0, y, z), 0.35, rot_z=-d * math.pi / 2) if fish else None
        if o is None:
            o = empty(f"fish{i}", (0, y, z))
            sphere(f"fishb{i}", 0.14, (0, 0, 0), mat(cols[i % 5], 0.4), o, scale=(1.4, 0.6, 1))
            cone(f"fisht{i}", 0.1, 0.0, 0.16, (-d * 0.22, 0, 0), mat(cols[i % 5], 0.4), o, rot=(0, d * math.pi / 2, 0))
        x0 = rnd.uniform(-5, 0) if d > 0 else rnd.uniform(0, 5)
        key(o, "location", 1, (x0, y, z), "LINEAR")
        key(o, "location", 400, (x0 + d * 9, y, z + rnd.uniform(-0.3, 0.3)), "LINEAR")
    bub = mat("#E8FAFF", 0.05, coat=1.0)
    for i in range(14):
        x, y, z0 = rnd.uniform(-4, 4), rnd.uniform(1.5, 4.5), rnd.uniform(-2, 0)
        b = sphere(f"ubub{i}", rnd.uniform(0.03, 0.07), (x, y, z0), bub, sub=0)
        key(b, "location", 1, (x, y, z0), "LINEAR")
        key(b, "location", 168, (x + rnd.uniform(-0.3, 0.3), y, z0 + 5.5), "LINEAR")
    return "underwater"


def _lolly(name, loc, h, c1, c2):
    root = empty(name, loc)
    cyl(name + "_stick", 0.04, h, (0, 0, h / 2), mat("#FFFFFF", 0.4), root)
    cyl(name + "_top", 0.42, 0.1, (0, 0, h + 0.36), checker(c1, c2, 2.5, 0.3, 0.6), root, rot=(math.radians(90), 0, 0),
        bevel=0.04)
    return root


def _set_candy(pal, rnd, sky, grass):
    box("ground", (40, 40, 0.2), (0, 6, -0.1), checker("#FF9ECB", "#FFBEDB", 3.0, 0.6), bevel=0)
    for i, (hx, hr, c) in enumerate(((-5, 4, "#B8F5D8"), (1, 5, "#FFC2E0"), (7, 4.5, "#C9B8FF"))):
        sphere(f"candyhill{i}", hr, (hx, 14, -hr * 0.55), mat(c, 0.5, coat=0.4), scale=(1.6, 1, 1), sub=1)
    cs = [("#FF4D8A", "#FFFFFF"), ("#4DA6FF", "#FFE27A"), ("#5CCB6B", "#FFFFFF"), ("#B57BFF", "#FFD1E8")]
    for i, (lx, ly, lh) in enumerate(((-3.2, 4.4, 1.6), (3.4, 4.8, 1.9), (-0.8, 6.0, 2.2), (1.4, 3.9, 1.2))):
        _lolly(f"lolly{i}", (lx, ly, 0), lh, *cs[i % 4])
    for i in range(8):  # gumdrops
        c = mat(pal.choice(["#FF4D8A", "#FFD23F", "#5CCB6B", "#4DA6FF", "#B57BFF", "#FF8A3D"]), 0.3, coat=0.8)
        sphere(f"gum{i}", 0.17, (rnd.uniform(-4, 4), rnd.uniform(2.2, 3.6), 0.05), c, scale=(1, 1, 1.15))
    kk("holiday", ["candy-cane-*"], "ccane", (-4.4, 3.2, 0), 1.6, rnd=pal)
    kk("holiday", ["candy-cane-*"], "ccane2", (4.6, 3.0, 0), 1.4, rnd=pal)
    kk("food", ["cupcake*"], "bigcupcake", (2.4, 6.4, 0), width=1.5, rnd=pal)
    kk("food", ["ice-cream.glb", "ice-cream-cne.glb"], "bigice", (-2.2, 6.8, 0), 2.0, rnd=pal)
    kk("food", ["lollypop.glb"], "klolly", (0.4, 3.4, 0), 0.8)
    cloud = mat("#FFE6F5", 0.9)
    for i, (cx, cz) in enumerate(((-3.5, 5.5), (1.5, 6.4), (5.5, 5.2))):
        for j, (ox, oz, rr) in enumerate(((0, 0, 0.7), (0.7, -0.15, 0.5), (-0.7, -0.15, 0.5), (0.3, 0.35, 0.5))):
            sphere(f"pcloud{i}{j}", rr, (cx + ox, 14, cz + oz), cloud, scale=(1.2, 0.6, 1), sub=1)
    return "candy"


def _set_market(pal, rnd, sky, grass):
    box("ground", (40, 40, 0.2), (0, 6, -0.1), checker("#C2AF98", "#B09C85", 10.0, 0.8), bevel=0)
    kk("fantasy", ["fountain-round.glb", "fountain-round-detail.glb"], "fountain", (0.0, 5.6, 0), width=2.4, rnd=pal)
    kk("fantasy", ["stall-red.glb", "stall.glb"], "stall1", (-1.8, 3.7, 0), width=1.5, rot_z=0.3, rnd=pal)
    kk("fantasy", ["stall-green.glb", "stall.glb"], "stall2", (1.9, 3.8, 0), width=1.5, rot_z=-0.3, rnd=pal)
    kk("fantasy", ["cart.glb", "cart-high.glb"], "cart", (-1.1, 5.4, 0), width=1.1, rot_z=0.5, rnd=pal)
    for i, (lx, ly) in enumerate(((-1.7, 3.2), (1.9, 3.3))):
        kk("fantasy", ["lantern.glb"], f"mlantern{i}", (lx, ly, 0), 1.4)
    for i, (tx, ty) in enumerate(((-4.4, 5.8), (4.5, 6.0), (-0.6, 8.0))):
        kk("fantasy", ["tree-high-round.glb", "tree.glb", "tree-high.glb"], f"mtree{i}", (tx, ty, 0), 2.6, rnd=pal)
    kk("fantasy", ["windmill.glb"], "windmill", (3.0, 12.0, 0), 5.0, rot_z=-0.3)
    _clouds()


def _set_desert(pal, rnd, sky, grass):
    box("ground", (40, 40, 0.2), (0, 6, -0.1), mat(pal.choice(["#F2C27B", "#EDB872", "#F5CC8C"]), 0.9), bevel=0)
    for i, (mx, my, sx, sz) in enumerate(((-5.5, 13, 3.0, 2.2), (0.5, 15, 3.5, 3.0), (6.5, 12, 2.5, 1.8))):
        box(f"mesa{i}", (sx, 2.0, sz), (mx, my, sz / 2), mat(pal.choice(["#D9733B", "#C9603A", "#E08A4F"]), 0.9), bevel=0.2)
        box(f"mesatop{i}", (sx + 0.2, 2.1, 0.12), (mx, my, sz), mat("#B5522F", 0.9), bevel=0.05)
    for i, (cx, cy) in enumerate(((-3.2, 3.6), (2.9, 4.0), (-0.9, 5.4), (4.6, 5.8), (-4.6, 6.0))):
        if not kk("nature", ["cactus_tall.glb", "cactus_short.glb"], f"cactus{i}", (cx, cy, 0), rnd.uniform(1.0, 2.0), rnd=pal):
            cyl(f"cactusp{i}", 0.18, 1.4, (cx, cy, 0.7), mat("#4FAE5A", 0.6))
    for i in range(5):
        kk("nature", ["rock_small*", "rock_largea.glb", "rock_tall*"], f"drock{i}",
           (rnd.uniform(-4.5, 4.5), rnd.uniform(2.6, 5), 0), rnd.uniform(0.25, 0.7), rnd=pal)
    tw = empty("tumbleweed", (-5, 2.4, 0.25))  # a tumbleweed rolls by
    for j in range(6):
        sphere(f"tw{j}", 0.22, (0, 0, 0), mat("#B58A4F", 0.9), tw, rot=(j, j * 0.7, 0), sub=0)
    key(tw, "location", 1, (-6, 2.4, 0.25), "LINEAR")
    key(tw, "location", 168, (6, 2.4, 0.25), "LINEAR")
    key(tw, "rotation_euler", 1, (0, 0, 0), "LINEAR")
    key(tw, "rotation_euler", 168, (0, math.radians(1440), 0), "LINEAR")
    return "golden" if sky == "day" else sky


def _leaf(name, loc, size, rot, m):
    """A big jungle leaf: a flattened, pointed blob on a little stem."""
    root = empty(name, loc)
    root.rotation_euler = rot
    sphere(name + "_l", size, (0, 0, size * 1.1), m, root, scale=(0.45, 0.08, 1.0), sub=1, seg=24)
    cyl(name + "_s", 0.015, size * 0.6, (0, 0, size * 0.1), mat("#2F7A3A", 0.6), root)
    return root


def _set_jungle(pal, rnd, sky, grass):
    box("ground", (40, 40, 0.2), (0, 6, -0.1), mat(pal.choice(["#4FAE4A", "#58B44F", "#4AA35A"]), 0.9), bevel=0)
    box("jpath", (40, 2.0, 0.02), (0, 0.4, 0.005), mat(pal.choice(["#C99A63", "#B88A55", "#D4A86E"]), 0.9), bevel=0)
    for i, (hx, hr) in enumerate(((-7, 4.5), (0, 6), (7.5, 5))):  # misty green hills far away
        sphere(f"jhill{i}", hr, (hx, 16, -hr * 0.55), mat("#3E8E5A", 0.95), scale=(1.5, 1, 1), sub=1)
    greens = [mat(c, 0.6) for c in ("#2E9E4F", "#3BB35A", "#228B45", "#45C267")]
    for i, (tx, ty) in enumerate(((-4.6, 4.2), (-2.2, 5.6), (1.0, 6.4), (3.4, 4.8), (5.6, 6.2), (-0.6, 8.0), (2.4, 8.6))):
        if not kk("nature", ["tree_palm*", "tree_fat*", "tree_default*"], f"jtree{i}", (tx, ty, 0),
                  rnd.uniform(2.6, 3.8), rot_z=rnd.uniform(-1, 1), rnd=pal):
            cyl(f"jtrunk{i}", 0.12, 2.6, (tx, ty, 1.3), mat("#8A5A3C", 0.7))
            sphere(f"jcrown{i}", 0.9, (tx, ty, 2.9), greens[i % 4], sub=1)
    for i in range(14):  # giant leaves at the sides and behind
        x = rnd.choice([rnd.uniform(-5.5, -2.0), rnd.uniform(2.0, 5.5), rnd.uniform(-2.0, 2.0)])
        y = rnd.uniform(2.3, 4.2) if abs(x) > 1.9 else rnd.uniform(3.4, 4.6)
        _leaf(f"jleaf{i}", (x, y, 0), rnd.uniform(0.35, 0.6), (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.7, 0.7), rnd.uniform(-0.5, 0.5)),
              greens[i % 4])
    for i in range(6):
        kk("nature", ["plant_bush*", "plant_flat*", "flower_*", "mushroom_*"], f"jbush{i}",
           (rnd.uniform(-5, 5), rnd.uniform(2.4, 4.0), 0), rnd.uniform(0.35, 0.7), rnd=pal)
    vine = mat("#2F8A3E", 0.7)
    for i, vx in enumerate((-3.6, -1.4, 1.7, 3.9)):  # hanging vines
        vy = rnd.uniform(3.2, 4.4)
        pts = [(0, 0, 0), (0.15, 0, -0.6), (-0.1, 0, -1.2), (0.12, 0, -1.8)]
        curve_line(f"vine{i}", pts, 0.025, vine, loc=(vx, vy, 4.6))
        for j in range(3):
            sphere(f"vleaf{i}{j}", 0.08, (vx + 0.1 * (-1) ** j, vy - 0.03, 4.3 - j * 0.55), greens[j % 4],
                   scale=(1, 0.3, 0.6), sub=0)
    fcols = ("#FF4D6D", "#FF8A3D", "#FFD23F", "#FF6BD6")
    for i in range(6):  # big tropical flowers
        x, y = rnd.uniform(-4.5, 4.5), rnd.uniform(2.3, 3.6)
        if abs(x) < 1.6:
            x += 2.4 if x >= 0 else -2.4
        for k in range(5):
            a = k / 5 * math.tau
            sphere(f"jfl{i}{k}", 0.07, (x + math.cos(a) * 0.08, y, 0.35 + math.sin(a) * 0.08), mat(fcols[i % 4], 0.5),
                   scale=(1, 0.4, 0.7), rot=(0, -a, 0), sub=0)
        sphere(f"jflc{i}", 0.04, (x, y - 0.02, 0.35), mat("#FFF2A8", 0.4), sub=0)
        cyl(f"jfls{i}", 0.012, 0.35, (x, y + 0.02, 0.17), mat("#2F7A3A", 0.6))
    for i in range(4):
        kk("nature", ["rock_small*", "rock_tall*", "stump_*", "log*"], f"jrock{i}",
           (rnd.uniform(-5, 5), rnd.uniform(2.5, 4.5), 0), rnd.uniform(0.3, 0.6), rnd=pal)
    _clouds(6.5, 18)
    return sky


EXTRA_SETS = {"farm": _set_farm, "camping": _set_camping, "castle": _set_castle, "underwater": _set_underwater,
              "candy": _set_candy, "market": _set_market, "desert": _set_desert, "jungle": _set_jungle}


def _room(pal):
    """A cosy indoor room: floor, back wall with a window, little pictures and bunting."""
    floor = pal.choice([("#E6C29A", "#D9B386"), ("#F2D7B6", "#E6C6A0"), ("#FFFFFF", "#CFE8FF"), ("#FFE3EE", "#FFFFFF")])
    box("floor", (40, 40, 0.2), (0, 6, -0.1), checker(*floor, 14.0, 0.5), bevel=0)
    box("wall", (14, 0.2, 5), (0, 4.0, 2.5), mat(pal.choice(["#CFE8FF", "#FFE0EC", "#E8FFE0", "#F2E8FF", "#FFF1C9"]), 0.8), bevel=0)
    box("skirting", (14, 0.05, 0.15), (0, 3.88, 0.075), WHITE, bevel=0.01)
    wx = pal.choice((-1.6, 0.4))
    box("win_frame", (1.5, 0.1, 1.2), (wx, 3.86, 2.3), WHITE, bevel=0.04)
    box("win_sky", (1.3, 0.1, 1.0), (wx, 3.84, 2.3), mat("#9FD8FF", 0.5, emit=1.2), bevel=0.02)
    box("win_cross", (0.06, 0.1, 1.0), (wx, 3.8, 2.3), WHITE, bevel=0.01)
    for i, (px, c) in enumerate(((wx + 1.6, pal.choice(PASTELS)), (wx - 1.5, pal.choice(PASTELS)))):
        box(f"pic{i}", (0.55, 0.06, 0.45), (px, 3.87, 2.4), mat("#FFFFFF", 0.4), bevel=0.02)
        box(f"picin{i}", (0.45, 0.06, 0.35), (px, 3.85, 2.4), mat(c, 0.6), bevel=0.01)
        sphere(f"picsun{i}", 0.07, (px - 0.1, 3.82, 2.47), mat("#FFD23F", 0.5), sub=0, scale=(1, 0.3, 1))
    flags = pal.sample(["#FF4D5E", "#4DA6FF", "#FFD23F", "#5CCB6B", "#B57BFF", "#FF8A3D"], 4)
    for i in range(13):  # bunting
        x = -3.6 + i * 0.6
        box(f"bunt{i}", (0.22, 0.02, 0.22), (x, 3.85, 3.35 - 0.12 * math.sin(i / 12 * math.pi)), mat(flags[i % 4], 0.6),
            rot=(0, math.radians(45), 0), bevel=0.005)


def make_set(kind, rnd=None):
    rnd = rnd or random.Random(1)
    pal = random.Random(THEME.get("pal", 1))  # same colours in every gag of one short
    sky = THEME.get("sky", "day")
    if sky not in SKY or sky in ("indoor", "snow", "space", "underwater", "candy"):
        sky = "day"
    grass = pal.choice(GRASS)
    if THEME.get("season") == "autumn":
        grass = pal.choice(["#9CCB5F", "#B5C95A", "#8FC260"])
    if kind in EXTRA_SETS:
        sky = EXTRA_SETS[kind](pal, rnd, sky, grass) or sky
    elif kind == "street":
        box("ground", (40, 40, 0.2), (0, 6, -0.1), mat(grass, 0.8), bevel=0)
        box("path", (40, 2.4, 0.02), (0, 0.4, 0.005), mat(pal.choice(["#E3B98A", "#D9C7B0", "#F0D2A0", "#C9B8D9"]), 0.85), bevel=0)
        cols = pal.sample(PASTELS, 5)
        houses = [(cols[0], -3.2), (cols[1], -0.6), (cols[2], 2.2), (cols[3], 4.8), (cols[4], -5.8)]
        roofs = pal.sample(["#E8574F", "#4F7BE8", "#8A5ACF", "#2EA87A", "#E88A2F", "#D94F8A"], 2)
        for i, (c, hx) in enumerate(houses):
            h = 2.2 + (i % 2) * 0.6
            box(f"house{i}", (2.2, 1.8, h), (hx, 5.0, h / 2), mat(c, 0.6), bevel=0.12)
            cone(f"roof{i}", 1.65, 0.0, 1.2, (hx, 5.0, h + 0.55), mat(roofs[i % 2], 0.5),
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
        cyl("lamp", 0.05, 2.2, (-2.6, 1.9, 1.1), mat("#2E3A59", 0.4))
        sphere("lampbulb", 0.16, (-2.6, 1.9, 2.25), mat("#FFF2B3", 0.3, emit=1.5), sub=1)
        _trees((-4.5, -1.9, 1.0, 3.6, 6.2), 3.2)
        _clouds()
    elif kind == "park":
        box("ground", (40, 40, 0.2), (0, 6, -0.1), mat(grass, 0.85), bevel=0)
        hill = pal.choice(["#5DBE55", "#69C95E", "#7CC96A", "#58B88A"])
        for i, (hx, hr, c) in enumerate(((-5, 4, hill), (1, 5, grass), (7, 4.5, hill))):
            sphere(f"hill{i}", hr, (hx, 14, -hr * 0.55), mat(c, 0.9), scale=(1.6, 1, 1), sub=1)
        _trees((-3.8, -1.4, 2.4, 4.6), 3.6)
        _trees((-6.0, 0.6, 6.5), 6.5)
        pond = cyl("pond", 1.4, 0.02, (2.6, 2.6, 0.012), mat("#4FB3FF", 0.05, coat=1.0), scale=(1.6, 0.7, 1))
        for i in range(6):
            a = i / 6 * math.tau
            sphere(f"rock{i}", 0.12, (2.6 + math.cos(a) * 2.2, 2.6 + math.sin(a) * 0.95, 0.04), mat("#B8B8C8", 0.7),
                   scale=(1.3, 1, 0.6))
        bench = empty("bench", (-2.2, 2.2, 0))
        bc = pal.choice(["#C0763C", "#FF7AA8", "#4DA6FF", "#5CCB6B"])
        box("bench_seat", (1.4, 0.38, 0.07), (0, 0, 0.42), mat(bc, 0.6), bench, bevel=0.02)
        box("bench_back", (1.4, 0.06, 0.32), (0, 0.18, 0.66), mat(bc, 0.6), bench, bevel=0.02)
        for sx in (-0.6, 0.6):
            box(f"bench_leg{sx}", (0.06, 0.34, 0.42), (sx, 0, 0.21), mat("#2E3A59", 0.4), bench, bevel=0.01)
        _flowers(26, 1.6, 4.0, rnd=rnd)
        for i, bx in enumerate((-4.5, 0.2, 4.2)):
            make_prop("bush", (bx, 3.3, 0), name=f"pbush{i}")
        _clouds()
    elif kind in ("beach", "pirate"):
        box("ground", (40, 22, 0.2), (0, -4.0, -0.1), mat(pal.choice(["#F2CF92", "#F5D9A8", "#EFC88A"]), 0.9), bevel=0)
        box("sea", (60, 40, 0.1), (0, 26, -0.07), mat(pal.choice(["#2FA8E8", "#23C2D9", "#3D8FE0"]), 0.08, coat=1.0), bevel=0)
        box("foam", (60, 0.25, 0.02), (0, 7.05, 0.0), mat("#FFFFFF", 0.4), bevel=0)
        um = empty("umbrella", (-2.3, 2.6, 0))
        cyl("um_pole", 0.03, 1.9, (0, 0, 0.95), mat("#FFFFFF", 0.4), um)
        uc = pal.sample(["#FF4D5E", "#4DA6FF", "#FFD23F", "#5CCB6B", "#B57BFF", "#FF8A3D"], 2)
        cone("um_top", 1.0, 0.05, 0.4, (0, 0, 1.95), checker(uc[0], "#FFFFFF", 3.0, 0.5), um)
        castle = empty("castle", (2.4, 2.8, 0) if kind == "beach" else (2.4, 2.8, -5))
        sand = mat("#E9C27D", 0.95)
        cyl("c_base", 0.45, 0.4, (0, 0, 0.2), sand, castle)
        for i, a in enumerate((0, 2.1, 4.2)):
            cyl(f"c_tower{i}", 0.13, 0.55, (math.cos(a) * 0.35, math.sin(a) * 0.35, 0.5), sand, castle)
            cone(f"c_top{i}", 0.15, 0.0, 0.2, (math.cos(a) * 0.35, math.sin(a) * 0.35, 0.87), sand, castle)
        box("c_flag", (0.18, 0.01, 0.1), (0.1, 0, 1.25), mat("#FF4D5E", 0.4), castle, bevel=0.005)
        cyl("c_flagpole", 0.008, 0.35, (0, 0, 1.12), mat("#FFFFFF", 0.4), castle)
        for i, px in enumerate((-4.6, 4.8)):
            palm = empty(f"palm{i}", (px, 4.5, 0))
            for j in range(6):
                cyl(f"palm{i}_t{j}", 0.13 - j * 0.01, 0.42, (j * 0.06, 0, 0.21 + j * 0.4), mat("#A4733F", 0.8), palm,
                    rot=(0, 0.08, 0))
            for j in range(6):
                a = j / 6 * math.tau
                sphere(f"palm{i}_l{j}", 0.5, (0.36 + math.cos(a) * 0.55, math.sin(a) * 0.55, 2.4 - 0.1 * (j % 2)),
                       mat("#3FB64E", 0.7), palm, scale=(1.5, 0.35, 0.12), rot=(0.25 * math.sin(a), 0.35, a))
        for i in range(7):
            sphere(f"shell{i}", 0.05, (rnd.uniform(-4, 4), rnd.uniform(0.3, 3.5), 0.02),
                   mat(("#FFB3CF", "#FFFFFF", "#FFD27A")[i % 3], 0.5), scale=(1, 0.8, 0.5))
        towel = box("towel", (1.0, 0.6, 0.01), (-2.0, 1.6, 0.005), checker(uc[1], "#FFFFFF", 4.0, 0.7), bevel=0)
        for i, (bx, c) in enumerate(((1.0, uc[1]), (-0.9, uc[0]))):  # beach balls / buckets
            if i == 0:
                sphere("bball", 0.16, (bx + 3.2, 3.4, 0.16), checker(c, "#FFFFFF", 2.0, 0.3, 0.6), sub=2)
            else:
                cyl("bucket", 0.13, 0.22, (bx - 2.6, 3.0, 0.11), mat(c, 0.3, coat=0.4), scale=(1, 1, 1))
        if kind == "pirate":  # free Kenney Pirate Kit
            kk("pirate", ["ship-pirate-*"], "ship", (pal.uniform(1.5, 4.0), 13.0, -0.05), 3.6, rot_z=math.pi / 2 + pal.uniform(-0.3, 0.3), rnd=pal)
            kk("pirate", ["chest.glb"], "chest", (2.0, 2.7, 0), 0.45, rot_z=-0.3)
            kk("pirate", ["flag-pirate-high*"], "pflag", (-1.1, 4.3, 0), 2.2, rnd=pal)
            for i, (bx, by) in enumerate(((-3.3, 3.3), (-2.9, 3.7))):
                kk("pirate", ["barrel.glb"], f"barrel{i}", (bx, by, 0), 0.5, rot_z=i)
            kk("pirate", ["boat-row-*"], "rowboat", (3.6, 4.8, 0), width=1.4, rot_z=0.4, rnd=pal)
            kk("pirate", ["palm-detailed-*"], "kpalm", (0.6, 5.2, 0), 3.0, rnd=pal)
            kk("pirate", ["cannon.glb"], "cannon", (-0.4, 3.6, 0), 0.5, rot_z=0.6)
        _clouds(6)
    elif kind == "kitchen":
        sky = "indoor"
        k = pal.sample(["#9FD9F5", "#FFC2D6", "#C9F2B8", "#FFE08A", "#D7C6FF"], 2)
        box("floor", (40, 40, 0.2), (0, 6, -0.1), checker("#FFFFFF", k[0], 26.0, 0.45), bevel=0)
        wall_m = mat(pal.choice(["#FFE7B8", "#FFE0EC", "#E3F4FF", "#E8FFE0", "#F2E8FF"]), 0.8)
        box("wall", (14, 0.2, 5), (0, 4.0, 2.5), wall_m, bevel=0)
        box("skirting", (14, 0.05, 0.15), (0, 3.88, 0.075), WHITE, bevel=0.01)
        box("win_frame", (1.7, 0.1, 1.3), (-1.2, 3.86, 2.1), WHITE, bevel=0.04)
        box("win_sky", (1.5, 0.1, 1.1), (-1.2, 3.84, 2.1), mat("#9FD8FF", 0.5, emit=1.2), bevel=0.02)
        box("win_cross_v", (0.06, 0.1, 1.1), (-1.2, 3.8, 2.1), WHITE, bevel=0.01)
        box("win_cross_h", (1.5, 0.1, 0.06), (-1.2, 3.8, 2.1), WHITE, bevel=0.01)
        cc = pal.choice([("#7FD1B9", "#9BE0CB"), ("#FF9EC4", "#FFB8D6"), ("#8FD3FF", "#B0E0FF"), ("#FFD27A", "#FFE29E")])
        cnt = mat(cc[0], 0.5)
        box("counter", (3.2, 0.7, 0.9), (2.2, 3.5, 0.45), cnt, bevel=0.04)
        box("counter_top", (3.3, 0.8, 0.08), (2.2, 3.48, 0.94), mat("#FFFFFF", 0.3, coat=0.4), bevel=0.02)
        for i in range(3):
            box(f"drawer{i}", (0.95, 0.04, 0.7), (1.15 + i * 1.05, 3.13, 0.45), mat(cc[1], 0.5), bevel=0.03)
            sphere(f"handle{i}", 0.035, (1.15 + i * 1.05, 3.1, 0.65), mat("#FFD23F", 0.2, coat=1), sub=0)
        box("fridge", (1.0, 0.8, 2.1), (-3.4, 3.45, 1.05), mat(pal.choice(["#FF9EC4", "#FFFFFF", "#8FD3FF", "#FFE27A"]), 0.35, coat=0.4), bevel=0.1)
        box("fridge_line", (0.98, 0.02, 0.03), (-3.4, 3.04, 1.35), mat("#E07AA0", 0.4), bevel=0)
        for i, (jx, c) in enumerate(((1.4, "#FF6B8B"), (1.9, "#FFD53D"), (2.4, "#B57BFF"), (2.95, "#5CCB6B"))):
            cyl(f"jar{i}", 0.12, 0.28, (jx, 3.5, 1.12), mat(c, 0.15, coat=1.0))
            cyl(f"jarlid{i}", 0.13, 0.05, (jx, 3.5, 1.29), WHITE, bevel=0.01)
        box("shelf", (2.4, 0.3, 0.06), (2.2, 3.82, 2.2), WHITE, bevel=0.01)
        for i, (px, c) in enumerate(((1.4, "#FF8A3D"), (2.0, "#4DA6FF"), (2.6, "#FF4D5E"), (3.1, "#FFD53D"))):
            cyl(f"pot{i}", 0.14, 0.22, (px, 3.8, 2.34), mat(c, 0.3, coat=0.5))
        cyl("lamp_cord", 0.01, 1.4, (0.3, 2.4, 4.3), mat("#2E3A59", 0.4))
        cone("lamp_shade", 0.3, 0.08, 0.25, (0.3, 2.4, 3.5), mat("#FFD23F", 0.4))
        sphere("lamp_bulb", 0.08, (0.3, 2.4, 3.36), mat("#FFF2B3", 0.3, emit=3), sub=0)
        box("rug", (2.6, 1.6, 0.012), (0, 0.6, 0.006), checker(k[1], "#FFFFFF", 5.0, 0.8), bevel=0)
        kk("furniture", ["toaster.glb"], "toaster", (0.85, 3.45, 0.98), 0.24)
        kk("furniture", ["kitchenblender.glb", "kitchencoffeemachine.glb"], "blender", (3.5, 3.45, 0.98), 0.42, rnd=pal)
    elif kind in ("bedroom", "livingroom"):
        sky = "indoor"
        _room(pal)
        if kind == "bedroom":
            bed = pal.choice(["bedsingle.glb", "bedbunk.glb", "beddouble.glb"])
            kk("furniture", [bed], "bed", (-2.5, 3.1, 0), width=2.1)
            kk("furniture", ["bookcaseopen.glb", "bookcaseopenlow.glb"], "bookcase", (2.6, 3.7, 0), width=1.1, rnd=pal)
            kk("furniture", ["bear.glb"], "teddy", (1.5, 3.3, 0), 0.55, rot_z=-0.3)
            kk("furniture", ["lampround*floor.glb", "lampsquarefloor.glb"], "flamp", (-0.9, 3.7, 0), 1.5, rnd=pal)
            kk("furniture", ["ruground.glb", "rugrounded.glb"], "rug", (0, 0.9, 0), width=2.6, rnd=pal)
            kk("furniture", ["cardboardboxopen.glb"], "toybox", (3.2, 2.5, 0), width=0.6, rot_z=0.3)
        else:
            kk("furniture", ["loungesofa.glb", "loungedesignsofa.glb", "loungesofalong.glb"], "sofa", (-0.2, 3.35, 0), width=2.3, rnd=pal)
            tv = kk("furniture", ["cabinettelevision*"], "tvcab", (2.7, 3.6, 0), width=1.3, rnd=pal)
            if tv:
                kk("furniture", ["televisionmodern.glb", "televisionvintage.glb"], "tv", (2.7, 3.6, top(tv)), width=0.9, rnd=pal)
            kk("furniture", ["tablecoffee.glb", "tablecoffeesquare.glb"], "ctable", (0.0, 2.35, 0), width=1.0, rnd=pal)
            kk("furniture", ["pottedplant.glb"], "plant", (-2.9, 3.6, 0), 1.1)
            kk("furniture", ["lampsquarefloor.glb", "lampround*floor.glb"], "flamp", (-1.9, 3.75, 0), 1.5, rnd=pal)
            kk("furniture", ["rugrectangle.glb", "rugsquare.glb"], "rug", (0, 1.0, 0), width=3.0, rnd=pal)
            kk("toycar", ["track-narrow-looping.glb", "track-striped-narrow-looping.glb"], "loop", (3.3, 2.4, 0), 0.7, rot_z=-0.5, rnd=pal)
        for i, (cx, cy) in enumerate(((0.9, 2.3), (-0.7, 2.7), (2.3, 1.9))):  # toy cars on the floor
            kk("toycar", ["vehicle-*"], f"toycar{i}", (cx, cy, 0), width=0.32, rot_z=pal.uniform(0, math.tau), rnd=pal)
    elif kind == "space":
        sky = "space"
        box("ground", (40, 40, 0.2), (0, 6, -0.1), mat(pal.choice(["#C9C3DD", "#BDB9CC", "#D6CFE6"]), 0.9), bevel=0)
        for i in range(9):  # craters
            cx, cy, cr = rnd.uniform(-5, 5), rnd.uniform(1.6, 7), rnd.uniform(0.25, 0.7)
            cyl(f"crater{i}", cr, 0.02, (cx, cy, 0.006), mat("#A39DB8", 0.95), scale=(1, 0.75, 1))
            cyl(f"craterrim{i}", cr * 1.15, 0.05, (cx, cy, 0.0), mat("#D9D3EA", 0.9), scale=(1, 0.75, 1))
        for i, (hx, hr) in enumerate(((-6, 4), (1, 5), (7.5, 4.5))):
            sphere(f"hill{i}", hr, (hx, 15, -hr * 0.6), mat("#B3ADC8", 0.9), scale=(1.6, 1, 1), sub=1)
        star = mat("#FFFFFF", 0.5, emit=6)
        for i in range(90):
            sphere(f"star{i}", rnd.uniform(0.025, 0.06), (rnd.uniform(-14, 14), rnd.uniform(19, 23), rnd.uniform(1.0, 13)), star, sub=0)
        p1, p2 = pal.sample(["#FF9EC4", "#8FD3FF", "#FFD27A", "#9EF0C0", "#B7A6FF", "#FF8A5C"], 2)
        sphere("planet", 1.7, (4.6, 21, 7.0), mat(p1, 0.6, emit=0.35), sub=2)
        cyl("planet_ring", 2.8, 0.03, (4.6, 21, 7.0), mat("#FFF4D6", 0.5, emit=0.3), rot=(math.radians(70), math.radians(18), 0))
        sphere("moonlet", 0.8, (-5.2, 22, 5.0), mat(p2, 0.6, emit=0.35), sub=2)
        rk = empty("rocket", (-1.6, 4.6, 0))  # our own cute rocket
        rc = pal.choice(["#FF4D5E", "#4DA6FF", "#FF8A3D", "#B57BFF"])
        cyl("rk_body", 0.38, 1.6, (0, 0, 1.0), mat("#FFFFFF", 0.35, coat=0.4), rk, bevel=0.05)
        cone("rk_nose", 0.38, 0.0, 0.7, (0, 0, 2.15), mat(rc, 0.35, coat=0.4), rk)
        sphere("rk_win", 0.17, (0, -0.33, 1.35), mat("#8FD3FF", 0.1, coat=1, emit=0.4), rk, scale=(1, 0.5, 1))
        cyl("rk_winrim", 0.2, 0.05, (0, -0.36, 1.35), mat(rc, 0.4), rk, rot=(math.radians(90), 0, 0))
        for j in range(3):
            a = j / 3 * math.tau + 0.5
            box(f"rk_fin{j}", (0.06, 0.45, 0.6), (math.cos(a) * 0.42, math.sin(a) * 0.42, 0.42), mat(rc, 0.4), rk,
                rot=(0, 0, a + math.pi / 2), bevel=0.02)
        cyl("rk_base", 0.3, 0.2, (0, 0, 0.12), mat("#6B6F86", 0.4, metal=0.5), rk)
        kk("space", ["rover.glb"], "rover", (1.8, 3.4, 0), width=0.9, rot_z=-0.4)
        kk("space", ["satellitedish_large.glb", "satellitedish_detailed.glb"], "dish", (3.3, 4.3, 0), 1.3, rot_z=0.6, rnd=pal)
        kk("space", ["rock_crystals*"], "crystals", (0.9, 4.1, 0), 0.7, rnd=pal)
        al = kk("space", ["alien.glb", "astronauta.glb", "astronautb.glb"], "alien", (-0.9, 3.5, 0), 0.6, rot_z=0.2, rnd=pal)
        if al:
            bob(al, phase=7, height=0.12, every=40)
        for i, (mx, my) in enumerate(((-4.2, 4.6), (4.6, 2.6), (-1.8, 5.6))):
            kk("space", ["meteor*", "rock_large*"], f"mrock{i}", (mx, my, 0), 0.45, rot_z=i * 2.0, rnd=pal)
    elif kind == "playground":
        box("ground", (40, 40, 0.2), (0, 6, -0.1), mat(grass, 0.85), bevel=0)
        box("sandpit", (4.2, 2.4, 0.02), (0, 0.5, 0.006), mat("#F2D49A", 0.95), bevel=0)
        pc = pal.sample(["#FF4D5E", "#4DA6FF", "#FFD23F", "#5CCB6B", "#B57BFF", "#FF8A3D"], 3)
        metal = mat("#E9EEF5", 0.3, metal=0.4)
        # slide
        sl = empty("slide", (-2.6, 3.6, 0))
        for sx in (-0.3, 0.3):
            cyl(f"sl_leg{sx}", 0.04, 1.6, (sx, 0.5, 0.8), metal, sl)
        for j in range(4):
            box(f"sl_step{j}", (0.62, 0.08, 0.04), (0, 0.5, 0.35 + j * 0.35), metal, sl, bevel=0.01)
        box("sl_top", (0.75, 0.6, 0.08), (0, 0.15, 1.6), mat(pc[0], 0.4, coat=0.4), sl, bevel=0.03)
        box("sl_chute", (0.6, 2.4, 0.06), (0, -1.0, 0.85), mat(pc[0], 0.3, coat=0.5), sl,
            rot=(math.radians(-38), 0, 0), bevel=0.03)
        # swings
        sw = empty("swings", (1.9, 4.2, 0))
        for sx in (-1.0, 1.0):
            for sy in (-0.35, 0.35):
                cyl(f"sw_leg{sx}{sy}", 0.045, 2.2, (sx, sy * 0.5, 1.05), mat(pc[1], 0.4), sw,
                    rot=(math.radians(sy * 30), 0, 0))
        cyl("sw_bar", 0.05, 2.1, (0, 0, 2.1), mat(pc[1], 0.4), sw, rot=(0, math.pi / 2, 0))
        for i, sx in enumerate((-0.45, 0.45)):
            for rx in (-0.16, 0.16):
                cyl(f"sw_rope{i}{rx}", 0.01, 1.55, (sx + rx, 0, 1.32), mat("#FFFFFF", 0.6), sw)
            box(f"sw_seat{i}", (0.42, 0.18, 0.05), (sx, 0, 0.55), mat(pc[2], 0.4, coat=0.3), sw, bevel=0.02)
        # seesaw
        ss = empty("seesaw", (4.4, 2.8, 0))
        cone("ss_base", 0.18, 0.05, 0.3, (0, 0, 0.15), mat(pc[2], 0.4), ss)
        box("ss_plank", (2.0, 0.24, 0.06), (0, 0, 0.33), mat(pc[0], 0.4, coat=0.3), ss, rot=(0, 0.18, 0), bevel=0.02)
        fence = mat(pal.choice(["#FFFFFF", "#FFE27A", "#8FD3FF"]), 0.5)
        for i in range(-14, 15):
            box(f"picket{i}", (0.09, 0.05, 0.5), (i * 0.4, 6.0, 0.25), fence, bevel=0.025)
        _trees((-5.5, -0.6, 3.4, 6.4), 7.2)
        _flowers(14, 1.8, 3.0, rnd=rnd)
        _clouds()
    elif kind in ("snow", "christmas"):
        sky = "snow"
        box("ground", (40, 40, 0.2), (0, 6, -0.1), mat("#EAF2FB", 0.7), bevel=0)
        for i, (hx, hr) in enumerate(((-5, 4), (1, 5), (7, 4.5))):
            sphere(f"hill{i}", hr, (hx, 14, -hr * 0.55), mat("#F7FBFF", 0.8), scale=(1.6, 1, 1), sub=1)
        _pines((-4.4, -2.0, 2.8, 5.0), 3.8)
        _pines((-6.2, 0.4, 6.6), 6.8)
        sm = empty("snowman", (-2.6, 2.4, 0))
        snow = mat("#FFFFFF", 0.6)
        for j, (r, z) in enumerate(((0.36, 0.33), (0.26, 0.86), (0.18, 1.24))):
            sphere(f"sm_{j}", r, (0, 0, z), snow, sm, sub=2)
        cone("sm_nose", 0.035, 0.0, 0.18, (0, -0.24, 1.24), mat("#FF8A1F", 0.4), sm, rot=(math.radians(90), 0, 0))
        for sx in (-0.07, 0.07):
            sphere(f"sm_eye{sx}", 0.025, (sx, -0.16, 1.3), BLACK, sm, sub=0)
        hatc = pal.choice(["#FF4D5E", "#4DA6FF", "#5CCB6B", "#B57BFF"])
        cyl("sm_scarf", 0.21, 0.06, (0, 0, 1.06), mat(hatc, 0.6), sm)
        cone("sm_hat", 0.17, 0.02, 0.3, (0, 0, 1.5), checker(hatc, "#FFFFFF", 5.0, 0.6), sm)
        sphere("sm_pom", 0.05, (0, 0, 1.66), snow, sm, sub=0)
        cab = empty("cabin", (2.6, 4.6, 0))
        box("cab_body", (1.8, 1.4, 1.3), (0, 0, 0.65), mat(pal.choice(["#C0763C", "#E8574F", "#4F7BE8"]), 0.6), cab, bevel=0.08)
        cone("cab_roof", 1.4, 0.0, 0.9, (0, 0, 1.75), snow, cab, rot=(0, 0, math.radians(45)), scale=(1, 0.85, 1))
        box("cab_win", (0.5, 0.1, 0.45), (0.4, -0.72, 0.75), mat("#FFE9A0", 0.3, emit=1.2), cab, bevel=0.04)
        box("cab_door", (0.45, 0.1, 0.8), (-0.4, -0.72, 0.4), mat("#6B4423", 0.5), cab, bevel=0.05)
        for i in range(10):
            sphere(f"snowlump{i}", rnd.uniform(0.08, 0.16), (rnd.uniform(-4, 4), rnd.uniform(1.6, 3.4), 0.0),
                   snow, scale=(1.4, 1, 0.5), sub=1)
        if kind == "christmas":  # free Kenney Holiday Kit
            kk("holiday", ["tree-decorated-snow.glb", "tree-decorated.glb"], "xtree", (0.4, 4.0, 0), 2.4, rnd=pal)
            for i, (gx, gy) in enumerate(((-0.4, 3.3), (0.0, 3.0), (1.1, 3.25), (0.7, 3.0))):
                kk("holiday", ["present-*"], f"present{i}", (gx, gy, 0), pal.uniform(0.22, 0.36), rot_z=pal.uniform(-0.6, 0.6), rnd=pal)
            kk("holiday", ["candy-cane-*"], "cane", (-3.6, 2.4, 0), 0.75, rnd=pal)
            kk("holiday", ["reindeer.glb"], "reindeer", (3.9, 3.2, 0), 1.1, rot_z=-0.4)
            kk("holiday", ["sled.glb", "sled-long.glb"], "sled", (1.9, 2.5, 0), width=0.8, rot_z=0.4, rnd=pal)
            kk("holiday", ["lantern.glb"], "lantern", (-1.5, 3.5, 0), 0.7)
            gb = kk("holiday", ["gingerbread-*"], "ginger", (-0.9, 2.9, 0), 0.45, rnd=pal)
            if gb:
                bob(gb, phase=12, height=0.1, every=46)
        _clouds()
    try:
        _dress(kind, random.Random(THEME.get("pal", 1) + 11))
    except Exception as e:  # noqa: BLE001  (decoration only)
        print("dressing skipped:", e)
    return sky


HDRI = {"day": "farm_field_puresky", "morning": "citrus_orchard_puresky", "golden": "autumn_field_puresky",
        "sunset": "belfast_sunset_puresky", "snow": "farm_field_puresky", "indoor": "brown_photostudio_02",
        "space": "brown_photostudio_02", "underwater": "farm_field_puresky", "candy": "citrus_orchard_puresky"}
HDRI_STRENGTH = {"indoor": 0.45, "snow": 0.5, "space": 0.3, "underwater": 0.45, "candy": 0.4}
ASSETS = os.environ.get("ASSETS", "")


def _hdri_path(sky):
    name = HDRI.get(sky)
    p = os.path.join(ASSETS, "hdri", f"{name}.hdr") if ASSETS and name else ""
    return p if p and os.path.exists(p) else None


_KENNEY = {}


def kenney_files(kit):
    """All .glb models of a downloaded Kenney kit (empty list when the kit isn't there)."""
    if kit not in _KENNEY:
        root = os.path.join(ASSETS, "kenney", kit)
        found = []
        for dp, _, fs in os.walk(root) if ASSETS else []:
            found += [os.path.join(dp, f) for f in fs if f.lower().endswith(".glb")]
        _KENNEY[kit] = sorted(found)
    return _KENNEY[kit]


def kenney_find(kit, patterns):
    import fnmatch
    files = kenney_files(kit)
    return [f for f in files if any(fnmatch.fnmatch(os.path.basename(f).lower(), p) for p in patterns)]


def kk(kit, pats, name, loc, h=None, rot_z=0.0, rnd=None, width=None, parent=None):
    """Place one random matching model from a free Kenney kit (None when the kit isn't downloaded)."""
    files = kenney_find(kit, pats)
    if not files:
        return None
    f = (rnd or VAR).choice(files)
    return kenney(f, name, loc, h or 1.0, parent, rot_z, width=width)


def top(root):
    """Height of the top of an imported model (to stack things on it)."""
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ v.co)[2] for o in root.children_recursive if o.type == "MESH" for v in o.data.vertices]
    return max(zs) if zs else 0.0


def bob(o, phase=0, height=0.1, every=44):
    """A little idle hop, forever (background animals)."""
    z0 = o.location.z
    for f, dz in ((1, 0), (6, height), (11, 0), (every, 0)):
        o.location.z = z0 + dz
        o.keyframe_insert("location", index=2, frame=f + phase)
    o.location.z = z0
    try:
        o.animation_data.action.fcurves.find("location", index=2).modifiers.new("CYCLES")
    except Exception:  # noqa: BLE001
        pass


def kenney(path, name, loc, height, parent=None, rot_z=0.0, width=None):
    """Import a Kenney toy model, scale it to `height` (or its footprint to `width`), stand it on the ground at loc."""
    before = set(bpy.data.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
    except Exception as e:  # noqa: BLE001
        print("kenney import failed", path, e)
        return None
    new = [o for o in bpy.data.objects if o not in before]
    if not new:
        return None
    root = empty(name, (0, 0, 0))
    for o in new:
        if o.parent is None:
            o.parent = root
        if o.type == "MESH":
            try:
                for poly in o.data.polygons:
                    poly.use_smooth = True
                o.data.set_sharp_from_angle(angle=math.radians(40))
            except Exception:  # noqa: BLE001
                pass
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in new if o.type == "MESH" for v in o.data.vertices]
    if pts:
        zs = [p[2] for p in pts]
        h = max(zs) - min(zs) or 1.0
        s = height / h
        if width:
            s = width / (max(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts)) or 1.0)
        cx = (max(p[0] for p in pts) + min(p[0] for p in pts)) / 2
        cy = (max(p[1] for p in pts) + min(p[1] for p in pts)) / 2
        for o in new:
            if o.parent is root:
                o.location = ((o.location[0] - cx), (o.location[1] - cy), o.location[2] - min(zs))
        root.scale = (s, s, s)
    root.rotation_euler = (0, 0, rot_z)
    root.location = loc
    if parent is not None:
        root.parent = parent
    return root


def make_world(sky="day"):
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    grad = nt.nodes.new("ShaderNodeTexGradient")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapn = nt.nodes.new("ShaderNodeMapping")
    mapn.inputs["Rotation"].default_value = (0, math.radians(90), 0)
    nt.links.new(coord.outputs["Generated"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    lo, hi = SKY.get(sky, SKY["day"])
    ramp.color_ramp.elements[0].color = (*lin(lo), 1)
    ramp.color_ramp.elements[1].color = (*lin(hi), 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.35 if sky == "indoor" else (0.85 if sky == "snow" else 0.7 if sky == "space" else 1.0)
    hdri = _hdri_path(sky)
    if hdri:  # real sky photo lights the scene (soft, rich light); the camera still sees our cartoon sky
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri)  # (no vector input = looks along the view direction)
        hbg = nt.nodes.new("ShaderNodeBackground")
        nt.links.new(env.outputs["Color"], hbg.inputs["Color"])
        hbg.inputs["Strength"].default_value = HDRI_STRENGTH.get(sky, 0.6)
        lp = nt.nodes.new("ShaderNodeLightPath")
        mix = nt.nodes.new("ShaderNodeMixShader")
        out = nt.nodes["World Output"]
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
        nt.links.new(hbg.outputs["Background"], mix.inputs[1])
        nt.links.new(bg.outputs["Background"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    soft = 0.7 if hdri else 1.0  # the sky photo already adds light

    def light(name, kind, energy, loc=None, rot=None, size=None, color=(1, 1, 1), angle=None, target=None):
        d = bpy.data.lights.new(name, kind)
        d.energy, d.color = energy, color
        if size is not None:
            d.size = size
        if angle is not None:
            d.angle = angle
        o = bpy.data.objects.new(name, d)
        sc.collection.objects.link(o)
        if loc:
            o.location = loc
        if rot:
            o.rotation_euler = rot
        if target is not None:
            tr = o.constraints.new("TRACK_TO")
            tr.target, tr.track_axis, tr.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
        return o

    sun_e = (1.3 if sky == "indoor" else (2.4 if sky == "snow" else 3.2)) * soft
    light("sun", "SUN", sun_e, rot=(math.radians(50), math.radians(10), math.radians(-35)), color=SUN.get(sky, (1, 0.93, 0.82)),
          angle=math.radians(4))
    light("fill", "AREA", (300 if sky != "indoor" else 220) * soft, (-2, -5, 3), (math.radians(60), 0, math.radians(-25)), 6,
          (0.9, 0.95, 1))
    light("rim", "AREA", 500, (2.5, 3.0, 2.6), size=2.5, color=(0.85, 0.92, 1), target=empty("rim_t", (0, 0.2, 0.6)))
    if sky == "indoor":
        light("ceiling", "AREA", 120, (0.3, 1.2, 4.2), (0, 0, 0), 3, (1, 0.95, 0.85))


def make_camera():
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 45
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


def fit(xs, lens=40, zc=0.85, y=0.2, margin=0.4, cam_z=None, min_d=2.2, max_d=4.8):
    """Camera position + target that frame the x-range xs (portrait 9:16): low camera looking slightly up,
    characters big in the lower part of the frame (less empty ground)."""
    x0, x1 = min(xs), max(xs)
    width = (x1 - x0) + 2 * margin
    d = min(max_d, max(min_d, width * lens / (36 * 9 / 16)))
    cx = (x0 + x1) / 2
    return (cx, y - d, cam_z if cam_z is not None else max(0.45, zc - 0.3)), (cx, y, zc)


def shot(cam, tgt, f0, f1, pos0, tgt0, lens, pos1=None, tgt1=None):
    """A camera shot from f0 to f1 (hard cut at both ends), optional slow move."""
    key(cam, "location", f0, pos0)
    key(tgt, "location", f0, tgt0)
    key(cam.data, "lens", f0, lens)
    key(cam, "location", f1, pos1 or pos0, "CONSTANT")
    key(tgt, "location", f1, tgt1 or tgt0, "CONSTANT")
    key(cam.data, "lens", f1, lens, "CONSTANT")


# ------------------------------------------------------------------ acting
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


def eyes_happy(ch, f, d=3):
    """^^ closed happy eyes."""
    for e in ch["eyes"]:
        key(e, "scale", f - d, tuple(e.scale))
        key(e, "scale", f, (1.1, 1, 0.22))


def brows(ch, f, up=0.0, d=4):
    for b in ch.get("brows", []):
        z0 = b["z0"]
        key(b, "location", f - d, tuple(b.location))
        key(b, "location", f, (b.location[0], b.location[1], z0 + up))


def look(ch, f, dx, dz=0.0):
    for p in ch["pupils"]:
        key(p, "location", f, (dx, p.location[1], dz))


def mouth_set(ch, f, open_z, w=1.0):
    """open_z <= 0.2 -> closed smile; bigger -> open oval mouth of that height."""
    m, sm = ch.get("mouth"), ch.get("smile")
    if m is None:
        return
    is_open = open_z > 0.2
    key(m, "scale", f, (w, 0.35, open_z if is_open else 0.05))
    if sm is not None:
        for o, hide in ((sm, is_open), (m, not is_open)):
            o.hide_render = hide
            o.keyframe_insert(data_path="hide_render", frame=f)
        for c in m.children:
            c.hide_render = not is_open
            c.keyframe_insert(data_path="hide_render", frame=f)


def arms(ch, f, angle, fwd=0.0, d=4, hold=True):
    """Raise both arms sideways by angle (radians), optionally forward."""
    for a in ch["arms"]:
        side = 1 if a.location[0] > 0 else -1
        if hold:
            key(a, "rotation_euler", f - d, tuple(a.rotation_euler))
        key(a, "rotation_euler", f, (fwd, -side * angle, 0))


def turn(ch, f, deg, d=6):
    r = ch["root"]
    key(r, "rotation_euler", f - d, tuple(r.rotation_euler))
    key(r, "rotation_euler", f, (0, 0, math.radians(deg)))


def lean(ch, f, deg, d=6, axis=1):
    p = ch["piv"]
    rot = [0, 0, 0]
    rot[axis] = math.radians(deg)
    key(p, "rotation_euler", f - d, tuple(p.rotation_euler))
    key(p, "rotation_euler", f, tuple(rot))


def squash(ch, f, amt=0.18, d=3, back=5):
    p = ch["piv"]
    key(p, "scale", f - d, (1, 1, 1))
    key(p, "scale", f, (1 + amt * 0.7, 1 + amt * 0.7, 1 - amt))
    key(p, "scale", f + back, (1, 1, 1))


def stretch(ch, f, amt=0.18, d=3, back=5):
    p = ch["piv"]
    key(p, "scale", f - d, (1, 1, 1))
    key(p, "scale", f, (1 - amt * 0.5, 1 - amt * 0.5, 1 + amt))
    key(p, "scale", f + back, (1, 1, 1))


def place(ch, f, x, y=None, z=0.0, interp=None):
    r = ch["root"]
    key(r, "location", f, (x, r.location[1] if y is None else y, z), interp)


def hop(ch, f0, x0, x1, h=0.4, n=12, y0=None, y1=None, sound=True):
    r, p = ch["root"], ch["piv"]
    y0 = r.location[1] if y0 is None else y0
    y1 = y0 if y1 is None else y1
    if sound:
        sfx(f0 + 2, "boing")
        sfx(f0 + n, "land")
    key(p, "scale", f0, (1, 1, 1))
    key(p, "scale", f0 + 2, (1.12, 1.12, 0.82))
    key(r, "location", f0 + 2, (x0, y0, 0))
    key(p, "scale", f0 + 5, (0.92, 0.92, 1.15))
    key(r, "location", f0 + n // 2 + 1, ((x0 + x1) / 2, (y0 + y1) / 2, h))
    key(p, "scale", f0 + n - 1, (0.95, 0.95, 1.08))
    key(r, "location", f0 + n, (x1, y1, 0))
    key(p, "scale", f0 + n + 1, (1.15, 1.15, 0.8))
    key(p, "scale", f0 + n + 5, (1, 1, 1))
    for a in ch["arms"]:
        side = 1 if a.location[0] > 0 else -1
        key(a, "rotation_euler", f0 + 2, (0, 0, 0))
        key(a, "rotation_euler", f0 + 6, (0, -side * 1.6, 0))
        key(a, "rotation_euler", f0 + n + 2, (0, 0, 0))
    return f0 + n + 5


def jump_joy(ch, f0, h=0.45, n=12, times=2, sound="ding"):
    """Happy jumps in place with arms up."""
    r = ch["root"]
    x, y = r.location[0], r.location[1]
    if sound:
        sfx(f0, sound)
    eyes_happy(ch, f0 + 2)
    mouth_set(ch, f0 + 2, 0.7, 1.1)
    if sound:
        sfx(f0 + 4, "xylo_up")
    f = f0
    for _ in range(times):
        hop(ch, f, x, x, h, n, y, y, sound=False)
        sfx(f + 2, "boing")
        f += n + 2
    arms(ch, f0 + 6, 2.4)
    return f


def laugh(ch, f0, f1, sound=True):
    """Giggle: closed happy eyes, open mouth, quick little body bounces."""
    eyes_happy(ch, f0 + 2)
    mouth_set(ch, f0 + 2, 0.75, 1.1)
    p = ch["piv"]
    f, k = f0, 0
    if sound:
        sfx(f0, "giggle")
    while f < f1:
        key(p, "scale", f, (1.06, 1.06, 0.92) if k % 2 else (0.97, 0.97, 1.05))
        if sound and k % 4 == 2 and f > f0 + 10:
            sfx(f, "squeak" if k % 8 == 2 else "tick")
        f += 3
        k += 1
    key(p, "scale", f1, (1, 1, 1))
    eyes_norm(ch, f1 + 3)
    mouth_set(ch, f1 + 3, 0.0)


def idle(ch, f0, f1, period=24, amt=0.03):
    p = ch["piv"]
    f = f0
    while f < f1:
        key(p, "scale", f, (1, 1, 1))
        key(p, "scale", f + period // 2, (1 + amt * 0.5, 1 + amt * 0.5, 1 - amt))
        f += period


def wobble(obj, f0, f1, amp=8, step=3, axis=2, sound="tick"):
    """Shake an object (rotation) - gift boxes, bushes, dizzy heads."""
    k = 0
    for f in range(f0, f1, step):
        rot = [0, 0, 0]
        rot[axis] = math.radians(amp if k % 2 else -amp)
        key(obj, "rotation_euler", f, tuple(rot))
        if sound and k % 2 == 0:
            sfx(f, sound)
        k += 1
    key(obj, "rotation_euler", f1, (0, 0, 0))


def dizzy_stars(ch, f0, f1, n=3):
    """Little stars circling over the head."""
    top = ch["top"] + 0.1
    orb = empty(ch["name"] + "_stars", (0, 0, top), ch["piv"])
    for i in range(n):
        a = i / n * math.tau
        star(f"{ch['name']}_star{i}", 0.07, (math.cos(a) * 0.32, math.sin(a) * 0.32, 0), mat("#FFD23F", 0.3, emit=0.6),
             orb)
    show(orb, 1, False)
    show(orb, f0, True)
    show(orb, f1, False)
    key(orb, "rotation_euler", f0, (0, 0, 0))
    key(orb, "rotation_euler", f1, (0, 0, math.radians(720)))
    for fc in orb.animation_data.action.fcurves:
        if fc.data_path == "rotation_euler":
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    sfx(f0, "sparkle")
    for f in range(f0 + 12, f1 - 6, 22):
        sfx(f, "tweet" if (f - f0) % 44 == 12 else "twinkle")


# ------------------------------------------------------------------ render
def use_gpu():
    """Render on the graphics card(s) when there is one (Kaggle's free GPU). Returns the device names."""
    if not os.environ.get("GPU"):
        return []
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except Exception:  # noqa: BLE001
        return []
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == kind]
            if devs:
                for d in prefs.devices:
                    d.use = d.type == kind
                return [f"{kind}:{d.name}" for d in devs]
        except Exception:  # noqa: BLE001
            continue
    return []


GPU_DEVICES = None


def setup_render(samples=20, res=100):
    global GPU_DEVICES
    R = sc.render
    R.engine = "CYCLES"
    if GPU_DEVICES is None:
        GPU_DEVICES = use_gpu()
        print("render devices:", GPU_DEVICES or "CPU", flush=True)
    sc.cycles.device = "GPU" if GPU_DEVICES else "CPU"
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 2
    sc.cycles.transparent_max_bounces = 2
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    try:  # faster: light that has bounced once is finished with a cheap ambient-occlusion guess (soft toon look stays)
        sc.cycles.use_fast_gi = True
        sc.cycles.fast_gi_method = "REPLACE"
        sc.cycles.ao_bounces_render = 1
        sc.world.light_settings.distance = 2.0
    except Exception:  # noqa: BLE001
        pass
    sc.cycles.light_sampling_threshold = 0.02
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = -0.2
    R.resolution_x, R.resolution_y = 1080, 1920
    R.resolution_percentage = res
    R.use_persistent_data = True
    sc.cycles.samples = samples
    if GPU_DEVICES:  # the GPU has time for more: more light bounces + a touch of motion blur on fast moves
        sc.cycles.max_bounces = 6
        sc.cycles.diffuse_bounces = 3
        sc.cycles.glossy_bounces = 3
        try:
            sc.cycles.denoising_use_gpu = True
        except Exception:  # noqa: BLE001
            pass
        R.use_motion_blur = True
        R.motion_blur_shutter = 0.3
    R.image_settings.file_format = "PNG"
    R.image_settings.color_mode = "RGB"


def render_frames(out, mode, thumb_frame=None):
    import time
    os.makedirs(f"{out}/frames", exist_ok=True)
    json.dump({"fps": FPS, "frames": sc.frame_end, "events": sorted(EVENTS), "thumb": thumb_frame},
              open(f"{out}/events.json", "w"))
    if mode == "stills":
        frames = sorted({sc.frame_start + 10, thumb_frame or 60, sc.frame_end // 2, sc.frame_end - 10})
    elif mode.startswith("part:"):
        k, n = (int(v) for v in mode.split(":")[1].split("/"))
        frames = list(range(sc.frame_start + k, sc.frame_end + 1, n))
    elif mode.startswith("every:"):
        n = int(mode.split(":")[1])
        frames = list(range(sc.frame_start + n // 2, sc.frame_end + 1, n))
    elif mode == "none":
        frames = []
    else:
        frames = list(range(sc.frame_start, sc.frame_end + 1))
    for f in frames:
        t0 = time.time()
        sc.frame_set(f)
        sc.render.filepath = f"{out}/frames/f_{f:04d}.png"
        bpy.ops.render.render(write_still=True)
        print(f"frame {f} in {time.time() - t0:.1f}s", flush=True)
    print("done", len(frames), "frames", flush=True)
