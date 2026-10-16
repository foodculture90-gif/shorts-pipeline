"""Makes one short.

Step 1 make_assets(): script + pictures + character voices (small files, stored until you decide).
Step 2 render.render(): edits them into a video — a small preview for the app, and the full
1080x1920 version only when you approve (keeps everything inside free storage limits).

    python -m pipeline.generate --offline     # local test, no keys needed
"""
import argparse
import json
import random
import time
from pathlib import Path

from . import config, images, render, story as story_mod, voice


def make_assets(workdir: Path, channel, *, past_titles=(), idea=None, feedback=None, previous=None,
                voice_name=None, offline=False, on_image=None, log=print, silent=False):
    workdir.mkdir(parents=True, exist_ok=True)
    log("Writing the script")
    if offline:
        st = story_mod.offline_story()
    else:
        st = story_mod.write_story(channel, list(past_titles), idea=idea, feedback=feedback, previous=previous,
                                  silent=silent)
    st["seed"] = random.randint(1, 1_000_000)
    log(f"Drawing {sum(len(sc['shots']) for sc in st['scenes'])} pictures for “{st['title']}”")
    images.make_pictures(st, workdir, offline=offline, on_image=on_image)
    st["silent"] = bool(silent)
    log("Music-only short (no talking)" if silent else "Recording character voices")
    voice.make_narration(st, workdir, voice=voice_name or channel.get("voice"), offline=offline, silent=silent)
    (workdir / "story.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    return st


def asset_files(story, clips=None):
    """Files that make up a short: script, pictures, voices (+ AI clips c{n}_{k}.mp4 once animated)."""
    clips = story.get("clips") if clips is None else clips
    files = ["story.json"]
    for i, sc in enumerate(story["scenes"]):
        files += [f"s{i + 1}_{k + 1}.jpg" for k in range(len(sc["shots"]))]
        files.append(f"voice{i + 1}.mp3")
        if clips:
            files += [f"c{i + 1}_{k + 1}.mp4" for k in range(len(sc["shots"]))]
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    if not args.offline:
        raise SystemExit("Shorts are made by the cloud worker. Use --offline for a local test.")
    work = config.OUTPUT / time.strftime("%Y%m%d-%H%M%S")
    st = make_assets(work, {"name": "Test"}, offline=True)
    for size in (config.PREVIEW_SIZE, config.FINAL_SIZE):
        t = time.time()
        out = render.render(work, st, work / f"r{size[0]}", size, use_depth_model=False)
        print(f"{size[0]}x{size[1]}: {out} ({time.time() - t:.0f}s to render)")
    render.thumbnail(work / "s1_1.jpg", st["title"], work / "thumb.jpg")


if __name__ == "__main__":
    main()
