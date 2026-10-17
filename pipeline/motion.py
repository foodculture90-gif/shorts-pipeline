"""The motion engine: turns still pictures into living, moving shots.

For every picture it estimates depth (near/far) and finds the main subject, then flies a virtual
camera through the scene (pans, push-ins, pull-outs, rises) with 2.5D parallax — near things move
more than far things. The subject is always kept in frame, and near things gently "breathe" and
bob so characters feel alive instead of frozen.
"""
import math

import cv2
import numpy as np

from . import animate, depth as depth_mod

MOVES = ["pan_right", "pan_left", "push_in", "pull_out", "rise"]


def ease(p):
    p = min(1.0, max(0.0, p))
    return 0.5 - 0.5 * math.cos(math.pi * p)


def grade(img):
    """Bright TV-cartoon look: a little more colour and contrast, lifted shadows."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.12, 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    out = (out - 128) * 1.05 + 131
    return np.clip(out, 0, 255).astype(np.uint8)


class Shot:
    def __init__(self, image_path, size, move, rng, use_depth_model=True, close=False, action=None,
                 animate_chars=True):
        W, H = size
        self.W, self.H = W, H
        L = int(H * 1.12)  # square source; the 9:16 window travels across it
        self.L = L
        img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        ih, iw = img.shape[:2]
        if abs(ih - iw) > 2:  # tall 9:16 picture -> centre square (fallback puppet engine works on squares)
            m = min(ih, iw)
            y0, x0 = (ih - m) // 2, (iw - m) // 2
            img = img[y0:y0 + m, x0:x0 + m]
            tmp = f"/tmp/sq_{abs(hash(str(image_path)))}.jpg"
            cv2.imwrite(tmp, img)
            image_path = tmp
        img = cv2.resize(img, (L, L), interpolation=cv2.INTER_LANCZOS4)
        blur = cv2.GaussianBlur(img, (0, 0), 1.2)
        self.src = grade(cv2.addWeighted(img, 1.35, blur, -0.35, 0))
        d = depth_mod.estimate(image_path, use_model=use_depth_model)
        d = cv2.resize(d, (L, L), interpolation=cv2.INTER_LINEAR)
        d = cv2.GaussianBlur(d, (0, 0), L / 120).astype(np.float32)
        self.depth = d - 0.5
        acts = [action] if action in animate.ACTIONS else []
        self.scene = animate.Scene(self.src, d, acts, rng, close=close) if animate_chars else None
        # foreground mask for the "alive" breathing motion
        lo, hi = np.quantile(d, 0.6), np.quantile(d, 0.9)
        self.fg = np.clip((d - lo) / max(1e-3, hi - lo), 0, 1).astype(np.float32)
        # main subject = centre of the nearest pixels
        thr = np.quantile(d, 0.85)
        ys, xs = np.nonzero(d >= thr)
        self.sx = float(np.median(xs)) if len(xs) else L / 2
        self.sy = float(np.median(ys)) if len(ys) else L / 2
        uu, vv = np.meshgrid(np.arange(W, dtype=np.float32) - W / 2, np.arange(H, dtype=np.float32) - H / 2)
        self.uu, self.vv = uu, vv
        self.move = move
        self.breath = (rng.uniform(1.7, 2.4), rng.uniform(0, 6.28))
        c = L / 2
        par = 0.04 * W
        sx = self.sx
        sy = min(max(self.sy, c - 0.12 * L), c + 0.12 * L)
        if move in ("pan_right", "pan_left"):
            z = 1.05 if not close else 1.02
            span = 0.07 * L
            a, b = (sx - span, sx + span) if move == "pan_right" else (sx + span, sx - span)
            self.path = ((a, sy, z), (b, sy, z + 0.03))
            self.par = (par * (1 if move == "pan_right" else -1), 0.0)
            self.pz = 0.0
        elif move == "push_in":
            z0, z1 = (1.04, 1.22) if not close else (1.0, 1.12)
            self.path = (((c + sx) / 2, (c + sy) / 2, z0), (sx, sy, z1))
            self.par, self.pz = (0.0, 0.0), 0.12
        elif move == "pull_out":
            zs = 1.24 if not close else 1.12
            self.path = ((sx, sy, zs), ((c + sx) / 2, (c + sy) / 2, 1.0 if close else 1.04))
            self.par, self.pz = (0.0, 0.0), -0.12
        else:  # rise: start low, end on the subject
            z = 1.1
            self.path = ((sx, sy + 0.12 * L, z), (sx, sy - 0.02 * L, z + 0.04))
            self.par, self.pz = (0.0, -0.6 * par), 0.0

    def frame(self, p, t=0.0):
        e = ease(p)
        (x0, y0, z0), (x1, y1, z1) = self.path
        cx, cy, z = x0 + (x1 - x0) * e, y0 + (y1 - y0) * e, z0 + (z1 - z0) * e
        hw, hh = self.W / (2 * z), self.H / (2 * z)
        margin = 0.06 * self.W
        cx = min(max(cx, hw + margin), self.L - hw - margin)
        cy = min(max(cy, hh + margin), self.L - hh - margin)
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
        # breathing / bobbing of near things (characters)
        period, ph = self.breath
        b = math.sin(2 * math.pi * t / period + ph)
        if self.scene is not None and self.scene.animated:
            src = self.scene.frame(t, p)   # characters move by themselves
        else:
            fg = cv2.remap(self.fg, xs, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            s = 1 + 0.012 * b * fg
            xs = self.sx + (xs - self.sx) / s
            ys = self.sy + (ys - self.sy) / s + 0.004 * self.H * b * fg
            src = self.src
        return cv2.remap(src, xs, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def pick_moves(rng):
    """Wide shots get pans/rises, close shots get push-ins (feels like a real edit)."""
    wide = rng.choice(["pan_right", "pan_left", "rise", "pull_out", "push_in"])
    close = rng.choice(["push_in", "push_in", "pull_out", "pan_left" if wide == "pan_right" else "pan_right"])
    return [wide, close]


class ClipShot:
    """A shot made from an AI-animated clip (Kaggle image-to-video): real character motion.
    Fills the frame, adds a slow push-in and the cartoon colour grade. If the scene runs longer than
    the clip, it plays on in reverse (ping-pong) so it never freezes."""

    def __init__(self, clip_path, size, rng, close=False):
        self.W, self.H = size
        cap = cv2.VideoCapture(str(clip_path))
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        frames = []
        while True:
            ok, f = cap.read()
            if not ok:
                break
            h, w = f.shape[:2]
            s = max(self.W / w, self.H / h)  # scale once to cover the output (saves memory and time)
            if abs(s - 1) > 0.01:
                f = cv2.resize(f, (int(w * s + 0.99), int(h * s + 0.99)),
                               interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            frames.append(f)
        cap.release()
        if not frames:
            raise ValueError(f"empty clip {clip_path}")
        self.frames = frames
        self.span = len(frames) / self.fps
        h, w = frames[0].shape[:2]
        self.base = max(self.W / w, self.H / h)
        self.zoom = (1.0, rng.uniform(1.02, 1.045))  # the clip already moves; just a gentle push-in
        self.drift = rng.uniform(-0.006, 0.006) * self.W
        self.cache = {}

    def _get(self, idx):
        if idx not in self.cache:
            if len(self.cache) > 6:
                self.cache.pop(next(iter(self.cache)))
            f = self.frames[idx]
            blur = cv2.GaussianBlur(f, (0, 0), 1.0)
            self.cache[idx] = grade(cv2.addWeighted(f, 1.15, blur, -0.15, 0))
        return self.cache[idx]

    def frame(self, p, t=0.0, seg_secs=None):
        secs = (seg_secs or self.span) * max(0.0, p)
        n = len(self.frames)
        k = int(secs * self.fps)
        period = max(1, 2 * n - 2)
        k %= period
        idx = k if k < n else period - k
        src = self._get(min(n - 1, idx))
        e = ease(p)
        z = self.base * (self.zoom[0] + (self.zoom[1] - self.zoom[0]) * e)
        h, w = src.shape[:2]
        M = np.float32([[z, 0, self.W / 2 - z * w / 2 + self.drift * (e - 0.5)],
                        [0, z, self.H / 2 - z * h / 2]])
        return cv2.warpAffine(src, M, (self.W, self.H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
