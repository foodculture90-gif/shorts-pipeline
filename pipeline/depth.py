"""Depth estimation (Depth Anything V2 Small, runs free on CPU) — tells the motion engine
what is near and what is far in each picture."""
import urllib.request

import numpy as np
from PIL import Image

from . import config

MODEL_URL = "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"
_session = None


def _load():
    global _session
    if _session is not None:
        return _session
    try:
        import onnxruntime as ort

        path = config.MODELS_DIR / "depth-anything-v2-small.onnx"
        if not path.exists():
            config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
            print("  downloading depth model (once)…")
            urllib.request.urlretrieve(MODEL_URL, path)
        _session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    except Exception as e:  # noqa: BLE001
        print(f"  depth model unavailable ({e}); using simple depth")
        _session = False
    return _session


def _fallback(h, w):
    """Lower in the picture = nearer. Rough, but still gives parallax."""
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    return np.repeat(y ** 1.6, w, axis=1)


def estimate(image_path, use_model=True):
    """Returns float32 HxW depth map in 0..1 (1 = nearest)."""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    sess = _load() if use_model else False
    if not sess:
        return _fallback(h, w)
    size = 518
    x = np.asarray(img.resize((size, size), Image.BICUBIC), dtype=np.float32) / 255.0
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    out = sess.run(None, {sess.get_inputs()[0].name: x})[0]
    d = np.squeeze(out).astype(np.float32)
    d = (d - d.min()) / max(1e-6, d.max() - d.min())
    return np.asarray(Image.fromarray(d).resize((w, h), Image.BICUBIC), dtype=np.float32)
