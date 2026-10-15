"""YouTube: connect channels (from the app), upload approved shorts, read stats. All free."""
import os

import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]


def exchange_code(code, redirect_uri):
    """Turns the one-time code from the app's 'Connect YouTube' button into a lasting permission."""
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "code": code, "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "redirect_uri": redirect_uri, "grant_type": "authorization_code"})
    if r.status_code != 200:
        raise RuntimeError(f"Google refused the connection: {r.text[:300]}")
    data = r.json()
    if "refresh_token" not in data:
        raise RuntimeError("Google gave no lasting permission — remove the app's access in your Google account and connect again")
    yt = _client(data["refresh_token"])
    items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    if not items:
        raise RuntimeError("That Google account has no YouTube channel yet")
    return data["refresh_token"], items[0]["id"], items[0]["snippet"]["title"]


def _client(refresh_token):
    creds = Credentials(token=None, refresh_token=refresh_token, client_id=os.environ["YT_CLIENT_ID"],
                        client_secret=os.environ["YT_CLIENT_SECRET"],
                        token_uri="https://oauth2.googleapis.com/token", scopes=SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(refresh_token, video_path, story, channel, publish_at=None):
    status = {"privacyStatus": "private" if publish_at else "public",
              "selfDeclaredMadeForKids": bool(channel.get("made_for_kids", True))}
    if publish_at:
        status["publishAt"] = publish_at
    tags = [t for t in (story.get("tags") or []) if isinstance(t, str)][:12] + ["shorts"]
    body = {
        "snippet": {
            "title": (story["title"][:88] + " #shorts"),
            "description": (f"{story.get('description', '')}\n\n{story.get('takeaway', '')}\n\n"
                            f"New stories every day on {channel.get('name', '')}! #shorts"),
            "tags": tags, "categoryId": "1", "defaultLanguage": "en", "defaultAudioLanguage": "en"},
        "status": status,
    }
    req = _client(refresh_token).videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"], resp.get("status", {}).get("privacyStatus")


def stats(refresh_token, video_ids):
    out, yt = {}, _client(refresh_token)
    for i in range(0, len(video_ids), 50):
        res = yt.videos().list(part="statistics,status", id=",".join(video_ids[i:i + 50])).execute()
        for it in res.get("items", []):
            s = it.get("statistics", {})
            out[it["id"]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                             "privacy": it.get("status", {}).get("privacyStatus")}
    return out
