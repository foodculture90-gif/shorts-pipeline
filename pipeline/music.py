"""Free background music, made from scratch for every short (so it is always copyright-free).

A gentle kids' tune: plucked harp/ukulele arpeggios, a soft pad, a round bass, a little bell
melody and a light shaker. Key, tempo, chords and instruments change with the seed.
Also makes small sound effects (whoosh, sparkle) for transitions.
"""
import random

import numpy as np

SR = 44100
_KS_CACHE = {}

PROGRESSIONS = [[0, 4, 5, 3], [0, 5, 3, 4], [0, 3, 4, 0], [5, 3, 0, 4], [0, 3, 0, 4], [3, 4, 0, 5]]
MAJOR = [0, 2, 4, 5, 7, 9, 11]


def _midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def _pluck(midi, secs=1.2, bright=0.5):
    """Karplus-Strong plucked string (cached per pitch)."""
    key = (midi, round(bright, 2))
    if key in _KS_CACHE:
        return _KS_CACHE[key]
    n = int(SR * secs)
    period = max(2, int(round(SR / _midi(midi))))
    rng = np.random.default_rng(midi)
    buf = rng.uniform(-1, 1, period).astype(np.float32)
    # soften the excitation for a warmer, ukulele/harp-like tone
    for _ in range(int(3 - 2 * bright)):
        buf = 0.5 * (buf + np.roll(buf, 1))
    out = np.empty(n + period, np.float32)
    out[:period] = buf
    decay = 0.996 - 0.0006 * max(0, midi - 60) / 12
    i = period
    while i < n + period:
        prev = out[i - period:i]
        blk = decay * 0.5 * (prev + np.concatenate(([prev[-1]], prev[:-1])))
        m = min(period, n + period - i)
        out[i:i + m] = blk[:m]
        i += m
    out = out[period:]
    out *= np.minimum(1, np.linspace(0, 60, n))  # 1/60 s fade-in, no click
    _KS_CACHE[key] = out
    return out


def _bell(midi, secs=1.6):
    t = np.arange(int(SR * secs)) / SR
    f = _midi(midi)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2)
         + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
         + 0.15 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 11))
    return (s * np.minimum(1, t * 400)).astype(np.float32)


def _sine_note(midi, secs, attack=0.01, release=0.2, detune=0.0):
    t = np.arange(int(SR * secs)) / SR
    f = _midi(midi)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 2 * t)
    if detune:
        s = 0.5 * s + 0.5 * np.sin(2 * np.pi * f * (1 + detune) * t)
    env = np.minimum(1, t / max(attack, 1e-3)) * np.minimum(1, (secs - t) / max(release, 1e-3))
    return (s * np.clip(env, 0, 1)).astype(np.float32)


def _add(track, sig, start, gain=1.0):
    a = int(start * SR)
    if a >= len(track):
        return
    b = min(len(track), a + len(sig))
    track[a:b] += sig[:b - a] * gain


def make_music(total, seed=1):
    """Returns stereo float32 array (n, 2) of `total` seconds."""
    rng = random.Random(seed * 7919 + 13)
    n = int(total * SR) + SR
    left = np.zeros(n, np.float32)
    right = np.zeros(n, np.float32)
    root = 60 + rng.choice([0, 2, 5, 7, -3])          # C, D, F, G, A
    bpm = rng.uniform(88, 112)
    beat = 60 / bpm
    prog = rng.choice(PROGRESSIONS)
    pattern = rng.choice([[0, 1, 2, 3, 2, 1, 2, 1], [0, 2, 1, 2, 3, 2, 1, 2], [0, 1, 2, 1, 3, 1, 2, 1]])
    bright = rng.uniform(0.3, 0.8)
    use_bells = rng.random() < 0.8
    shaker = rng.random() < 0.7

    def chord(deg):
        notes = [MAJOR[(deg + k) % 7] + 12 * ((deg + k) // 7) for k in (0, 2, 4)]
        return [root + x for x in notes]

    bar = 4 * beat
    nbars = int(total / bar) + 2
    melody_note = None
    for b in range(nbars):
        c = chord(prog[b % len(prog)])
        t0 = b * bar
        # plucked arpeggio, eighth notes
        tones = [c[0], c[1], c[2], c[0] + 12]
        for k in range(8):
            m = tones[pattern[k]]
            s = _pluck(m, 1.4, bright)
            pan = 0.5 + 0.25 * np.sin(k)
            g = 0.32 * (1.0 if k % 2 == 0 else 0.8)
            _add(left, s, t0 + k * beat / 2, g * (1 - pan) * 2)
            _add(right, s, t0 + k * beat / 2, g * pan * 2)
        # soft pad
        for m in c:
            pad = _sine_note(m - 12, bar + 0.4, attack=0.6, release=0.6, detune=0.004)
            _add(left, pad, t0, 0.045)
            _add(right, pad, t0, 0.045)
        # bass on beats 1 and 3
        for k in (0, 2):
            bs = _sine_note(c[0] - 24, beat * 1.6, attack=0.01, release=0.4)
            _add(left, bs, t0 + k * beat, 0.22)
            _add(right, bs, t0 + k * beat, 0.22)
        # little bell melody on bars 2 and 4 of each phrase
        if use_bells and b % 2 == 1:
            for k in range(4):
                if rng.random() < 0.75:
                    cand = [x + 12 for x in c] + [c[0] + 24]
                    if melody_note is not None:
                        cand.sort(key=lambda x: abs(x - melody_note))
                        m = cand[min(len(cand) - 1, rng.choice([0, 0, 1, 2]))]
                    else:
                        m = rng.choice(cand)
                    melody_note = m
                    _add(left, _bell(m), t0 + k * beat, 0.09)
                    _add(right, _bell(m), t0 + k * beat + 0.012, 0.09)
        if shaker:
            nrng = np.random.default_rng(b)
            for k in range(8):
                ln = int(0.05 * SR)
                hit = nrng.uniform(-1, 1, ln).astype(np.float32) * np.exp(-np.arange(ln) / (0.012 * SR))
                hit = hit - np.concatenate(([0], hit[:-1]))   # crude high-pass = crisp
                _add(left, hit, t0 + k * beat / 2 + beat / 4, 0.03 if k % 2 else 0.018)
                _add(right, hit, t0 + k * beat / 2 + beat / 4, 0.018 if k % 2 else 0.03)
    st = np.stack([left, right], 1)[: int(total * SR)]
    # gentle fade in/out and normalise
    m = len(st)
    fade = np.ones(m, np.float32)
    fi, fo = int(0.6 * SR), int(1.6 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo)
    st *= fade[:, None]
    peak = np.abs(st).max() or 1
    return (st / peak * 0.9).astype(np.float32)


def whoosh(secs=0.45, seed=0):
    rng = np.random.default_rng(seed)
    n = int(secs * SR)
    noise = rng.normal(0, 1, n).astype(np.float32)
    t = np.linspace(0, 1, n)
    env = np.sin(np.pi * t) ** 2
    # sweep: blend between smoothed (dark) and raw (bright) noise
    dark = np.convolve(noise, np.ones(24) / 24, mode="same")
    s = (dark * (1 - t) + noise * t * 0.35) * env
    return (s / (np.abs(s).max() or 1)).astype(np.float32)


def sparkle(seed=0):
    rng = random.Random(seed)
    out = np.zeros(int(0.9 * SR), np.float32)
    base = 84 + rng.choice([0, 2, 4])
    for k, step in enumerate([0, 4, 7, 12]):
        b = _bell(base + step, 0.6)
        a = int(k * 0.06 * SR)
        out[a:a + len(b)] += b[: len(out) - a] * (0.8 - 0.12 * k)
    return out / (np.abs(out).max() or 1)


# ------------------------------------------------------------------ sound effects
SFX = ["boing", "pop", "twinkle", "whoosh", "slide_up", "slide_down", "splash", "tada", "taps", "honk",
       "ding", "drum_roll", "bubble"]


def _env(n, attack=0.005, decay=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t / decay)


def sfx(name, seed=0):
    """Cartoon sound effects, synthesised (no samples, no copyright)."""
    rng = np.random.default_rng(seed)
    if name == "boing":
        n = int(0.55 * SR); t = np.arange(n) / SR
        f = 180 + 260 * np.exp(-t * 7) + 30 * np.sin(2 * np.pi * 14 * t) * np.exp(-t * 3)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.003, 0.22)
    elif name == "pop":
        n = int(0.12 * SR); t = np.arange(n) / SR
        s = np.sin(2 * np.pi * np.cumsum(900 - 5000 * t) / SR) * _env(n, 0.001, 0.03)
    elif name == "twinkle":
        s = sparkle(seed)
    elif name == "whoosh":
        s = whoosh(0.5, seed)
    elif name in ("slide_up", "slide_down"):
        n = int(0.6 * SR); t = np.arange(n) / SR
        f = 400 + 900 * (t / t[-1]) if name == "slide_up" else 1300 - 900 * (t / t[-1])
        vib = 1 + 0.02 * np.sin(2 * np.pi * 9 * t)
        s = np.sin(2 * np.pi * np.cumsum(f * vib) / SR) * np.minimum(1, t / 0.03) * np.minimum(1, (t[-1] - t) / 0.08)
        s += 0.3 * np.sin(2 * 2 * np.pi * np.cumsum(f * vib) / SR) * np.minimum(1, t / 0.03) * np.minimum(1, (t[-1] - t) / 0.08)
    elif name == "splash":
        n = int(0.7 * SR)
        noise = rng.normal(0, 1, n)
        noise = noise - np.concatenate(([0], noise[:-1])) * 0.7
        s = noise * _env(n, 0.004, 0.18)
        for k in range(6):  # droplets
            a = int(rng.uniform(0.1, 0.6) * SR); m = int(0.05 * SR)
            tt = np.arange(m) / SR
            s[a:a + m] += 0.6 * np.sin(2 * np.pi * np.cumsum(1200 + 2500 * tt) / SR)[: n - a] * np.exp(-tt * 60)[: n - a]
    elif name == "tada":
        n = int(1.3 * SR); s = np.zeros(n)
        for k, (m, st) in enumerate([(72, 0.0), (76, 0.0), (79, 0.0), (84, 0.18), (88, 0.18), (91, 0.18)]):
            note = _sine_note(m, 1.1 - st, attack=0.01, release=0.5)
            a = int(st * SR); s[a:a + len(note)] += note[: n - a] * 0.4
    elif name == "taps":
        n = int(0.9 * SR); s = np.zeros(n)
        for k in range(4):
            m = int(0.04 * SR); tt = np.arange(m) / SR
            hit = np.sin(2 * np.pi * (300 + 60 * (k % 2)) * tt) * np.exp(-tt * 90) + rng.normal(0, 0.3, m) * np.exp(-tt * 200)
            a = int(k * 0.2 * SR); s[a:a + m] += hit
    elif name == "honk":
        n = int(0.5 * SR); t = np.arange(n) / SR
        sq = np.sign(np.sin(2 * np.pi * 330 * t)) * 0.5 + np.sign(np.sin(2 * np.pi * 415 * t)) * 0.5
        s = np.convolve(sq, np.ones(12) / 12, mode="same") * np.minimum(1, t / 0.01) * np.minimum(1, (t[-1] - t) / 0.05)
        s[int(0.22 * SR):int(0.27 * SR)] *= 0.1
    elif name == "ding":
        s = _bell(88, 1.2)
    elif name == "giggle":
        n = int(0.8 * SR); s = np.zeros(n)
        for k in range(5):
            m = int(0.09 * SR); tt = np.arange(m) / SR
            f0 = 520 + 40 * k + 80 * np.sin(2 * np.pi * 7 * tt)
            v = (np.sin(2 * np.pi * np.cumsum(f0) / SR) + 0.4 * np.sin(4 * np.pi * np.cumsum(f0) / SR))
            v *= np.sin(np.pi * tt / tt[-1]) ** 2
            a = int(k * 0.13 * SR); s[a:a + m] += v[: n - a] * (1 - 0.12 * k)
    elif name == "drum_roll":
        n = int(1.0 * SR); s = np.zeros(n)
        for k in range(28):
            m = int(0.03 * SR); tt = np.arange(m) / SR
            a = int(k * 0.034 * SR)
            s[a:a + m] += (rng.normal(0, 1, m) * 0.5 + np.sin(2 * np.pi * 180 * tt)) * np.exp(-tt * 80) * (0.4 + 0.6 * k / 28)
    elif name == "bubble":
        n = int(0.5 * SR); s = np.zeros(n)
        for k in range(4):
            m = int(0.06 * SR); tt = np.arange(m) / SR
            a = int(rng.uniform(0, 0.4) * SR)
            s[a:a + m] += np.sin(2 * np.pi * np.cumsum(500 + 1800 * tt / tt[-1]) / SR)[: n - a] * np.exp(-tt * 40)[: n - a]
    else:
        return np.zeros(1, np.float32)
    s = np.asarray(s, np.float32)
    return s / (np.abs(s).max() or 1)
