# Runs on Kaggle's free GPU. The worker fills in JOB below, pushes this script as a private
# Kaggle "kernel", waits for it, then downloads /kaggle/working/*.mp4.
# Turns each still picture into a short moving clip with an open image-to-video model.
JOB = {}  # filled in by pipeline/kaggle_video.py

import json, os, subprocess, sys, time, traceback, urllib.request

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def sh(cmd):
    log("$", cmd)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode:
        log(r.stdout[-2000:], r.stderr[-2000:])
    return r.returncode


log("job:", json.dumps({k: v for k, v in JOB.items() if k != "shots"}))
sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
sh("pip uninstall -y -q torchao")  # Kaggle's old torchao breaks new diffusers; not needed
sh("pip install -q -U 'diffusers>=0.33' 'transformers>=4.48' accelerate sentencepiece imageio imageio-ffmpeg ftfy")

import torch  # noqa: E402
from PIL import Image  # noqa: E402

log("torch", torch.__version__, "cuda", torch.cuda.is_available(), torch.cuda.device_count())
OUT = "/kaggle/working"
W, H = JOB.get("width", 512), JOB.get("height", 896)
FRAMES = JOB.get("frames", 73)
STEPS = JOB.get("steps", 30)
MODEL = JOB.get("model", "Lightricks/LTX-Video-0.9.5")
NEG = ("worst quality, inconsistent motion, blurry, jittery, distorted, deformed, extra limbs, "
       "morphing, text, watermark")


def fetch(url, path):
    urllib.request.urlretrieve(url, path)
    return path


def prep(path):
    """Square picture -> centred vertical crop at the video size."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    tw = int(h * W / H)
    x = max(0, (w - tw) // 2)
    return im.crop((x, 0, x + tw, h)).resize((W, H), Image.LANCZOS)


try:
    from huggingface_hub import list_models
    if JOB.get("list_models"):
        log("LTX models:", [m.id for m in list_models(author="Lightricks", search="LTX", limit=40)])
except Exception as e:  # noqa: BLE001
    log("list models failed", e)

done = 0
try:
    from diffusers import LTXConditionPipeline
    from diffusers.pipelines.ltx.pipeline_ltx_condition import LTXVideoCondition
    from diffusers.utils import export_to_video

    dtype = torch.float16 if JOB.get("fp16", True) else torch.float32
    log("loading", MODEL, dtype)
    try:
        pipe = LTXConditionPipeline.from_pretrained(MODEL, torch_dtype=dtype)
    except Exception as e:  # noqa: BLE001  (model not in diffusers format etc.)
        log("could not load", MODEL, "->", str(e)[:300], "; using Lightricks/LTX-Video-0.9.5")
        MODEL, STEPS = "Lightricks/LTX-Video-0.9.5", max(STEPS, 30)
        pipe = LTXConditionPipeline.from_pretrained(MODEL, torch_dtype=dtype)
    # T5 text encoder in full precision on the CPU (fp16 T5 overflows); everything else on GPU 0
    pipe.text_encoder.to("cpu", torch.float32)
    pipe.transformer.to("cuda:0")
    pipe.vae.to("cuda:0")
    pipe.vae.enable_tiling()
    log("loaded; gpu mem GB", torch.cuda.memory_allocated() / 1e9)

    # encode every prompt first, then free the big text encoder so the GPU path is clean
    embeds = []
    for shot in JOB["shots"]:
        with torch.no_grad():
            pe, pm, ne, nm = pipe.encode_prompt(prompt=shot["prompt"], negative_prompt=NEG,
                                                do_classifier_free_guidance=True, device="cpu",
                                                max_sequence_length=256)
        embeds.append((pe.to("cuda:0", dtype), pm.to("cuda:0"), ne.to("cuda:0", dtype), nm.to("cuda:0")))
    log("prompts encoded")
    import gc
    pipe.text_encoder = None
    gc.collect()

    for i, shot in enumerate(JOB["shots"]):
        t = time.time()
        src = fetch(shot["image"], f"/tmp/in{i}.jpg")
        img = prep(src)
        pe, pm, ne, nm = embeds[i]
        cond = LTXVideoCondition(image=img, frame_index=0)
        g = torch.Generator("cuda:0").manual_seed(shot.get("seed", 1))
        video = pipe(conditions=[cond], prompt_embeds=pe, prompt_attention_mask=pm,
                     negative_prompt_embeds=ne, negative_prompt_attention_mask=nm,
                     width=W, height=H, num_frames=FRAMES, num_inference_steps=STEPS,
                     guidance_scale=JOB.get("guidance", 3.0), generator=g,
                     decode_timestep=0.05, decode_noise_scale=0.025,
                     output_type="pil").frames[0]
        name = shot.get("name", f"clip{i}")
        export_to_video(video, f"{OUT}/{name}.mp4", fps=JOB.get("fps", 24))
        done += 1
        log(f"clip {name}: {len(video)} frames in {time.time() - t:.0f}s")
except Exception:
    log("FAILED\n" + traceback.format_exc())

json.dump({"done": done, "secs": time.time() - T0}, open(f"{OUT}/result.json", "w"))
log("finished", done, "clips")
