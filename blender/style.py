"""Art styles: the same story can be drawn in different looks, so the channel doesn't look the same every day.

plush      soft 3D plush toys with fur (the classic look)
clay       stop-motion clay: matte, finger-pressed, moves "on twos" (each pose held for 2 frames)
toon       flat cartoon: no fur, matte colours, bold dark outlines
storybook  painted picture-book: brush strokes, warm paper and a soft vignette
dreamy     pastel dream: soft glow, light pastel colours, extra-soft background

before_build(style) runs before anything is made (fur on/off, grass amount);
apply(style) runs after the whole scene is built (materials, lights, camera, compositor)."""
import math
import os

import bpy

STYLES = ("plush", "clay", "toon", "storybook", "dreamy")
NO_FUR = ("clay", "toon", "storybook")   # clay figures have no strands; flat/painted looks don't need them (faster)
ON_TWOS = ("clay",)


def before_build(style):
    import toon as T
    if style in NO_FUR:
        T.FUR = False
    if style == "toon":  # no grass blades: they turn into ink speckles
        os.environ["GRASS_TUFTS"] = "0"
    elif style == "clay":
        os.environ["GRASS_TUFTS"] = "6000"


def _principled(m):
    if not (m and m.use_nodes and m.node_tree):
        return None
    return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def _set(b, name, v):
    s = b.inputs.get(name)
    if s is not None and not s.is_linked:
        s.default_value = v


def _is_eye(m, b):
    """Glossy eye parts (whites, pupils, iris, shine) keep their sparkle in every style."""
    n = m.name.lower()
    coat = b.inputs.get("Coat Weight")
    return "iris" in n or (coat is not None and not coat.is_linked and coat.default_value >= 0.55) or \
        (b.inputs["Emission Strength"].default_value > 2 and not b.inputs["Emission Strength"].is_linked)


def _bump(m, b, scale, strength, detail=4.0, voronoi=False):
    """Add a fine surface (fingerprints, paper) when the material has no bump of its own yet."""
    nt = m.node_tree
    if b.inputs["Normal"].is_linked:
        return
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if voronoi:
        tx = nt.nodes.new("ShaderNodeTexVoronoi")
        tx.feature = "SMOOTH_F1"
        tx.inputs["Scale"].default_value = scale
        out = tx.outputs["Distance"]
    else:
        tx = nt.nodes.new("ShaderNodeTexNoise")
        tx.inputs["Scale"].default_value = scale
        tx.inputs["Detail"].default_value = detail
        out = tx.outputs["Fac"]
    nt.links.new(tc.outputs["Object"], tx.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    bp.inputs["Distance"].default_value = 0.02
    nt.links.new(out, bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])


def _materials(style):
    done = set()
    for o in bpy.data.objects:
        if o.type not in ("MESH", "CURVE", "CURVES", "META", "SURFACE", "FONT"):
            continue
        for s in o.material_slots:
            m = s.material
            if not m or m.name in done:
                continue
            done.add(m.name)
            b = _principled(m)
            if b is None or _is_eye(m, b):
                continue
            if style == "clay":
                _set(b, "Roughness", max(0.62, b.inputs["Roughness"].default_value))
                _set(b, "Coat Weight", 0.0)
                _set(b, "Sheen Weight", 0.15)
                _set(b, "Specular IOR Level", 0.35)
                _set(b, "Subsurface Weight", 0.08)
                _bump(m, b, 22.0, 0.22, detail=6.0)          # thumb-pressed clay
            elif style == "toon":
                _set(b, "Roughness", 1.0)
                for k in ("Coat Weight", "Sheen Weight", "Specular IOR Level"):
                    _set(b, k, 0.0)
                if b.inputs["Normal"].is_linked:            # flat colours: no grain, no bumps
                    for ln in list(b.inputs["Normal"].links):
                        m.node_tree.links.remove(ln)
            elif style == "storybook":
                _set(b, "Coat Weight", 0.0)
                _set(b, "Specular IOR Level", 0.25)
            elif style == "dreamy":
                _set(b, "Coat Weight", min(0.3, b.inputs["Coat Weight"].default_value))


def _lights(style):
    sun = bpy.data.objects.get("sun")
    if style == "toon":
        if sun:
            sun.data.angle = math.radians(1.5)          # crisp cartoon shadows
        for n in ("fill", "rim"):
            o = bpy.data.objects.get(n)
            if o:
                o.data.energy *= 1.35
    elif style == "clay":
        if sun:
            sun.data.angle = math.radians(2.5)
            sun.data.color = (1.0, 0.9, 0.78)
    elif style == "dreamy":
        if sun:
            sun.data.angle = math.radians(18)
            sun.data.energy *= 0.85
        fill = bpy.data.objects.get("fill")
        if fill:
            fill.data.color = (1.0, 0.9, 0.97)
            fill.data.energy *= 1.4
    elif style == "storybook" and sun:
        sun.data.color = (1.0, 0.9, 0.75)


def _camera(style):
    cam = bpy.context.scene.camera
    if cam and style == "dreamy":
        cam.data.dof.use_dof = True
        cam.data.dof.aperture_fstop = max(0.6, cam.data.dof.aperture_fstop * 0.45)  # very soft background


def _vignette(nt, img, k, amount=0.35):
    em = nt.nodes.new("CompositorNodeEllipseMask")   # big soft oval: only the corners darken a little
    em.mask_width, em.mask_height = 1.25, 1.05
    bl = nt.nodes.new("CompositorNodeBlur")
    bl.filter_type = "FAST_GAUSS"
    bl.size_x = bl.size_y = int(420 * k)
    nt.links.new(em.outputs["Mask"], bl.inputs["Image"])
    inv = nt.nodes.new("CompositorNodeMath")
    inv.operation = "MULTIPLY_ADD"
    inv.inputs[1].default_value = amount
    inv.inputs[2].default_value = 1.0 - amount
    nt.links.new(bl.outputs["Image"], inv.inputs[0])
    mul = nt.nodes.new("CompositorNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs["Fac"].default_value = 1.0
    nt.links.new(img, mul.inputs[1])
    nt.links.new(inv.outputs[0], mul.inputs[2])
    return mul.outputs["Image"]


def _outlines(nt, rl, img, k):
    """Dark outlines where depth or surface direction jumps (Sobel on 1/depth + normals)."""
    vl = bpy.context.scene.view_layers[0]
    vl.use_pass_z = vl.use_pass_normal = True
    inv = nt.nodes.new("CompositorNodeMath")
    inv.operation = "DIVIDE"
    inv.inputs[0].default_value = 1.0
    nt.links.new(rl.outputs["Depth"], inv.inputs[1])
    ez = nt.nodes.new("CompositorNodeFilter")
    ez.filter_type = "SOBEL"
    nt.links.new(inv.outputs[0], ez.inputs["Image"])
    zbw = nt.nodes.new("CompositorNodeRGBToBW")
    nt.links.new(ez.outputs["Image"], zbw.inputs["Image"])
    zs = nt.nodes.new("CompositorNodeMath")
    zs.operation = "MULTIPLY"
    zs.inputs[1].default_value = 9.0
    nt.links.new(zbw.outputs["Val"], zs.inputs[0])
    en = nt.nodes.new("CompositorNodeFilter")
    en.filter_type = "SOBEL"
    nt.links.new(rl.outputs["Normal"], en.inputs["Image"])
    nbw = nt.nodes.new("CompositorNodeRGBToBW")
    nt.links.new(en.outputs["Image"], nbw.inputs["Image"])
    ns = nt.nodes.new("CompositorNodeMath")
    ns.operation = "MULTIPLY"
    ns.inputs[1].default_value = 0.55
    nt.links.new(nbw.outputs["Val"], ns.inputs[0])
    mx = nt.nodes.new("CompositorNodeMath")
    mx.operation = "MAXIMUM"
    nt.links.new(zs.outputs[0], mx.inputs[0])
    nt.links.new(ns.outputs[0], mx.inputs[1])
    th = nt.nodes.new("CompositorNodeMath")   # soft threshold -> clean ink line
    th.operation = "SUBTRACT"
    th.inputs[1].default_value = 0.35
    nt.links.new(mx.outputs[0], th.inputs[0])
    gain = nt.nodes.new("CompositorNodeMath")
    gain.operation = "MULTIPLY"
    gain.use_clamp = True
    gain.inputs[1].default_value = 2.5
    nt.links.new(th.outputs[0], gain.inputs[0])
    ink = nt.nodes.new("CompositorNodeMixRGB")
    ink.inputs[2].default_value = (0.06, 0.04, 0.08, 1)
    nt.links.new(gain.outputs[0], ink.inputs["Fac"])
    nt.links.new(img, ink.inputs[1])
    return ink.outputs["Image"]


def _compositor(style):
    sc = bpy.context.scene
    if style == "plush":
        return
    sc.use_nodes = True
    sc.render.use_compositing = True
    nt = sc.node_tree
    nt.nodes.clear()
    k = sc.render.resolution_percentage / 100.0       # effect sizes follow the render size
    rl = nt.nodes.new("CompositorNodeRLayers")
    comp = nt.nodes.new("CompositorNodeComposite")
    img = rl.outputs["Image"]
    if style == "toon":
        hs = nt.nodes.new("CompositorNodeHueSat")
        hs.inputs["Saturation"].default_value = 1.06
        nt.links.new(img, hs.inputs["Image"])
        img = _outlines(nt, rl, hs.outputs["Image"], k)
    elif style == "clay":
        cb = nt.nodes.new("CompositorNodeColorBalance")
        cb.correction_method = "LIFT_GAMMA_GAIN"
        cb.gain = (1.04, 1.0, 0.94)
        nt.links.new(img, cb.inputs["Image"])
        img = _vignette(nt, cb.outputs["Image"], k, 0.12)
    elif style == "storybook":
        kw = nt.nodes.new("CompositorNodeKuwahara")
        kw.variation = "ANISOTROPIC"
        kw.inputs["Size"].default_value = max(4, round(16 * k))
        kw.sharpness, kw.eccentricity = 0.6, 1.0
        nt.links.new(img, kw.inputs["Image"])
        cb = nt.nodes.new("CompositorNodeColorBalance")
        cb.correction_method = "LIFT_GAMMA_GAIN"
        cb.lift, cb.gain = (1.04, 1.03, 1.0), (1.03, 0.99, 0.9)
        nt.links.new(kw.outputs["Image"], cb.inputs["Image"])
        tx = bpy.data.textures.new("paper", "CLOUDS")       # paper grain
        tx.noise_scale, tx.noise_depth = 0.012, 3
        tn = nt.nodes.new("CompositorNodeTexture")
        tn.texture = tx
        pm = nt.nodes.new("CompositorNodeMath")
        pm.operation = "MULTIPLY_ADD"
        pm.inputs[1].default_value = 0.08
        pm.inputs[2].default_value = 0.96
        nt.links.new(tn.outputs["Value"], pm.inputs[0])
        mul = nt.nodes.new("CompositorNodeMixRGB")
        mul.blend_type = "MULTIPLY"
        nt.links.new(cb.outputs["Image"], mul.inputs[1])
        nt.links.new(pm.outputs[0], mul.inputs[2])
        img = _vignette(nt, mul.outputs["Image"], k, 0.14)
    elif style == "dreamy":
        gl = nt.nodes.new("CompositorNodeGlare")
        gl.glare_type, gl.quality = "FOG_GLOW", "MEDIUM"
        gl.threshold, gl.mix, gl.size = 0.85, -0.7, 8
        nt.links.new(img, gl.inputs["Image"])
        cb = nt.nodes.new("CompositorNodeColorBalance")
        cb.correction_method = "LIFT_GAMMA_GAIN"
        cb.lift, cb.gain = (1.05, 1.03, 1.06), (1.02, 0.99, 1.03)
        nt.links.new(gl.outputs["Image"], cb.inputs["Image"])
        hs = nt.nodes.new("CompositorNodeHueSat")
        hs.inputs["Saturation"].default_value = 0.92
        nt.links.new(cb.outputs["Image"], hs.inputs["Image"])
        img = _vignette(nt, hs.outputs["Image"], k, 0.1)
    nt.links.new(img, comp.inputs["Image"])


def apply(style):
    if style not in STYLES or style == "plush":
        return
    _materials(style)
    _lights(style)
    _camera(style)
    _compositor(style)
