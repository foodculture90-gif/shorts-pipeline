"""Build + render one 3D short from a spec.

  blender -b --python blender/scene.py -- spec.json <outdir> <mode>
  mode: part:K/N (render every Nth frame from K+1) | stills | all | none
  spec: {"gag": "steal_treat", "set": "street", "hero": "pip", "friend": "chiko", "prop": "cake", "seed": 1}
  env: SAMPLES (default 20), RES (percent of 1080x1920, default 100)
"""
import json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gags  # noqa: E402
import toon as T  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
spec = json.load(open(argv[0]))
out = os.path.abspath(argv[1] if len(argv) > 1 else "out")
mode = argv[2] if len(argv) > 2 else "all"
os.makedirs(out, exist_ok=True)

T.reset()
T.base_mats()
rnd = random.Random(spec.get("seed", 1))
sky = T.make_set(spec.get("set", "street"), rnd)
T.make_world(sky)
cam, tgt = T.make_camera()
end, thumb = gags.GAGS[spec["gag"]](spec, cam, tgt)
T.sc.frame_start, T.sc.frame_end = 1, end
T.setup_render(int(os.environ.get("SAMPLES", "20")), int(os.environ.get("RES", "100")))
T.render_frames(out, mode, thumb)
