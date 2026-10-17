"""Pictures from Cloudflare Workers AI (FLUX schnell) — free 10,000 neurons/day ≈ 170 pictures."""
import base64
import os
import random
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter

from . import config
from .story import image_prompt


class QuotaExceeded(Exception):
    """Today's free picture allowance is used up — try again after midnight UTC."""


def _cloudflare(prompt, seed, out: Path):
    acct, token = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
    r = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{config.IMAGE_MODEL}",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": prompt[:2048], "steps": config.IMAGE_STEPS},  # this model accepts only these two
        timeout=120,
    )
    body = r.text.lower()
    if "neuron" in body and ("allocation" in body or "limit" in body or "daily" in body):
        print("  cloudflare:", r.status_code, r.text[:300])
        raise QuotaExceeded("Cloudflare free daily picture limit reached")
    if r.status_code == 429:  # too many requests at once (4 workers) -> slow down and retry
        raise RuntimeError(f"Cloudflare busy (429): {r.text[:200]}")
    if r.status_code in (401, 403):
        raise PermissionError(f"Cloudflare refused the key ({r.status_code}): {r.text[:200]} — "
                              "re-copy CLOUDFLARE_API_TOKEN (Workers AI template) into GitHub secrets")
    if r.status_code == 400:
        raise ValueError(f"Cloudflare rejected the picture request: {r.text[:300]}")
    r.raise_for_status()
    data = r.json()
    img = (data.get("result") or {}).get("image")
    if not img:
        raise RuntimeError(f"no image returned: {str(data)[:200]}")
    out.write_bytes(base64.b64decode(img))
    Image.open(out).convert("RGB").save(out, "JPEG", quality=92)


def demo_picture(idx, out: Path, size=1024):
    """Offline test scene with clear depth layers (sky, hills, character, foreground grass)."""
    rnd = random.Random(idx)
    pal = [((255, 190, 140), (120, 90, 170)), ((150, 210, 255), (255, 240, 210)),
           ((40, 50, 110), (120, 80, 150)), ((255, 220, 170), (250, 150, 120))][idx % 4]
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):  # sky gradient
        t = y / size
        d.line([(0, y), (size, y)], fill=tuple(int(pal[0][i] * (1 - t) + pal[1][i] * t) for i in range(3)))
    d.ellipse([size * .62, size * .1, size * .82, size * .3], fill=(255, 245, 200))
    for k, (col, top) in enumerate([((110, 150, 190), .45), ((90, 170, 120), .58), ((60, 140, 90), .7)]):
        pts = [(0, size)] + [(x, size * top + 40 * __import__("math").sin(x / (90 + 30 * k) + idx + k)) for x in range(0, size + 8, 8)] + [(size, size)]
        d.polygon(pts, fill=col)
    for _ in range(9):  # trees
        x = rnd.randint(0, size); y = size * .6 + rnd.randint(-20, 30)
        d.rectangle([x - 6, y, x + 6, y + 60], fill=(90, 60, 40))
        d.ellipse([x - 40, y - 70, x + 40, y + 10], fill=(40, 120, 70))
    cx, cy = size * (.35 + .3 * (idx % 2)), size * .74  # character
    d.ellipse([cx - 90, cy - 150, cx + 90, cy + 30], fill=(250, 160, 80))
    d.ellipse([cx - 70, cy - 110, cx - 20, cy - 60], fill="white"); d.ellipse([cx + 20, cy - 110, cx + 70, cy - 60], fill="white")
    d.ellipse([cx - 52, cy - 95, cx - 32, cy - 72], fill=(30, 30, 40)); d.ellipse([cx + 32, cy - 95, cx + 52, cy - 72], fill=(30, 30, 40))
    d.arc([cx - 40, cy - 60, cx + 40, cy - 10], 20, 160, fill=(80, 30, 20), width=6)
    d.rectangle([cx - 80, cy + 10, cx + 80, cy + 40], fill=(200, 40, 60))
    for _ in range(60):  # foreground grass
        x = rnd.randint(0, size)
        d.line([(x, size), (x + rnd.randint(-25, 25), size - rnd.randint(50, 130))], fill=(30, 100, 50), width=6)
    img.filter(ImageFilter.SMOOTH_MORE).save(out, "JPEG", quality=92)


def make_pictures(story, workdir: Path, offline=False, on_image=None):
    """8 pictures (4 scenes × 2 shots). on_image() is called after each real picture (quota tracking).
    Returns list of lists: [[wide, close], ...]."""
    seed = random.randint(1, 2_000_000_000)  # same seed for all shots helps characters match
    scenes = []
    for si, scene in enumerate(story["scenes"]):
        shots = []
        for hi, shot in enumerate(scene["shots"]):
            out = workdir / f"s{si + 1}_{hi + 1}.jpg"
            if offline:
                demo_picture(si * 2 + hi, out)
            else:
                for attempt in range(4):
                    try:
                        _cloudflare(image_prompt(story, shot), seed + attempt * 7, out)
                        if on_image:
                            on_image()
                        break
                    except (QuotaExceeded, PermissionError, ValueError):
                        raise
                    except Exception as e:  # noqa: BLE001
                        print(f"  picture {si + 1}.{hi + 1} attempt {attempt + 1}: {e}")
                        if attempt == 3:
                            raise
                        time.sleep(15 * (attempt + 1))
            shots.append(out)
        scenes.append(shots)
    return scenes
