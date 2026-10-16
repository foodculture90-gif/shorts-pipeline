"""Defaults for the free pipeline. Channel-specific settings live in the database (panel → Channels)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
MUSIC_DIR = ROOT / "music"          # drop royalty-free .mp3 files here (in the GitHub repo)
MODELS_DIR = ROOT / ".models"       # depth model is downloaded here once (cached by GitHub)

# --- Writer: Google Gemini (free tier) -----------------------------------------------
GEMINI_MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest"]  # fallbacks; real list is fetched from Google

# --- Pictures: Cloudflare Workers AI (free 10,000 "neurons" per day) -------------------
IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell"
IMAGE_STEPS = 4
NEURONS_PER_IMAGE = 58          # 1024x1024 at 4 steps ≈ 4×4.8 + 4×9.6
DAILY_NEURONS = 9_800           # keep a little under the free 10,000
SHOTS_PER_SCENE = 2
SCENES = 4                      # → 8 pictures per short → ~20 shorts per day free

# --- Voice: free Microsoft Edge neural voices -------------------------------------------
DEFAULT_VOICE = "en-US-AnaNeural"
VOICE_RATE = "-5%"

# --- Video -------------------------------------------------------------------------------
FINAL_SIZE = (1080, 1920)
PREVIEW_SIZE = (540, 960)       # what you watch in the app (small = stays inside free storage)
FPS = 30

# --- Variety: every short gets a random format, art style and spark ----------------------
# All styles share one look: a bright 3D CGI preschool TV cartoon. The lighting and palette
# change per short, and the characters are always new.
_TV = ("3D CGI preschool TV cartoon, smooth clean shading, big expressive eyes, rounded chunky shapes, "
       "simple clean environments, saturated primary colours, crisp render, kid-friendly, high quality animation still")
STYLES = [
    f"{_TV}, sunny daytime, bright blue sky, cheerful",
    f"{_TV}, golden late-afternoon light, warm orange tones",
    f"{_TV}, soft night-time lighting, glowing lamps, cosy blues and purples",
    f"{_TV}, rainy day, shiny puddles, colourful raincoats and umbrellas",
    f"{_TV}, snowy winter, soft white snow, warm cheerful lights",
    f"{_TV}, underwater world, sparkling light rays, bright corals",
    f"{_TV}, outer space, glowing planets and stars, shiny spaceship",
    f"{_TV}, lush green park and town, tidy streets, fluffy clouds",
    f"{_TV}, jungle with big leaves, dappled sunlight, vivid greens",
    f"{_TV}, seaside harbour town, bright boats, sparkling water",
]
FORMATS = [
    "funny fable with a gentle lesson", "bedtime story", "animal adventure", "space adventure",
    "underwater adventure", "silly mystery with a happy reveal", "fairy-tale with a twist",
    "story about a brave little vehicle or robot", "nature story explaining a real fact",
    "friendship story", "story about trying something new", "seasonal/holiday story",
]
SPARKS = [
    "a lost balloon", "a sleepy volcano", "a hiccuping dragon", "a library at night", "a snail race",
    "a moon made of cheese rumours", "a shy lighthouse", "a rainbow that lost a colour", "a penguin who hates cold",
    "a kite with a mind of its own", "a garden of singing flowers", "a tiny robot's first day", "a whale who sings off-key",
    "a bakery for animals", "a sock that ran away", "a cloud who wanted to be a sheep", "the noisiest owl",
    "a bus that drives to the stars", "a treasure map made by a squirrel", "a firefly who's afraid of the dark",
    "a ladybug counting spots", "a snowman in summer", "a turtle in a hurry", "the last cookie", "a bear who can't whistle",
]
