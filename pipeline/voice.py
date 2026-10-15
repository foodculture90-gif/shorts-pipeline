"""Narration + exact word timings (so captions pop in right as each word is spoken).

Free Microsoft Edge neural voices.
"""
import asyncio
import subprocess
from pathlib import Path

from . import config


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _even_words(text, secs):
    """Fallback timing: spread words evenly over the audio."""
    words = text.split()
    step = secs / max(1, len(words))
    return [(w, i * step, (i + 1) * step) for i, w in enumerate(words)]


async def _edge(text, voice, out: Path):
    import edge_tts

    try:
        comm = edge_tts.Communicate(text, voice, rate=config.VOICE_RATE, boundary="WordBoundary")
    except TypeError:  # older edge-tts
        comm = edge_tts.Communicate(text, voice, rate=config.VOICE_RATE)
    words = []
    with open(out, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append((chunk["text"], start, start + chunk["duration"] / 1e7))
    return words


def make_narration(story, workdir: Path, voice=None, offline=False):
    """Writes voice{n}.mp3 per scene; stores word timings in story["scenes"][n]["words"]."""
    voice = voice or config.DEFAULT_VOICE
    results = []
    for i, scene in enumerate(story["scenes"]):
        text = scene["narration"]
        out = workdir / f"voice{i + 1}.mp3"
        words = []
        if offline:
            secs = max(3.5, len(text.split()) / 2.6)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            f"sine=frequency=330:duration={secs}", "-af", "volume=0.04", str(out)],
                           check=True)
        else:
            words = asyncio.run(_edge(text, voice, out))
        secs = duration(out)
        if not words or len(words) < len(text.split()) // 2:
            words = _even_words(text, secs)
        scene["words"] = [[w, round(a, 3), round(b, 3)] for w, a, b in words]
        results.append(secs)
    return results
