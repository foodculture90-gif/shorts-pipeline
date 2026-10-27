"""Picture of the cast standing in a row (to check how the characters look).

  blender -b --python blender/cast_sheet.py -- pip,bubu,leo out.png [samples] [width] [height]
"""
import os, random, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toon as T  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
names, out = argv[0].split(","), argv[1]
samples = int(argv[2]) if len(argv) > 2 else 16
W = int(argv[3]) if len(argv) > 3 else 1600
H = int(argv[4]) if len(argv) > 4 else 720
t0 = time.time()
T.reset()
T.THEME.clear()
T.THEME.update({"sky": "day", "season": "summer", "pal": 3}, set="park")
T.LOOKS.clear()
T.VAR = random.Random(3)
T.base_mats()
T.make_world(T.make_set("park", random.Random(3)))
cam, tgt = T.make_camera()
n, gap = len(names), 1.25
for i, nm in enumerate(names):
    ch = T.make_character(nm, (i - (n - 1) / 2) * gap, 0.3)
    T.turn(ch, 1, (i - (n - 1) / 2) * -6, 1)
print("built in %.1fs" % (time.time() - t0), flush=True)
d = ((n - 1) * gap + 1.6) * 50 / 36
cam.data.lens = 50
cam.location = (0, 0.3 - d, 1.0)
tgt.location = (0, 0.3, 0.62)
cam.data.dof.use_dof = False
T.sc.frame_start = T.sc.frame_end = 1
T.setup_render(samples, 100)
T.sc.render.resolution_x, T.sc.render.resolution_y = W, H
T.sc.frame_set(1)
T.sc.render.filepath = out
t1 = time.time()
T.bpy.ops.render.render(write_still=True)
print("render %.1fs" % (time.time() - t1), flush=True)
