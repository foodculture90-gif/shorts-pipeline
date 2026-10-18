"""Toon kit: everything needed to build a little 3D cartoon in Blender from code.

Materials, shapes, the recurring cast, props, sets, lights, camera moves, animation moves and the
sound-effect cue list (EVENTS -> blender/audio.py). Used by blender/gags.py + blender/scene.py.
"""
import json, math, os, random

import bpy

FPS = 24
MATS = {}
EVENTS = []  # [frame, sound kind]
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
}


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


def make_character(name, x=0.0, y=0.0, z=0.0):
    d = CAST[name]
    root = empty(name, (x, y, z))
    root.scale = (d["size"],) * 3
    piv = empty(name + "_piv", (0, 0, 0), root)  # squash & stretch from the floor
    ch = dict(name=name, root=root, piv=piv, mouth=None, smile=None, size=d["size"])
    if d["kind"] == "bird":
        yel = mat(d["body"], 0.5)
        sphere(name + "_body", 0.34, (0, 0, 0.38), yel, piv, scale=(1, 0.95, 1.08), sub=2)
        sphere(name + "_tuft", 0.07, (0, 0, 0.76), yel, piv, scale=(0.6, 0.6, 1.6), rot=(0.3, 0, 0))
        sphere(name + "_belly", 0.2, (0, -0.2, 0.3), mat("#FFF1B8", 0.6), piv, scale=(1, 0.5, 0.9), sub=2)
        ev, pp, br = eyes(piv, -0.285, 0.5, 0.12, 0.11, d["iris"])
        cone(name + "_beak", 0.07, 0.0, 0.14, (0, -0.33, 0.37), mat(d["beak"], 0.4), piv, rot=(math.radians(90), 0, 0))
        arms = []
        for side in (-1, 1):
            sh = empty(f"{name}_wing{side}", (side * 0.32, 0, 0.4), piv)
            sphere(f"{name}_w{side}", 0.1, (side * 0.04, 0, -0.06), yel, sh, scale=(0.5, 0.9, 1.4), rot=(0, side * 0.3, 0))
            arms.append(sh)
        feet = [sphere(f"{name}_foot{s}", 0.07, (s * 0.12, -0.06, 0.03), mat(d["beak"], 0.4), root, scale=(1, 1.6, 0.5))
                for s in (-1, 1)]
        ch.update(eyes=ev, pupils=pp, brows=br, arms=arms, feet=feet, top=0.85, head=0.5)
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
            sphere(f"{name}_ear{side}", 0.15, (side * 0.3, 0.02, 1.0), body_m, piv, scale=(0.8, 0.6, 1.2), rot=(0, side * 0.5, 0))
        elif ears == "bunny":
            e = sphere(f"{name}_ear{side}", 0.11, (side * 0.17, 0.05, 1.22), body_m, piv, scale=(0.75, 0.5, 2.6),
                       rot=(0, side * 0.22, 0))
            sphere(f"{name}_earin{side}", 0.07, (0, -0.05, 0.0), mat("#FFB3CF", 0.6), e, scale=(0.8, 0.4, 0.85))
        elif ears == "cat":
            cone(f"{name}_ear{side}", 0.14, 0.02, 0.28, (side * 0.27, 0.0, 1.03), body_m, piv, rot=(0, side * 0.45, 0))
    if d.get("tuft"):
        sphere(name + "_tuft", 0.09, (0.04, 0.0, 1.08), body_m, piv, scale=(0.7, 0.7, 1.5), rot=(0, 0.35, 0))
        sphere(name + "_tuft2", 0.07, (-0.06, 0.02, 1.06), body_m, piv, scale=(0.7, 0.7, 1.3), rot=(0, -0.4, 0))
    if d.get("tail"):
        sphere(name + "_tail", 0.1, (0.0, 0.45, 0.25), body_m, piv, scale=(0.8, 1.6, 0.8), rot=(0.6, 0, 0))
    if d.get("eyes_top"):
        ev, pp, br = eyes(piv, -0.22, 1.0, 0.2, 0.17, d["iris"], mat(d["brow"], 0.5))
        for e in ev:  # eye bumps on top (frog-ish)
            sphere(e.name + "_lid", 0.2, (0, 0.04, -0.02), body_m, e, scale=(1, 0.8, 0.9))
    else:
        ev, pp, br = eyes(piv, -0.405, 0.74, 0.175, 0.165, d["iris"], mat(d["brow"], 0.5))
    mouth = sphere(name + "_mouth", 0.1, (0, -0.455, 0.44), mat("#5A1020", 0.4), piv, scale=(1.2, 0.35, 0.05))
    sphere(name + "_tongue", 0.06, (0, -0.02, -0.04), mat("#FF5A7A", 0.5), mouth, scale=(1, 0.8, 0.5))
    w = 0.085
    smile = curve_line(name + "_smile", [(-w, 0, w * 0.45), (0, 0, -w * 0.25), (w, 0, w * 0.45)], 0.014,
                       mat("#5A1020", 0.4), piv, (0, -0.475, 0.455))
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
    return ch


# ------------------------------------------------------------------ props
def make_prop(kind, loc, parent=None, name=None):
    name = name or kind
    root = empty(name, loc, parent)
    if kind == "cake":
        cyl(name + "_plate", 0.24, 0.02, (0, 0, 0.01), WHITE, root, bevel=0.008)
        cyl(name + "_body", 0.19, 0.16, (0, 0, 0.1), mat("#FFB3CF", 0.5), root, bevel=0.03)
        cyl(name + "_icing", 0.2, 0.05, (0, 0, 0.19), mat("#FFFFFF", 0.3, coat=0.5), root, bevel=0.025)
        for i in range(10):
            a = i / 10 * math.tau
            sphere(f"{name}_drip{i}", 0.03, (math.cos(a) * 0.195, math.sin(a) * 0.195, 0.155),
                   mat("#FFFFFF", 0.3, coat=0.5), root, scale=(1, 1, 1.6), sub=0)
        sphere(name + "_cherry", 0.045, (0, 0, 0.255), mat("#E0102F", 0.2, coat=1), root, sub=1)
    elif kind == "icecream":
        cone(name + "_cone", 0.02, 0.1, 0.26, (0, 0, 0.13), checker("#E8B36A", "#C98B3F", 14, 0.6), root)
        sphere(name + "_s1", 0.105, (0, 0, 0.29), mat("#FF9EC4", 0.4, coat=0.3), root)
        sphere(name + "_s2", 0.09, (0, 0, 0.42), mat("#FFF4D6", 0.4, coat=0.3), root)
        sphere(name + "_cherry", 0.035, (0, 0, 0.53), mat("#E0102F", 0.2, coat=1), root, sub=1)
    elif kind == "cookie":
        cyl(name + "_plate", 0.2, 0.02, (0, 0, 0.01), WHITE, root, bevel=0.008)
        cyl(name + "_body", 0.15, 0.04, (0, 0, 0.045), mat("#D99A4E", 0.7), root, bevel=0.015)
        for i, (cx, cy) in enumerate(((0.05, 0.03), (-0.06, 0.04), (0.0, -0.07), (-0.03, -0.02), (0.08, -0.05))):
            sphere(f"{name}_chip{i}", 0.022, (cx, cy, 0.068), mat("#4A2A12", 0.5), root, sub=0)
    elif kind == "apple":
        sphere(name + "_body", 0.13, (0, 0, 0.13), mat("#E8232F", 0.25, coat=1), root, scale=(1, 1, 0.9))
        cyl(name + "_stem", 0.012, 0.07, (0, 0, 0.27), mat("#6B4423", 0.6), root)
        sphere(name + "_leaf", 0.04, (0.04, 0, 0.27), mat("#3FB64E", 0.5), root, scale=(1.4, 0.3, 0.6), rot=(0, -0.5, 0))
    elif kind == "ball":
        sphere(name + "_body", 0.18, (0, 0, 0.18), checker("#FF3B4E", "#FFFFFF", 2.0, 0.3, 0.6), root, sub=2)
    elif kind == "balloon":
        b = sphere(name + "_body", 0.24, (0, 0, 0.0), mat("#FF3B6E", 0.15, coat=1.0), root, scale=(1, 1, 1.2), sub=2)
        cone(name + "_knot", 0.035, 0.0, 0.05, (0, 0, -0.29), mat("#FF3B6E", 0.2), root, rot=(math.pi, 0, 0))
        curve_line(name + "_string", [(0, 0, -0.3), (0.03, 0, -0.55), (-0.02, 0, -0.85)], 0.006, mat("#FFFFFF", 0.5), root)
    elif kind == "gift":
        wall = mat("#4DA6FF", 0.4, coat=0.3)
        s = 0.62
        box(name + "_bottom", (s, s, 0.04), (0, 0, 0.02), wall, root, bevel=0.01)
        for i, (px, py, sx, sy) in enumerate(((0, -s / 2, s, 0.04), (0, s / 2, s, 0.04), (-s / 2, 0, 0.04, s), (s / 2, 0, 0.04, s))):
            box(f"{name}_wall{i}", (sx, sy, s), (px, py, s / 2), wall, root, bevel=0.012)
        rib = mat("#FFD23F", 0.3, coat=0.5)
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
        g = mat("#45B85A", 0.75)
        for j, (ox, oz, rr) in enumerate(((0, 0.32, 0.42), (0.36, 0.25, 0.32), (-0.34, 0.24, 0.3), (0.12, 0.6, 0.28))):
            sphere(f"{name}_{j}", rr, (ox, 0, oz), g, root, sub=1)
        for j in range(5):
            sphere(f"{name}_berry{j}", 0.035, (-0.3 + j * 0.15, -0.35, 0.3 + (j % 2) * 0.15), mat("#FF4D6D", 0.3, coat=1), root, sub=0)
    return root


def make_table(loc, color="#FF7AA8"):
    t = empty("table", loc)
    cyl("table_leg", 0.06, 0.62, (0, 0, 0.31), mat("#FFFFFF", 0.4), t)
    cyl("table_foot", 0.2, 0.03, (0, 0, 0.015), mat("#FFFFFF", 0.4), t, bevel=0.01)
    cyl("table_top", 0.42, 0.06, (0, 0, 0.64), mat(color, 0.35, coat=0.3), t, bevel=0.02)
    return t


# ------------------------------------------------------------------ sets
SKY = {"day": ("#D8F1FF", "#5EB8FF"), "sunset": ("#FFD6A8", "#7A8CFF"), "indoor": ("#FFF4E6", "#FFE0C2")}


def _clouds(z0=5.5, y=14):
    cloud = mat("#FFFFFF", 0.9)
    for i, (cx, cz) in enumerate(((-3.5, z0), (1.5, z0 + 0.9), (5.5, z0 - 0.3))):
        for j, (ox, oz, rr) in enumerate(((0, 0, 0.7), (0.7, -0.15, 0.5), (-0.7, -0.15, 0.5), (0.3, 0.35, 0.5))):
            sphere(f"cloud{i}{j}", rr, (cx + ox, y, cz + oz), cloud, scale=(1.2, 0.6, 1), sub=1)


def _trees(xs, y, crown="#3FB64E"):
    for i, tx in enumerate(xs):
        cyl(f"trunk{i}", 0.09, 0.9, (tx, y, 0.45), mat("#9A6A43", 0.7))
        sphere(f"crown{i}", 0.55, (tx, y, 1.25), mat(crown, 0.7), sub=1)
        sphere(f"crownb{i}", 0.38, (tx + 0.3, y + 0.1, 1.05), mat(crown, 0.7), sub=1)


def _flowers(n, y0, y1, xs=(-4, 4), rnd=None):
    rnd = rnd or random.Random(3)
    cols = ("#FF6B8B", "#FFFFFF", "#FFD53D", "#B57BFF", "#FF8A3D")
    for i in range(n):
        x, y = rnd.uniform(*xs), rnd.uniform(y0, y1)
        cyl(f"stem{i}", 0.008, 0.14, (x, y, 0.07), mat("#3FA64E", 0.6))
        sphere(f"flower{i}", 0.045, (x, y, 0.15), mat(cols[i % len(cols)], 0.5), sub=0, scale=(1, 1, 0.6))


def make_set(kind, rnd=None):
    rnd = rnd or random.Random(1)
    sky = "day"
    if kind == "street":
        box("ground", (40, 40, 0.2), (0, 6, -0.1), mat("#6CCB5F", 0.8), bevel=0)
        box("path", (40, 2.4, 0.02), (0, 0.4, 0.005), mat("#E3B98A", 0.85), bevel=0)
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
        cyl("lamp", 0.05, 2.2, (-2.6, 1.9, 1.1), mat("#2E3A59", 0.4))
        sphere("lampbulb", 0.16, (-2.6, 1.9, 2.25), mat("#FFF2B3", 0.3, emit=1.5), sub=1)
        _trees((-4.5, -1.9, 1.0, 3.6, 6.2), 3.2)
        _clouds()
    elif kind == "park":
        box("ground", (40, 40, 0.2), (0, 6, -0.1), mat("#73D165", 0.85), bevel=0)
        for i, (hx, hr, c) in enumerate(((-5, 4, "#5DBE55"), (1, 5, "#69C95E"), (7, 4.5, "#5DBE55"))):
            sphere(f"hill{i}", hr, (hx, 14, -hr * 0.55), mat(c, 0.9), scale=(1.6, 1, 1), sub=1)
        _trees((-3.8, -1.4, 2.4, 4.6), 3.6, "#47B856")
        _trees((-6.0, 0.6, 6.5), 6.5, "#3CA84C")
        pond = cyl("pond", 1.4, 0.02, (2.6, 2.6, 0.012), mat("#4FB3FF", 0.05, coat=1.0), scale=(1.6, 0.7, 1))
        for i in range(6):
            a = i / 6 * math.tau
            sphere(f"rock{i}", 0.12, (2.6 + math.cos(a) * 2.2, 2.6 + math.sin(a) * 0.95, 0.04), mat("#B8B8C8", 0.7),
                   scale=(1.3, 1, 0.6))
        bench = empty("bench", (-2.2, 2.2, 0))
        box("bench_seat", (1.4, 0.38, 0.07), (0, 0, 0.42), mat("#C0763C", 0.6), bench, bevel=0.02)
        box("bench_back", (1.4, 0.06, 0.32), (0, 0.18, 0.66), mat("#C0763C", 0.6), bench, bevel=0.02)
        for sx in (-0.6, 0.6):
            box(f"bench_leg{sx}", (0.06, 0.34, 0.42), (sx, 0, 0.21), mat("#2E3A59", 0.4), bench, bevel=0.01)
        _flowers(26, 1.6, 4.0, rnd=rnd)
        for i, bx in enumerate((-4.5, 0.2, 4.2)):
            make_prop("bush", (bx, 3.3, 0), name=f"pbush{i}")
        _clouds()
    elif kind == "beach":
        box("ground", (40, 9, 0.2), (0, 2.5, -0.1), mat("#F6D59A", 0.9), bevel=0)
        box("sea", (60, 40, 0.1), (0, 26, -0.07), mat("#2FA8E8", 0.08, coat=1.0), bevel=0)
        box("foam", (60, 0.25, 0.02), (0, 7.05, 0.0), mat("#FFFFFF", 0.4), bevel=0)
        um = empty("umbrella", (-2.3, 2.6, 0))
        cyl("um_pole", 0.03, 1.9, (0, 0, 0.95), mat("#FFFFFF", 0.4), um)
        cone("um_top", 1.0, 0.05, 0.4, (0, 0, 1.95), checker("#FF4D5E", "#FFFFFF", 3.0, 0.5), um)
        castle = empty("castle", (2.4, 2.8, 0))
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
        towel = box("towel", (1.0, 0.6, 0.01), (-2.0, 1.6, 0.005), checker("#4DA6FF", "#FFFFFF", 4.0, 0.7), bevel=0)
        _clouds(6)
    elif kind == "kitchen":
        sky = "indoor"
        box("floor", (14, 10, 0.2), (0, 3, -0.1), checker("#FFFFFF", "#9FD9F5", 9.0, 0.3, 0.2), bevel=0)
        wall_m = mat("#FFE7B8", 0.8)
        box("wall", (14, 0.2, 5), (0, 4.0, 2.5), wall_m, bevel=0)
        box("skirting", (14, 0.05, 0.15), (0, 3.88, 0.075), WHITE, bevel=0.01)
        box("win_frame", (1.7, 0.1, 1.3), (-1.2, 3.86, 2.1), WHITE, bevel=0.04)
        box("win_sky", (1.5, 0.1, 1.1), (-1.2, 3.84, 2.1), mat("#9FD8FF", 0.5, emit=1.2), bevel=0.02)
        box("win_cross_v", (0.06, 0.1, 1.1), (-1.2, 3.8, 2.1), WHITE, bevel=0.01)
        box("win_cross_h", (1.5, 0.1, 0.06), (-1.2, 3.8, 2.1), WHITE, bevel=0.01)
        cnt = mat("#7FD1B9", 0.5)
        box("counter", (3.2, 0.7, 0.9), (2.2, 3.5, 0.45), cnt, bevel=0.04)
        box("counter_top", (3.3, 0.8, 0.08), (2.2, 3.48, 0.94), mat("#FFFFFF", 0.3, coat=0.4), bevel=0.02)
        for i in range(3):
            box(f"drawer{i}", (0.95, 0.04, 0.7), (1.15 + i * 1.05, 3.13, 0.45), mat("#9BE0CB", 0.5), bevel=0.03)
            sphere(f"handle{i}", 0.035, (1.15 + i * 1.05, 3.1, 0.65), mat("#FFD23F", 0.2, coat=1), sub=0)
        box("fridge", (1.0, 0.8, 2.1), (-3.4, 3.45, 1.05), mat("#FF9EC4", 0.35, coat=0.4), bevel=0.1)
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
        box("rug", (2.6, 1.6, 0.012), (0, 0.6, 0.006), checker("#FFB3CF", "#FFFFFF", 5.0, 0.8), bevel=0)
    return sky


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
    bg.inputs["Strength"].default_value = 0.8 if sky == "indoor" else 1.0

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

    sun_e = 2.2 if sky == "indoor" else 3.2
    light("sun", "SUN", sun_e, rot=(math.radians(50), math.radians(10), math.radians(-35)), color=(1, 0.93, 0.82),
          angle=math.radians(4))
    light("fill", "AREA", 300 if sky != "indoor" else 450, (-2, -5, 3), (math.radians(60), 0, math.radians(-25)), 6,
          (0.9, 0.95, 1))
    light("rim", "AREA", 500, (2.5, 3.0, 2.6), size=2.5, color=(0.85, 0.92, 1), target=empty("rim_t", (0, 0.2, 0.6)))
    if sky == "indoor":
        light("ceiling", "AREA", 250, (0.3, 1.2, 4.2), (0, 0, 0), 3, (1, 0.95, 0.85))


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


def fit(xs, lens=40, zc=0.62, y=0.2, margin=0.75, cam_z=None, min_d=2.2):
    """Camera position + target that frame the x-range xs (portrait 9:16)."""
    x0, x1 = min(xs), max(xs)
    width = (x1 - x0) + 2 * margin
    d = max(min_d, width * lens / (36 * 9 / 16))
    cx = (x0 + x1) / 2
    return (cx, y - d, cam_z if cam_z is not None else zc + 0.15), (cx, y, zc)


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
    while f < f1:
        key(p, "scale", f, (1.06, 1.06, 0.92) if k % 2 else (0.97, 0.97, 1.05))
        if sound and k % 2 == 0:
            sfx(f, "tick")
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


# ------------------------------------------------------------------ render
def setup_render(samples=20, res=100):
    R = sc.render
    R.engine = "CYCLES"
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
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = -0.2
    R.resolution_x, R.resolution_y = 1080, 1920
    R.resolution_percentage = res
    R.use_persistent_data = True
    sc.cycles.samples = samples
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
