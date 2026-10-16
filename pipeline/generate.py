"""Makes one short.

Step 1 make_assets(): script + 8 pictures + narration (small files, stored until you decide).
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
    log(f"Drawing 8 pictures for “{st['title']}”")
    images.make_pictures(st, workdir, offline=offline, on_image=on_image)
    st["silent"] = bool(silent)
    log("Music-only short (no talking)" if silent else "Recording narration")
    voice.make_narration(st, workdir, voice=voice_name or channel.get("voice"), offline=offline, silent=silent)
    (workdir / "story.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    return st


ASSET_FILES = ["story.json"] + [f"s{i}_{k}.jpg" for i in range(1, 5) for k in (1, 2)] + \
              [f"voice{i}.mp3" for i in range(1, 5)]


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
