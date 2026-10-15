"""Edits the final Short: motion shots + narration + word-timed captions + title + music.
Works at any size (small preview for the app, full 1080x1920 for YouTube)."""
import random
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config, motion
from .voice import duration

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _font(size):
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def _text_png(text, out: Path, size, y_center, frame, wrap=14, fill="white"):
    W, H = frame
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = _font(size)
    lines = textwrap.wrap(text, wrap)
    lh = int(size * 1.18)
    y = y_center - lh * len(lines) // 2
    for line in lines:
        w = d.textlength(line, font=f)
        d.text(((W - w) / 2, y), line, font=f, fill=fill,
               stroke_width=max(3, size // 9), stroke_fill=(25, 20, 45))
        y += lh
    img.save(out)


def _caption_groups(words, max_words=3):
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or str(w[0])[-1:] in ".,!?":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return [(" ".join(x[0] for x in g), g[0][1], g[-1][2]) for g in groups]


def scene_lengths(voice_secs):
    return [s + (0.9 if i == len(voice_secs) - 1 else 0.35) for i, s in enumerate(voice_secs)]


def _scene(i, clip, audio, words, seconds, title, workdir: Path, frame):
    W, H = frame
    s = W / 1080
    inputs = ["-i", str(clip), "-i", str(audio)]
    overlays = []
    groups = _caption_groups([tuple(w) for w in words])
    for c, (text, start, end) in enumerate(groups):
        png = workdir / f"cap{i}_{c}.png"
        _text_png(text.upper(), png, int(94 * s), int(H * 0.80), frame,
                  fill=(255, 224, 90) if c % 2 else "white")
        nxt = groups[c + 1][1] if c + 1 < len(groups) else seconds
        overlays.append((png, start, max(end, nxt)))
    if title:
        png = workdir / "title.png"
        _text_png(title, png, int(80 * s), int(H * 0.13), frame, wrap=20)
        overlays.append((png, 0, min(2.6, seconds)))
    for png, *_ in overlays:
        inputs += ["-i", str(png)]
    graph = (f"[0:v]setpts=PTS-STARTPTS,vignette=angle=PI/6,"
             f"fade=t=in:st=0:d=0.2,fade=t=out:st={seconds - 0.2:.2f}:d=0.2[v0];")
    last = "v0"
    for k, (_, start, end) in enumerate(overlays):
        graph += f"[{last}][{k + 2}:v]overlay=0:0:enable='between(t,{start:.2f},{end:.2f})'[v{k + 1}];"
        last = f"v{k + 1}"
    graph += f"[1:a]aresample=44100,apad=whole_dur={seconds:.2f}[a]"
    out = workdir / f"part{i}.mp4"
    preview = W < 1080
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph,
         "-map", f"[{last}]", "-map", "[a]", "-t", f"{seconds:.2f}", "-r", str(config.FPS),
         "-c:v", "libx264", "-preset", "medium", "-crf", "27" if preview else "19", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "96k" if preview else "192k", "-ac", "2", str(out)],
        check=True)
    return out


def render(assets: Path, story, workdir: Path, frame, music_volume=0.12, use_depth_model=True) -> Path:
    """assets: folder with s{n}_{k}.jpg pictures + voice{n}.mp3. Returns path of finished mp4."""
    workdir.mkdir(parents=True, exist_ok=True)
    voices = [assets / f"voice{i + 1}.mp3" for i in range(len(story["scenes"]))]
    lengths = scene_lengths([duration(v) for v in voices])
    seed = story.get("seed", 1)
    parts = []
    for i, (scene, secs) in enumerate(zip(story["scenes"], lengths)):
        pics = [assets / f"s{i + 1}_{k + 1}.jpg" for k in range(len(scene["shots"]))]
        clip = motion.render_scene(pics, secs, workdir / f"motion{i}.mp4", frame, config.FPS,
                                   seed=seed + i, use_depth_model=use_depth_model,
                                   crf=24 if frame[0] < 1080 else 17)
        parts.append(_scene(i, clip, voices[i], scene.get("words") or [], secs,
                            story["title"] if i == 0 else None, workdir, frame))
    listing = workdir / "parts.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    joined = workdir / "joined.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-c", "copy", str(joined)], check=True, cwd=workdir)
    final = workdir / ("preview.mp4" if frame[0] < 1080 else "video.mp4")
    tracks = sorted(config.MUSIC_DIR.glob("*.mp3")) if config.MUSIC_DIR.exists() else []
    if tracks and music_volume > 0:
        music = random.Random(seed).choice(tracks)
        total = duration(joined)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined), "-stream_loop", "-1", "-i", str(music),
             "-filter_complex",
             f"[1:a]volume={music_volume},afade=t=in:d=0.8,afade=t=out:st={max(0, total - 1.5):.2f}:d=1.5[m];"
             "[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-t", f"{total:.2f}", "-movflags", "+faststart", str(final)], check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined), "-c", "copy",
                        "-movflags", "+faststart", str(final)], check=True)
    return final


def thumbnail(picture: Path, title: str, out: Path):
    img = Image.open(picture).convert("RGB")
    w, h = img.size
    img = img.crop(((w - h * 9 // 16) // 2, 0, (w + h * 9 // 16) // 2, h)).resize((360, 640))
    tmp = out.with_suffix(".png")
    _text_png(title, tmp, 34, 90, (360, 640), wrap=18, fill=(255, 224, 90))
    over = Image.open(tmp)
    img.paste(over, (0, 0), over)
    img.save(out, "JPEG", quality=80)
    tmp.unlink()
    return out
