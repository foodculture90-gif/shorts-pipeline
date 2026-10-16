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


# character voices for cartoon dialogue: (voice, rate, pitch)
CHARACTER_VOICES = {
    "girl": ("en-US-AnaNeural", "+5%", "+0Hz"), "boy": ("en-US-AnaNeural", "+0%", "-18Hz"),
    "toddler": ("en-US-AnaNeural", "+8%", "+25Hz"), "woman": ("en-US-EmmaMultilingualNeural", "+0%", "+0Hz"),
    "man": ("en-US-AndrewMultilingualNeural", "+0%", "+0Hz"), "grandma": ("en-GB-SoniaNeural", "-8%", "-8Hz"),
    "grandpa": ("en-GB-RyanNeural", "-8%", "-12Hz"), "creature": ("en-US-BrianMultilingualNeural", "+12%", "+35Hz"),
}


async def _edge(text, voice, out: Path, rate=None, pitch="+0Hz"):
    import edge_tts

    rate = rate or config.VOICE_RATE
    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    except TypeError:  # older edge-tts
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    words = []
    with open(out, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append((chunk["text"], start, start + chunk["duration"] / 1e7))
    return words


SILENT_SCENE_SECS = 2.6   # a scene without a spoken line (the AI clip is ~2.7 s)


def _silence(out: Path, secs):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", f"{secs:.2f}", "-q:a", "9", str(out)], check=True)


def make_narration(story, workdir: Path, voice=None, offline=False, silent=False):
    """Writes voice{n}.mp3 per scene and word timings in story["scenes"][n]["words"].
    Each scene's shot may have a short character "line" (cartoon dialogue, voiced per character);
    scenes without a line (or silent=True: music + sound effects only) get quiet time instead."""
    looks = {c.get("name", "").lower(): c for c in story.get("characters", [])}
    results = []
    for i, scene in enumerate(story["scenes"]):
        out = workdir / f"voice{i + 1}.mp3"
        shot = (scene.get("shots") or [{}])[0]
        text = "" if silent else (shot.get("line") or "").strip()
        if not text or offline:
            _silence(out, SILENT_SCENE_SECS)
            scene["words"] = []
            results.append(duration(out))
            continue
        who = looks.get((shot.get("speaker") or "").lower(), {})
        v, rate, pitch = CHARACTER_VOICES.get((who.get("voice") or "girl").lower(), CHARACTER_VOICES["girl"])
        words = asyncio.run(_edge(text, v, out, rate, pitch))
        secs = duration(out)
        if not words or len(words) < len(text.split()) // 2:
            words = _even_words(text, secs)
        scene["words"] = [[w, round(a, 3), round(b, 3)] for w, a, b in words]
        results.append(secs)
    return results
