"""Plans a 3D short for the Blender engine: which gag, set, cast and prop, plus the YouTube title,
description, hashtags and tags (Gemini writes them; offline templates if it is busy).

The recurring cast (like Morphle's Mila & Morphle) builds a channel identity: same faces every day,
new little stories.
"""
import random

from . import llm

CAST = {
    "pip": "Pip, a round red fluffy creature with big blue eyes and little round ears",
    "bubu": "Bubu, a blue bunny-eared fluffball",
    "mimi": "Mimi, a purple kitty-eared fluffball with a tail",
    "gogo": "Gogo, a green frog-like fluffball with eyes on top of his head",
    "chiko": "Chiko, a tiny yellow chick",
}
NAMES = {k: v.split(",")[0] for k, v in CAST.items()}

GAGS = {
    "steal_treat": dict(props=["cake", "icecream", "cookie", "apple"], sets=["street", "park", "kitchen", "beach"],
                        story="{hero} spots a yummy {prop} on a table and hops over to eat it - but sneaky {friend} "
                              "pops up and slides it away right before the bite! Then {friend} peeks back with a giggle."),
    "ball_bonk": dict(props=["ball"], sets=["park", "street", "beach"],
                      story="{hero} kicks a ball - it bonks {friend} right on the head! Dizzy stars spin around, "
                            "{hero} giggles, and then they both jump and laugh together."),
    "balloon_float": dict(props=["balloon"], sets=["park", "beach", "street"],
                          story="{hero} holds a big red balloon and floats up, up into the sky while {friend} watches "
                                "amazed... then POP! {hero} falls down with a bump, dizzy stars, and everyone laughs."),
    "gift_surprise": dict(props=["gift"], sets=["kitchen", "park", "street"],
                          story="A gift box wiggles and jiggles... {hero} hops over to peek and - SURPRISE! - "
                                "{friend} springs out with a big smile! {hero} jumps back, then they laugh together."),
    "hide_seek": dict(props=["bush"], sets=["park", "street", "beach"],
                      story="{friend} covers their eyes and counts while {hero} tiptoes behind a bush. {friend} "
                            "looks everywhere... the bush wiggles... BOO! {hero} pops out and they both laugh."),
    "slip_peel": dict(props=["peel"], sets=["street", "park", "kitchen"],
                      story="{hero} hops along happily - and slips on a banana peel! A big flip in the air, a bump, "
                            "dizzy stars... {friend} can't stop laughing, and {hero} laughs too."),
}
PROP_NAMES = {"cake": "birthday cake", "icecream": "ice cream", "cookie": "cookie", "apple": "apple",
              "ball": "ball", "balloon": "balloon", "gift": "gift box", "bush": "bush", "peel": "banana peel"}
TABLE_COLORS = ["#FF7AA8", "#7FD1B9", "#FFD23F", "#8FD3FF", "#B7A6FF"]


def plan(recent_specs=(), idea=None, rnd=None):
    """Pick a fresh combination, avoiding the last few gags and hero/friend pairs."""
    rnd = rnd or random.Random()
    recent = [s for s in recent_specs if isinstance(s, dict)]
    recent_gags = [s.get("gag") for s in recent[:4]]
    gags = [g for g in GAGS if g not in recent_gags] or list(GAGS)
    if idea:
        low = idea.lower()
        hits = [g for g in GAGS if any(w in low for w in g.split("_") + GAGS[g]["props"])]
        gags = hits or gags
    gag = rnd.choice(gags)
    g = GAGS[gag]
    pairs = {(s.get("hero"), s.get("friend")) for s in recent[:6]}
    cast = list(CAST)
    for _ in range(20):
        hero, friend = rnd.sample(cast, 2)
        if (hero, friend) not in pairs:
            break
    recent_sets = [s.get("set") for s in recent[:2]]
    sets = [s for s in g["sets"] if s not in recent_sets] or g["sets"]
    return {"gag": gag, "set": rnd.choice(sets), "hero": hero, "friend": friend, "prop": rnd.choice(g["props"]),
            "table_color": rnd.choice(TABLE_COLORS), "seed": rnd.randint(1, 10 ** 6)}


def describe(spec):
    g = GAGS[spec["gag"]]
    return g["story"].format(hero=NAMES[spec["hero"]], friend=NAMES[spec["friend"]], prop=PROP_NAMES[spec["prop"]])


SYSTEM = """You write the YouTube metadata for a wordless 3D cartoon short (about 7 seconds) for kids aged 2-6,
in the style of hit channels like Morphle and Cocomelon. It has only music and cartoon sound effects, no talking.
- Title: a curiosity hook that makes kids AND parents tap, like "How To Get A FREE Cake!!", "Who Took The Cake?!",
  "Don't Pop The Balloon! 🎈". Max 50 characters, Title Case, one fitting emoji at the end. Name the funny thing
  that happens. You may use the characters' names. No clickbait the short doesn't deliver.
- Description: 2 short lines. Line 1 = a playful hook about what happens (with 1 emoji). Line 2 = a line that makes
  them watch again (e.g. "Watch till the end for the surprise! 🎁"). No hashtags in it.
- Hashtags: 4 lowercase hashtags (without #) that real people search, mixing broad and specific.
- Tags: 12 search keywords/phrases (the funny thing, the object, "kids cartoon", "funny cartoon",
  "3d animation for kids", "cartoon for toddlers"...).
- "takeaway": one short gentle sentence (sharing, friendship, laughing together...).
Reply as JSON: {"title": "...", "description": "line 1\\nline 2", "hashtags": [...], "tags": [...], "takeaway": "..."}"""

OFFLINE_TITLES = {
    "steal_treat": ["Who Took My {P}?! 😱", "How To Get A FREE {P}!! 🎂", "The Sneaky {P} Thief! 🤭"],
    "ball_bonk": ["Bonk! Watch Out For The Ball! ⚽", "Oops! The Ball Went BONK! 😵", "Ball Kick Gone Wrong! 😂"],
    "balloon_float": ["Up Up And Away... POP! 🎈", "Don't Pop The Balloon! 🎈", "Flying With A Balloon! 🎈"],
    "gift_surprise": ["What's Inside The Wiggly Box?! 🎁", "The Biggest Surprise Ever! 🎁", "Don't Open The Box! 🎁"],
    "hide_seek": ["Hide And Seek... BOO! 🙈", "Where Is {H}?! 🙈", "Best Hiding Spot Ever! 🌳"],
    "slip_peel": ["Watch Out For The Banana! 🍌", "Oops! Banana Peel Slip! 🍌", "The Silly Banana Slip! 😂"],
}


def _offline(spec, rnd):
    t = rnd.choice(OFFLINE_TITLES[spec["gag"]]).format(P=PROP_NAMES[spec["prop"]].title(), H=NAMES[spec["hero"]])
    return {"title": t, "description": f"{describe(spec)} 😂\nWatch till the end - then watch it again! 🔁",
            "hashtags": ["kidscartoon", "funnycartoon", "cartoonforkids", spec["prop"]],
            "tags": ["kids cartoon", "funny cartoon", "3d animation for kids", "cartoon for toddlers",
                     PROP_NAMES[spec["prop"]], "funny kids video", "preschool cartoon", "cute cartoon",
                     "nursery cartoon", "kids shorts", "toddler video", "cartoon shorts"],
            "takeaway": "It's more fun when we laugh together."}


def meta(spec, past_titles=(), rnd=None):
    rnd = rnd or random.Random()
    cast = "\n".join(f"- {CAST[k]}" for k in (spec["hero"], spec["friend"]))
    recent = "\n".join(f"- {t}" for t in list(past_titles)[:40]) or "- (none yet)"
    prompt = (f"What happens: {describe(spec)}\nCharacters:\n{cast}\n"
              f"Recent titles on this channel (don't repeat them):\n{recent}")
    try:
        m = llm.generate_json(SYSTEM, prompt, temperature=1.0)
        if not (isinstance(m, dict) and m.get("title")):
            raise ValueError("no title")
        out = _offline(spec, rnd)
        out.update({k: v for k, v in m.items() if k in out and v})
        return out
    except Exception as e:  # noqa: BLE001  (Gemini busy/down -> still make the short)
        print("  meta: offline titles because", str(e)[:200])
        return _offline(spec, rnd)
