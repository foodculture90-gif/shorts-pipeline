"""Writes a fresh short every time: new characters, new world, new art style."""
import random

from . import config, music
from .llm import generate_json

SYSTEM = """You write viral YouTube Shorts for a kids' 3D cartoon channel, in the style of the most-watched
preschool cartoon Shorts: one quick, funny, surprising moment that kids want to watch again and again.
Every short has NEW original characters - never reuse characters from earlier shorts, never use existing
characters, shows, brands, real people or celebrities. Invent fresh, uncommon character names (never "Pip").
Characters suit a bright 3D preschool TV cartoon: cute kids, toddlers, grandparents, funny pets and animals,
friendly creatures or vehicles, each with a bold signature colour, a simple outfit and one distinctive detail.

Hard rules:
- Exactly 4 scenes, each is ONE shot of about 4 seconds. Whole short: 16-20 seconds.
- HOOK: scene 1 starts in the MIDDLE of the action - something funny, odd or exciting is already happening in
  the very first second (no intro, no establishing shot, no character just standing there).
- Scene 4 is a clear, funny or heart-warming payoff (a twist, a big laugh, a hug, a happy surprise).
- LOOP: scene 4 must end in the same place, framing and situation as scene 1 begins (e.g. the payoff sets up
  the exact moment the short starts with), so when the short replays it flows straight back into scene 1.
- Simple physical comedy and big expressions that a 3-year-old understands with no words.
- Gentle and safe: no danger, no scary moments, no meanness, no unsafe behaviour to copy.
- Title: a curiosity hook that makes kids AND parents tap - like "How To Get A FREE Cake!!",
  "Who Ate The Last Cookie?!", "Don't Wake The Baby Dragon! 🐉". Max 50 characters, Title Case, one fitting emoji
  at the end. Name the funny thing that happens, never the moral. No clickbait that the short doesn't deliver.
- Description: 2 short lines. Line 1 = a playful hook about what happens (with 1 emoji). Line 2 = a short line that
  makes them watch to the end or again (e.g. "Wait for the sneaky surprise at the end! 🎂"). No hashtags in it.
- Hashtags: 4 lowercase hashtags (without #) that real people search, mixing broad and specific
  (e.g. "kidscartoon", "funnycartoon", "cartoonforkids", "birthdaycake").
- Tags: 12 search keywords/phrases (topic, characters' species, "kids cartoon", "funny cartoon", "3d animation for kids"...).
- Each shot:
  * "framing": "close" (head and shoulders, big expressive faces - use this most) or "wide" (full bodies, place).
  * "prompt": the still picture - who (described by look), what they are doing, where, expression, lighting.
    No text or signs in pictures.
  * "motion": what happens during the 3 seconds, as simple physical action for an animator
    (e.g. "the girl blinks, gasps and points at the cake, her eyes grow huge"). One clear action, small moves,
    characters stay in the frame.
  * "line": what a character says in this shot - max 7 short, funny words, or "" for no line.
    Lines are optional; many great shorts have only 1-3 lines. "speaker": the character's name.
  * "sfx": a cartoon sound effect, one of: SFX_LIST, or "none".
- "characters": every character with a precise, fixed visual description (species/type, colours, clothing,
  one distinctive detail) - keep them identical in every shot - and a "voice": one of
  girl, boy, toddler, woman, man, grandma, grandpa, creature.

Reply as JSON:
{"title": "...",
 "description": "line 1\nline 2",
 "hashtags": ["4 hashtags"],
 "tags": ["12 keywords"],
 "takeaway": "one short sentence",
 "characters": [{"name": "...", "look": "...", "voice": "..."}],
 "setting": "one sentence: the world, palette and mood",
 "scenes": [{"narration": "one sentence describing the scene",
             "shots": [{"framing": "close", "prompt": "...", "motion": "...", "speaker": "...", "line": "...",
                        "sfx": "..."}]}]}"""
SYSTEM = SYSTEM.replace("SFX_LIST", ", ".join(music.SFX))

SILENT_NOTE = ("This short has NO talking: every \"line\" must be \"\" - it is watched with music and sound "
               "effects only, so tell the joke purely through clear, expressive actions.\n")


def write_story(channel, past_titles, idea=None, feedback=None, previous=None, silent=False):
    """channel: dict with name, niche, audience. Returns (story, style)."""
    niche = channel.get("niche") or "kids' stories for ages 3-7"
    if previous and feedback:
        style = previous.get("style") or random.choice(config.STYLES)
        prompt = ((SILENT_NOTE if silent else "") + f"Channel niche: {niche}\nHere is a short you wrote:\n{previous}\n\n"
                  f"The owner wants these changes: {feedback}\nRewrite it, following all rules.")
    else:
        styles = channel.get("styles") or config.STYLES
        style = random.choice(styles)
        fmt = random.choice(config.FORMATS)
        spark = random.choice(config.SPARKS)
        topic = random.choice(config.TOPICS)
        recent = "\n".join(f"- {t}" for t in past_titles[-50:]) or "- (none yet)"
        prompt = (
            (SILENT_NOTE if silent else "")
            + f"Channel: {channel.get('name', '')}\nChannel niche: {niche}\n"
            + f"Format for this short: {fmt}\n"
            f"Popular kids' topic this short is about (put it in the title): {topic}\n"
            f"Random spark (use it, or let it inspire something better): {spark}\n"
            f"Art style the artist will use: {style}\n"
            + (f"The owner's idea for this short: {idea}\n" if idea else "")
            + (f"Extra request: {feedback}\n" if feedback and not previous else "")
            + f"Titles already used on this channel (must be clearly different):\n{recent}"
        )
    for _ in range(3):
        st = generate_json(SYSTEM, prompt, temperature=1.05)
        if _valid(st):
            st["style"] = style
            return st
    raise ValueError("Writer returned an invalid script three times")


def _valid(st):
    try:
        return (len(st["scenes"]) == config.SCENES
                and all(len(s["shots"]) == config.SHOTS_PER_SCENE and s["shots"][0].get("prompt") for s in st["scenes"])
                and st["title"] and st["characters"])
    except (KeyError, TypeError):
        return False


def image_prompt(story, shot):
    # only the characters in this shot (others' features would bleed into them)
    text = " ".join(str(shot.get(k, "")) for k in ("prompt", "motion", "speaker")).lower()
    chars = [c for c in story["characters"] if any(w in text for w in c["name"].lower().split() if len(w) > 2)] or story["characters"]
    cast = "; ".join(f"{c['name']}: {c['look']}" for c in chars)
    # tall 9:16 pictures: keep the characters big and in the middle
    framing = ("wide shot, characters full body in the centre of a tall vertical frame, important action centred"
               if shot.get("framing") == "wide"
               else "medium close-up in a tall vertical frame, head and shoulders big in the centre, "
                    "expressive face, shallow depth of field")
    # characters first: the image model follows the start of the prompt most closely,
    # which keeps the same character looking the same in every shot
    p = (f"{story['style']}. Characters, exactly as described every time: {cast}. "
         f"Shot: {shot['prompt']}. {framing}. World: {story.get('setting', '')}. "
         "Masterpiece, beautiful composition, clean details, no text, no letters, no watermark, no border.")
    return p[:2000]


def offline_story():
    return {
        "title": "The Firefly Who Was Afraid of the Dark",
        "description": "Tilly the firefly is scared of the night. A wise old owl shows her she carries her own light.",
        "tags": ["bedtime story", "kids stories", "firefly"],
        "takeaway": "The light you need is already inside you.",
        "characters": [{"name": "Tilly", "voice": "girl", "look": "a tiny firefly with big round eyes, a glowing lemon-yellow tail and a red knitted scarf"},
                       {"name": "Oma", "voice": "grandma", "look": "a fluffy grey owl with round gold glasses and a lavender shawl"}],
        "setting": "a mossy forest at dusk, deep blues and warm glows, cosy and calm",
        "style": config.STYLES[0],
        "scenes": [
            {"narration": "Tilly hides under a leaf.", "shots": [{"framing": "close", "prompt": "Tilly hiding under a leaf",
             "motion": "Tilly peeks out and blinks", "speaker": "Tilly", "line": "It's so dark!", "sfx": "bubble"}]},
            {"narration": "Oma lands.", "shots": [{"framing": "wide", "prompt": "owl lands beside Tilly",
             "motion": "the owl flaps and lands", "speaker": "Oma", "line": "", "sfx": "whoosh"}]},
            {"narration": "Her tail glows.", "shots": [{"framing": "close", "prompt": "Tilly's tail glowing",
             "motion": "Tilly turns and gasps", "speaker": "Tilly", "line": "Whoa! That's me?!", "sfx": "twinkle"}]},
            {"narration": "Everyone follows her light.", "shots": [{"framing": "wide", "prompt": "fireflies flying",
             "motion": "fireflies swirl happily", "speaker": "Oma", "line": "", "sfx": "tada"}]},
        ],
    }
