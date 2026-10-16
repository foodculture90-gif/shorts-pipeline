"""Writes a fresh short every time: new characters, new world, new art style."""
import random

from . import config
from .llm import generate_json

SYSTEM = """You write scripts for YouTube Shorts. Each short is a complete mini-story told in 4 scenes,
narrated aloud over beautiful illustrations. Every short has NEW original characters — never reuse
characters from earlier shorts, never use existing characters, brands, real people or celebrities.
Invent fresh, uncommon character names every time (never "Pip"). Characters suit a bright 3D preschool
TV cartoon: cute animals (often puppies or other pets), kids and friendly vehicles, each with a clear job or
special skill, a bold signature colour and a simple outfit or gear.

Hard rules:
- Exactly 4 scenes. Each scene: 1-2 short sentences of narration, 15-24 words.
- Total narration 70-90 words (about 35 seconds).
- Scene 1's first sentence is a hook (a surprise, question or funny problem).
- A satisfying ending. For kids' channels: gentle, warm, simple words, a kind takeaway, no scary or unsafe moments.
- Each scene has exactly 2 shots: first a WIDE shot (the place and action), then a CLOSE shot
  (a character's face/reaction or an important object).
- Shot prompts describe only what is visible: who, doing what, where, expression, lighting, time of day.
  Name characters by their look (not just their name) so an artist can draw them. No text or signs in images.
- "characters": every recurring character with a precise, fixed visual description
  (species/type, colours, clothing, one distinctive detail). Keep them identical in every shot.

Reply as JSON:
{"title": "max 60 chars, catchy, no emojis",
 "description": "2 short sentences",
 "tags": ["5-8 tags"],
 "takeaway": "one short sentence",
 "characters": [{"name": "...", "look": "..."}],
 "setting": "one sentence: the world, palette and mood",
 "scenes": [{"narration": "...", "shots": [{"framing": "wide", "prompt": "..."},
                                          {"framing": "close", "prompt": "..."}]}]}"""


def write_story(channel, past_titles, idea=None, feedback=None, previous=None):
    """channel: dict with name, niche, audience. Returns (story, style)."""
    niche = channel.get("niche") or "kids' stories for ages 3-7"
    if previous and feedback:
        style = previous.get("style") or random.choice(config.STYLES)
        prompt = (f"Channel niche: {niche}\nHere is a short you wrote:\n{previous}\n\n"
                  f"The owner wants these changes: {feedback}\nRewrite it, following all rules.")
    else:
        styles = channel.get("styles") or config.STYLES
        style = random.choice(styles)
        fmt = random.choice(config.FORMATS)
        spark = random.choice(config.SPARKS)
        recent = "\n".join(f"- {t}" for t in past_titles[-50:]) or "- (none yet)"
        prompt = (
            f"Channel: {channel.get('name', '')}\nChannel niche: {niche}\n"
            f"Format for this short: {fmt}\n"
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
                and all(len(s["shots"]) == config.SHOTS_PER_SCENE and s["narration"] for s in st["scenes"])
                and st["title"] and st["characters"])
    except (KeyError, TypeError):
        return False


def image_prompt(story, shot):
    cast = "; ".join(f"{c['name']}: {c['look']}" for c in story["characters"])
    framing = ("wide establishing shot, full scene visible" if shot.get("framing") == "wide"
               else "close-up, expressive face, shallow depth of field")
    p = (f"{shot['prompt']}. {framing}. Characters (draw exactly as described): {cast}. "
         f"World: {story.get('setting', '')}. Style: {story['style']}. "
         "Masterpiece, beautiful composition, clean details, no text, no letters, no watermark, no border.")
    return p[:2000]


def offline_story():
    return {
        "title": "The Firefly Who Was Afraid of the Dark",
        "description": "Tilly the firefly is scared of the night. A wise old owl shows her she carries her own light.",
        "tags": ["bedtime story", "kids stories", "firefly"],
        "takeaway": "The light you need is already inside you.",
        "characters": [{"name": "Tilly", "look": "a tiny firefly with big round eyes, a glowing lemon-yellow tail and a red knitted scarf"},
                       {"name": "Oma", "look": "a fluffy grey owl with round gold glasses and a lavender shawl"}],
        "setting": "a mossy forest at dusk, deep blues and warm glows, cosy and calm",
        "style": config.STYLES[0],
        "scenes": [
            {"narration": "Every evening, when the sun went down, little Tilly the firefly hid under a leaf. She was afraid of the dark!",
             "shots": [{"framing": "wide", "prompt": "a forest at dusk"}, {"framing": "close", "prompt": "Tilly hiding"}]},
            {"narration": "Oma the owl landed beside her. Why do you hide, little one? Because the night is so big, Tilly whispered.",
             "shots": [{"framing": "wide", "prompt": "owl lands"}, {"framing": "close", "prompt": "Tilly whispering"}]},
            {"narration": "Oma smiled. Look behind you, Tilly. Tilly turned around, and her tail was glowing like a tiny golden star!",
             "shots": [{"framing": "wide", "prompt": "glowing tail"}, {"framing": "close", "prompt": "surprised face"}]},
            {"narration": "That night, Tilly lit the way for all her friends. The light you need is already inside you. Goodnight!",
             "shots": [{"framing": "wide", "prompt": "fireflies flying"}, {"framing": "close", "prompt": "Tilly smiling"}]},
        ],
    }
