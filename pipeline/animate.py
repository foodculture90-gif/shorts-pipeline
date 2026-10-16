"""Character animation: cuts the characters out of each picture and brings them to life.

Two free cut-out models (run on CPU) find the characters; the gap they leave in the background is
painted in. Each character then moves like a cartoon puppet — hops with squash-and-stretch,
sways, dances, jumps, waddles, nods and breathes — while the camera moves through the scene.
"""
import math
import urllib.request

import cv2
import numpy as np
from PIL import Image

from . import config

SEG_MODELS = {
    "isnet-general-use": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx",
    "u2netp": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx",
}
ACTIONS = ["bounce", "hop", "sway", "dance", "jump", "walk", "idle", "nod", "wiggle"]
_sessions = None


def _load():
    global _sessions
    if _sessions is not None:
        return _sessions
    _sessions = []
    try:
        import onnxruntime as ort
        for name, url in SEG_MODELS.items():
            path = config.MODELS_DIR / f"{name}.onnx"
            if not path.exists():
                config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
                print(f"  downloading cut-out model {name} (once)…")
                urllib.request.urlretrieve(url, path)
            _sessions.append(ort.InferenceSession(str(path), providers=["CPUExecutionProvider"]))
    except Exception as e:  # noqa: BLE001
        print(f"  cut-out models unavailable ({e}); characters stay still")
        _sessions = []
    return _sessions


def _segment(sess, rgb):
    n = sess.get_inputs()[0].shape[2]
    x = cv2.resize(rgb, (n, n), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    if n >= 1024:  # ISNet
        x = x - 0.5
    else:          # U2Net
        x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    o = sess.run(None, {sess.get_inputs()[0].name: x})[0][0, 0]
    o = (o - o.min()) / (o.max() - o.min() + 1e-6)
    return cv2.resize(o.astype(np.float32), (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)


class Puppet:
    """One cut-out character with its own motion."""

    def __init__(self, rgba, x0, y0, action, rng, L=None):
        self.rgba = rgba            # float32 (h, w, 4), alpha 0..1, premultiplied colour
        self.x0, self.y0 = x0, y0   # top-left in the source picture
        h, w = rgba.shape[:2]
        self.h, self.w = h, w
        self.px, self.py = w / 2, h * 0.97   # pivot: feet
        self.action = action
        # big (close-up) characters move less, so they never leave the frame or uncover the background
        frac = h / float(L or h * 3)
        self.amp = min(1.0, max(0.25, 0.28 / max(frac, 1e-3)))
        self.phase = rng.uniform(0, 6.28)
        self.speed = rng.uniform(0.85, 1.15)

    def pose(self, t, p):
        """(dx, dy, angle_deg, sx, sy, bend) at time t (seconds) / shot progress p (0..1)."""
        a, ph, sp = self.action, self.phase, self.speed
        H = self.h
        dx = dy = ang = bend = 0.0
        sx = sy = 1.0
        breath = math.sin(2 * math.pi * t / 2.0 + ph)
        sy += 0.015 * breath
        sx -= 0.008 * breath
        if a in ("bounce", "hop", "walk", "dance"):
            f = {"bounce": 2.2, "hop": 1.6, "walk": 2.6, "dance": 2.4}[a] * sp
            c = (t * f + ph / 6.28) % 1.0
            height = {"bounce": 0.07, "hop": 0.11, "walk": 0.03, "dance": 0.05}[a] * self.amp
            air = math.sin(math.pi * c)
            dy -= height * H * air
            squash = max(0.0, 1 - air * 4) if c < 0.5 else max(0.0, 1 - (1 - c) * 6)
            k = 0.10 if a != "walk" else 0.04
            sy *= 1 - k * squash + 0.05 * air
            sx *= 1 + k * 0.8 * squash - 0.03 * air
            if a == "walk":
                ang += 4 * math.sin(2 * math.pi * t * f / 2 + ph)
                dx += 0.04 * self.w * self.amp * math.sin(2 * math.pi * p * 0.5)
            if a == "dance":
                bend += 0.10 * self.w * math.sin(2 * math.pi * t * f / 2 + ph)
                ang += 5 * math.sin(2 * math.pi * t * f / 2 + ph)
        elif a == "jump":
            # anticipation squash, big leap, landing squash, settle
            c = (p * 1.0) % 1.0
            if 0.25 < c < 0.75:
                q = (c - 0.25) / 0.5
                dy -= 0.16 * H * self.amp * math.sin(math.pi * q)
                sy *= 1.06
                sx *= 0.96
            else:
                q = min(abs(c - 0.25), abs(c - 0.75)) / 0.12
                if q < 1:
                    sy *= 1 - 0.12 * (1 - q)
                    sx *= 1 + 0.09 * (1 - q)
        elif a == "sway":
            ang += 5 * math.sin(2 * math.pi * t * 0.6 * sp + ph)
            bend += 0.05 * self.w * math.sin(2 * math.pi * t * 0.6 * sp + ph + 0.8)
        elif a == "wiggle":
            bend += 0.08 * self.w * math.sin(2 * math.pi * t * 2.2 * sp + ph)
            sy *= 1 + 0.03 * math.sin(2 * math.pi * t * 4.4 * sp)
        elif a == "nod":
            bend += 0.0
            sy *= 1 - 0.035 * max(0.0, math.sin(2 * math.pi * t * 1.4 * sp + ph))
            ang += 2.5 * math.sin(2 * math.pi * t * 0.7 * sp + ph)
        else:  # idle
            ang += 1.5 * math.sin(2 * math.pi * t * 0.4 + ph)
            bend += 0.02 * self.w * math.sin(2 * math.pi * t * 0.5 + ph)
        return dx, dy, ang, sx, sy, bend

    def render(self, t, p, pad):
        """Returns (rgba_crop, ox, oy): the posed character and where its top-left goes."""
        dx, dy, ang, sx, sy, bend = self.pose(t, p)
        ox, oy = self.x0 - pad, self.y0 - pad
        if getattr(self, "_grid_pad", None) != pad:
            H, W = self.h + 2 * pad, self.w + 2 * pad
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            self._gx, self._gy, self._grid_pad = xx - pad - self.px, yy - pad - self.py, pad
        # output coords relative to pivot (feet), then undo: translate, rotate, scale, bend
        u = self._gx - dx
        v = self._gy - dy
        r = math.radians(-ang)
        cu, cv_ = math.cos(r), math.sin(r)
        u, v = u * cu - v * cv_, u * cv_ + v * cu
        u, v = u / sx, v / sy
        hw = np.clip(-v / max(1, self.py), 0, 1) ** 1.6
        u = u - bend * hw
        mx = (u + self.px).astype(np.float32)
        my = (v + self.py).astype(np.float32)
        out = cv2.remap(self.rgba, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        return out, ox, oy


class Scene:
    """A picture split into a painted-in background and animated character puppets."""

    CLOSE_SAFE = {"bounce": "nod", "hop": "wiggle", "jump": "nod", "walk": "sway", "dance": "wiggle"}

    def __init__(self, img_bgr, depth, actions, rng, max_chars=3, close=False):
        self.bg = img_bgr
        self.puppets = []
        sess = _load()
        if not sess:
            return
        L = img_bgr.shape[0]
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        m = np.maximum.reduce([_segment(s, rgb) for s in sess])
        m = np.clip((m - 0.3) / 0.35, 0, 1)
        binary = (m > 0.5).astype(np.uint8)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
        dthr = np.quantile(depth, 0.55)
        comps = []
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if area < 0.012 * L * L or area > 0.6 * L * L:
                continue
            if float(np.median(depth[lab == i])) < dthr:   # far away (moon, mountains) → not a character
                continue
            comps.append((area, i, x, y, w, h))
        comps.sort(reverse=True)
        if not comps:
            return
        hole = np.zeros((L, L), np.uint8)
        for k, (area, i, x, y, w, h) in enumerate(comps[:max_chars]):
            comp = (lab == i).astype(np.uint8)
            soft = cv2.GaussianBlur(cv2.dilate(comp, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 1.5)
            alpha = np.clip(np.maximum(m * cv2.dilate(comp, np.ones((15, 15), np.uint8)), soft * 0.0), 0, 1)
            alpha = np.where(alpha > 0.04, alpha, 0).astype(np.float32)
            pad = int(0.06 * max(w, h))
            x1, y1 = max(0, x - pad), max(0, y - pad)
            x2, y2 = min(L, x + w + pad), min(L, y + h + pad)
            crop = img_bgr[y1:y2, x1:x2].astype(np.float32)
            a = alpha[y1:y2, x1:x2, None]
            rgba = np.concatenate([crop * a, a], 2)
            act = actions[k % len(actions)] if actions else rng.choice(ACTIONS)
            if k > 0:  # side characters do something gentler, so the main one stands out
                act = rng.choice(["idle", "sway", "nod", "bounce"])
            if close or h > 0.6 * L:
                act = self.CLOSE_SAFE.get(act, act)
            self.puppets.append(Puppet(rgba, x1, y1, act, rng, L))
            hole |= (cv2.dilate(comp, np.ones((int(L * 0.025) | 1,) * 2, np.uint8)) > 0).astype(np.uint8)
        # paint the background behind the characters (at half size, then blended back)
        s = 0.5
        small = cv2.resize(img_bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        hs = cv2.resize(hole, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
        filled = cv2.inpaint(small, hs, 9, cv2.INPAINT_TELEA)
        filled = cv2.GaussianBlur(filled, (0, 0), 2)
        filled = cv2.resize(filled, (L, L), interpolation=cv2.INTER_CUBIC)
        hm = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 3)[..., None]
        self.bg = (img_bgr * (1 - hm) + filled * hm).astype(np.uint8)
        self.pad = int(0.35 * L * 0.5)

    @property
    def animated(self):
        return bool(self.puppets)

    def frame(self, t, p):
        if not self.puppets:
            return self.bg
        out = self.bg.copy()
        L = out.shape[0]
        for pup in sorted(self.puppets, key=lambda q: q.y0 + q.h):  # back to front
            pad = int(0.22 * max(pup.h, pup.w))
            rgba, ox, oy = pup.render(t, p, pad)
            h, w = rgba.shape[:2]
            x0, y0, x1, y1 = max(ox, 0), max(oy, 0), min(ox + w, L), min(oy + h, L)
            if x0 >= x1 or y0 >= y1:
                continue
            src = rgba[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
            a = src[..., 3:4]
            roi = out[y0:y1, x0:x1].astype(np.float32)
            out[y0:y1, x0:x1] = np.clip(roi * (1 - a) + src[..., :3], 0, 255).astype(np.uint8)
        return out
