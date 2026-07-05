#!/usr/bin/env python3
"""
sync_garden_data.py

Checks the Slack channel #tgif for data-logger files that haven't been
synced yet. If there's nothing new, it does nothing. If there are new
files, it downloads them, converts them to CSV, drops them in
data/garden/, and updates data/garden/manifest.json so the dashboard
(garden-dashboard.html) picks them up.

Meant to be run on a schedule via GitHub Actions
(.github/workflows/sync-garden-data.yml), but works fine run locally too:

    export SLACK_BOT_TOKEN=xoxb-...
    python scripts/sync_garden_data.py

Requires: slack_sdk, pandas, openpyxl, requests
    pip install slack_sdk pandas openpyxl requests

Slack app setup (one-time):
  1. Create a Slack app at https://api.slack.com/apps, install it to the
     Hu Lab workspace.
  2. Grant it the bot scopes: channels:history, files:read
  3. Invite the bot to #tgif:  /invite @your-bot-name
  4. Copy the "Bot User OAuth Token" (starts with xoxb-) into a GitHub
     Actions secret named SLACK_BOT_TOKEN.
"""

import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    sys.exit("Missing dependency: pip install slack_sdk")

try:
    import pandas as pd
except ImportError:
    sys.exit("Missing dependency: pip install pandas openpyxl")

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHANNEL_ID = "C0AGSKQS5PY"          # #tgif
CHANNEL_NAME = "#tgif"
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "garden"
MANIFEST_PATH = DATA_DIR / "manifest.json"

SPREADSHEET_MIMETYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",                                          # .xls
}
SPREADSHEET_EXTENSIONS = {"xlsx", "xls"}
CSV_MIMETYPES = {"text/csv"}


def is_spreadsheet_file(f):
    """True if this Slack file object looks like an Excel file — checked
    by mimetype AND filename extension, since Slack's reported mimetype
    for spreadsheet uploads isn't always reliable."""
    if f.get("mimetype") in SPREADSHEET_MIMETYPES:
        return True
    name = (f.get("name") or f.get("title") or "").lower()
    return any(name.endswith("." + ext) for ext in SPREADSHEET_EXTENSIONS)


def is_csv_file(f):
    if f.get("mimetype") in CSV_MIMETYPES:
        return True
    name = (f.get("name") or f.get("title") or "").lower()
    return name.endswith(".csv")


def load_manifest():
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return []


def save_manifest(manifest):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
        f.write("\n")


def safe_filename(title):
    """Turn a Slack file title into a filesystem- and URL-safe .csv name."""
    base = re.sub(r"[^\w\-. ]", "", title).strip()
    base = re.sub(r"\s+", "_", base)
    if not base.lower().endswith(".csv"):
        base = re.sub(r"\.(xlsx|xls)$", "", base, flags=re.IGNORECASE) + ".csv"
    return base


def download_slack_file(client, file_info):
    """Download a Slack file's binary content using the bot token."""
    url = file_info["url_private_download"]
    token = client.token
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.content


def convert_to_csv_bytes(raw_bytes, f):
    """Return CSV text for a Slack file. xlsx/xls get converted; files
    that are already CSV pass straight through."""
    if is_csv_file(f):
        return raw_bytes.decode("utf-8", errors="replace")

    if is_spreadsheet_file(f):
        df = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=0, header=None)
        # NOTE: sheet_name=0 grabs the first sheet only. HOBO-style loggers
        # can sometimes prepend a title row before the real header row —
        # the dashboard's CSV parser has a heuristic to find it, so we
        # deliberately do NOT try to strip it here and lose information.
        return df.to_csv(index=False, header=False)

    raise ValueError(f"Unrecognized file type: {f.get('name') or f.get('title')}")


def main():
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        sys.exit("SLACK_BOT_TOKEN environment variable is not set.")

    client = WebClient(token=token)
    manifest = load_manifest()
    known_file_ids = {entry["slack_file_id"] for entry in manifest if "slack_file_id" in entry}

    try:
        history = client.conversations_history(channel=CHANNEL_ID, limit=200)
    except SlackApiError as e:
        sys.exit(f"Could not read {CHANNEL_NAME}: {e.response['error']}")

    messages = history.get("messages", [])
    new_files = []
    for msg in messages:
        for f in msg.get("files", []):
            if f["id"] in known_file_ids:
                continue
            if is_spreadsheet_file(f) or is_csv_file(f):
                new_files.append(f)

    if not new_files:
        print(f"No new data files found in {CHANNEL_NAME}. Nothing to do.")
        return

    # Oldest first, so the manifest / commit history reads chronologically.
    new_files.sort(key=lambda f: float(f.get("timestamp", 0)))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    added = []

    for f in new_files:
        title = f.get("title") or f.get("name") or f["id"]
        print(f"Downloading: {title}")
        try:
            raw = download_slack_file(client, f)
            csv_text = convert_to_csv_bytes(raw, f)
        except Exception as e:
            print(f"  Skipped ({e})")
            continue

        out_name = safe_filename(title)
        out_path = DATA_DIR / out_name
        # Avoid clobbering a same-named file synced on a previous run.
        counter = 2
        while out_path.exists():
            out_path = DATA_DIR / f"{out_name[:-4]}_{counter}.csv"
            counter += 1
        out_path.write_text(csv_text)

        entry = {
            "slack_file_id": f["id"],
            "label": title,
            "file": f"data/garden/{out_path.name}",
            "recorded": datetime.fromtimestamp(float(f.get("timestamp", 0)), tz=timezone.utc).isoformat()
                        if f.get("timestamp") else None,
            "synced": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        manifest.append(entry)
        added.append(entry)
        print(f"  Saved -> {out_path.relative_to(REPO_ROOT)}")

    if added:
        save_manifest(manifest)
        print(f"\nSynced {len(added)} new file(s). Manifest updated: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    else:
        print("\nFound new files in Slack but none could be converted — nothing was added.")


if __name__ == "__main__":
    main()
