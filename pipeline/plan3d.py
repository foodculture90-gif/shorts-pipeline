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
    "bolt": "Bolt, a friendly little teal robot with a blinking antenna and a screen face",
    "rexy": "Rexy, a green baby T-rex dinosaur with orange back spikes",
    "trixie": "Trixie, a pink baby triceratops with a purple frill and three little horns",
    "drako": "Drako, a purple baby dragon with tiny blue wings",
    "momo": "Momo, a shaggy blue fluffy monster with orange horns and two little teeth",
    "ocki": "Ocki, a cheerful orange octopus with wiggly legs",
    "ellie": "Ellie, a little blue-grey elephant with big floppy ears and a curly trunk",
    "pinky": "Pinky, a pink piglet with a round snout and a curly tail",
    "hoot": "Hoot, a little brown owl with big amber eyes and ear tufts",
    "buzzy": "Buzzy, a round yellow bumblebee with black stripes and see-through wings",
    "kiki": "Kiki, a little girl with brown pigtails and a pink t-shirt",
    "nino": "Nino, a little boy with curly black hair and a yellow t-shirt",
}
ALL_SETS = ["street", "park", "beach", "kitchen", "playground", "snow", "bedroom", "livingroom", "space", "pirate",
            "christmas", "farm", "camping", "castle", "underwater", "candy", "market", "desert", "jungle"]
OUTDOOR = ["street", "park", "beach", "playground", "snow", "pirate", "christmas", "farm", "camping", "castle", "candy",
           "market", "desert", "jungle"]
INDOOR = ["kitchen", "bedroom", "livingroom"]
GREEN = ["park", "street", "beach", "playground", "snow", "pirate", "christmas", "farm", "camping", "castle", "market",
         "jungle"]
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
    "magic_trick": dict(props=["hat"], sets=ALL_SETS,
                        story="{hero} taps a magic hat with a wand - POOF! - out pop flowers! {friend} borrows the wand, "
                              "taps... POOF! {hero} turns teeny tiny and squeaks! One more POOF and {hero} is back, giggling."),
    "seesaw": dict(props=["seesaw"], sets=OUTDOOR + ["space"],
                   story="{hero} sits on a {color} seesaw. {friend} jumps on the other end - BOING! - {hero} flies sky high "
                         "with a flip, lands with a bump and launches {friend} up instead! Dizzy stars and big laughs."),
    "paint_splat": dict(props=["paint"], sets=ALL_SETS,
                        story="{hero} paints a little picture, dab by dab. {friend} leans in very close to look... and "
                              "SPLAT! a big paint stroke lands on their face! {friend} grabs a brush and paints {hero} back."),
}
# moral stories: one longer story (~22-26 s) with a gentle lesson, used as the whole short
GARDEN = ["park", "street", "playground", "farm", "camping", "castle", "market", "jungle"]
MORALS = {
    "patience": dict(lesson="Good things take time", props=["seed"], sets=GARDEN,
                     story="{hero} plants a little seed and waters it, then waits... and waits. Nothing! {hero} even tries "
                           "to pull the tiny sprout up to make it grow faster, but {friend} says 'wait' and they sit "
                           "together. Day and night pass, they water it again... and it blooms into a giant flower!"),
    "sharing": dict(lesson="Sharing makes everyone happy", props=["cookie", "donut", "cupcake"], sets=ALL_SETS,
                    story="{hero} has a plate of yummy {prop}s. {friend} arrives hungry and sad. {hero} hugs the plate... "
                          "then has an idea and gives {friend} one! The last one they split in half, and they hug."),
    "helping": dict(lesson="Always help a friend in need", props=["boxes"], sets=ALL_SETS,
                    story="{friend} carries a wobbly stack of boxes, trips and everything falls - {friend} cries. {hero} "
                          "comes to help, picks up every box, gives a hand up and a hug, and they carry the boxes together."),
    "sorry": dict(lesson="Say sorry and make it right", props=["blocks"], sets=ALL_SETS,
                  story="{friend} builds a tall block tower. {hero} kicks a ball and - CRASH - knocks it down. {friend} is "
                        "sad. {hero} says sorry with a little bow and a flower, and they build an even taller tower together."),
    "teamwork": dict(lesson="Together we can do it", props=["rock"], sets=OUTDOOR + ["space"],
                     story="A big rock blocks the way to a yummy cake. {hero} pushes and pushes, but it won't move. "
                           "{friend} comes to help: 1, 2, 3, PUSH! Together they roll it away and share the cake."),
    "try_again": dict(lesson="Never give up - try again", props=["star"], sets=ALL_SETS,
                      story="{hero} wants the shiny star on top of a high ledge. Jump - bonk! Jump - slide down! {hero} "
                            "almost gives up, but {friend} cheers 'you can do it!' - and a super jump gets the star!"),
}
ALLG = {**GAGS, **MORALS}
PROP_NAMES = {"seed": "seed", "boxes": "boxes", "blocks": "block tower", "rock": "big rock", "star": "star",
              "hat": "magic hat", "seesaw": "seesaw", "paint": "paint brush", "flower": "big flower", "confetti": "confetti", "bubbles": "bubbles", "horn": "party horn",
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
             "jungle": ["jungle", "rainforest", "dinosaur land", "dino land", "palm", "monkey", "safari"],
             "park": ["park", "pond", "garden", "grass", "picnic"], "street": ["street", "town", "road", "village"]},
    "gags": {"steal_treat": ["steal", "stole", "took", "treat", "eat", "snack", "food", "hungry", "cake", "donut", "pizza", "cupcake", "gingerbread",
                             "ice cream", "cookie", "apple", "watermelon", "strawberry"],
             "ball_bonk": ["ball", "kick", "football", "soccer", "bonk"], "balloon_float": ["balloon", "fly", "float", "pop"],
             "gift_surprise": ["gift", "present", "box", "surprise", "birthday"], "hide_seek": ["hide", "seek", "boo", "hiding"],
             "slip_peel": ["banana", "slip", "fall", "trip", "peel"],
             "sneeze": ["sneeze", "achoo", "atchoo", "sniff"], "dance_party": ["dance", "dancing", "disco", "party"],
             "bubbles": ["bubble", "bubbles"], "wake_up": ["sleep", "asleep", "wake", "snore", "nap"],
             "race": ["race", "racing", "running", "who is fastest", "finish line"],
             "magic_trick": ["magic", "magician", "wand", "trick", "tiny", "shrink", "poof"],
             "seesaw": ["seesaw", "see-saw", "see saw", "launch", "fly high", "catapult"],
             "paint_splat": ["paint", "painting", "art", "brush", "splat", "messy", "colours", "colors"],
             "patience": ["patience", "patient", "take time", "takes time", "plant", "seed", "grow"],
             "sharing": ["sharing", "share", "kind", "kindness", "generous"],
             "helping": ["helping", "help a friend", "help", "fell down", "kind friend"],
             "sorry": ["sorry", "apologise", "apologize", "mistake", "make it right"],
             "teamwork": ["teamwork", "team", "together", "work together"],
             "try_again": ["never give up", "give up", "try again", "keep trying", "practice"]},
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
    gags += "\n" + "\n".join(f"- {k} (a whole moral story - lesson: {m['lesson']}): "
                              f"{m['story'].format(hero='HERO', friend='FRIEND', prop='treat')}" for k, m in MORALS.items())
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
        out["gags"] = [g for g in w["gags"] if g in ALLG][:5]
    for k in ("cast", "avoid_cast"):
        if isinstance(w.get(k), list):
            out[k] = [c for c in w[k] if c in CAST][:2 if k == "cast" else 9]
    if w.get("set") in ALL_SETS:
        out["set"] = w["set"]
    if isinstance(w.get("props"), dict):
        out["props"] = {g: p for g, p in w["props"].items() if g in ALLG and p in ALLG[g]["props"]}
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
    if [g for g in choose.get("gags") or [] if g in ALLG]:
        w["gags"] = [g for g in choose["gags"] if g in ALLG][:5]
        if w.get("set") and not all(w["set"] in ALLG[g]["sets"] for g in w["gags"]):
            w["gags"] = [g for g in w["gags"] if w["set"] in ALLG[g]["sets"]] or w["gags"]
            if not all(w["set"] in ALLG[g]["sets"] for g in w["gags"]):
                w.pop("set")  # the chosen story can't happen there -> keep the story, pick a fitting place
    # a moral story (one longer story with a lesson) - asked for, or half of the daily shorts
    moral = next((g for g in (w.get("gags") or []) if g in MORALS), None)
    if not moral and base and base.get("moral") in MORALS and not w.get("gags"):
        moral = base["moral"]
    if not moral and choose.get("moral"):
        used = [s.get("moral") for s in recent[:len(MORALS) * 3]]
        least = min(used.count(m) for m in MORALS)
        opts = [m for m in MORALS if used.count(m) == least and m not in used[:2]] or list(MORALS)
        if w.get("set"):
            opts = [m for m in opts if w["set"] in MORALS[m]["sets"]] or opts
        moral = opts[slot % len(opts)] if slot is not None else rnd.choice(opts)
    if moral and w.get("set") and w["set"] not in MORALS[moral]["sets"]:
        w.pop("set")
    if moral:
        gags = [moral]
    else:
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
    common = [x for x in ALL_SETS if all(x in ALLG[g]["sets"] for g in gags)]
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
        g = ALLG[gag]
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
            if k == "cap" and c in ("bubu", "mimi", "gogo", "tobi", "bolt", "trixie", "drako", "momo", "hoot", "buzzy"):
                k = "bow"
            looks[c] = [k, rnd.choice(ACC_COLORS)]
    spec = {"hero": a, "friend": b, "set": segs[0]["set"], "gag": segs[0]["gag"], "segments": segs,
            "theme": theme, "looks": looks, "seed": rnd.randint(1, 10 ** 6)}
    if moral:
        spec["moral"], spec["lesson"] = moral, MORALS[moral]["lesson"]
    if idea:
        spec["wish"] = {"text": idea[:300], "note": w.get("note") or ""}
    return spec


def describe_one(seg):
    g = ALLG[seg["gag"]]
    return g["story"].format(hero=NAMES[seg["hero"]], friend=NAMES[seg["friend"]], prop=PROP_NAMES[seg["prop"]],
                             color=seg.get("color", "red"))


def describe(spec):
    s = " Then: ".join(describe_one(s) for s in (spec.get("segments") or [spec]))
    place = {"snow": "in the snow", "playground": "at the playground", "kitchen": "in the kitchen",
             "beach": "at the beach", "park": "in the park", "street": "on their street", "bedroom": "in the bedroom",
             "livingroom": "in the living room", "space": "on the moon", "pirate": "on pirate island",
             "christmas": "on a snowy Christmas day", "farm": "on the farm", "camping": "at the campsite",
             "castle": "at the fairy-tale castle", "underwater": "under the sea", "candy": "in Candy Land",
             "market": "at the village market", "desert": "in the sunny desert", "jungle": "in the jungle"}.get(spec.get("set"))
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
    "sneeze": ["The Biggest Sneeze Ever... ACHOO! 🤧", "Don't Sneeze, {H}! 🤧", "{H}'s Silly Sneeze! 😂"],
    "dance_party": ["{H}'s Silly Dance Party! 🎉", "Try Not To Dance! 🕺", "The Wiggliest Dance Ever! 🎉"],
    "bubbles": ["Pop All The Bubbles! 🫧", "{H} And The Giant Bubble! 🫧", "Don't Pop The Big Bubble! 🫧"],
    "wake_up": ["Wake Up, {H}! ⏰", "Shh... Don't Wake {H}! 😴", "The Silliest Wake Up Ever! 😴"],
    "race": ["Who Will Win The Race?! 🏁", "The Silliest Race Ever! 🏁", "{H}'s Big Race! 🏁"],
    "magic_trick": ["The Magic Hat Went POOF! 🎩", "{H} Turned Teeny Tiny! 🪄", "Don't Touch The Magic Wand! 🪄"],
    "seesaw": ["The Highest Seesaw Jump Ever! 🚀", "{H} Flew Sky High! 🚀", "Don't Jump On The Seesaw! 😂"],
    "paint_splat": ["SPLAT! Paint On Your Face! 🎨", "{H}'s Messy Painting! 🎨", "Don't Look Too Close! 🎨"],
}
OFFLINE_TITLES.update({
    "patience": ["Good Things Take Time! 🌱", "{H}'s Magic Seed 🌱", "Wait For It... 🌻"],
    "sharing": ["Sharing Is Caring! 🍪", "{H} Shares The Last {P}! 💛", "One For You, One For Me! 🍪"],
    "helping": ["Always Help A Friend! 🤝", "{H} To The Rescue! 💛", "Oops! Who Will Help? 📦"],
    "sorry": ["Saying Sorry Makes It Better 💛", "Oops! The Tower Fell! 🧱", "{H} Says Sorry 🌸"],
    "teamwork": ["Together We Can Do It! 💪", "The Rock Won't Move! 🪨", "Teamwork Makes It Work! 🎂"],
    "try_again": ["Never Give Up! ⭐", "{H} Tries Again! ⭐", "You Can Do It, {H}! ⭐"],
})
_ANY_TITLES = ["{H}'s Silliest Day Ever! 😂", "Watch What {H} Does! 😂", "Oops, {H}! 😂"]


def _offline(spec, rnd):
    first = (spec.get("segments") or [spec])[0]
    prop = PROP_NAMES.get(first.get("prop"), str(first.get("prop") or "surprise")).title()
    t = rnd.choice(OFFLINE_TITLES.get(first.get("gag"), _ANY_TITLES)).format(P=prop, H=NAMES.get(first.get("hero"), "Pip"))
    desc = (f"{NAMES[spec['hero']]} and {NAMES[spec['friend']]} have the silliest day! 😂\n"
            "Watch till the end - then watch it again! 🔁")
    if spec.get("lesson"):
        desc = (f"A sweet little story with {NAMES[spec['hero']]} and {NAMES[spec['friend']]} 💛\n"
                "Watch till the end for the happy surprise! 🌟")
    return {"title": t, "description": desc,
            "hashtags": ["kidscartoon", "funnycartoon", "cartoonforkids", str(first.get("prop") or "cartoon")],
            "tags": ["kids cartoon", "funny cartoon", "3d animation for kids", "cartoon for toddlers",
                     prop.lower(), "funny kids video", "preschool cartoon", "cute cartoon",
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
    if spec.get("lesson"):
        wish_line += (f"This is a MORAL STORY. The lesson: \"{spec['lesson']}\". The title should make kids curious about "
                      f"the story or name the lesson (e.g. \"{spec['lesson']}! \u2728\"). The takeaway is exactly the lesson.\n")
    prompt = (f"{wish_line}What happens: {describe(spec)}\nCharacters:\n{cast}\n"
              f"Recent titles on this channel (don't repeat them):\n{recent}")
    try:
        m = llm.generate_json(SYSTEM.replace("FORMAT", fmt), prompt, temperature=1.0)
        if not (isinstance(m, dict) and m.get("title")):
            raise ValueError("no title")
        out = _offline(spec, rnd)
        out.update({k: v for k, v in m.items() if k in out and v})
        return _lesson(spec, out)
    except Exception as e:  # noqa: BLE001  (Gemini busy/down -> still make the short)
        print("  meta: offline titles because", str(e)[:200])
        return _lesson(spec, _offline(spec, rnd))


def _lesson(spec, out):
    """Moral stories: the lesson goes in the takeaway, the description and the hashtags."""
    if spec.get("lesson"):
        out["takeaway"] = spec["lesson"] + "."
        if spec["lesson"].lower() not in str(out.get("description", "")).lower():
            out["description"] = f"{out.get('description', '').rstrip()}\n💛 Lesson: {spec['lesson']}."
        tags = [t for t in out.get("hashtags") or [] if t not in ("moralstory", "kidslessons")]
        out["hashtags"] = ["moralstory", "kidslessons"] + tags[:3]
        out["tags"] = list(dict.fromkeys(["moral story for kids", "kids lesson", spec["lesson"].lower()] + list(out.get("tags") or [])))[:15]
    return out
