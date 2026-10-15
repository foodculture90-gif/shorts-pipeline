"""Optional phone notifications via a Telegram bot ("video ready — open the panel").
Skipped silently if TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID aren't set."""
import os

import requests


def send(text):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return
    panel = os.getenv("PANEL_URL", "")
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=20, json={
            "chat_id": chat, "text": f"{text}\n{panel}".strip(), "disable_web_page_preview": True})
    except requests.RequestException as e:
        print("notify failed:", e)
