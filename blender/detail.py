"""Makes every set richer and less 'basic shapes' after it is built (scene.py calls enrich()).

  - every surface gets gentle colour variation + a fine surface texture (no flat plastic)
  - leaves (tree crowns, bushes, hedges) become lumpy, leafy clumps; clouds become puffy
  - trunks get bark, house walls get bricks/planks, roofs get tiles, wood gets grain
  - grass blades on grassy ground, pebbles on sand
  - far away: rolling hills with little trees, and now and then a hot-air balloon or a kite in the sky
Characters are left alone (they have their own look in sculpt.py).
"""
import colorsys
import os
import math
import random

import bpy
from mathutils import Vector

import toon as T

DONE = set()


def _char_objects():
    out = set()
    for ch in T.CHARS:
        out.add(ch["root"])
        out.update(ch["root"].children_recursive)
    return out


def _base_color(m):
    if not (m and m.use_nodes and "Principled BSDF" in m.node_tree.nodes):
        return None
    inp = m.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
    if inp.is_linked:
        return None
    return tuple(inp.default_value[:3])


def _hsv(c):
    g = [max(0.0, v) ** (1 / 2.2) for v in c]
    return colorsys.rgb_to_hsv(*g)


def _kind(o, c):
    """What a part is, from its name and colour."""
    n = o.name.lower()
    if any(k in n for k in ("cloud",)):
        return "cloud"
    if any(k in n for k in ("trunk", "log", "stump")):
        return "bark"
    if any(k in n for k in ("roof",)):
        return "roof"
    if any(k in n for k in ("house", "wall", "tower", "castle", "shop", "barn", "hut")):
        return "wall"
    if any(k in n for k in ("crown", "bush", "hedge", "shrub", "leaf", "tree", "pine", "palm", "jungle")):
        return "leaf"
    if c is not None and not any(k in n for k in ("ball", "gift", "balloon", "apple", "hat", "treat", "cup", "prop")):
        h, s, v = _hsv(c)
        if 0.04 < h < 0.12 and s > 0.35 and 0.25 < v < 0.75 and o.type == "MESH" and o.get("r") is None:
            return "wood"
    return "plain"


# ------------------------------------------------------------------ materials
def _nodes(m):
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    return nt, b, tc


def _vary(m, c, scale=2.5, amt=0.1, bump=0.08, bump_scale=35.0, pattern=None):
    """Colour variation + fine texture; pattern = (node type, settings) for bricks/planks/tiles/grain."""
    nt, b, tc = _nodes(m)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 4.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    lo = tuple(max(0.0, v * (1 - amt * 1.4)) for v in c)
    hi = tuple(min(1.0, v * (1 + amt)) for v in c)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.3, (*lo, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.7, (*hi, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    col_out = ramp.outputs["Color"]
    height = None
    if pattern == "brick":
        br = nt.nodes.new("ShaderNodeTexBrick")
        br.inputs["Scale"].default_value = 9.0
        br.inputs["Mortar Size"].default_value = 0.015
        br.inputs["Color1"].default_value = (*c, 1)
        br.inputs["Color2"].default_value = (*lo, 1)
        br.inputs["Mortar"].default_value = (*tuple(min(1.0, v * 1.25 + 0.05) for v in c), 1)
        nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["Factor"].default_value = 0.35
        nt.links.new(col_out, mix.inputs["A"])
        nt.links.new(br.outputs["Color"], mix.inputs["B"])
        col_out, height = mix.outputs["Result"], br.outputs["Fac"]
    elif pattern in ("tiles", "grain"):
        wv = nt.nodes.new("ShaderNodeTexWave")
        wv.wave_type = "BANDS"
        wv.bands_direction = "Z" if pattern == "tiles" else "X"
        wv.inputs["Scale"].default_value = 7.0 if pattern == "tiles" else 4.0
        wv.inputs["Distortion"].default_value = 0.5 if pattern == "tiles" else 6.0
        wv.inputs["Detail"].default_value = 2.0
        nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["Factor"].default_value = 0.22
        dk = nt.nodes.new("ShaderNodeRGB")
        dk.outputs[0].default_value = (*lo, 1)
        nt.links.new(col_out, mix.inputs["A"])
        nt.links.new(dk.outputs[0], mix.inputs["B"])
        nt.links.new(wv.outputs["Fac"], mix.inputs["Factor"])
        col_out, height = mix.outputs["Result"], wv.outputs["Fac"]
    nt.links.new(col_out, b.inputs["Base Color"])
    if bump:
        fz = nt.nodes.new("ShaderNodeTexNoise")
        fz.inputs["Scale"].default_value = bump_scale
        fz.inputs["Detail"].default_value = 3.0
        nt.links.new(tc.outputs["Object"], fz.inputs["Vector"])
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.02
        if height is not None:
            add = nt.nodes.new("ShaderNodeMath")
            add.operation = "ADD"
            nt.links.new(fz.outputs["Fac"], add.inputs[0])
            nt.links.new(height, add.inputs[1])
            nt.links.new(add.outputs[0], bp.inputs["Height"])
        else:
            nt.links.new(fz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])


def _leaf(m, c):
    """Leafy clumps: blotchy light/dark greens + a bumpy leaf texture + soft sheen."""
    nt, b, tc = _nodes(m)
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 9.0
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    h, s, v = _hsv(c)
    def rgb(hh, ss, vv):
        return tuple(x ** 2.2 for x in colorsys.hsv_to_rgb(hh % 1.0, min(1, ss), min(1, vv)))
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*rgb(h + 0.02, s * 1.1, v * 0.62), 1)
    ramp.color_ramp.elements[1].color = (*rgb(h - 0.03, s * 0.9, v * 1.12), 1)
    mid = ramp.color_ramp.elements.new(0.55)
    mid.color = (*c, 1)
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = 0.6
    nt.links.new(vo.outputs["Distance"], add.inputs[0])
    nt.links.new(nz.outputs["Fac"], add.inputs[2])
    nt.links.new(add.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.45
    bp.inputs["Distance"].default_value = 0.05
    nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.65
    b.inputs["Sheen Weight"].default_value = 0.4


def _own_material(o, chars_mats):
    """Set objects that share a material with a character get their own copy (eyes stay clean)."""
    out = []
    for slot in o.material_slots:
        m = slot.material
        if m is None:
            continue
        if m.name in chars_mats:
            m = m.copy()
            slot.material = m
        out.append(m)
    return out


def _lumpy(o, strength, size):
    """Bumpy, clumpy surface instead of a perfect ball."""
    if not any(md.type == "SUBSURF" for md in o.modifiers):
        s = o.modifiers.new("s", "SUBSURF")
        s.levels = s.render_levels = 1
        s.use_limit_surface = False
    tx = bpy.data.textures.new(o.name + "_lump", "CLOUDS")
    tx.noise_scale = size
    tx.noise_depth = 2
    d = o.modifiers.new("lump", "DISPLACE")
    d.texture = tx
    d.texture_coords = "GLOBAL"
    d.strength = strength
    d.mid_level = 0.5


# ------------------------------------------------------------------ ground cover
def _blade_mesh():
    me = bpy.data.meshes.new("blade")
    w, h = 0.012, 1.0
    verts = [(-w, 0, 0), (w, 0, 0), (-w * 0.7, 0.03, 0.45 * h), (w * 0.7, 0.03, 0.45 * h),
             (-w * 0.35, 0.09, 0.8 * h), (w * 0.35, 0.09, 0.8 * h), (0, 0.16, h)]
    faces = [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 6)]
    me.from_pydata(verts, [], faces)
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new("blade", me)
    T.sc.collection.objects.link(o)
    o.hide_render = True
    o.hide_viewport = True
    return o


def _grass_material(c):
    m = bpy.data.materials.new("grassblade")
    m.use_nodes = True
    nt, b, _ = _nodes(m)
    oi = nt.nodes.new("ShaderNodeObjectInfo")   # every blade a slightly different green
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    h, s, v = _hsv(c)
    def rgb(hh, ss, vv):
        return tuple(x ** 2.2 for x in colorsys.hsv_to_rgb(hh % 1.0, min(1, ss), min(1, vv)))
    ramp.color_ramp.elements[0].color = (*rgb(h + 0.02, s * 1.05, v * 0.75), 1)
    ramp.color_ramp.elements[1].color = (*rgb(h - 0.04, s * 0.85, v * 1.15), 1)
    nt.links.new(oi.outputs["Random"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.55
    b.inputs["Sheen Weight"].default_value = 0.3
    return m


def _scatter(name, pts, inst, mat, rnd, size=(0.6, 1.3), tilt=0.35):
    """Instance `inst` on a list of (x, y, z, scale) points with random turn/tilt (geometry nodes)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x, y, z) for x, y, z, _ in pts], [], [])
    sca = me.attributes.new("sca", "FLOAT", "POINT")
    sca.data.foreach_set("value", [s_ for *_, s_ in pts])
    o = bpy.data.objects.new(name, me)
    T.sc.collection.objects.link(o)
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links.new
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    oi = N.new("GeometryNodeObjectInfo")
    oi.inputs["Object"].default_value = inst
    oi.inputs["As Instance"].default_value = True
    rot = N.new("FunctionNodeRandomValue")
    rot.data_type = "FLOAT_VECTOR"
    rot.inputs["Min"].default_value = (-tilt, -tilt, 0)
    rot.inputs["Max"].default_value = (tilt, tilt, math.tau)
    sa = N.new("GeometryNodeInputNamedAttribute")
    sa.data_type = "FLOAT"
    sa.inputs["Name"].default_value = "sca"
    rs = N.new("FunctionNodeRandomValue")
    rs.data_type = "FLOAT"
    rs.inputs[2].default_value, rs.inputs[3].default_value = size
    mul = N.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    L(sa.outputs["Attribute"], mul.inputs[0])
    L(rs.outputs[1], mul.inputs[1])
    ins = N.new("GeometryNodeInstanceOnPoints")
    L(gi.outputs[0], ins.inputs["Points"])
    L(oi.outputs["Geometry"], ins.inputs["Instance"])
    L(rot.outputs["Value"], ins.inputs["Rotation"])
    L(mul.outputs[0], ins.inputs["Scale"])
    sm = N.new("GeometryNodeSetMaterial")
    sm.inputs["Material"].default_value = mat
    L(ins.outputs[0], sm.inputs["Geometry"])
    L(sm.outputs[0], go.inputs[0])
    md = o.modifiers.new(name, "NODES")
    md.node_group = ng
    return o


def _on_ground(x, y, ground, dg):
    hit, loc, _n, _i, ob, _m = T.sc.ray_cast(dg, Vector((x, y, 5.0)), Vector((0, 0, -1)), distance=8.0)
    return hit and ob is not None and ob.name == ground.name and abs(loc.z) < 0.05, loc


def _grass(ground, c, rnd):
    """Tufts of grass blades over the visible ground (short near the action, taller further back)."""
    blade = _blade_mesh()
    mat = _grass_material(c)
    pts = []
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    for _ in range(int(os.environ.get("GRASS_TUFTS", "11000"))):
        x, y = rnd.uniform(-6.5, 6.5), rnd.uniform(-1.6, 9.0)
        ok, loc = _on_ground(x, y, ground, dg)
        if not ok:
            continue
        h = 0.065 if y < 1.2 else 0.09 + min(0.06, (y - 1.2) * 0.01)
        for k in range(rnd.randint(4, 8)):   # a little tuft
            pts.append((x + rnd.uniform(-0.04, 0.04), y + rnd.uniform(-0.04, 0.04), loc.z, h * rnd.uniform(0.7, 1.25)))
    if pts:
        _scatter("grassfield", pts, blade, mat, rnd, size=(0.7, 1.3), tilt=0.4)


def _pebbles(ground, c, rnd):
    peb = bpy.data.objects.new("pebble", bpy.data.meshes.new("pebble"))
    T.sc.collection.objects.link(peb)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for v in bm.verts:
        v.co *= rnd.uniform(0.85, 1.1)
        v.co.z *= 0.55
    bm.to_mesh(peb.data)
    bm.free()
    for p in peb.data.polygons:
        p.use_smooth = True
    peb.hide_render = peb.hide_viewport = True
    m = T.mat(T._shade("#%02X%02X%02X" % tuple(int(255 * (v ** (1 / 2.2))) for v in c), 0.8), 0.7)
    pts = []
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    for _ in range(700):
        x, y = rnd.uniform(-6, 6), rnd.uniform(-1.0, 7.0)
        ok, loc = _on_ground(x, y, ground, dg)
        if ok:
            pts.append((x, y, loc.z, rnd.uniform(0.015, 0.035)))
    if pts:
        _scatter("pebbles", pts, peb, m, rnd, size=(0.6, 1.4), tilt=0.3)


# ------------------------------------------------------------------ far background
def _blob_mesh(name, balls, m, res=0.12):
    mb = bpy.data.metaballs.new(name)
    mb.resolution = mb.render_resolution = res
    mo = bpy.data.objects.new(name + "_mb", mb)
    T.sc.collection.objects.link(mo)
    for (x, y, z), r, scl in balls:
        e = mb.elements.new(type="ELLIPSOID")
        e.co, e.radius = (x, y, z), r
        e.size_x, e.size_y, e.size_z = scl
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(mo.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(mo)
    bpy.data.metaballs.remove(mb)
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    T.sc.collection.objects.link(o)
    me.materials.append(m)
    return o


def _far(c, rnd, end):
    """Rolling hills far behind, dotted with little trees + a hot-air balloon or kite drifting by."""
    h, s, v = _hsv(c)
    def hexs(hh, ss, vv):
        r, g, b = colorsys.hsv_to_rgb(hh % 1.0, min(1, ss), min(1, vv))
        return "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255))
    for row, (y, z0, shade) in enumerate(((26.0, -2.6, 0.82), (34.0, -2.2, 0.7))):
        m = T.mat(hexs(h + 0.02, s * 0.75, v * shade), 0.9)
        balls = [((x + rnd.uniform(-2, 2), 0, z0), rnd.uniform(5.5, 8.0), (1.6, 0.6, 1.0)) for x in range(-36, 40, 9)]
        hill = _blob_mesh(f"farhill{row}", balls, m, res=0.6)
        hill.location = (0, y, 0)
        _vary(m, T.lin(hexs(h + 0.02, s * 0.75, v * shade)), scale=0.15, amt=0.12, bump=0.0)
        tm = T.mat(hexs(h + 0.05, s * 0.9, v * shade * 0.75), 0.8)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        for i in range(26 if row == 0 else 18):   # little trees on the hilltops
            x = rnd.uniform(-30, 30)
            hit, loc, *_ = T.sc.ray_cast(dg, Vector((x, y - 1.0, 12)), Vector((0, 0, -1)), distance=20)
            if not hit or loc.z < 0.4:
                continue
            k = rnd.uniform(0.7, 1.3) * (1.0 if row == 0 else 1.3)
            T.sphere(f"fartree{row}_{i}", 0.45 * k, (loc.x, loc.y, loc.z + 0.55 * k), tm, sub=0, seg=12)
    if rnd.random() < 0.65:
        _balloon(rnd, end) if rnd.random() < 0.6 else _kite(rnd, end)


def _balloon(rnd, end):
    cols = rnd.sample(["#FF5D5D", "#FFD23F", "#4DA6FF", "#5CCB6B", "#B57BFF", "#FF8A3D"], 3)
    root = T.empty("hotair", (0, 0, 0))
    for i, cc in enumerate(cols):   # striped envelope
        T.sphere(f"hotair_e{i}", 0.62, (0, 0, 0), T.mat(cc, 0.5), root, scale=(1 - i * 0.18, 1 - i * 0.18, 1.12), sub=1, seg=24)
    T.cone("hotair_neck", 0.32, 0.12, 0.45, (0, 0, -0.75), T.mat(cols[0], 0.5), root)
    T.box("hotair_basket", (0.26, 0.26, 0.2), (0, 0, -1.2), T.mat("#9A6A43", 0.8), root, bevel=0.03)
    for sx in (-1, 1):
        for sy in (-1, 1):
            T.cyl(f"hotair_r{sx}{sy}", 0.008, 0.38, (sx * 0.11, sy * 0.11, -0.95), T.mat("#5A4030", 0.7), root)
    y, z = rnd.uniform(14, 20), rnd.uniform(4.5, 6.5)
    d = rnd.choice((-1, 1))
    T.key(root, "location", 1, (-7 * d, y, z), "LINEAR")
    T.key(root, "location", end, (7 * d, y, z + 0.8), "LINEAR")


def _kite(rnd, end):
    root = T.empty("kite", (0, 0, 0))
    me = bpy.data.meshes.new("kite")
    me.from_pydata([(0, 0, 0.5), (0.32, 0, 0), (0, 0, -0.6), (-0.32, 0, 0)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("kite_sail", me)
    T.sc.collection.objects.link(o)
    o.parent = root
    me.materials.append(T.mat(rnd.choice(["#FF5D5D", "#FFD23F", "#4DA6FF", "#B57BFF"]), 0.5))
    so = o.modifiers.new("t", "SOLIDIFY")
    so.thickness = 0.02
    T.curve_line("kite_tail", [(0, 0, -0.6), (0.15, 0, -1.0), (-0.1, 0, -1.4), (0.12, 0, -1.8)], 0.012,
                 T.mat("#FFFFFF", 0.6), root)
    x, y, z = rnd.uniform(-3, 3), rnd.uniform(10, 14), rnd.uniform(4.5, 6.0)
    for f in range(1, end + 20, 18):
        T.key(root, "location", f, (x + math.sin(f * 0.05) * 0.6, y, z + math.sin(f * 0.08) * 0.3))
        T.key(root, "rotation_euler", f, (0, math.sin(f * 0.11) * 0.35, 0))


# ------------------------------------------------------------------ main
def enrich(set_kind, sky, end, rnd=None):
    rnd = rnd or random.Random(7)
    chars = _char_objects()
    chars_mats = {s.material.name for o in chars if o.type in ("MESH", "CURVE") for s in o.material_slots if s.material}
    seen = set()
    ground = T.sc.objects.get("ground")
    gc = None
    if ground is not None and ground.material_slots and ground.material_slots[0].material:
        gc = _base_color(ground.material_slots[0].material)   # before it gets its texture
    for o in list(T.sc.objects):
        if o in chars or o.type not in ("MESH", "CURVE"):
            continue
        mats = _own_material(o, chars_mats)
        c = _base_color(mats[0]) if mats else None
        k = _kind(o, c)
        if k == "leaf" and o.type == "MESH":
            size = max(o.dimensions) if o.dimensions.length else 0.6
            _lumpy(o, 0.09 * max(0.4, min(2.0, size)), 0.22 * max(0.5, min(2.0, size)))
        elif k == "cloud" and o.type == "MESH":
            _lumpy(o, 0.25, 0.45)
        for m in mats:
            if m.name in seen or m.name in DONE:
                continue
            seen.add(m.name)
            cc = _base_color(m)
            if cc is None or not m.use_nodes:
                continue
            bsdf = m.node_tree.nodes["Principled BSDF"]
            if bsdf.inputs["Emission Strength"].default_value > 0.5 or bsdf.inputs["Transmission Weight"].default_value > 0.2:
                continue
            if k == "leaf":
                _leaf(m, cc)
            elif k == "bark":
                _vary(m, cc, scale=3.0, amt=0.18, bump=0.35, bump_scale=18.0, pattern="grain")
            elif k == "wood":
                _vary(m, cc, scale=3.0, amt=0.12, bump=0.12, pattern="grain")
            elif k == "wall":
                _vary(m, cc, scale=1.5, amt=0.08, bump=0.15, pattern="brick")
            elif k == "roof":
                _vary(m, cc, scale=2.0, amt=0.12, bump=0.25, pattern="tiles")
            elif k == "cloud":
                _vary(m, cc, scale=1.2, amt=0.04, bump=0.0)
            else:
                _vary(m, cc)
    outdoor = sky not in T.INDOOR
    if ground is not None and gc is not None:
        if True:
            h, s, v = _hsv(gc)
            if 0.18 < h < 0.45 and s > 0.25:
                _grass(ground, gc, rnd)
                if outdoor and set_kind not in ("beach", "pirate", "underwater", "space"):
                    _far(gc, rnd, end)
            elif 0.06 < h < 0.16 and s > 0.15:
                _pebbles(ground, gc, rnd)
