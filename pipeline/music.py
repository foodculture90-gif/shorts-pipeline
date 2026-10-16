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
