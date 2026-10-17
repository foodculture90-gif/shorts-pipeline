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
sh("pip install -q -U 'diffusers>=0.33' 'transformers>=4.48' accelerate sentencepiece imageio imageio-ffmpeg ftfy spandrel")

import torch  # noqa: E402
from PIL import Image  # noqa: E402

log("torch", torch.__version__, "cuda", torch.cuda.is_available(), torch.cuda.device_count())
OUT = "/kaggle/working"
W, H = JOB.get("width", 576), JOB.get("height", 1024)
FRAMES = JOB.get("frames", 97)
OUT_W, OUT_H = JOB.get("out_width", 1080), JOB.get("out_height", 1920)  # final clip size after upscaling
ESRGAN = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth"
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
GENERATED = {}  # pic_name -> local path of pictures drawn here


def draw_pictures():
    """Draw the shorts' pictures here with an open 3D-cartoon image model (one copy per GPU); the first picture of
    each short is the look reference (IP-Adapter) for its other shots. Saved for the app + used as first frames."""
    import gc, shutil, threading
    from diffusers import DiffusionPipeline
    todo = [s for s in JOB["shots"] if s.get("gen_prompt")]
    if not todo:
        return
    model = JOB.get("image_model", "playgroundai/playground-v2.5-1024px-aesthetic")
    log("drawing", len(todo), "pictures with", model)
    # one short's pictures stay together on one GPU, first shot first: it is the look reference for the rest
    groups = {}
    for s in todo:
        groups.setdefault(s["pic_name"].split("__")[0], []).append(s)
    groups = [sorted(g, key=lambda s: s["pic_name"]) for g in groups.values()]
    n = max(1, min(torch.cuda.device_count(), 2, len(groups)))
    pipes, ipa, loaded = [], [False] * n, [False] * n
    for k in range(n):
        try:
            pp = DiffusionPipeline.from_pretrained(model, torch_dtype=torch.float16, variant="fp16")
        except Exception:  # noqa: BLE001  (no fp16 files)
            pp = DiffusionPipeline.from_pretrained(model, torch_dtype=torch.float16)
        pp = pp.to(f"cuda:{k}")
        if JOB.get("ip_adapter", True):  # keeps the same characters across a short's shots
            try:
                pp.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.bin")
                pp.to(f"cuda:{k}")
                if getattr(pp, "image_encoder", None) is not None:  # loads in fp32 -> Half/float mismatch + wasted memory
                    pp.image_encoder.to(f"cuda:{k}", torch.float16)
                ipa[k] = loaded[k] = True
            except Exception as e:  # noqa: BLE001
                log("IP-Adapter unavailable:", str(e)[:200])
        try:  # 768x1344 VAE decode + adapter don't fit a T4 otherwise
            pp.enable_vae_tiling()
        except Exception:  # noqa: BLE001
            pass
        pipes.append(pp)

    def work(k):
        for grp in groups[k::n]:
            ref = None
            for s in grp:
                t = time.time()
                try:
                    g = torch.Generator(f"cuda:{k}").manual_seed(int(s.get("gen_seed", 1)))
                    blank = Image.new("RGB", (224, 224), "white")
                    extra = {}
                    if loaded[k]:  # adapter loaded: reference picture (or a blank one at strength 0)
                        use = ipa[k] and ref is not None
                        pipes[k].set_ip_adapter_scale(JOB.get("ip_scale", 0.45) if use else 0.0)
                        extra["ip_adapter_image"] = ref if use else blank
                    args = dict(prompt=s["gen_prompt"], negative_prompt=s.get("gen_negative"), width=768, height=1344,
                                num_inference_steps=JOB.get("image_steps", 30), guidance_scale=JOB.get("image_guidance", 3.0))
                    try:
                        im = pipes[k](generator=g, **args, **extra).images[0]
                    except Exception as e:  # noqa: BLE001  (IP-Adapter / memory trouble -> unload it and carry on)
                        if not loaded[k]:
                            raise
                        log("IP-Adapter FAILED, removing it:", repr(e)[:400])
                        ipa[k] = loaded[k] = False
                        try:
                            pipes[k].unload_ip_adapter()
                        except Exception as e2:  # noqa: BLE001
                            log("unload_ip_adapter:", repr(e2)[:200])
                        gc.collect()
                        torch.cuda.empty_cache()
                        g = torch.Generator(f"cuda:{k}").manual_seed(int(s.get("gen_seed", 1)))
                        im = pipes[k](generator=g, **args).images[0]
                    if ref is None:
                        ref = im.copy()
                    im = im.convert("RGB").resize((W, H), Image.LANCZOS)
                    path = f"{OUT}/{s['pic_name']}.jpg"
                    im.save(path, "JPEG", quality=93)
                    GENERATED[s["pic_name"]] = path
                    s["image_path"] = path
                    log(f"gpu{k} picture {s['pic_name']} in {time.time() - t:.0f}s")
                except Exception:  # noqa: BLE001
                    log(f"picture {s['pic_name']} FAILED\n" + traceback.format_exc()[-1200:])
                finally:
                    gc.collect()
                    torch.cuda.empty_cache()

    th = [threading.Thread(target=work, args=(k,)) for k in range(n)]
    [x.start() for x in th]
    [x.join() for x in th]
    del pipes
    gc.collect()
    torch.cuda.empty_cache()
    shutil.rmtree(os.path.expanduser("~/.cache/huggingface/hub/models--" + model.replace("/", "--")), ignore_errors=True)


try:
    draw_pictures()
except Exception:  # noqa: BLE001
    log("picture step FAILED\n" + traceback.format_exc())

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
    # bf16 on the 2nd GPU is ~20x faster than the CPU and doesn't overflow like fp16; CPU fp32 = fallback
    enc_dev = "cpu"
    if torch.cuda.device_count() > 1 and JOB.get("t5_gpu", True):
        try:
            pipe.text_encoder.to("cuda:1", torch.bfloat16)
            enc_dev = "cuda:1"
        except Exception as e:  # noqa: BLE001
            log("T5 on GPU failed, using CPU:", str(e)[:200])
            pipe.text_encoder.to("cpu", torch.float32)
    else:
        pipe.text_encoder.to("cpu", torch.float32)

    def encode_all():
        out = []
        for shot in JOB["shots"]:
            with torch.no_grad():
                pe, pm, ne, nm = pipe.encode_prompt(prompt=shot["prompt"], negative_prompt=NEG,
                                                    do_classifier_free_guidance=CFG, device=enc_dev,
                                                    max_sequence_length=256)
            out.append((pe.float().cpu().to(dtype), pm.cpu(),
                        ne.float().cpu().to(dtype) if CFG else None, nm.cpu() if CFG else None))
        return out

    try:
        embeds = encode_all()
        if enc_dev != "cpu" and not all(torch.isfinite(e[0]).all() for e in embeds):
            raise ValueError("non-finite prompt embeddings")
    except Exception as e:  # noqa: BLE001
        log("GPU text encoding failed -> CPU:", str(e)[:200])
        enc_dev = "cpu"
        pipe.text_encoder.to("cpu", torch.float32)
        embeds = encode_all()
    log("text encoder on", enc_dev)
    log("prompts encoded")
    pipe.text_encoder = None
    gc.collect()
    torch.cuda.empty_cache()

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

    # 3) cartoon upscaler (Real-ESRGAN anime-video, tiny + fast): 576x1024 -> crisp 1080x1920
    import numpy as np
    import imageio
    import torch.nn.functional as F
    upscalers = {}
    if JOB.get("upscale", True):
        try:
            from spandrel import ModelLoader
            fetch(ESRGAN, "/tmp/esrgan.pth")
            for k in range(ngpu):
                upscalers[k] = ModelLoader().load_from_file("/tmp/esrgan.pth").model.eval().half().to(f"cuda:{k}")
            log("upscaler ready")
        except Exception as e:  # noqa: BLE001
            log("upscaler unavailable:", str(e)[:300])

    def save_clip(frames, path, k):
        arr = np.stack([np.asarray(f.convert("RGB")) for f in frames])  # T,H,W,3 uint8
        out = []
        if k in upscalers:
            try:
                with torch.no_grad():
                    for i in range(0, len(arr), 4):
                        x = torch.from_numpy(arr[i:i + 4]).to(f"cuda:{k}").permute(0, 3, 1, 2).half() / 255
                        y = upscalers[k](x).clamp(0, 1)
                        y = F.interpolate(y.float(), size=(OUT_H, OUT_W), mode="area")
                        out.append((y * 255).round().byte().permute(0, 2, 3, 1).cpu().numpy())
                arr = np.concatenate(out)
            except Exception as e:  # noqa: BLE001
                log("upscale failed, saving raw:", str(e)[:200])
        w = imageio.get_writer(path, fps=JOB.get("fps", 24), codec="libx264", quality=None, macro_block_size=8,
                               ffmpeg_params=["-crf", str(JOB.get("crf", 20)), "-pix_fmt", "yuv420p", "-preset", "medium"])
        for fr in arr:
            w.append_data(fr)
        w.close()

    END = float(JOB.get("end_strength", 0.0))  # >0: also pin the last frame to the picture (less drift/blur)

    def work(k):
        pp, dev = pipes[k], f"cuda:{k}"
        for i in range(k, len(JOB["shots"]), ngpu):
            shot = JOB["shots"][i]
            name = shot.get("name", f"clip{i}")
            t = time.time()
            try:
                if not (shot.get("image_path") or shot.get("image")):
                    raise RuntimeError("no picture for this shot")
                img = prep(shot.get("image_path") or fetch(shot["image"], f"/tmp/in{i}.jpg"))
                pe, pm, ne, nm = embeds[i]
                conds = [LTXVideoCondition(image=img, frame_index=0)]
                end, gs = float(shot.get("end_strength", END)), float(shot.get("guidance", GUIDE))
                if end > 0:
                    end_img = img
                    if shot.get("end_image"):  # loop back to the short's first picture
                        try:
                            e = shot["end_image"]
                            end_img = prep(GENERATED[e[4:]] if e.startswith("gen:") else fetch(e, f"/tmp/end{i}.jpg"))
                        except Exception as e:  # noqa: BLE001
                            log("end image failed", e)
                    conds.append(LTXVideoCondition(image=end_img, frame_index=FRAMES - 1, strength=end))
                g = torch.Generator(dev).manual_seed(shot.get("seed", 1))
                extra = dict(negative_prompt_embeds=ne.to(dev), negative_prompt_attention_mask=nm.to(dev)) if gs > 1.0 else {}
                with torch.cuda.device(k):
                    video = pp(conditions=conds, prompt_embeds=pe.to(dev), prompt_attention_mask=pm.to(dev), **extra,
                               width=W, height=H, num_frames=FRAMES, num_inference_steps=STEPS,
                               guidance_scale=gs, generator=g, decode_timestep=0.05, decode_noise_scale=0.025,
                               output_type="pil").frames[0]
                save_clip(video, f"{OUT}/{name}.mp4", k)
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
