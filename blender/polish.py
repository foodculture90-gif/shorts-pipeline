"""Animation polish, applied to every short after the gags are keyed:

* snap + settle: a pose that is reached and then held (arms up, lean, turn, head tilt) now arrives quickly,
  overshoots a little and settles back, like hand-drawn cartoon timing, instead of a slow robotic ease-in/out;
* jelly: the bounce back from a squash or stretch wobbles once or twice before it settles;
* camera: every held shot slowly pushes in, and the aim drifts very slightly, so the frame is never dead still.
"""
import bpy

ROT_MIN, SCALE_MIN = 0.06, 0.05          # smaller moves stay as they are


def _arrivals(fc, small):
    """(left key, right key, change) for each move that ends in a hold."""
    kps = sorted(fc.keyframe_points, key=lambda k: k.co[0])
    for i in range(len(kps) - 1):
        a, b = kps[i], kps[i + 1]
        dt, dv = b.co[0] - a.co[0], b.co[1] - a.co[1]
        if a.interpolation != "BEZIER" or not 3 <= dt <= 18 or abs(dv) < small:
            continue
        nxt = kps[i + 2] if i + 2 < len(kps) else None
        held = nxt is None or nxt.co[0] - b.co[0] >= 6 or abs(nxt.co[1] - b.co[1]) < abs(dv) * 0.25
        if held:
            yield a, b, dv, dt


def snap(chars):
    n = 0
    for ch in chars:
        objs = {ch.get("root"), ch.get("piv"), ch.get("hd_act"), *(ch.get("arms") or [])}
        for o in objs:
            ad = getattr(o, "animation_data", None) if o is not None else None
            if not ad or not ad.action:
                continue
            for fc in ad.action.fcurves:
                if fc.data_path == "rotation_euler":
                    for a, b, dv, dt in _arrivals(fc, ROT_MIN):
                        a.interpolation, a.easing = "BACK", "EASE_OUT"
                        a.back = 1.3 if dt >= 5 else 0.9          # ~8 % overshoot, less on very quick moves
                        n += 1
                elif fc.data_path == "scale" and o is ch.get("piv"):
                    for a, b, dv, dt in _arrivals(fc, SCALE_MIN):
                        if abs(b.co[1] - 1.0) < 1e-3:         # springing back to normal after a squash/stretch
                            a.interpolation, a.easing = "ELASTIC", "EASE_OUT"
                            a.amplitude, a.period = 0.3, max(2.5, min(3.5, dt * 0.4))   # jelly: 0.95 1.05 0.99 1.0
                            n += 1
                        else:
                            a.interpolation, a.easing, a.back = "BACK", "EASE_OUT", 1.1
                            n += 1
    return n


def camera(cam, tgt, end):
    """Slow push-in on held shots + a barely-there drift of the aim."""
    ad = cam.animation_data
    if ad and ad.action:
        locs = [ad.action.fcurves.find("location", index=i) for i in range(3)]
        taim = tgt.animation_data.action if tgt.animation_data else None
        if all(locs) and taim:
            aims = [taim.fcurves.find("location", index=i) for i in range(3)]
            if all(aims):
                frames = sorted({int(k.co[0]) for k in locs[0].keyframe_points})
                for f0, f1 in zip(frames, frames[1:]):
                    if f1 - f0 < 24:
                        continue
                    p0 = [c.evaluate(f0) for c in locs]
                    p1 = [c.evaluate(f1 - 0.01) for c in locs]
                    if max(abs(x - y) for x, y in zip(p0, p1)) > 1e-3:
                        continue                                  # the gag already moves this shot
                    t0 = [c.evaluate(f0) for c in aims]
                    k = min(0.07, 0.0016 * (f1 - f0))           # ~7 % closer over a long shot
                    for i, c in enumerate(locs):
                        # key just before the cut so the move eases out and the next shot starts clean
                        c.keyframe_points.insert(f1 - 1, p0[i] + (t0[i] - p0[i]) * k).interpolation = "CONSTANT"
                    for c in locs:
                        for kp in c.keyframe_points:
                            if int(kp.co[0]) == f0:
                                kp.interpolation = "SINE"
                                kp.easing = "EASE_IN_OUT"
                for c in locs:
                    c.update()
    if tgt.animation_data and tgt.animation_data.action:
        for i, amp in ((0, 0.012), (2, 0.008)):
            fc = tgt.animation_data.action.fcurves.find("location", index=i)
            if fc and not any(m.type == "NOISE" for m in fc.modifiers):
                m = fc.modifiers.new("NOISE")
                m.scale, m.strength, m.phase = 70.0, amp * 2, 11.0 * (i + 1)


def apply(end):
    import toon as T
    try:
        n = snap(T.CHARS)
        print("polish: snapped", n, "moves", flush=True)
    except Exception as ex:  # noqa: BLE001
        print("polish snap skipped:", ex)
    try:
        cam = bpy.data.objects.get("cam")
        tgt = bpy.data.objects.get("cam_target")
        if cam and tgt:
            camera(cam, tgt, end)
    except Exception as ex:  # noqa: BLE001
        print("polish camera skipped:", ex)
