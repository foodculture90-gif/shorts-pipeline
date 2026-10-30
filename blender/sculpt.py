"""Turns a character's ball-and-stick parts into one smooth, sculpted body.

The character builders in toon.py place simple parts (spheres for the body, head, ears, snout...). Here:
  - every "shape" part becomes an element of one metaball, so the parts melt into each other with soft
    joins (like a sculpted vinyl toy instead of balls stuck together),
  - "paint" parts (belly, patches, spots, inner ears...) are not geometry any more: they become colour
    painted onto the surface with soft edges,
  - the face (eyes, brows, mouth, nose, cheeks) is moved onto the new surface,
  - the skin gets a soft plush/fuzz material with tiny surface detail.
Eyes, mouth, arms and feet stay separate objects, so every animation move keeps working.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

THRESH = 0.6
STIFF = 3.0  # higher = parts keep their own shape, with smaller soft joins


def _k(stiff):
    """A metaball ball of radius R ends at k * R (Blender's field: stiffness * (1 - (d/R)^2)^3 = threshold)."""
    return math.sqrt(1.0 - (THRESH / stiff) ** (1.0 / 3.0))


def _mats(o):
    return [s.material for s in o.material_slots if s.material]


def _color(o):
    for m in _mats(o):
        if m.use_nodes and "Principled BSDF" in m.node_tree.nodes:
            c = m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
            return np.array(c[:3])
    return np.array((0.8, 0.8, 0.8))


def _unit(o, inv):
    """Matrix: piv space -> the part's unit sphere (|q| = 1 on the part's surface)."""
    r = float(o.get("r", 0.5))
    return (inv @ o.matrix_world @ Matrix.Scale(r, 4)).inverted()


def _surf_bvh(objs, dg, inv):
    """One BVH (in piv space) for a list of mesh objects, evaluated (modifiers applied)."""
    verts, polys = [], []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        m = inv @ o.matrix_world
        base = len(verts)
        verts += [m @ v.co for v in me.vertices]
        polys += [[base + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys) if polys else None


def _front_y(bvh, x, z):
    if bvh is None:
        return None
    hit = bvh.ray_cast(Vector((x, -5.0, z)), Vector((0, 1, 0)))
    return hit[0].y if hit[0] is not None else None


def plush_material(name, fuzz=0.6, rough=0.55, coat=0.0, bump=0.12, grain="fuzz"):
    """Skin/fur material that takes its colours from the painted "Col" attribute."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    # a little colour wobble so big areas don't look like flat plastic
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 6.0
    nz.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["To Min"].default_value = 0.9
    ramp.inputs["To Max"].default_value = 1.08
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(attr.outputs["Color"], mul.inputs["A"])
    nt.links.new(ramp.outputs["Result"], mul.inputs["B"])
    nt.links.new(mul.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if fuzz:
        b.inputs["Sheen Weight"].default_value = fuzz
        b.inputs["Sheen Roughness"].default_value = 0.35
        b.inputs["Sheen Tint"].default_value = (1, 1, 1, 1)
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    b.inputs["Subsurface Weight"].default_value = 0.0
    if bump:  # surface grain: fuzz (plush), scales (dinos) or skin (smooth, very fine)
        if grain == "scales":
            fz = nt.nodes.new("ShaderNodeTexVoronoi")
            fz.feature = "SMOOTH_F1"
            fz.inputs["Scale"].default_value = 38.0
            out = fz.outputs["Distance"]
        else:
            fz = nt.nodes.new("ShaderNodeTexNoise")
            fz.inputs["Scale"].default_value = 140.0 if grain == "fuzz" else 70.0
            fz.inputs["Detail"].default_value = 2.0
            out = fz.outputs["Fac"]
        nt.links.new(tc.outputs["Object"], fz.inputs["Vector"])
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.02
        nt.links.new(out, bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def sculpt(ch, shape, paint, face=(), res=0.012, fuzz=0.6, rough=0.55, coat=0.0, bump=0.12, blend=0.012, fur=None,
           grain="fuzz"):
    """shape / paint: lists of part objects (children of ch["piv"]). face: objects to move onto the new surface.
    Returns the new body object."""
    piv = ch["piv"]
    bpy.context.view_layer.update()
    inv = piv.matrix_world.inverted()
    dg = bpy.context.evaluated_depsgraph_get()
    shape = [o for o in shape if o is not None]
    paint = [o for o in paint if o is not None]
    if not shape:
        return None
    old = _surf_bvh(shape, dg, inv)
    # ---- one metaball: every shape part becomes an ellipsoid element
    mb = bpy.data.metaballs.new(ch["name"] + "_mb")
    mb.resolution = mb.render_resolution = res
    mb.threshold = THRESH
    mo = bpy.data.objects.new(ch["name"] + "_mb", mb)
    bpy.context.scene.collection.objects.link(mo)
    info = []
    for o in shape:
        m = inv @ o.matrix_world
        loc, rot, scl = m.decompose()
        r = float(o.get("r", 0.5))
        e = mb.elements.new(type="ELLIPSOID")
        e.co, e.rotation = loc, rot
        e.stiffness = float(o.get("stiff", STIFF))
        e.radius = r / _k(e.stiffness)
        e.size_x, e.size_y, e.size_z = scl
        info.append((np.array(_unit(o, inv)), r * (scl.x + scl.y + scl.z) / 3, _color(o),
                     float(o.get("fur", 1.0)), float(o.get("furlen", 1.0))))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(mo.evaluated_get(dg))
    me.name = ch["name"] + "_skin"
    bpy.data.objects.remove(mo)
    bpy.data.metaballs.remove(mb)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    body = bpy.data.objects.new(ch["name"] + "_skin", me)
    bpy.context.scene.collection.objects.link(body)
    body.parent = piv
    body.matrix_parent_inverse = Matrix.Identity(4)
    # ---- paint: nearest shape part's colour, then the paint parts on top (soft edges)
    n = len(me.vertices)
    V = np.empty(n * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(n, 3)
    Vh = np.c_[V, np.ones(n)]
    dists, cols = [], []
    for A, rad, col, _fd, _fl in info:
        q = Vh @ A.T
        dists.append((np.linalg.norm(q[:, :3], axis=1) - 1.0) * rad)
        cols.append(col)
    D = np.array(dists)
    w = np.exp(-(D - D.min(0)) / blend)
    w /= w.sum(0)
    C = (w[:, :, None] * np.array(cols)[:, None, :]).sum(0)
    FD = (w * np.array([i[3] for i in info])[:, None]).sum(0)   # fur density per part (0 = bare skin)
    FL = (w * np.array([i[4] for i in info])[:, None]).sum(0)   # fur length per part
    # ---- floppy parts (ears, tails, tufts): a vertex group each + the point where they join the body,
    # so rig.py can make them bounce and flop (follow-through)
    groups = {}
    for i, o in enumerate(shape):
        nm = o.name.split(".")[0]
        tail = nm[len(ch["name"]) + 1:] if nm.startswith(ch["name"] + "_") else nm
        kind = next((k for k in ("ear", "tail", "tuft") if tail.startswith(k)), None)
        if kind is None or tail.startswith("earin"):
            continue
        key_ = tail.split("_")[0].rstrip("0123456789") if kind == "tuft" else tail.split("_")[0]
        groups.setdefault(key_, (kind, []))[1].append(i)
    flex = []
    for gname, (kind, idx) in groups.items():
        g = w[idx].sum(0)
        g = np.clip((g - 0.3) / 0.55, 0.0, 1.0)
        g = g * g * (3 - 2 * g)
        if g.max() < 0.5:
            continue
        ring = (g > 0.2) & (g < 0.6)
        piv_pt = V[ring].mean(0) if ring.sum() >= 6 else V[g > 0.5].mean(0)
        vg = body.vertex_groups.new(name="flex_" + gname)
        q = np.round(g * 32).astype(int)   # 33 weight levels: one call per level (fast)
        for lv in np.unique(q[q > 0]):
            vg.add(np.nonzero(q == lv)[0].tolist(), float(lv) / 32.0, "REPLACE")
        flex.append({"group": vg.name, "kind": kind, "pivot": [float(c) for c in piv_pt],
                     "tip": [float(c) for c in V[g > 0.9].mean(0)] if (g > 0.9).sum() else [float(c) for c in piv_pt]})
    if flex:
        import json as _json
        body["flex"] = _json.dumps(flex)
    for o in paint:
        A = np.array(_unit(o, inv))
        s = np.linalg.norm((Vh @ A.T)[:, :3], axis=1)
        soft = float(o.get("soft", 0.06))
        t = np.clip((1.0 + soft - s) / (2 * soft), 0.0, 1.0)
        t = t * t * (3 - 2 * t)
        if not o.get("nocolor"):
            C = C * (1 - t[:, None]) + _color(o)[None, :] * t[:, None]
        if "fur" in o:
            FD = FD * (1 - t) + float(o["fur"]) * t
        if "furlen" in o:
            FL = FL * (1 - t) + float(o["furlen"]) * t
    # where fur grows: everywhere except right around the eyes, nose and mouth (keeps the face clean)
    fm = np.ones(n)
    for f in face:
        if f is None:
            continue
        c = np.array(inv @ f.matrix_world.translation)
        rad = float(f.get("clear", 0.1))
        dd = np.linalg.norm(V - c, axis=1)
        t = np.clip((dd - rad) / 0.06, 0.0, 1.0)
        fm = np.minimum(fm, t * t * (3 - 2 * t))
    fa = me.attributes.new("fur", "FLOAT", "POINT")
    fa.data.foreach_set("value", fm * FD)
    la = me.attributes.new("furlen", "FLOAT", "POINT")
    la.data.foreach_set("value", FL)
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", np.c_[C, np.ones(n)].ravel())
    body.data.materials.append(plush_material(ch["name"] + "_plush", fuzz, rough, coat, bump, grain))
    # ---- move the face onto the new surface (keeps each feature's depth relative to the skin)
    new = _surf_bvh([body], bpy.context.evaluated_depsgraph_get(), inv)
    for f in face:
        if f is None:
            continue
        p = inv @ f.matrix_world.translation
        y0, y1 = _front_y(old, p.x, p.z), _front_y(new, p.x, p.z)
        if y0 is None or y1 is None:
            continue
        mw = f.matrix_world.copy()
        delta = piv.matrix_world.to_3x3() @ Vector((0, y1 - y0 + float(f.get("sink", 0.0)), 0))
        mw.translation = mw.translation + delta
        f.matrix_world = mw
    # ---- remove the old parts (their other children are kept, re-hung on the pivot where they are)
    gone = set(shape) | set(paint)
    for o in list(gone):
        for c in list(o.children):
            if c not in gone:
                mw = c.matrix_world.copy()
                c.parent = piv
                c.matrix_world = mw
    for o in gone:
        bpy.data.objects.remove(o)
    if fur is not None:
        add_fur(body, **fur)
    return body


def _fur_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "Col"
    info = nt.nodes.new("ShaderNodeHairInfo")  # darker at the root, lighter at the tip = depth
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 1.0  # dense fur shades itself darker: lift it back to the skin colour
    mr.inputs["To Max"].default_value = 1.4
    nt.links.new(info.outputs["Intercept"], mr.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(at.outputs["Color"], mul.inputs["A"])
    nt.links.new(mr.outputs["Result"], mul.inputs["B"])
    nt.links.new(mul.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    b.inputs["Sheen Weight"].default_value = 0.3
    return m


def solid_skin(o, hexcol=None):
    """Give a separate body part (arm, hand...) the painted-skin look + fur colour of the body."""
    me = o.data
    c = _color(o)
    if "Col" not in me.color_attributes:
        ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        ca.data.foreach_set("color", np.tile(np.r_[c, 1.0], len(me.vertices)))
    for nm in ("fur", "furlen"):
        if nm not in me.attributes:
            fa = me.attributes.new(nm, "FLOAT", "POINT")
            fa.data.foreach_set("value", np.ones(len(me.vertices)))
    return o


def match_skin(parts, body):
    """Arms, hands, tails... that move on their own get the same skin material as the sculpted body."""
    if body is None:
        return
    m = body.data.materials[0]
    for o in parts:
        if o is None or o.type != "MESH":
            continue
        solid_skin(o)
        o.data.materials.clear()
        o.data.materials.append(m)


def add_fur(body, length=0.017, density=20000.0, radius=0.0026, seed=0, comb=-0.4):
    """Short soft fur over the whole skin (real strands, coloured like the skin under them)."""
    ng = bpy.data.node_groups.new(body.name + "_fur", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes
    L = ng.links.new
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    oi = N.new("GeometryNodeObjectInfo")  # fur lives on its own Curves object (Cycles renders those strands)
    oi.transform_space = "RELATIVE"
    oi.inputs["Object"].default_value = body
    dist = N.new("GeometryNodeDistributePointsOnFaces")
    fa = N.new("GeometryNodeInputNamedAttribute")
    fa.data_type = "FLOAT"
    fa.inputs["Name"].default_value = "fur"
    dm = N.new("ShaderNodeMath")
    dm.operation = "MULTIPLY"
    dm.inputs[1].default_value = density
    L(fa.outputs["Attribute"], dm.inputs[0])
    L(dm.outputs[0], dist.inputs["Density"])
    dist.inputs["Seed"].default_value = seed
    L(oi.outputs["Geometry"], dist.inputs["Mesh"])
    line = N.new("GeometryNodeCurvePrimitiveLine")
    line.inputs["End"].default_value = (0, 0, 1)
    res = N.new("GeometryNodeResampleCurve")
    res.inputs["Count"].default_value = 3
    L(line.outputs[0], res.inputs["Curve"])
    # strand direction: along the surface normal, combed a little downwards, plus a random wiggle
    comb_down = comb
    comb = N.new("ShaderNodeVectorMath")
    comb.operation = "ADD"
    comb.inputs[1].default_value = (0, 0, comb_down)
    L(dist.outputs["Normal"], comb.inputs[0])
    rnd = N.new("FunctionNodeRandomValue")
    rnd.data_type = "FLOAT_VECTOR"
    rnd.inputs["Min"].default_value = (-0.22, -0.22, -0.22)
    rnd.inputs["Max"].default_value = (0.22, 0.22, 0.22)
    add2 = N.new("ShaderNodeVectorMath")
    add2.operation = "ADD"
    L(comb.outputs[0], add2.inputs[0])
    L(rnd.outputs["Value"], add2.inputs[1])
    align = N.new("FunctionNodeAlignEulerToVector")
    align.axis = "Z"
    L(add2.outputs[0], align.inputs["Vector"])
    scl = N.new("FunctionNodeRandomValue")
    scl.data_type = "FLOAT"
    scl.inputs[2].default_value = length * 0.6
    scl.inputs[3].default_value = length * 1.15
    inst = N.new("GeometryNodeInstanceOnPoints")
    L(dist.outputs["Points"], inst.inputs["Points"])
    L(res.outputs[0], inst.inputs["Instance"])
    L(align.outputs[0], inst.inputs["Rotation"])
    fl = N.new("ShaderNodeMath")  # shorter fur where the mask fades out (no sparse fringe)
    fl.operation = "MULTIPLY"
    L(scl.outputs[1], fl.inputs[0])
    L(fa.outputs["Attribute"], fl.inputs[1])
    la = N.new("GeometryNodeInputNamedAttribute")  # longer tufts on the head, cheeks, tail...
    la.data_type = "FLOAT"
    la.inputs["Name"].default_value = "furlen"
    fl2 = N.new("ShaderNodeMath")
    fl2.operation = "MULTIPLY"
    L(fl.outputs[0], fl2.inputs[0])
    L(la.outputs["Attribute"], fl2.inputs[1])
    L(fl2.outputs[0], inst.inputs["Scale"])
    real = N.new("GeometryNodeRealizeInstances")
    L(inst.outputs[0], real.inputs[0])
    # colour of the skin under each strand
    samp = N.new("GeometryNodeSampleNearestSurface")
    samp.data_type = "FLOAT_COLOR"
    L(oi.outputs["Geometry"], samp.inputs["Mesh"])
    col = N.new("GeometryNodeInputNamedAttribute")
    col.data_type = "FLOAT_COLOR"
    col.inputs["Name"].default_value = "Col"
    L(col.outputs["Attribute"], samp.inputs["Value"])
    store = N.new("GeometryNodeStoreNamedAttribute")
    store.data_type = "FLOAT_COLOR"
    store.domain = "CURVE"
    store.inputs["Name"].default_value = "Col"
    L(real.outputs[0], store.inputs["Geometry"])
    L(samp.outputs["Value"], store.inputs["Value"])
    # thick at the root, thin at the tip
    sp = N.new("GeometryNodeSplineParameter")
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = radius
    mr.inputs["To Max"].default_value = radius * 0.15
    L(sp.outputs["Factor"], mr.inputs["Value"])
    rad = N.new("GeometryNodeSetCurveRadius")
    L(store.outputs[0], rad.inputs["Curve"])
    L(mr.outputs["Result"], rad.inputs["Radius"])
    sm = N.new("GeometryNodeSetMaterial")
    sm.inputs["Material"].default_value = _fur_material(body.name + "_furm")
    L(rad.outputs[0], sm.inputs["Geometry"])
    L(sm.outputs[0], go.inputs[0])
    hc = bpy.data.hair_curves.new(body.name + "_fur")
    fo = bpy.data.objects.new(body.name + "_fur", hc)
    bpy.context.scene.collection.objects.link(fo)
    fo.parent = body
    fo.matrix_parent_inverse = Matrix.Identity(4)
    hc.materials.append(sm.inputs["Material"].default_value)
    mod = fo.modifiers.new("fur", "NODES")
    mod.node_group = ng
    return fo
