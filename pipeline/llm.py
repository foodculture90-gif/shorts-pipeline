"""Google Gemini, free tier (key from aistudio.google.com).

Model names change often, so we ask Google which models this key can use and pick the
best "flash" model automatically (newest version first, "lite" as backup)."""
import json
import os
import re
import time

import requests

from . import config

API = "https://generativelanguage.googleapis.com/v1beta"
_models = None


class LLMError(Exception):
    pass


def _version(name):
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0


def available_models():
    """Flash text models this key can call, best first."""
    global _models
    if _models is not None:
        return _models
    preferred = [m.strip() for m in os.getenv("GEMINI_MODELS", "").split(",") if m.strip()]
    found = []
    try:
        r = requests.get(f"{API}/models", headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                         params={"pageSize": 200}, timeout=30)
        r.raise_for_status()
        for m in r.json().get("models", []):
            name = m["name"].split("/", 1)[-1]
            if "generateContent" not in m.get("supportedGenerationMethods", []):
                continue
            if "flash" not in name or any(x in name for x in ("image", "tts", "live", "audio", "embedding", "robotics", "thinking-exp")):
                continue
            found.append(name)
    except Exception as e:  # noqa: BLE001
        print("  could not list Gemini models:", e)
    # newest version first; stable before preview/exp; full flash before lite
    found.sort(key=lambda n: (-_version(n), "preview" in n or "exp" in n, "lite" in n, len(n)))
    _models = preferred + [m for m in found if m not in preferred] + \
        [m for m in config.GEMINI_MODELS if m not in found and m not in preferred]
    print("  writer models:", ", ".join(_models[:4]))
    return _models


class Busy(LLMError):
    """Every model was busy or over its free limit — try again later."""


def generate_json(system, prompt, temperature=1.0):
    """Tries each model quickly; busy (503) or slow models are skipped instead of waited on.
    Two passes over the model list; raises Busy if Google is overloaded/limited everywhere."""
    key = os.environ["GEMINI_API_KEY"]
    last, busy_only = None, True
    for rnd in range(2):
        for model in available_models()[:8]:
            try:
                r = requests.post(
                    f"{API}/models/{model}:generateContent",
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json={
                        "systemInstruction": {"parts": [{"text": system}]},
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": temperature, "responseMimeType": "application/json",
                                             "maxOutputTokens": 8192},
                    },
                    timeout=(10, 75),
                )
                if r.status_code == 404:          # model retired → next one
                    last = f"{model}: not available"
                    continue
                if r.status_code in (429, 500, 502, 503, 504):
                    last = f"{model}: {r.status_code} {r.text[:160]}"
                    print(f"  {model}: {'free limit reached' if r.status_code == 429 else 'busy'} ({r.status_code}), next model")
                    continue
                if not r.ok:
                    busy_only = False
                    last = f"{model}: {r.status_code} {r.text[:200]}"
                    print(f"  {model}: error {r.status_code}, next model")
                    continue
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                m = re.search(r"\{.*\}", text, re.S)
                return json.loads(m.group(0) if m else text)
            except requests.Timeout:
                last = f"{model}: too slow"
                print(f"  {model}: too slow, next model")
            except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as e:
                busy_only = False
                last = f"{model}: {e}"
                print(f"  {model}: {str(e)[:120]}")
        if rnd == 0:
            print("  all writer models busy — waiting 30 s and trying once more")
            time.sleep(30)
    raise (Busy if busy_only else LLMError)(f"Gemini failed: {last}")
