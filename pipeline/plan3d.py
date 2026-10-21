"""Plans a 3D short for the Blender engine: which gag, set, cast and prop, plus the YouTube title,
description, hashtags and tags (Gemini writes them; offline templates if it is busy).

The recurring cast (like Morphle's Mila & Morphle) builds a channel identity: same faces every day,
new little stories.
"""
import math
import random

from . import llm

CAST = {
    "pip": "Pip, a round red fluffy creature with big blue eyes and little round ears",
    "bubu": "Bubu, a blue bunny-eared fluffball",
    "mimi": "Mimi, a purple kitty-eared fluffball with a tail",
    "gogo": "Gogo, a green frog-like fluffball with eyes on top of his head",
    "chiko": "Chiko, a tiny yellow chick",
    "lulu": "Lulu, a pink teddy-bear fluffball",
    "tobi": "Tobi, an orange fox fluffball with a white-tipped tail",
    "teo": "Teo, a cream puppy fluffball with floppy brown ears",
    "popo": "Popo, a little navy-blue penguin",
    "bobo": "Bobo, a cuddly panda fluffball with black ears and eye patches",
    "zuzu": "Zuzu, a lilac unicorn fluffball with a golden horn and a rainbow mane",
    "leo": "Leo, a sunny little lion fluffball with a big orange mane",
    "dodo": "Dodo, a fluffy white duckling",
}
ALL_SETS = ["street", "park", "beach", "kitchen", "playground", "snow", "bedroom", "livingroom", "space", "pirate",
            "christmas", "farm", "camping", "castle", "underwater", "candy", "market", "desert"]
OUTDOOR = ["street", "park", "beach", "playground", "snow", "pirate", "christmas", "farm", "camping", "castle", "candy",
           "market", "desert"]
INDOOR = ["kitchen", "bedroom", "livingroom"]
GREEN = ["park", "street", "beach", "playground", "snow", "pirate", "christmas", "farm", "camping", "castle", "market"]
COLORS = ["red", "blue", "yellow", "green", "purple", "orange", "pink"]
ACCESSORIES = ["party_hat", "bow", "cap", "flower", "bowtie", "crown"]
ACC_COLORS = ["#FF4D6D", "#FFD23F", "#4DA6FF", "#5CCB6B", "#B57BFF", "#FF8A3D", "#FFFFFF", "#2EC4B6"]
ACC_WORDS = {"party_hat": "a party hat", "bow": "a bow", "cap": "a cap", "flower": "a flower", "bowtie": "a bow tie",
             "crown": "a little crown"}
NAMES = {k: v.split(",")[0] for k, v in CAST.items()}

GAGS = {
    "steal_treat": dict(props=["cake", "icecream", "cookie", "apple", "donut", "cupcake", "watermelon", "pizza",
                               "strawberry", "gingerbread"], sets=ALL_SETS,
                        story="{hero} spots a yummy {prop} on a table and hops over to eat it - but sneaky {friend} "
                              "pops up and slides it away right before the bite! Then {friend} peeks back with a giggle."),
    "ball_bonk": dict(props=["ball"], sets=OUTDOOR + ["bedroom", "livingroom", "space"],
                      story="{hero} kicks a ball - it bonks {friend} right on the head! Dizzy stars spin around, "
                            "{hero} giggles, and then they both jump and laugh together."),
    "balloon_float": dict(props=["balloon"], sets=OUTDOOR,
                          story="{hero} holds a big {color} balloon and floats up, up into the sky while {friend} watches "
                                "amazed... then POP! {hero} falls down with a bump, dizzy stars, and everyone laughs."),
    "gift_surprise": dict(props=["gift"], sets=ALL_SETS,
                          story="A gift box wiggles and jiggles... {hero} hops over to peek and - SURPRISE! - "
                                "{friend} springs out with a big smile! {hero} jumps back, then they laugh together."),
    "hide_seek": dict(props=["bush"], sets=GREEN,
                      story="{friend} covers their eyes and counts while {hero} tiptoes behind a bush. {friend} "
                            "looks everywhere... the bush wiggles... BOO! {hero} pops out and they both laugh."),
    "slip_peel": dict(props=["peel"], sets=ALL_SETS,
                      story="{hero} hops along happily - and slips on a banana peel! A big flip in the air, a bump, "
                            "dizzy stars... {friend} can't stop laughing, and {hero} laughs too."),
    "sneeze": dict(props=["flower"], sets=ALL_SETS,
                   story="{hero} sniffs a big flower... ah... ah... AH-CHOO! The giant sneeze blows {friend} away with "
                         "a flip and all the petals fly off! {hero} goes 'oops', then they both laugh."),
    "dance_party": dict(props=["confetti"], sets=ALL_SETS,
                        story="{hero} starts a silly dance with wiggles and a spin. {friend} copies - but spins so fast "
                              "they get dizzy and plop down! Then they dance together and confetti pops."),
    "bubbles": dict(props=["bubbles"], sets=ALL_SETS,
                    story="{hero} blows bubbles and {friend} hops to pop them, pop, pop, pop! Then {hero} blows a GIANT "
                          "bubble that catches {friend} and floats them up... POP! Down they plop, and everyone laughs."),
    "wake_up": dict(props=["horn"], sets=ALL_SETS,
                    story="{friend} is fast asleep, snoring with a little bubble. {hero} tiptoes over with a party horn "
                          "and - PARP! - {friend} jumps sky-high! Then {friend} grabs the horn and does it right back."),
    "race": dict(props=["flag"], sets=OUTDOOR + ["space"],
                 story="Ready, set, GO! {hero} and {friend} race to the finish line. {friend} zooms ahead, but {hero} "
                       "does a super leap over them and snaps the finish tape! Confetti, cheers and giggles."),
}
PROP_NAMES = {"flower": "big flower", "confetti": "confetti", "bubbles": "bubbles", "horn": "party horn",
              "flag": "finish flag","cake": "birthday cake", "icecream": "ice cream", "cookie": "cookie", "apple": "apple",
              "donut": "donut", "cupcake": "cupcake", "watermelon": "watermelon slice", "pizza": "pizza slice",
              "strawberry": "big strawberry", "gingerbread": "gingerbread man",
              "ball": "ball", "balloon": "balloon", "gift": "gift box", "bush": "bush", "peel": "banana peel"}
TABLE_COLORS = ["#FF7AA8", "#7FD1B9", "#FFD23F", "#8FD3FF", "#B7A6FF"]


SEG_SECONDS = 7.0  # each gag is a 7-second mini story


def _segments(recent):
    for s in recent:
        for g in (s.get("segments") or [s]):
            yield g


# ---- turning a wish ("Lulu and Popo in the snow with a blue balloon", "different characters") into choices
WORDS = {  # offline fallback when Gemini is busy
    "sets": {"christmas": ["christmas", "xmas", "santa", "reindeer", "sleigh", "sled", "presents"],
             "space": ["space", "moon", "rocket", "alien", "planet", "astronaut", "spaceship"],
             "pirate": ["pirate", "ship", "treasure", "island", "parrot"],
             "bedroom": ["bedroom", "bed", "bedtime", "sleep", "toys", "teddy", "toy"],
             "livingroom": ["living room", "sofa", "couch", "tv", "lounge", "movie", "home", "house"],
             "snow": ["snow", "winter", "ice", "cold", "snowman"], "beach": ["beach", "sea", "sand", "ocean", "summer holiday"],
             "kitchen": ["kitchen", "inside", "indoor", "cooking", "baking"], "playground": ["playground", "swing", "slide", "seesaw", "school"],
             "underwater": ["underwater", "under the sea", "ocean floor", "fish", "mermaid", "coral"],
             "farm": ["farm", "barn", "cow", "pig", "tractor", "hay"],
             "camping": ["camping", "camp", "tent", "campfire", "forest", "woods"],
             "castle": ["castle", "princess", "prince", "king", "queen", "knight", "fairy tale", "fairytale"],
             "candy": ["candy", "candyland", "sweets", "lollipop", "sweet land"],
             "market": ["market", "fountain", "stall", "shopping", "village square"],
             "desert": ["desert", "cactus", "wild west", "cowboy"],
             "park": ["park", "pond", "garden", "grass", "picnic"], "street": ["street", "town", "road", "village"]},
    "gags": {"steal_treat": ["steal", "stole", "took", "treat", "eat", "snack", "food", "hungry", "cake", "donut", "pizza", "cupcake", "gingerbread",
                             "ice cream", "cookie", "apple", "watermelon", "strawberry"],
             "ball_bonk": ["ball", "kick", "football", "soccer", "bonk"], "balloon_float": ["balloon", "fly", "float", "pop"],
             "gift_surprise": ["gift", "present", "box", "surprise", "birthday"], "hide_seek": ["hide", "seek", "boo", "hiding"],
             "slip_peel": ["banana", "slip", "fall", "trip", "peel"],
             "sneeze": ["sneeze", "achoo", "atchoo", "sniff"], "dance_party": ["dance", "dancing", "disco", "party"],
             "bubbles": ["bubble", "bubbles"], "wake_up": ["sleep", "asleep", "wake", "snore", "nap"],
             "race": ["race", "racing", "running", "who is fastest", "finish line"]},
    "sky": {"sunset": ["sunset", "evening"], "morning": ["morning", "sunrise", "dawn"], "golden": ["golden", "afternoon"]},
    "season": {"autumn": ["autumn", "fall leaves", "halloween", "pumpkin"], "spring": ["spring", "blossom", "flowers"]},
}
WISH_SYSTEM = """You turn a parent's wish for a wordless kids' 3D cartoon short into choices from a fixed menu.
Use ONLY ids from the menu. Leave a key out when the wish says nothing about it. If the wish asks for something the
menu can't do, pick the closest thing that keeps its spirit and say so in "note".
Reply as JSON with any of these keys:
"gags": 1-5 gag ids in the order they should happen (put the one the wish is about first),
"cast": 1-2 character ids who must star, "avoid_cast": character ids to leave out,
"set": one place id, "props": {gag id: prop id}, "color": one colour (for the balloon/ball),
"sky": day|morning|golden|sunset, "season": summer|spring|autumn,
"looks": {character id: [accessory id or "none", "#RRGGBB"]},
"note": one short friendly sentence saying how the wish was used."""


def _menu():
    gags = "\n".join(f"- {k}: {g['story'].format(hero='HERO', friend='FRIEND', prop='a treat', color='coloured')} "
                     f"(props: {', '.join(g['props'])}; places: {', '.join(g['sets'])})" for k, g in GAGS.items())
    cast = "\n".join(f"- {k}: {v}" for k, v in CAST.items())
    return (f"GAGS:\n{gags}\nCHARACTERS:\n{cast}\nPLACES: {', '.join(ALL_SETS)}\nCOLOURS: {', '.join(COLORS)}\n"
            f"ACCESSORIES: {', '.join(ACCESSORIES)}")


def _wish_offline(text, base=None):
    low = " " + text.lower() + " "
    w = {}
    cast = [k for k in CAST if f" {k}" in low or NAMES[k].lower() in low]
    if cast:
        w["cast"] = cast[:2]
    if any(x in low for x in ("different character", "new character", "other character", "different friends")) and base:
        w["avoid_cast"] = [base.get("hero"), base.get("friend")]
    import re
    hit = lambda words: [m.start() for x in words for m in [re.search(r"\b" + re.escape(x) + r"s?\b", low)] if m]
    for key in ("sets", "sky", "season"):
        for opt, words in WORDS[key].items():
            if hit(words):
                w["set" if key == "sets" else key] = opt
                break
    gags = sorted((min(hit(words)), g) for g, words in WORDS["gags"].items() if hit(words))
    if gags:
        w["gags"] = [g for _, g in gags]  # in the order the person mentioned them
    acc = {"party_hat": ["party hat", "hat"], "bow": ["bow"], "cap": ["cap"], "flower": ["flower"],
           "bowtie": ["bow tie", "bowtie"], "crown": ["crown"]}
    found = [k for k, words in acc.items() if hit(words)]
    if found and cast:
        w["looks"] = {cast[0]: [found[-1], "#" + {"red": "FF4D6D", "blue": "4DA6FF", "yellow": "FFD23F", "green": "5CCB6B",
                                                   "purple": "B57BFF", "orange": "FF8A3D", "pink": "FF8FC8"}.get(
            next((c for c in COLORS if f" {c}" in low), "yellow"))]}
    props = {}
    for g in GAGS:
        for pr in GAGS[g]["props"]:
            if pr in low.replace(" ", "") or PROP_NAMES[pr] in low:
                props[g] = pr
    if props:
        w["props"] = props
    col = [c for c in COLORS if f" {c}" in low]
    if col:
        w["color"] = col[0]
    if any(x in low for x in ("different art", "new look", "different colour", "different color", "new colours")):
        w["restyle"] = True
    return w


def wish(text, base=None):
    """What the person asked for, as choices the 3D engine can make. Gemini reads it; keyword matching if busy."""
    if not text:
        return {}
    offline = _wish_offline(text, base)
    prompt = f"MENU\n{_menu()}\n\nWISH: {text}"
    if base:
        prompt += ("\n\nThis is a change request for an existing short: "
                   + describe(base) + f" Stars: {base.get('hero')} and {base.get('friend')}. Keep what the wish doesn't change.")
    try:
        w = llm.generate_json(WISH_SYSTEM, prompt, temperature=0.4)
        if not isinstance(w, dict):
            raise ValueError("not a dict")
    except Exception as e:  # noqa: BLE001
        print("  wish: keyword matching because", str(e)[:150])
        return offline
    # keep only valid menu choices
    out = {}
    if isinstance(w.get("gags"), list):
        out["gags"] = [g for g in w["gags"] if g in GAGS][:5]
    for k in ("cast", "avoid_cast"):
        if isinstance(w.get(k), list):
            out[k] = [c for c in w[k] if c in CAST][:2 if k == "cast" else 9]
    if w.get("set") in ALL_SETS:
        out["set"] = w["set"]
    if isinstance(w.get("props"), dict):
        out["props"] = {g: p for g, p in w["props"].items() if g in GAGS and p in GAGS[g]["props"]}
    if w.get("color") in COLORS:
        out["color"] = w["color"]
    if w.get("sky") in ("day", "morning", "golden", "sunset"):
        out["sky"] = w["sky"]
    if w.get("season") in ("summer", "spring", "autumn"):
        out["season"] = w["season"]
    if isinstance(w.get("looks"), dict):
        out["looks"] = {c: [v[0], v[1] if len(v) > 1 and str(v[1]).startswith("#") else "#FF4D6D"]
                        for c, v in w["looks"].items() if c in CAST and isinstance(v, list) and v
                        and (v[0] in ACCESSORIES or v[0] == "none")}
    if w.get("note"):
        out["note"] = str(w["note"])[:200]
    for k, v in offline.items():  # names/places the person typed always count
        if k in ("cast", "set") and k not in out:
            out[k] = v
    return {k: v for k, v in out.items() if v not in ([], {}, None, "")}


def plan(recent_specs=(), idea=None, rnd=None, min_s=20, max_s=60, slot=None, base=None, choose=None):
    """One short = 3-5 gags in a row with the same two friends (21-35 s, never under 20 or over 60):
    longer watch time, a recurring duo, and a fresh mix every day.
    idea = what the person typed (new short idea or "change this short" feedback); base = the short being changed."""
    rnd = rnd or random.Random()
    recent = [s for s in recent_specs if isinstance(s, dict)]
    w = wish(idea, base) if idea else {}
    choose = choose or {}  # picked in the app: these always win over the typed idea
    if [c for c in choose.get("cast") or [] if c in CAST]:
        w["cast"] = [c for c in choose["cast"] if c in CAST][:2]
    if choose.get("set") in ALL_SETS:
        w["set"] = choose["set"]
    if [g for g in choose.get("gags") or [] if g in GAGS]:
        w["gags"] = [g for g in choose["gags"] if g in GAGS][:5]
        if w.get("set") and not all(w["set"] in GAGS[g]["sets"] for g in w["gags"]):
            w["gags"] = [g for g in w["gags"] if w["set"] in GAGS[g]["sets"]] or w["gags"]
            if not all(w["set"] in GAGS[g]["sets"] for g in w["gags"]):
                w.pop("set")  # the chosen story can't happen there -> keep the story, pick a fitting place
    lo, hi = max(3, int(-(-min_s // SEG_SECONDS))), min(len(GAGS), int(max_s // SEG_SECONDS))
    n = rnd.choice([k for k in (3, 4, 4, 5) if lo <= k <= hi] or [lo])
    recent_gags = [g.get("gag") for g in list(_segments(recent))[:6]]
    order = [g for g in GAGS if g not in recent_gags] + [g for g in GAGS if g in recent_gags]
    rnd.shuffle(order)
    order.sort(key=lambda g: g in recent_gags)  # fresh gags first
    wanted = list(w.get("gags") or [])
    if base and not wanted and not w.get("restyle"):  # a change request keeps the same funny moments
        wanted = [s["gag"] for s in (base.get("segments") or [base])]
    place = w.get("set")
    if not place and not wanted and not base:  # pick the place first, so every place gets its turn
        import datetime
        sets = [x for x in ALL_SETS if x != "christmas" or datetime.date.today().month in (11, 12, 1)]  # Christmas in season
        used = [s.get("set") for s in recent[:len(sets) * 2]]
        least = min(used.count(x) for x in sets)
        place = rnd.choice([x for x in sets if used.count(x) == least and x not in used[:3]] or sets)
        w = dict(w, set=place)
    if place:  # only gags that can happen there
        order = [g for g in order if place in GAGS[g]["sets"]]
        wanted = [g for g in wanted if place in GAGS[g]["sets"]]
        n = min(n, len(order))
    if wanted:
        n = max(min(len(wanted), hi), lo) if len(wanted) >= lo else n
        order = wanted + [g for g in order if g not in wanted]
    elif slot is not None:  # shorts planned at the same moment still get different lead gags
        lead = list(GAGS)[slot % len(GAGS)]
        order = [lead] + [g for g in order if g != lead]
    gags = order[:n]
    if not wanted:
        rest = gags[1:]
        rnd.shuffle(rest)
        gags = [gags[0]] + rest
    pairs = {(s.get("hero"), s.get("friend")) for s in recent[:6]}
    avoid = set(w.get("avoid_cast") or [])
    cast = [c for c in CAST if c not in avoid] or list(CAST)
    want_cast = [c for c in (w.get("cast") or []) if c in cast]
    if not want_cast and base and not avoid:
        want_cast = [base.get("hero"), base.get("friend")]
    duos = [(x, y) for i, x in enumerate(cast) for y in cast[i + 1:]]
    if len(want_cast) >= 2:
        a, b = want_cast[:2]
    elif want_cast:
        a = want_cast[0]
        b = rnd.choice([c for c in cast if c != a])
    elif slot is not None:  # a stride that never shares a factor with the number of duos -> all duos get a turn
        stride = next(k for k in (7, 11, 13, 17, 19, 23) if math.gcd(k, len(duos)) == 1)
        a, b = duos[(slot * stride) % len(duos)]
        if rnd.random() < 0.5:
            a, b = b, a
    else:
        for _ in range(20):
            a, b = rnd.sample(cast, 2)
            if (a, b) not in pairs and (b, a) not in pairs:
                break
    # one home set for the whole short when the gags allow it
    common = [x for x in ALL_SETS if all(x in GAGS[g]["sets"] for g in gags)]
    recent_sets = [s.get("set") for s in recent[:3]]
    fresh = [x for x in common if x not in recent_sets] or common
    if w.get("set") in common:
        home = w["set"]
    elif base and base.get("set") in common and not w.get("restyle"):
        home = base["set"]
    elif slot is not None and fresh:
        home = fresh[(slot * 5) % len(fresh)]
    else:
        home = rnd.choice(fresh) if fresh else None
    props = w.get("props") or {}
    segs = []
    for k, gag in enumerate(gags):
        g = GAGS[gag]
        hero, friend = (a, b) if k % 2 == 0 else (b, a)  # the two friends take turns being the hero
        st = home or rnd.choice(g["sets"])
        segs.append({"gag": gag, "set": st, "hero": hero, "friend": friend,
                     "prop": props.get(gag) or rnd.choice(g["props"]),
                     "color": w.get("color") or rnd.choice(COLORS), "table_color": rnd.choice(TABLE_COLORS),
                     "seed": rnd.randint(1, 10 ** 6)})
    # colours of the day: sky/time of day, season and palette of the set, plus a little outfit for each friend
    theme = {"sky": w.get("sky") or rnd.choice(["day", "day", "morning", "golden", "sunset"]),
             "season": w.get("season") or rnd.choice(["summer", "summer", "spring", "autumn"]),
             "pal": rnd.randint(1, 10 ** 6)}
    looks = {}
    for c in (a, b):
        if c in (w.get("looks") or {}):
            if w["looks"][c][0] != "none":
                looks[c] = w["looks"][c]
        elif rnd.random() < 0.75:
            k = rnd.choice(ACCESSORIES)
            if k == "cap" and c in ("bubu", "mimi", "gogo", "tobi"):  # ears/eyes on top: a cap would hide them
                k = "bow"
            looks[c] = [k, rnd.choice(ACC_COLORS)]
    spec = {"hero": a, "friend": b, "set": segs[0]["set"], "gag": segs[0]["gag"], "segments": segs,
            "theme": theme, "looks": looks, "seed": rnd.randint(1, 10 ** 6)}
    if idea:
        spec["wish"] = {"text": idea[:300], "note": w.get("note") or ""}
    return spec


def describe_one(seg):
    g = GAGS[seg["gag"]]
    return g["story"].format(hero=NAMES[seg["hero"]], friend=NAMES[seg["friend"]], prop=PROP_NAMES[seg["prop"]],
                             color=seg.get("color", "red"))


def describe(spec):
    s = " Then: ".join(describe_one(s) for s in (spec.get("segments") or [spec]))
    place = {"snow": "in the snow", "playground": "at the playground", "kitchen": "in the kitchen",
             "beach": "at the beach", "park": "in the park", "street": "on their street", "bedroom": "in the bedroom",
             "livingroom": "in the living room", "space": "on the moon", "pirate": "on pirate island",
             "christmas": "on a snowy Christmas day", "farm": "on the farm", "camping": "at the campsite",
             "castle": "at the fairy-tale castle", "underwater": "under the sea", "candy": "in Candy Land",
             "market": "at the village market", "desert": "in the sunny desert"}.get(spec.get("set"))
    wear = [f"{NAMES[c]} wears {ACC_WORDS[k]}" for c, (k, _) in (spec.get("looks") or {}).items() if k in ACC_WORDS]
    return s + (f" (It all happens {place}.)" if place else "") + (" " + ", ".join(wear) + "." if wear else "")


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
    wish_line = f"The parent asked for: {spec['wish']['text']}\n" if spec.get("wish") else ""
    prompt = (f"{wish_line}What happens: {describe(spec)}\nCharacters:\n{cast}\n"
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
