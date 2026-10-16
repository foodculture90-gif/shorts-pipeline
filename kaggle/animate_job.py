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
       "morphing, melting, character leaving the frame, empty scene, fast camera move, text, watermark")


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

NAMES = []
try:
    import copy, gc, threading
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

    # 1) encode every prompt with the T5 text encoder in full precision on the CPU (fp16 T5 overflows),
    #    then free it
    GUIDE = float(JOB.get("guidance", 3.0))
    CFG = any(float(s.get("guidance", GUIDE)) > 1.0 for s in JOB["shots"])  # guidance 1 = no negative pass = 2x faster
    pipe.text_encoder.to("cpu", torch.float32)
    embeds = []
    for shot in JOB["shots"]:
        with torch.no_grad():
            pe, pm, ne, nm = pipe.encode_prompt(prompt=shot["prompt"], negative_prompt=NEG,
                                                do_classifier_free_guidance=CFG, device="cpu",
                                                max_sequence_length=256)
        embeds.append((pe.to(dtype), pm, ne.to(dtype) if CFG else None, nm if CFG else None))
    log("prompts encoded")
    pipe.text_encoder = None
    gc.collect()

    # 2) one copy of the video model per GPU (Kaggle gives 2 x T4) -> twice as many clips per hour
    ngpu = max(1, min(torch.cuda.device_count(), int(JOB.get("gpus", 2)), len(JOB["shots"])))
    pipes = [pipe]
    for k in range(1, ngpu):
        pipes.append(LTXConditionPipeline(scheduler=copy.deepcopy(pipe.scheduler), vae=copy.deepcopy(pipe.vae),
                                          text_encoder=None, tokenizer=pipe.tokenizer,
                                          transformer=copy.deepcopy(pipe.transformer)))
    for k, pp in enumerate(pipes):
        pp.transformer.to(f"cuda:{k}")
        pp.vae.to(f"cuda:{k}")
        pp.vae.enable_tiling()
    log("model on", ngpu, "GPU(s)")

    END = float(JOB.get("end_strength", 0.0))  # >0: also pin the last frame to the picture (less drift/blur)

    def work(k):
        pp, dev = pipes[k], f"cuda:{k}"
        for i in range(k, len(JOB["shots"]), ngpu):
            shot = JOB["shots"][i]
            name = shot.get("name", f"clip{i}")
            t = time.time()
            try:
                img = prep(fetch(shot["image"], f"/tmp/in{i}.jpg"))
                pe, pm, ne, nm = embeds[i]
                conds = [LTXVideoCondition(image=img, frame_index=0)]
                end, gs = float(shot.get("end_strength", END)), float(shot.get("guidance", GUIDE))
                if end > 0:
                    conds.append(LTXVideoCondition(image=img, frame_index=FRAMES - 1, strength=end))
                g = torch.Generator(dev).manual_seed(shot.get("seed", 1))
                extra = dict(negative_prompt_embeds=ne.to(dev), negative_prompt_attention_mask=nm.to(dev)) if gs > 1.0 else {}
                with torch.cuda.device(k):
                    video = pp(conditions=conds, prompt_embeds=pe.to(dev), prompt_attention_mask=pm.to(dev), **extra,
                               width=W, height=H, num_frames=FRAMES, num_inference_steps=STEPS,
                               guidance_scale=gs, generator=g, decode_timestep=0.05, decode_noise_scale=0.025,
                               output_type="pil").frames[0]
                export_to_video(video, f"{OUT}/{name}.mp4", fps=JOB.get("fps", 24))
                NAMES.append(name)
                log(f"gpu{k} clip {name}: {len(video)} frames in {time.time() - t:.0f}s")
            except Exception:  # noqa: BLE001  (one bad shot must not stop the rest)
                log(f"gpu{k} clip {name} FAILED\n" + traceback.format_exc()[-1500:])

    threads = [threading.Thread(target=work, args=(k,)) for k in range(ngpu)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
except Exception:
    log("FAILED\n" + traceback.format_exc())

json.dump({"done": len(NAMES), "secs": time.time() - T0, "names": NAMES}, open(f"{OUT}/result.json", "w"))
log("finished", len(NAMES), "clips")
