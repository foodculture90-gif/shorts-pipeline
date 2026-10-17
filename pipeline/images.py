"""Pictures from Cloudflare Workers AI — free 10,000 neurons/day.

Main model: FLUX.2 klein 4B, drawn directly in tall 9:16 (576x1024, ≈110 neurons ≈ 90 pictures/day).
Later shots get the first picture as a reference image, so the characters look the same in every shot.
Fallback: FLUX.1 schnell (square, no references)."""
import base64
import os
import random
import time
from pathlib import Path

import requests
import io

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


KLEIN = "@cf/black-forest-labs/flux-2-klein-4b"
PIC_W, PIC_H = 576, 1024
_klein_ok = [True]


def _check(r):
    body = r.text.lower()
    if "neuron" in body and ("allocation" in body or "limit" in body or "daily" in body):
        print("  cloudflare:", r.status_code, r.text[:300])
        raise QuotaExceeded("Cloudflare free daily picture limit reached")
    if r.status_code == 429:  # too many requests at once (4 workers) -> slow down and retry
        raise RuntimeError(f"Cloudflare busy (429): {r.text[:200]}")
    if r.status_code in (401, 403):
        raise PermissionError(f"Cloudflare refused the key ({r.status_code}): {r.text[:200]} — "
                              "re-copy CLOUDFLARE_API_TOKEN (Workers AI template) into GitHub secrets")


def _ref_bytes(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((500, 500))  # reference images must be under 512x512
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def _klein(prompt, seed, out: Path, refs=()):
    """Tall 9:16 picture; refs = earlier pictures whose characters must look the same."""
    acct, token = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
    if refs:
        prompt = ("The characters in the reference image(s) are this story's cast: keep every character looking "
                  "exactly the same (same species, colours, clothes, details) but draw a brand-new shot. " + prompt)
    files = {"prompt": (None, prompt[:2000]), "width": (None, str(PIC_W)), "height": (None, str(PIC_H)),
             "seed": (None, str(seed % 2_000_000_000))}
    for i, ref in enumerate(list(refs)[:2]):
        files[f"input_image_{i}"] = (f"ref{i}.jpg", _ref_bytes(ref), "image/jpeg")
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{KLEIN}",
                      headers={"Authorization": f"Bearer {token}"}, files=files, timeout=150)
    _check(r)
    if r.status_code >= 400:
        raise ValueError(f"klein {r.status_code}: {r.text[:300]}")
    data = r.json()
    img = (data.get("result") or {}).get("image") or data.get("image")
    if not img:
        raise ValueError(f"klein returned no image: {str(data)[:200]}")
    out.write_bytes(base64.b64decode(img))
    Image.open(out).convert("RGB").save(out, "JPEG", quality=93)


def picture(prompt, seed, out: Path, refs=()):
    """Best available model; falls back to FLUX.1 schnell if klein is unavailable."""
    if _klein_ok[0]:
        try:
            return _klein(prompt, seed, out, refs)
        except ValueError as e:
            print("  klein unavailable, using schnell:", e)
            _klein_ok[0] = False
    _cloudflare(prompt, seed, out)


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
    """One picture per shot. on_image() is called after each real picture (quota tracking).
    Returns list of lists of picture paths per scene."""
    seed = random.randint(1, 2_000_000_000)  # same seed for all shots helps characters match
    scenes = []
    for si, scene in enumerate(story["scenes"]):
        shots = []
        for hi, shot in enumerate(scene["shots"]):
            out = workdir / f"s{si + 1}_{hi + 1}.jpg"
            done = [p for sc in scenes for p in sc] + shots
            refs = [p for p in ([done[0]] + done[-1:]) if p != out][:2] if done else []
            refs = list(dict.fromkeys(refs))
            if offline:
                demo_picture(si * 2 + hi, out)
                Image.open(out).crop((224, 0, 800, 1024)).save(out, "JPEG", quality=92)  # 576x1024
            else:
                for attempt in range(4):
                    try:
                        picture(image_prompt(story, shot), seed + attempt * 7, out, refs)
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
