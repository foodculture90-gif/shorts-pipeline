"""Tiny Supabase client (database + file storage) for the cloud worker."""
import json
import os
from pathlib import Path

import requests

BUCKET = "media"


def _base():
    return os.environ["SUPABASE_URL"].rstrip("/")


def _headers(extra=None):
    key = os.environ["SUPABASE_SERVICE_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    h.update(extra or {})
    return h


def select(table, query=""):
    r = requests.get(f"{_base()}/rest/v1/{table}?{query}", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def insert(table, row):
    r = requests.post(f"{_base()}/rest/v1/{table}", headers=_headers({"Prefer": "return=representation"}),
                      data=json.dumps(row, default=str), timeout=30)
    r.raise_for_status()
    return r.json()[0]


def insert_many(table, rows):
    r = requests.post(f"{_base()}/rest/v1/{table}", headers=_headers({"Prefer": "return=minimal"}),
                      data=json.dumps(rows, default=str), timeout=30)
    r.raise_for_status()


def update(table, match, values):
    r = requests.patch(f"{_base()}/rest/v1/{table}?{match}", headers=_headers({"Prefer": "return=representation"}),
                       data=json.dumps(values, default=str), timeout=30)
    r.raise_for_status()
    return r.json()


def rpc(fn, **args):
    r = requests.post(f"{_base()}/rest/v1/rpc/{fn}", headers=_headers(), data=json.dumps(args), timeout=30)
    r.raise_for_status()
    return r.json()


def upsert(table, row, on_conflict):
    r = requests.post(f"{_base()}/rest/v1/{table}?on_conflict={on_conflict}",
                      headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
                      data=json.dumps(row, default=str), timeout=30)
    r.raise_for_status()


def settings():
    return {row["key"]: row["value"] for row in select("settings", "select=key,value")}


def log(message, kind="info", project="shorts"):
    print(f"[{kind}] {message}")
    try:
        insert("activity", {"project_id": project, "kind": kind, "message": message[:500]})
    except Exception as e:  # noqa: BLE001
        print("  (could not log activity)", e)


# ---- Storage ------------------------------------------------------------------
def upload(local: Path, remote: str, content_type="application/octet-stream"):
    with open(local, "rb") as f:
        r = requests.post(f"{_base()}/storage/v1/object/{BUCKET}/{remote}",
                          headers=_headers({"Content-Type": content_type, "x-upsert": "true"}),
                          data=f, timeout=600)
    r.raise_for_status()
    return remote


def download(remote: str, local: Path):
    r = requests.get(f"{_base()}/storage/v1/object/{BUCKET}/{remote}", headers=_headers(), timeout=600)
    if r.status_code in (400, 404):
        return None
    r.raise_for_status()
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(r.content)
    return local


def list_files(prefix):
    r = requests.post(f"{_base()}/storage/v1/object/list/{BUCKET}", headers=_headers(),
                      data=json.dumps({"prefix": prefix, "limit": 100}), timeout=30)
    r.raise_for_status()
    return [f"{prefix.rstrip('/')}/{f['name']}" for f in r.json() if f.get("id")]


def remove(paths):
    if not paths:
        return
    requests.delete(f"{_base()}/storage/v1/object/{BUCKET}", headers=_headers(),
                    data=json.dumps({"prefixes": list(paths)}), timeout=60)
