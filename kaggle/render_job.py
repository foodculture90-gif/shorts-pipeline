# Runs on Kaggle's free GPU: renders a whole 3D short with Blender Cycles on the graphics card at full
# 1080x1920 with more samples than the free CPU machines can afford, then encodes it to gpu.mp4.
# pipeline/kaggle_render.py fills in JOB, pushes this as a private Kaggle script and downloads the result.
JOB = {}

import glob, json, os, shutil, subprocess, tarfile, time, urllib.request

T0 = time.time()
OUT = "/kaggle/working"
WORK = "/tmp/mc"


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def sh(cmd, env=None):
    log("$", cmd[:300])
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    if r.returncode:
        log(r.stdout[-3000:], r.stderr[-3000:])
    return r


result = {"done": False}
try:
    os.makedirs(WORK, exist_ok=True)
    sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
    # 1. Blender 4.2 LTS
    for v in ("4.2.3", "4.2.2", "4.2.1", "4.2.0"):
        try:
            urllib.request.urlretrieve(f"https://download.blender.org/release/Blender4.2/blender-{v}-linux-x64.tar.xz",
                                       f"{WORK}/b.tar.xz")
            sh(f"cd {WORK} && tar -xJf b.tar.xz && mv blender-{v}-linux-x64 bl && rm b.tar.xz")
            break
        except Exception as e:  # noqa: BLE001
            log("blender", v, "unavailable", e)
    log("blender ready")
    # 2. our code at the exact commit that asked for this render
    url = f"https://codeload.github.com/{JOB['repo']}/tar.gz/{JOB.get('sha') or 'main'}"
    urllib.request.urlretrieve(url, f"{WORK}/code.tgz")
    with tarfile.open(f"{WORK}/code.tgz") as t:
        t.extractall(f"{WORK}/code_x")
    code = glob.glob(f"{WORK}/code_x/*")[0]
    # 3. free assets (sky photos + toy models)
    sh(f"bash {code}/pipeline/get_assets.sh {WORK}/assets")
    # 4. render every frame on the GPU
    json.dump(JOB["spec"], open(f"{WORK}/spec.json", "w"))
    env = dict(os.environ, GPU="1", SAMPLES=str(JOB.get("samples", 48)), RES=str(JOB.get("res", 100)),
               ASSETS=f"{WORK}/assets")
    t1 = time.time()
    p = subprocess.Popen([f"{WORK}/bl/blender", "-b", "--python", f"{code}/blender/scene.py", "--",
                          f"{WORK}/spec.json", f"{WORK}/out", "all"], env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    n = 0
    for line in p.stdout:
        if line.startswith(("frame", "done", "render devices")) or "Error" in line or "Traceback" in line:
            n += line.startswith("frame")
            if not line.startswith("frame") or n % 25 == 1:
                log(line.rstrip()[:300])
    p.wait()
    log(f"rendered {n} frames in {time.time() - t1:.0f}s")
    ev = json.load(open(f"{WORK}/out/events.json"))
    frames = sorted(glob.glob(f"{WORK}/out/frames/f_*.png"))
    if len(frames) < ev["frames"]:
        raise RuntimeError(f"only {len(frames)} of {ev['frames']} frames")
    # 5. encode (near-lossless; the finishing machine adds sound and makes the final file)
    try:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        sh("pip install -q imageio-ffmpeg")
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
    r = sh(f"{ff} -y -loglevel error -framerate {ev.get('fps', 24)} -i {WORK}/out/frames/f_%04d.png "
           f"-vf scale=1080:1920:flags=lanczos,setsar=1 -c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p {OUT}/gpu.mp4")
    if r.returncode:
        raise RuntimeError("encode failed")
    shutil.copy(f"{WORK}/out/events.json", f"{OUT}/events.json")
    tf = ev.get("thumb") or ev["frames"] // 2
    thumb = f"{WORK}/out/frames/f_{tf:04d}.png"
    shutil.copy(thumb if os.path.exists(thumb) else frames[len(frames) // 2], f"{OUT}/thumb.png")
    result = {"done": True, "frames": len(frames), "seconds": round(time.time() - t1)}
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    result["error"] = str(e)[:500]
json.dump(result, open(f"{OUT}/result.json", "w"))
log("result", result)
