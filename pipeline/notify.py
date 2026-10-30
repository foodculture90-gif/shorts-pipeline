"""Phone notifications: web push to the installed Shorts Studio app (the daily views report), plus the optional
Telegram bot ("video ready") - skipped silently if TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID aren't set.

The app makes the push keys itself (Settings -> Notifications) and saves them, with each phone's
subscription, in the `settings` table: `push_vapid` {pub, priv} and `push_subs` [subscription, ...].
"""
import base64
import json
import os
import struct
import time
import traceback
from urllib.parse import urlparse

import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import db

DUB = ZoneInfo("Europe/Dublin")
REPORT_HOUR = 8          # Irish time: the daily report goes out on the first worker run after this


# ---------------------------------------------------------------- web push (RFC 8291 + VAPID RFC 8292), no extra library
def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _b64e(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _encrypt(sub, payload: bytes):
    """aes128gcm body for one subscription."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    ua_pub = _b64d(sub["keys"]["p256dh"])
    auth = _b64d(sub["keys"]["auth"])
    ua = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_pub)
    eph = ec.generate_private_key(ec.SECP256R1())
    as_pub = eph.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    shared = eph.exchange(ec.ECDH(), ua)
    ikm = HKDF(hashes.SHA256(), 32, auth, b"WebPush: info\x00" + ua_pub + as_pub).derive(shared)
    salt = os.urandom(16)
    cek = HKDF(hashes.SHA256(), 16, salt, b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt, b"Content-Encoding: nonce\x00").derive(ikm)
    ct = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    return salt + struct.pack(">IB", 4096, len(as_pub)) + as_pub + ct


def _vapid(endpoint, priv_b64):
    import jwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.derive_private_key(int.from_bytes(_b64d(priv_b64), "big"), ec.SECP256R1())
    pub = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    u = urlparse(endpoint)
    tok = jwt.encode({"aud": f"{u.scheme}://{u.netloc}", "exp": int(time.time()) + 12 * 3600,
                      "sub": "https://mission-control-app-one-xi.vercel.app"}, key, algorithm="ES256")
    return f"vapid t={tok}, k={_b64e(pub)}"


def push_one(sub, data: dict, priv, ttl=12 * 3600):
    body = _encrypt(sub, json.dumps(data).encode())
    return requests.post(sub["endpoint"], data=body, timeout=20, headers={
        "Authorization": _vapid(sub["endpoint"], priv), "Content-Encoding": "aes128gcm",
        "Content-Type": "application/octet-stream", "TTL": str(ttl), "Urgency": "normal"})


def send(text):
    """Optional Telegram message."""
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return
    panel = os.getenv("PANEL_URL", "")
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=20, json={
            "chat_id": chat, "text": f"{text}\n{panel}".strip(), "disable_web_page_preview": True})
    except requests.RequestException as e:
        print("notify failed:", e)


def push(title, body, url="./#/views", tag="report"):
    """Push to every phone that turned notifications on. Returns how many got it."""
    st = db.settings()
    keys, subs = st.get("push_vapid") or {}, st.get("push_subs") or []
    if not keys.get("priv") or not subs:
        return 0
    sent, keep = 0, []
    for s in subs:
        try:
            r = push_one(s, {"title": title, "body": body, "url": url, "tag": tag}, keys["priv"])
            if r.status_code < 300:
                sent += 1
            else:
                print("push failed:", r.status_code, r.text[:200])
            if r.status_code not in (404, 410):      # 404/410 = that phone turned them off -> forget it
                keep.append(s)
        except Exception as ex:  # noqa: BLE001
            keep.append(s)
            print("push failed:", ex)
    if len(keep) != len(subs):
        db.upsert("settings", {"key": "push_subs", "value": keep}, "key")
    return sent


def snapshot(ch_id, cs):
    """Remember the channel's totals at the end of each day (the last stats run of the day wins)."""
    if not cs:
        return
    key = f"yt_days_{ch_id}"
    days = db.settings().get(key) or {}
    today = datetime.now(DUB).date().isoformat()
    days[today] = {"subs": cs.get("subs"), "views": cs.get("views")}
    days = dict(sorted(days.items())[-40:])
    db.upsert("settings", {"key": key, "value": days}, "key")


def _views_by_day():
    """Views gained per (UTC) day across all shorts, from each short's daily view history."""
    eps = db.select("episodes", "select=story&youtube_id=not.is.null&status=in.(published,scheduled)")
    gain = {}
    for e in eps:
        hist = sorted(((e.get("story") or {}).get("yt") or {}).get("hist") or [])
        prev = 0
        for d, v in hist:
            gain[d] = gain.get(d, 0) + max(0, (v or 0) - prev)
            prev = v or 0
    return gain


def _subs_by_day():
    """Subscribers gained per day (needs a snapshot at the end of both days)."""
    tot = {}
    for k, v in db.settings().items():
        if k.startswith("yt_days_") and isinstance(v, dict):
            for d, x in v.items():
                if x.get("subs") is not None:
                    tot[d] = tot.get(d, 0) + int(x["subs"])
    out, ds = {}, sorted(tot)
    for a, b in zip(ds, ds[1:]):
        if (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days == 1:
            out[b] = tot[b] - tot[a]
    return out, (tot[ds[-1]] if ds else None)


def _n(x):
    return f"{x:,}"


def daily_report(force=False):
    """Once a day (morning): yesterday's views and subscribers, compared with the day before."""
    st = db.settings()
    today = datetime.now(DUB).date()
    if not force and (st.get("report_sent") == today.isoformat() or datetime.now(DUB).hour < REPORT_HOUR):
        return
    if not force and not (st.get("push_subs") and (st.get("push_vapid") or {}).get("priv")):
        return
    y, yy = (today - timedelta(days=1)).isoformat(), (today - timedelta(days=2)).isoformat()
    views = _views_by_day()
    v1, v2 = views.get(y, 0), views.get(yy, 0)
    subs, total = _subs_by_day()
    if v2:
        pct = round((v1 - v2) / v2 * 100)
        vtxt = f"{'▲' if pct >= 0 else '▼'} {abs(pct)}% vs the day before ({_n(v2)})"
    else:
        vtxt = f"day before: {_n(v2)}"
    if y in subs:
        s1 = subs[y]
        stxt = f"{s1:+,} subscribers" + (f" (day before {subs[yy]:+,})" if yy in subs else "")
    else:
        stxt = "subscriber change shows from the next report"
    if total is not None:
        stxt += f" · {_n(total)} total"
    title = f"📈 Yesterday: {_n(v1)} views"
    body = f"{vtxt}\n👥 {stxt}"
    n = push(title, body)
    db.upsert("settings", {"key": "report_sent", "value": today.isoformat()}, "key")
    db.log(f"📲 Daily report{' sent to ' + str(n) + ' phone(s)' if n else ''}: {title} — {vtxt} · {stxt}")


def maybe_report():
    try:
        daily_report()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
