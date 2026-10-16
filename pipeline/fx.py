"""Visual extras drawn on every frame: floating particles (bubbles, snow, fireflies, sparkles,
sunlight dust), bouncy karaoke captions and the title card."""
import math
import random
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import config

FONT_URLS = {  # free Google fonts, downloaded once on the worker
    "LuckiestGuy.ttf": "https://github.com/google/fonts/raw/main/apache/luckiestguy/LuckiestGuy-Regular.ttf",
}
FALLBACK_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
_font_path = None


def font_path():
    global _font_path
    if _font_path is not None:
        return _font_path
    p = config.MODELS_DIR / "LuckiestGuy.ttf"
    try:
        if not p.exists():
            config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(FONT_URLS["LuckiestGuy.ttf"], p)
        ImageFont.truetype(str(p), 20)
        _font_path = str(p)
    except Exception:  # noqa: BLE001
        p.unlink(missing_ok=True)
        _font_path = next((f for f in FALLBACK_FONTS if Path(f).exists()), "")
    return _font_path


def _font(size):
    fp = font_path()
    return ImageFont.truetype(fp, size) if fp else ImageFont.load_default(size)


# ------------------------------------------------------------------ particles
def particle_kind(story):
    text = f"{story.get('setting', '')} {story.get('style', '')}".lower()
    for kind, words in [("bubbles", ["underwater", "ocean", "sea ", "undersea", "coral", "reef", "fish"]),
                        ("snow", ["snow", "winter", "frost", "ice"]),
                        ("fireflies", ["night", "evening", "dusk", "moon", "firefl", "lamp"]),
                        ("sparkle", ["magic", "space", "star", "fairy", "galaxy", "planet"])]:
        if any(w in text for w in words):
            return kind
    return "dust"


def _sprite(kind, r):
    s = 2 * r + 3
    a = np.zeros((s, s), np.float32)
    c = np.zeros((s, s, 3), np.float32)
    yy, xx = np.mgrid[0:s, 0:s] - (s - 1) / 2
    d = np.sqrt(xx ** 2 + yy ** 2) / max(r, 1)
    if kind == "bubbles":
        ring = np.exp(-((d - 0.85) ** 2) / 0.02)
        hl = np.exp(-(((xx + r * 0.35) ** 2 + (yy + r * 0.35) ** 2) / (0.06 * r * r + 1)))
        a = np.clip(0.55 * ring + 0.12 * (d < 0.9) + 0.8 * hl, 0, 1)
        c[:] = (255, 245, 225)
    elif kind == "sparkle":
        star = np.exp(-(np.abs(xx) * np.abs(yy)) / (0.03 * r * r + 1)) * np.exp(-d * 1.6)
        a = np.clip(star * 1.4 + np.exp(-d * d * 6), 0, 1)
        c[:] = (210, 245, 255)
    else:
        a = np.exp(-d * d * (3.0 if kind == "fireflies" else 2.2))
        c[:] = {"snow": (255, 255, 255), "fireflies": (120, 235, 255), "dust": (200, 235, 255)}[kind]
    return c, a


class Particles:
    def __init__(self, kind, size, seed=1, count=None):
        self.kind = kind
        self.W, self.H = size
        rng = random.Random(seed)
        s = self.W / 1080
        n = count or {"bubbles": 26, "snow": 70, "fireflies": 22, "sparkle": 24, "dust": 34}[kind]
        self.p = []
        for _ in range(n):
            depth = rng.random()  # 0 far .. 1 near
            r = {"bubbles": 6 + 22 * depth, "snow": 3 + 8 * depth, "fireflies": 5 + 9 * depth,
                 "sparkle": 7 + 14 * depth, "dust": 2 + 5 * depth}[kind] * s
            self.p.append(dict(x=rng.random(), y=rng.random(), r=max(2, int(r)), depth=depth,
                               ph=rng.random() * 6.28, sp=rng.uniform(0.6, 1.4)))
        self.sprites = {}

    def _get(self, r):
        if r not in self.sprites:
            self.sprites[r] = _sprite(self.kind, r)
        return self.sprites[r]

    def draw(self, frame, t):
        H, W = frame.shape[:2]
        for q in self.p:
            k, sp, ph, dep = self.kind, q["sp"], q["ph"], q["depth"]
            if k == "bubbles":
                y = (q["y"] - t * 0.07 * sp * (0.5 + dep)) % 1.15 - 0.075
                x = q["x"] + 0.012 * math.sin(t * 2.2 * sp + ph)
                alpha = 0.75
            elif k == "snow":
                y = (q["y"] + t * 0.05 * sp * (0.5 + dep)) % 1.1 - 0.05
                x = q["x"] + 0.02 * math.sin(t * 0.9 * sp + ph)
                alpha = 0.55 + 0.4 * dep
            elif k == "fireflies":
                y = q["y"] + 0.03 * math.sin(t * 0.7 * sp + ph)
                x = q["x"] + 0.03 * math.cos(t * 0.5 * sp + ph * 1.3)
                alpha = 0.25 + 0.75 * max(0.0, math.sin(t * 2.1 * sp + ph)) ** 2
            elif k == "sparkle":
                y = (q["y"] - t * 0.012 * sp) % 1.0
                x = q["x"]
                alpha = max(0.0, math.sin(t * 3.0 * sp + ph)) ** 3
            else:  # dust motes in sunlight
                y = (q["y"] - t * 0.01 * sp) % 1.0
                x = q["x"] + 0.015 * math.sin(t * 0.6 * sp + ph)
                alpha = 0.18 + 0.22 * (0.5 + 0.5 * math.sin(t * 1.3 * sp + ph))
            if alpha < 0.02:
                continue
            col, a = self._get(q["r"])
            s = a.shape[0]
            cx, cy = int(x * W) - s // 2, int(y * H) - s // 2
            x0, y0, x1, y1 = max(cx, 0), max(cy, 0), min(cx + s, W), min(cy + s, H)
            if x0 >= x1 or y0 >= y1:
                continue
            aa = a[y0 - cy:y1 - cy, x0 - cx:x1 - cx, None] * alpha
            cc = col[y0 - cy:y1 - cy, x0 - cx:x1 - cx]
            roi = frame[y0:y1, x0:x1].astype(np.float32)
            if k in ("fireflies", "sparkle", "dust"):
                roi = roi + cc * aa  # glow (additive)
            else:
                roi = roi * (1 - aa) + cc * aa
            frame[y0:y1, x0:x1] = np.clip(roi, 0, 255).astype(np.uint8)
        return frame


# ------------------------------------------------------------------ text
def _text_rgba(lines, size, colours, stroke, W):
    """lines: list of list of (word, colour_index). Returns RGBA numpy (h, w, 4)."""
    f = _font(size)
    pad = stroke * 2 + 8
    lh = int(size * 1.12)
    widths = []
    space = f.getlength(" ")
    for ln in lines:
        widths.append(sum(f.getlength(w) for w, _ in ln) + space * (len(ln) - 1))
    w = int(min(W, max(widths) + 2 * pad))
    h = int(lh * len(lines) + 2 * pad + size * 0.25)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # soft drop shadow
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    for li, ln in enumerate(lines):
        x = (w - widths[li]) / 2
        y = pad + li * lh
        for word, ci in ln:
            ds.text((x + stroke * 0.6, y + stroke * 0.9), word, font=f, fill=(0, 0, 0, 150),
                    stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
            d.text((x, y), word, font=f, fill=colours[ci], stroke_width=stroke, stroke_fill=(30, 22, 60, 255))
            x += f.getlength(word) + space
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(stroke * 0.8))
    sh.alpha_composite(img)
    arr = np.asarray(sh).copy()
    arr[..., :3] = arr[..., [2, 1, 0]]  # RGBA -> BGRA for OpenCV frames
    return arr


def _wrap_words(words, max_chars):
    lines, cur = [], []
    for i, w in enumerate(words):
        if cur and len(" ".join(x for x, _ in cur)) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = []
        cur.append((w, i))
    if cur:
        lines.append(cur)
    return lines


def _ease_back(p):
    p = min(1.0, max(0.0, p))
    c1 = 1.9
    return 1 + (c1 + 1) * (p - 1) ** 3 + c1 * (p - 1) ** 2


def blit(frame, rgba, cx, cy, scale=1.0, alpha=1.0):
    if scale <= 0.02 or alpha <= 0.01:
        return frame
    if abs(scale - 1) > 0.01:
        rgba = cv2.resize(rgba, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = rgba.shape[:2]
    H, W = frame.shape[:2]
    x, y = int(cx - w / 2), int(cy - h / 2)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return frame
    src = rgba[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = src[..., 3:4] / 255.0 * alpha
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (roi * (1 - a) + src[..., :3] * a).astype(np.uint8)
    return frame


class Captions:
    """Big bouncy captions, 2-3 words at a time; the word being spoken lights up yellow."""
    WHITE = (255, 255, 255, 255)
    YELLOW = (255, 214, 64, 255)

    def __init__(self, timed_words, size, max_words=3):
        """timed_words: [(word, start, end)] on the video's global timeline."""
        self.W, self.H = size
        s = self.W / 1080
        self.size = int(104 * s)
        self.stroke = max(3, int(10 * s))
        self.groups = []
        cur = []
        for w in timed_words:
            cur.append(w)
            if len(cur) >= max_words or str(w[0])[-1:] in ".,!?;:" or (len(w) > 3 and w[3]):
                self.groups.append(cur)
                cur = []
        if cur:
            self.groups.append(cur)
        self.cache = {}

    def _img(self, gi, active):
        key = (gi, active)
        if key not in self.cache:
            words = [str(w[0]).upper() for w in self.groups[gi]]
            lines = _wrap_words(words, 12)
            cols = [[(w, 1 if i == active else 0) for w, i in ln] for ln in lines]
            self.cache[key] = _text_rgba(cols, self.size, [self.WHITE, self.YELLOW], self.stroke, self.W)
        return self.cache[key]

    def draw(self, frame, t):
        for gi, g in enumerate(self.groups):
            start = g[0][1]
            end = self.groups[gi + 1][0][1] if gi + 1 < len(self.groups) else g[-1][2] + 0.6
            end = min(end, g[-1][2] + 0.6)
            if not (start - 0.02 <= t < end):
                continue
            active = 0
            for i, w in enumerate(g):
                if t >= w[1]:
                    active = i
            scale = _ease_back((t - start) / 0.16) * 0.25 + 0.75 if t - start < 0.16 else 1.0
            blit(frame, self._img(gi, active), self.W / 2, self.H * 0.76, scale)
        return frame


class Title:
    def __init__(self, text, size, secs=2.4):
        self.W, self.H = size
        s = self.W / 1080
        words = text.upper().split()
        lines = _wrap_words(words, 14)
        cols = [[(w, 1) for w, _ in ln] for ln in lines]
        txt = _text_rgba(cols, int(84 * s), [Captions.WHITE, Captions.YELLOW], max(3, int(9 * s)), self.W)
        h, w = txt.shape[:2]
        pad = int(18 * s)
        pill = Image.new("RGBA", (w + 2 * pad, h + pad), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle([0, 0, w + 2 * pad - 1, h + pad - 1], radius=int(40 * s),
                                               fill=(40, 24, 80, 150))
        bg = np.asarray(pill).copy()
        bg[..., :3] = bg[..., [2, 1, 0]]
        blit_rgba = bg.astype(np.float32)
        a = txt[..., 3:4].astype(np.float32) / 255
        y0, x0 = pad // 2, pad
        region = blit_rgba[y0:y0 + h, x0:x0 + w]
        region[..., :3] = region[..., :3] * (1 - a) + txt[..., :3] * a
        region[..., 3:4] = np.maximum(region[..., 3:4], txt[..., 3:4])
        self.img = blit_rgba.clip(0, 255).astype(np.uint8)
        self.secs = secs

    def draw(self, frame, t):
        if t > self.secs:
            return frame
        scale = 0.8 + 0.2 * _ease_back(t / 0.3)
        alpha = min(1.0, (self.secs - t) / 0.3)
        return blit(frame, self.img, self.W / 2, self.H * 0.085 + self.img.shape[0] / 2, scale, alpha)
