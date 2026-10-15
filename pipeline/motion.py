"""The motion engine: turns still pictures into moving shots.

For every picture it knows the depth (near/far), then flies a virtual camera through it:
pans, push-ins, pull-outs and rises, where near things move more than far things (2.5D parallax).
Two shots per scene, joined with a soft cross-fade. Output: silent mp4 of exact length.
"""
import random
import subprocess
from pathlib import Path

import cv2
import numpy as np

from . import depth as depth_mod

MOVES = ["pan_right", "pan_left", "push_in", "pull_out", "rise"]


def _smooth(p):
    return p * p * (3 - 2 * p)


class Shot:
    def __init__(self, image_path, size, move, rng, use_depth_model=True):
        W, H = size
        self.W, self.H = W, H
        L = int(H * 1.14)  # square source side; the 9:16 window travels across it
        self.L = L
        img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        img = cv2.resize(img, (L, L), interpolation=cv2.INTER_LANCZOS4)
        blur = cv2.GaussianBlur(img, (0, 0), 1.2)
        self.src = cv2.addWeighted(img, 1.35, blur, -0.35, 0)  # gentle sharpen after upscale
        d = depth_mod.estimate(image_path, use_model=use_depth_model)
        d = cv2.resize(d, (L, L), interpolation=cv2.INTER_LINEAR)
        self.depth = cv2.GaussianBlur(d, (0, 0), L / 90).astype(np.float32) - 0.5
        uu, vv = np.meshgrid(np.arange(W, dtype=np.float32) - W / 2, np.arange(H, dtype=np.float32) - H / 2)
        self.uu, self.vv = uu, vv
        self.move = move
        c = L / 2
        par = 0.045 * W
        jitter = rng.uniform(-0.06, 0.06) * L
        # (cx0, cy0, z0) -> (cx1, cy1, z1), parallax x/y, depth-zoom
        if move in ("pan_right", "pan_left"):
            z = 1.04
            span = (L - W / z) / 2 - par - 4
            span = min(span, 0.2 * L)
            a, b = (c - span, c + span) if move == "pan_right" else (c + span, c - span)
            self.path = ((a, c, z), (b, c, z))
            self.par = (par * (1 if move == "pan_right" else -1), 0.0)
            self.pz = 0.0
        elif move == "push_in":
            self.path = ((c, c, 1.02), (c + jitter, c - 0.02 * L, 1.2))
            self.par, self.pz = (0.0, 0.0), 0.10
        elif move == "pull_out":
            self.path = ((c + jitter, c - 0.02 * L, 1.2), (c, c, 1.02))
            self.par, self.pz = (0.0, 0.0), -0.10
        else:  # rise
            z = 1.1
            dy = (L - H / z) / 2 - 6
            self.path = ((c + jitter, c + dy, z), (c + jitter, c - dy, z + 0.03))
            self.par, self.pz = (0.0, -0.6 * par), 0.0

    def frame(self, p):
        e = _smooth(min(1.0, max(0.0, p)))
        (x0, y0, z0), (x1, y1, z1) = self.path
        cx, cy, z = x0 + (x1 - x0) * e, y0 + (y1 - y0) * e, z0 + (z1 - z0) * e
        # clamp so the window never leaves the picture
        hw, hh = self.W / (2 * z), self.H / (2 * z)
        cx = min(max(cx, hw + 2), self.L - hw - 2)
        cy = min(max(cy, hh + 2), self.L - hh - 2)
        xs = cx + self.uu / z
        ys = cy + self.vv / z
        d = cv2.remap(self.depth, xs, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        k = (e - 0.5) * 2
        if self.pz:
            zz = 1.0 + self.pz * d * (e if self.pz > 0 else 1 - e) * 2
            xs = cx + (xs - cx) / zz
            ys = cy + (ys - cy) / zz
        if self.par[0] or self.par[1]:
            xs = xs + self.par[0] * d * k
            ys = ys + self.par[1] * d * k
        return cv2.remap(self.src, xs, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def pick_moves(rng):
    """Wide shots get pans/rises, close shots get push-ins (feels like a real edit)."""
    wide = rng.choice(["pan_right", "pan_left", "rise", "pull_out"])
    close = rng.choice(["push_in", "push_in", "pan_left" if wide == "pan_right" else "pan_right"])
    return [wide, close]


def render_scene(images, seconds, out: Path, size, fps=30, seed=None, use_depth_model=True, crf=18):
    rng = random.Random(seed)
    W, H = size
    moves = pick_moves(rng)
    shots = [Shot(p, size, m, rng, use_depth_model) for p, m in zip(images, moves)]
    n = max(2, round(seconds * fps))
    cut = round(n * 0.55)
    fade = min(round(0.45 * fps), cut - 1)
    a_len, b_start = cut, cut - fade
    b_len = n - b_start
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
         "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
         "-pix_fmt", "yuv420p", str(out)],
        stdin=subprocess.PIPE)
    try:
        for i in range(n):
            if i < b_start:
                f = shots[0].frame(i / max(1, a_len - 1))
            elif i < cut:
                t = (i - b_start + 1) / (fade + 1)
                fa = shots[0].frame(i / max(1, a_len - 1))
                fb = shots[1].frame((i - b_start) / max(1, b_len - 1))
                f = cv2.addWeighted(fa, 1 - t, fb, t, 0)
            else:
                f = shots[1].frame((i - b_start) / max(1, b_len - 1))
            proc.stdin.write(f.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode:
        raise RuntimeError("ffmpeg failed while rendering motion")
    return out
