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


SEG_SECONDS = 7.0  # each gag is a 7-second mini story


def _segments(recent):
    for s in recent:
        for g in (s.get("segments") or [s]):
            yield g


def plan(recent_specs=(), idea=None, rnd=None, min_s=20, max_s=60, slot=None):
    """One short = 3-5 gags in a row with the same two friends (21-35 s, never under 20 or over 60):
    longer watch time, a recurring duo, and a fresh mix every day."""
    rnd = rnd or random.Random()
    recent = [s for s in recent_specs if isinstance(s, dict)]
    lo, hi = max(3, int(-(-min_s // SEG_SECONDS))), min(len(GAGS), int(max_s // SEG_SECONDS))
    n = rnd.choice([k for k in (3, 4, 4, 5) if lo <= k <= hi] or [lo])
    recent_gags = [g.get("gag") for g in list(_segments(recent))[:6]]
    order = [g for g in GAGS if g not in recent_gags] + [g for g in GAGS if g in recent_gags]
    rnd.shuffle(order)
    order.sort(key=lambda g: g in recent_gags)  # fresh gags first
    if idea:
        low = idea.lower()
        hits = [g for g in GAGS if any(w in low for w in g.split("_") + GAGS[g]["props"])]
        order = hits + [g for g in order if g not in hits]
    if slot is not None and not idea:  # shorts planned at the same moment still get different lead gags
        lead = list(GAGS)[slot % len(GAGS)]
        order = [lead] + [g for g in order if g != lead]
    gags = order[:n]
    rest = gags[1:]
    rnd.shuffle(rest)
    gags = [gags[0]] + rest
    pairs = {(s.get("hero"), s.get("friend")) for s in recent[:6]}
    cast = list(CAST)
    duos = [(x, y) for i, x in enumerate(cast) for y in cast[i + 1:]]
    if slot is not None:
        a, b = duos[(slot * 7) % len(duos)]
        if rnd.random() < 0.5:
            a, b = b, a
    else:
        for _ in range(20):
            a, b = rnd.sample(cast, 2)
            if (a, b) not in pairs and (b, a) not in pairs:
                break
    # one home set for the whole short when the gags allow it
    common = [x for x in ["street", "park", "beach", "kitchen"] if all(x in GAGS[g]["sets"] for g in gags)]
    home = rnd.choice(common) if common else None
    segs = []
    for k, gag in enumerate(gags):
        g = GAGS[gag]
        hero, friend = (a, b) if k % 2 == 0 else (b, a)  # the two friends take turns being the hero
        st = home or rnd.choice(g["sets"])
        segs.append({"gag": gag, "set": st, "hero": hero, "friend": friend, "prop": rnd.choice(g["props"]),
                     "table_color": rnd.choice(TABLE_COLORS), "seed": rnd.randint(1, 10 ** 6)})
    return {"hero": a, "friend": b, "set": segs[0]["set"], "gag": segs[0]["gag"], "segments": segs,
            "seed": rnd.randint(1, 10 ** 6)}


def describe_one(seg):
    g = GAGS[seg["gag"]]
    return g["story"].format(hero=NAMES[seg["hero"]], friend=NAMES[seg["friend"]], prop=PROP_NAMES[seg["prop"]])


def describe(spec):
    return " Then: ".join(describe_one(s) for s in (spec.get("segments") or [spec]))


SYSTEM = """You write the YouTube metadata for a wordless 3D cartoon short (20-40 seconds, a few funny moments in a row)
for kids aged 2-6,
in the style of hit channels like Morphle and Cocomelon. It has only music and cartoon sound effects, no talking.
- Title: a curiosity hook that makes kids AND parents tap. Max 50 characters, Title Case, one fitting emoji at the end.
  Name the funniest thing that happens (it is usually the FIRST moment). You may use the characters' names.
  Use this title format: FORMAT. Never start with the same first two words as a recent title.
  No clickbait the short doesn't deliver.
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
    first = (spec.get("segments") or [spec])[0]
    t = rnd.choice(OFFLINE_TITLES[first["gag"]]).format(P=PROP_NAMES[first["prop"]].title(), H=NAMES[first["hero"]])
    return {"title": t, "description": f"{NAMES[spec['hero']]} and {NAMES[spec['friend']]} have the silliest day! 😂\n"
                                       "Watch till the end - then watch it again! 🔁",
            "hashtags": ["kidscartoon", "funnycartoon", "cartoonforkids", first["prop"]],
            "tags": ["kids cartoon", "funny cartoon", "3d animation for kids", "cartoon for toddlers",
                     PROP_NAMES[first["prop"]], "funny kids video", "preschool cartoon", "cute cartoon",
                     "nursery cartoon", "kids shorts", "toddler video", "cartoon shorts"],
            "takeaway": "It's more fun when we laugh together."}


TITLE_FORMATS = ["How To ... (e.g. \"How To Get A FREE Cake!!\")", "Don't ... (e.g. \"Don't Pop The Balloon!\")",
                 "a question that is NOT \"Who ...\" (e.g. \"Where Did The Cake Go?!\")", "Name + action (e.g. \"Pip's Big Banana Slip!\")",
                 "an exclamation (e.g. \"Oops! The Ball Went BONK!\")", "The ... (e.g. \"The Sneakiest Cake Thief Ever!\")",
                 "a challenge or warning (e.g. \"Try Not To Laugh: Balloon Edition!\")"]


def meta(spec, past_titles=(), rnd=None, slot=None):
    rnd = rnd or random.Random()
    fmt = TITLE_FORMATS[slot % len(TITLE_FORMATS)] if slot is not None else rnd.choice(TITLE_FORMATS)
    cast = "\n".join(f"- {CAST[k]}" for k in (spec["hero"], spec["friend"]))
    recent = "\n".join(f"- {t}" for t in list(past_titles)[:40]) or "- (none yet)"
    prompt = (f"What happens: {describe(spec)}\nCharacters:\n{cast}\n"
              f"Recent titles on this channel (don't repeat them):\n{recent}")
    try:
        m = llm.generate_json(SYSTEM.replace("FORMAT", fmt), prompt, temperature=1.0)
        if not (isinstance(m, dict) and m.get("title")):
            raise ValueError("no title")
        out = _offline(spec, rnd)
        out.update({k: v for k, v in m.items() if k in out and v})
        return out
    except Exception as e:  # noqa: BLE001  (Gemini busy/down -> still make the short)
        print("  meta: offline titles because", str(e)[:200])
        return _offline(spec, rnd)
