"""Google Gemini, free tier (key from aistudio.google.com)."""
import json
import os
import re
import time

import requests

from . import config


class LLMError(Exception):
    pass


def generate_json(system, prompt, temperature=1.0):
    key = os.environ["GEMINI_API_KEY"]
    last = None
    for model in config.GEMINI_MODELS:
        for attempt in range(3):
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model.strip()}:generateContent",
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json={
                        "systemInstruction": {"parts": [{"text": system}]},
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": temperature, "responseMimeType": "application/json",
                                             "maxOutputTokens": 4096},
                    },
                    timeout=120,
                )
                if r.status_code == 429:  # free-tier rate limit: wait, then try again / next model
                    last = "rate limited"
                    time.sleep(20 * (attempt + 1))
                    continue
                r.raise_for_status()
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts)
                m = re.search(r"\{.*\}", text, re.S)
                return json.loads(m.group(0) if m else text)
            except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as e:
                last = e
                time.sleep(5)
    raise LLMError(f"Gemini failed: {last}")
