"""Edits the final Short in one pass: living motion shots, smooth transitions, floating particles,
bouncy karaoke captions, title card, narration, made-from-scratch music and sound effects.
Works at any size (small preview for the app, full 1080x1920 for YouTube). Same seed = same video."""
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from . import config, fx, motion, music
from .voice import duration

SR = music.SR
FADE = 0.4          # cross-fade between shots (seconds)


def scene_lengths(voice_secs):
    return [s + (1.0 if i == len(voice_secs) - 1 else 0.4) for i, s in enumerate(voice_secs)]


def _decode(path: Path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def _timeline(story, lengths):
    """Shot segments on the global timeline: [(scene, shot, start, end)], overlapping by FADE."""
    segs, t = [], 0.0
    for i, (scene, secs) in enumerate(zip(story["scenes"], lengths)):
        n = len(scene["shots"])
        cuts = [t + secs * k / n for k in range(n + 1)]
        if n == 2:
            cuts[1] = t + secs * 0.55
        for k in range(n):
            a = cuts[k] - (FADE / 2 if (i or k) else 0)
            b = cuts[k + 1] + FADE / 2
            segs.append((i, k, a, b))
        t += secs
    return segs, t


def _audio(story, voices, lengths, total, music_volume, seed, out: Path, segs=()):
    n = int(total * SR) + 1
    voice = np.zeros(n, np.float32)
    t = 0.0
    starts = []
    for v, secs in zip(voices, lengths):
        a = _decode(v)
        i = int((t + 0.12) * SR)
        voice[i:i + len(a)] += a[: max(0, n - i)]
        starts.append(t)
        t += secs
    mix = np.stack([voice, voice], 1) * 1.0
    if music_volume > 0:
        tracks = sorted(config.MUSIC_DIR.glob("*.mp3")) if config.MUSIC_DIR.exists() else []
        if tracks:
            m = _decode(random.Random(seed).choice(tracks))
            m = np.resize(m, n)
            m = np.stack([m, m], 1)
        else:
            m = music.make_music(total, seed)
            m = np.pad(m, ((0, max(0, n - len(m))), (0, 0)))[:n]
        # duck the music while someone is speaking
        env = np.abs(voice)
        k = int(0.25 * SR)
        env = np.convolve(env, np.ones(k) / k, mode="same")
        speaking = np.clip(env / (env.max() * 0.15 + 1e-6), 0, 1)
        gain = music_volume * 2.2 * (1 - 0.45 * speaking)
        mix += m * gain[:, None]
        # whoosh on every scene change, sparkle on the title
        for j, s0 in enumerate(starts[1:], 1):
            w = music.whoosh(0.5, seed + j)
            i = max(0, int((s0 - 0.25) * SR))
            seg = w[: n - i]
            mix[i:i + len(seg)] += (seg * 0.10)[:, None]
        sp = music.sparkle(seed)
        mix[: len(sp)] += (sp[: n] * 0.10)[:, None]
    # cartoon sound effect for each shot, chosen by the writer to fit the action
    loud = 0.30 if story.get("silent") else 0.16
    for j, (i, k, a, b) in enumerate(segs):
        name = (story["scenes"][i]["shots"][k].get("sfx") or "").strip().lower()
        if name not in music.SFX:
            continue
        fx_ = music.sfx(name, seed + j)
        st_ = int(max(0.0, a + FADE / 2 + 0.3) * SR)
        seg = fx_[: max(0, n - st_)]
        mix[st_:st_ + len(seg)] += (seg * loud)[:, None]
    peak = np.abs(mix).max() or 1
    if peak > 0.97:
        mix *= 0.97 / peak
    out.write_bytes(mix.astype(np.float32).tobytes())
    return out


def render(assets: Path, story, workdir: Path, frame, music_volume=0.12, use_depth_model=True) -> Path:
    """assets: folder with s{n}_{k}.jpg pictures + voice{n}.mp3. Returns path of finished mp4."""
    workdir.mkdir(parents=True, exist_ok=True)
    W, H = frame
    fps = config.FPS
    seed = int(story.get("seed", 1))
    voices = [assets / f"voice{i + 1}.mp3" for i in range(len(story["scenes"]))]
    lengths = scene_lengths([duration(v) for v in voices])
    segs, total = _timeline(story, lengths)

    # shots
    rng = random.Random(seed)
    shots = {}
    for i, scene in enumerate(story["scenes"]):
        moves = motion.pick_moves(rng)
        for k in range(len(scene["shots"])):
            shots[(i, k)] = motion.Shot(assets / f"s{i + 1}_{k + 1}.jpg", frame, moves[k % len(moves)], rng,
                                        use_depth_model, close=(k % 2 == 1),
                                        action=scene["shots"][k].get("action"), animate_chars=use_depth_model)

    # captions on the global timeline (voice starts 0.12 s into each scene)
    words, t0 = [], 0.0
    for scene, secs in zip(story["scenes"], lengths):
        for w in scene.get("words") or []:
            words.append((w[0], t0 + 0.12 + float(w[1]), t0 + 0.12 + float(w[2])))
        t0 += secs
    caps = fx.Captions([] if story.get("silent") else words, frame)  # music-only shorts: no captions
    title = fx.Title(story["title"], frame)
    parts = fx.Particles(fx.particle_kind(story), frame, seed)

    audio = _audio(story, voices, lengths, total, music_volume, seed, workdir / "mix.f32", segs)
    out = workdir / ("preview.mp4" if W < 1080 else "video.mp4")
    preview = W < 1080
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
         "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", str(audio),
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium",
         "-crf", "28" if preview else "18", "-pix_fmt", "yuv420p",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100",
         "-c:a", "aac", "-b:a", "96k" if preview else "192k", "-shortest", "-movflags", "+faststart", str(out)],
        stdin=subprocess.PIPE)
    try:
        nframes = int(round(total * fps))
        for f in range(nframes):
            t = f / fps
            active = [s for s in segs if s[2] <= t < s[3]] or [segs[-1]]
            imgs = []
            for (i, k, a, b) in active[:2]:
                img = shots[(i, k)].frame((t - a) / (b - a), t)
                w8 = 1.0
                if len(active) > 1:
                    if (i, k) == active[1][:2]:
                        w8 = motion.ease((t - a) / FADE)
                imgs.append((img, w8))
            if len(imgs) == 2:
                w8 = imgs[1][1]
                img = (imgs[0][0].astype(np.float32) * (1 - w8) + imgs[1][0].astype(np.float32) * w8).astype(np.uint8)
            else:
                img = imgs[0][0]
            img = np.ascontiguousarray(img)
            parts.draw(img, t)
            title.draw(img, t)
            caps.draw(img, t)
            if t > total - 0.5:  # soft fade to black at the very end
                img = (img.astype(np.float32) * max(0.0, (total - t) / 0.5)).astype(np.uint8)
            proc.stdin.write(img.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode:
        raise RuntimeError("ffmpeg failed while rendering the video")
    audio.unlink(missing_ok=True)
    return out


def thumbnail(picture: Path, title: str, out: Path):
    img = Image.open(picture).convert("RGB")
    w, h = img.size
    img = img.crop(((w - h * 9 // 16) // 2, 0, (w + h * 9 // 16) // 2, h)).resize((360, 640))
    arr = np.asarray(img)[..., ::-1].copy()
    arr = motion.grade(arr)
    fx.Title(title, (360, 640), secs=99).draw(arr, 1.0)
    Image.fromarray(arr[..., ::-1]).save(out, "JPEG", quality=82)
    return out
