"""Build + render one 3D short from a spec.

  blender -b --python blender/scene.py -- spec.json <outdir> <mode>
  mode: part:K/N (render every Nth frame of the whole short from K+1) | stills | every:N | all | none
  spec: {"segments": [{"gag": "steal_treat", "set": "street", "hero": "pip", "friend": "chiko", "prop": "cake",
                       "seed": 1}, ...], "seed": 7}      (or a single gag spec without "segments")
  A short is several gags in a row with the same two friends; each gag is built as its own little scene and its
  frames are numbered across the whole short, so many machines can share the work.
  env: SAMPLES (default 20), RES (percent of 1080x1920, default 100)
"""
import json, os, random, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gags  # noqa: E402
import toon as T  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
spec = json.load(open(argv[0]))
out = os.path.abspath(argv[1] if len(argv) > 1 else "out")
mode = argv[2] if len(argv) > 2 else "all"
os.makedirs(f"{out}/frames", exist_ok=True)
segments = spec.get("segments") or [spec]
samples, res = int(os.environ.get("SAMPLES", "20")), int(os.environ.get("RES", "100"))


COLORS = {"red": "#FF3B6E", "blue": "#4DA6FF", "yellow": "#FFD23F", "green": "#5CCB6B", "purple": "#B57BFF",
          "orange": "#FF8A3D", "pink": "#FF8FC8"}


def build(seg):
    T.reset()
    T.THEME.clear()
    T.THEME.update(spec.get("theme") or {}, set=seg.get("set", "street"))
    T.LOOKS.clear()
    T.LOOKS.update(spec.get("looks") or {})
    T.VAR = random.Random(seg.get("seed", 1) * 7 + 3)
    T.PROP_COLOR = COLORS.get(seg.get("color"))
    T.base_mats()
    sky = T.make_set(seg.get("set", "street"), random.Random(seg.get("seed", 1)))
    T.make_world(sky)
    cam, tgt = T.make_camera()
    end, thumb = gags.GAGS[seg["gag"]](seg, cam, tgt)
    try:  # friends in the background, birds, butterflies
        T.add_extras(seg.get("set", "street"), sky, end, random.Random(seg.get("seed", 1) * 13 + 5))
    except Exception as e:  # noqa: BLE001 - the short still works without them
        print("extras skipped:", e)
    try:  # richer set: textures, leafy trees, grass, far hills, a balloon or kite
        import detail
        detail.enrich(seg.get("set", "street"), sky, end, random.Random(seg.get("seed", 1) * 17 + 3))
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("details skipped:", e)
    T.add_life(end)  # breathing, sway, blinks - nobody stands frozen
    T.sc.frame_start, T.sc.frame_end = 1, end
    T.setup_render(samples, res)
    return end, thumb


def wanted(g, total_known):
    """Should this machine render global frame g?"""
    if mode.startswith("part:"):
        k, n = (int(v) for v in mode.split(":")[1].split("/"))
        return (g - 1) % n == k
    if mode.startswith("every:"):
        n = int(mode.split(":")[1])
        return (g - 1) % n == n // 2
    if mode == "stills":
        return g in total_known
    if mode.startswith("list:"):
        return g in LIST
    return mode == "all"


LIST = {int(v) for v in mode.split(":", 1)[1].split(",") if v} if mode.startswith("list:") else set()


offset, events, thumb_g, done = 0, [], None, 0
sets = []
stills = set()
for i, seg in enumerate(segments):
    end, thumb = build(seg)
    if thumb_g is None:
        thumb_g = offset + thumb
    stills |= {offset + thumb, offset + end // 2}
    events += [[f + offset, kind] for f, kind in T.EVENTS]
    sets.append([offset + 1, seg.get("set", "street")])
    if i:
        events.append([offset + 1, "swish"])  # little whoosh on the cut to the next funny moment
    for f in range(1, end + 1):
        g = offset + f
        if mode == "none" or not wanted(g, stills):
            continue
        t0 = time.time()
        T.sc.frame_set(f)
        T.sc.render.filepath = f"{out}/frames/f_{g:04d}.png"
        T.bpy.ops.render.render(write_still=True)
        done += 1
        print(f"frame {g} (gag {i + 1}/{len(segments)}) in {time.time() - t0:.1f}s", flush=True)
    offset += end

json.dump({"fps": T.FPS, "frames": offset, "events": sorted(events), "thumb": thumb_g,
           "segments": len(segments), "sets": sets}, open(f"{out}/events.json", "w"))
print("done", done, "frames of", offset, flush=True)
