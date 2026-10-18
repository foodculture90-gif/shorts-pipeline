"""Sound for the 3D shorts: cartoon sound effects synced to the animation + cheerful kids' music.
No voices. Everything is made here, so it's free and safe to use commercially.

  python3 blender/audio.py events.json out.wav [seconds] [seed]

events.json: {"fps": 24, "frames": 144, "events": [[frame, "kind"], ...]}
Kinds: boing, land, pop, whoosh, chomp, sparkle, slide_up, slide_down, doink, zip, thud, tick, ding, swish
Music: written as MIDI here and played with a General MIDI soundfont by fluidsynth (if installed).
"""
import json, math, os, random, shutil, struct, subprocess, sys, tempfile, wave

import numpy as np

SR = 44100
rng = np.random.default_rng(1)


# ------------------------------------------------------------------ helpers
def t(sec):
    return np.arange(int(SR * sec)) / SR


def env(n, a=0.005, d=None, curve=4.0):
    """Attack then exponential decay over n samples."""
    x = np.arange(n) / SR
    att = np.clip(x / max(a, 1e-4), 0, 1)
    dur = n / SR
    dec = np.exp(-curve * x / (d or dur))
    return att * dec


def fade(sig, a=0.003, r=0.02):
    n = len(sig)
    na, nr = int(SR * a), int(SR * r)
    if na:
        sig[:na] *= np.linspace(0, 1, na)
    if nr:
        sig[-nr:] *= np.linspace(1, 0, nr)
    return sig


def osc(freq, kind="sine"):
    """freq: array of instantaneous Hz."""
    ph = 2 * np.pi * np.cumsum(freq) / SR
    if kind == "sine":
        return np.sin(ph)
    if kind == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if kind == "soft_square":
        return np.tanh(3 * np.sin(ph))
    return np.sin(ph)


def noise(n):
    return rng.standard_normal(n)


def bandpass(x, lo, hi):
    """FFT band-pass (static)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.clip((f - lo * 0.7) / (lo * 0.3 + 1e-9), 0, 1) * np.clip((hi * 1.3 - f) / (hi * 0.3 + 1e-9), 0, 1)
    return np.fft.irfft(X * m, len(x))


def sweep_filter(x, f0, f1, q=4.0):
    """Time-varying band-pass (state-variable filter) sweeping f0 -> f1."""
    n = len(x)
    fc = np.geomspace(f0, f1, n)
    y = np.zeros(n)
    low = band = 0.0
    damp = 1.0 / q
    for i in range(n):
        f = 2 * math.sin(math.pi * min(fc[i], SR / 6) / SR)
        high = x[i] - low - damp * band
        band += f * high
        low += f * band
        y[i] = band
    return y


def lowpass(x, fc):
    a = math.exp(-2 * math.pi * fc / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def bell(freq, dur=0.6, bright=1.0):
    """Glockenspiel-ish bell: inharmonic partials with fast-decaying highs."""
    tt = t(dur)
    out = np.zeros_like(tt)
    for ratio, amp, dec in ((1, 1, 3), (2.76, 0.45 * bright, 6), (5.4, 0.25 * bright, 10), (8.93, 0.12 * bright, 16)):
        out += amp * np.sin(2 * np.pi * freq * ratio * tt) * np.exp(-dec * tt / dur * 2)
    return fade(out * np.clip(tt / 0.002, 0, 1))


# ------------------------------------------------------------------ cartoon sound effects
def sfx_boing(pitch=1.0):
    """Spring 'boing': a wobbling tone that rises then sags, with a twangy overtone."""
    d = 0.55
    tt = t(d)
    base = 170 * pitch * (1 + 0.9 * (1 - np.exp(-tt * 30)) - 0.35 * tt / d)
    wob = 1 + 0.22 * np.sin(2 * np.pi * 22 * tt) * np.exp(-tt * 5)
    f = base * wob
    s = osc(f, "tri") * 0.8 + 0.25 * osc(f * 2.01) + 0.08 * osc(f * 3.02)
    return fade(s * env(len(tt), 0.004, d, 3.5))


def sfx_land(pitch=1.0):
    """Soft cartoon landing: low thump + tiny squish."""
    d = 0.22
    tt = t(d)
    f = 120 * pitch * np.exp(-tt * 14) + 45
    thump = osc(f) * env(len(tt), 0.002, d, 6)
    squish = bandpass(noise(len(tt)), 300, 1400) * env(len(tt), 0.002, 0.08, 6) * 0.25
    return fade(thump + squish)


def sfx_pop(pitch=1.0):
    d = 0.12
    tt = t(d)
    f = 900 * pitch * np.exp(-tt * 28) + 250 * pitch
    s = osc(f) * env(len(tt), 0.001, d, 5)
    click = bandpass(noise(len(tt)), 2000, 7000) * env(len(tt), 0.0005, 0.01, 8) * 0.4
    return fade(s + click, 0.0005, 0.01)


def sfx_whoosh(dur=0.45, up=True):
    n = int(SR * dur)
    x = noise(n)
    y = sweep_filter(x, 350 if up else 2600, 2600 if up else 350, q=2.5)
    e = np.sin(np.linspace(0, np.pi, n)) ** 1.6
    return fade(norm(y) * e * 0.8)


def sfx_swish():
    return sfx_whoosh(0.22, True) * 0.8


def sfx_chomp():
    out = np.zeros(int(SR * 0.32))
    for k, st in enumerate((0.0, 0.14)):
        n = int(SR * 0.09)
        crunch = bandpass(noise(n), 900, 5000) * env(n, 0.001, 0.07, 5)
        clack = osc(np.full(n, 520 - 80 * k)) * env(n, 0.0005, 0.03, 8) * 0.6
        i = int(SR * st)
        out[i:i + n] += crunch + clack
    return fade(norm(out, 0.8))


def sfx_sparkle(root=1046.5):
    """Magic 'ting-a-ling': fast rising bell arpeggio."""
    notes = [1, 1.26, 1.5, 2, 2.52, 3]
    out = np.zeros(int(SR * 0.9))
    for k, r in enumerate(notes):
        b = bell(root * r, 0.5, 0.8) * (0.9 - k * 0.08)
        i = int(SR * 0.045 * k)
        out[i:i + len(b)] += b
    return fade(norm(out, 0.6))


def sfx_slide(up=True, dur=0.5):
    """Slide whistle."""
    tt = t(dur)
    a, b = (500, 1500) if up else (1500, 450)
    f = a * (b / a) ** (tt / dur) * (1 + 0.012 * np.sin(2 * np.pi * 6 * tt))
    s = osc(f) + 0.06 * osc(f * 2)
    breath = bandpass(noise(len(tt)), 1500, 6000) * 0.04
    e = np.clip(tt / 0.03, 0, 1) * np.clip((dur - tt) / 0.06, 0, 1)
    return fade((s + breath) * e * 0.7)


def sfx_doink():
    """Bonk/'doink' for a surprise or a bump."""
    d = 0.35
    tt = t(d)
    f = 700 * np.exp(-tt * 9) + 180
    s = osc(f) + 0.3 * osc(f * 2.4)
    knock = bandpass(noise(len(tt)), 1500, 4000) * env(len(tt), 0.0005, 0.02, 8) * 0.5
    return fade(norm(s * env(len(tt), 0.002, d, 4) + knock, 0.8))


def sfx_zip():
    """Zoom away: quick rising whistle + whoosh."""
    a = sfx_slide(True, 0.25) * 0.7
    b = sfx_whoosh(0.3, True)
    out = np.zeros(max(len(a), len(b)))
    out[:len(a)] += a
    out[:len(b)] += b
    return fade(norm(out, 0.8))


def sfx_thud():
    return sfx_land(0.7) * 1.2


def sfx_tick():
    n = int(SR * 0.05)
    return fade(bandpass(noise(n), 2500, 6000) * env(n, 0.0005, 0.02, 6) * 0.5 + osc(np.full(n, 1800)) * env(n, 0.0005, 0.015, 8) * 0.3)


def sfx_ding():
    return norm(bell(1568, 1.0, 0.6) + 0.6 * bell(2093, 1.0, 0.4), 0.6)


SFX = dict(boing=sfx_boing, land=sfx_land, pop=sfx_pop, whoosh=sfx_whoosh, swish=sfx_swish, chomp=sfx_chomp,
           sparkle=sfx_sparkle, slide_up=lambda: sfx_slide(True), slide_down=lambda: sfx_slide(False),
           doink=sfx_doink, zip=sfx_zip, thud=sfx_thud, tick=sfx_tick, ding=sfx_ding)
GAIN = dict(boing=0.55, land=0.6, pop=0.55, whoosh=0.45, swish=0.4, chomp=0.65, sparkle=0.4, slide_up=0.45,
            slide_down=0.45, doink=0.55, zip=0.5, thud=0.7, tick=0.35, ding=0.4)


def reverb(x, wet=0.12, length=0.9):
    """Small bright room: convolve with a decaying-noise impulse response."""
    n = int(SR * length)
    ir = noise(n) * np.exp(-np.arange(n) / SR * 7)
    ir = lowpass(ir, 6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
    return x + wet * y


# ------------------------------------------------------------------ music (MIDI -> fluidsynth)
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11]}
PROGS = [[0, 4, 5, 3], [0, 5, 3, 4], [0, 3, 4, 0], [0, 3, 0, 4], [5, 3, 0, 4]]  # scale degrees (I V vi IV ...)
# GM programs that sound like kids' TV: (melody, chords/accomp, bass)
BANDS = [
    dict(melody=9, accomp=45, bass=32, name="glock+pizz"),  # glockenspiel, pizzicato strings, acoustic bass
    dict(melody=12, accomp=24, bass=58, name="marimba+uke-ish"),  # marimba, nylon guitar, tuba
    dict(melody=73, accomp=45, bass=70, name="flute+pizz"),  # flute, pizzicato, bassoon
    dict(melody=11, accomp=0, bass=32, name="vibes+piano"),  # vibraphone, piano, bass
    dict(melody=8, accomp=12, bass=58, name="celesta+marimba"),
]


def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def write_midi(path, tracks, tpq=480, bpm=120):
    """tracks: list of (channel, program, [(start_beats, dur_beats, note, vel), ...])"""
    chunks = []
    tempo = int(60_000_000 / bpm)
    meta = b"\x00\xFF\x51\x03" + tempo.to_bytes(3, "big") + b"\x00\xFF\x2F\x00"
    chunks.append(b"MTrk" + struct.pack(">I", len(meta)) + meta)
    for ch, prog, notes in tracks:
        ev = []
        for st, du, nt, vel in notes:
            ev.append((int(st * tpq), 1, nt, vel))
            ev.append((int((st + du) * tpq), 0, nt, 0))
        ev.sort(key=lambda e: (e[0], e[1]))
        data = bytearray()
        if ch != 9:
            data += b"\x00" + bytes([0xC0 | ch, prog])
        data += b"\x00" + bytes([0xB0 | ch, 7, 100]) + b"\x00" + bytes([0xB0 | ch, 91, 40])
        last = 0
        for tick, on, nt, vel in ev:
            data += vlq(tick - last) + bytes([(0x90 if on else 0x80) | ch, nt, vel])
            last = tick
        data += b"\x00\xFF\x2F\x00"
        chunks.append(b"MTrk" + struct.pack(">I", len(data)) + bytes(data))
    hdr = b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), tpq)
    with open(path, "wb") as f:
        f.write(hdr + b"".join(chunks))


def compose(seconds, seed=0):
    r = random.Random(seed)
    bpm = r.choice([112, 116, 120, 126, 132])
    beats = seconds * bpm / 60
    bars = max(2, int(math.ceil(beats / 4)))
    key = r.choice([0, 2, 5, 7, -3]) + 60  # C, D, F, G, A
    sc = SCALES["major"]
    prog = r.choice(PROGS)
    band = r.choice(BANDS)

    def deg(d, octave=0):
        return key + sc[d % 7] + 12 * (d // 7 + octave)

    mel, acc, bass, drums = [], [], [], []
    motif = [r.choice([0, 2, 4]) for _ in range(4)]
    rhythm = r.choice([[1, 0.5, 0.5, 1, 1], [0.5, 0.5, 1, 0.5, 0.5, 1], [1, 1, 0.5, 0.5, 1], [0.75, 0.25, 1, 0.5, 0.5, 1]])
    for b in range(bars):
        root = prog[b % len(prog)]
        chord = [root, root + 2, root + 4]
        t0 = b * 4
        # bass: root on 1, fifth on 3 (bouncy)
        bass.append((t0, 0.9, deg(root, -2), 92))
        bass.append((t0 + 2, 0.9, deg(root + 4, -2), 84))
        # accompaniment: off-beat chord stabs
        for beat in (0.5, 1.5, 2.5, 3.5):
            for c in chord:
                acc.append((t0 + beat, 0.4, deg(c, -1), 62))
        # melody: motif on chord tones, varied every other bar
        tt = t0
        k = 0
        for du in rhythm:
            if tt >= t0 + 4:
                break
            if k == 0 or r.random() < 0.55:
                d = r.choice(chord) + (7 if r.random() < 0.3 else 0)
            else:
                d = motif[k % 4] + root + r.choice([-1, 1])
            if b == bars - 1 and tt + du >= t0 + 4 - 0.01:
                d = 0  # end on the tonic so the loop resolves
            mel.append((tt, du * 0.9, deg(d, 1), r.randint(84, 100)))
            tt += du
            k += 1
        # light percussion: shaker 8ths, woodblock on 2 and 4, soft kick on 1
        for e in range(8):
            drums.append((t0 + e * 0.5, 0.1, 70, 50 if e % 2 else 64))
        drums += [(t0 + 1, 0.1, 76, 70), (t0 + 3, 0.1, 76, 70), (t0, 0.2, 36, 70)]
    return bpm, [(0, band["melody"], mel), (1, band["accomp"], acc), (2, band["bass"], bass), (9, 0, drums)], band


SF2_CANDIDATES = [os.environ.get("SF2", ""), "/usr/share/sounds/sf2/GeneralUser-GS.sf2", "GeneralUser-GS.sf2",
                  "/usr/share/sounds/sf2/FluidR3_GM.sf2", "/usr/share/sounds/sf2/default-GM.sf2",
                  "/usr/share/sounds/sf2/TimGM6mb.sf2"]


def read_wav(path):
    with wave.open(path) as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        a = np.frombuffer(w.readframes(n), dtype=np.int16 if sw == 2 else np.int32).astype(np.float64)
    a = a.reshape(-1, ch).mean(axis=1) / (32768 if sw == 2 else 2 ** 31)
    if sr != SR:
        a = np.interp(np.arange(int(len(a) * SR / sr)) * sr / SR, np.arange(len(a)), a)
    return a


def music(seconds, seed=0):
    sf2 = next((p for p in SF2_CANDIDATES if p and os.path.exists(p)), None)
    if not shutil.which("fluidsynth") or not sf2:
        print("music: fluidsynth/soundfont missing -> no music", file=sys.stderr)
        return np.zeros(int(SR * seconds))
    bpm, tracks, band = compose(seconds + 1, seed)
    d = tempfile.mkdtemp()
    write_midi(f"{d}/m.mid", tracks, bpm=bpm)
    subprocess.run(["fluidsynth", "-ni", "-g", "0.8", "-r", str(SR), "-F", f"{d}/m.wav", sf2, f"{d}/m.mid"],
                   check=True, capture_output=True)
    a = read_wav(f"{d}/m.wav")[: int(SR * seconds)]
    a = np.pad(a, (0, max(0, int(SR * seconds) - len(a))))
    print(f"music: {band['name']} {bpm}bpm sf2={os.path.basename(sf2)}", file=sys.stderr)
    return a


# ------------------------------------------------------------------ mix
def mix(events, fps, seconds, seed=0, music_gain=0.32):
    n = int(SR * seconds)
    fx = np.zeros(n + SR)
    duck = np.ones(n + SR)
    r = random.Random(seed)
    for frame, kind in events:
        if kind not in SFX:
            continue
        s = SFX[kind]() * GAIN.get(kind, 0.5) * r.uniform(0.85, 1.0)
        i = int(frame / fps * SR)
        if i >= n:
            continue
        s = s[: len(fx) - i]
        fx[i:i + len(s)] += s
        # duck the music a little under each effect
        dn = min(len(s) + int(SR * 0.1), len(duck) - i)
        duck[i:i + dn] = np.minimum(duck[i:i + dn], 0.65)
    fx = reverb(fx[:n], 0.12)
    duck = lowpass(duck[:n], 12)
    m = music(seconds, seed) * music_gain * duck
    out = fx + m
    out = np.tanh(out * 1.2) / 1.2  # gentle limiter
    # tiny fades so the loop point doesn't click
    return fade(norm(out, 0.89), 0.01, 0.05)


def save(path, x):
    x16 = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(x16.tobytes())


if __name__ == "__main__":
    ev = json.load(open(sys.argv[1]))
    fps = ev.get("fps", 24)
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else ev["frames"] / fps
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else ev.get("seed", 0)
    save(sys.argv[2], mix(ev["events"], fps, secs, seed))
    print("audio ok", sys.argv[2])
