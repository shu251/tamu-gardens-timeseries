# TAMU Gardens dashboard — setup notes

## What's here

```
garden-dashboard.html              the new interactive page
data/garden/manifest.json          index of synced sensor files (starts empty)
scripts/sync_garden_data.py        checks #tgif for new files, converts to CSV
.github/workflows/sync-garden-data.yml   runs the script weekly
```

## 1. Drop these into your repo

Copy `garden-dashboard.html`, the `data/` folder, `scripts/` folder, and
`.github/workflows/sync-garden-data.yml` into the root of
`tamu-gardens-timeseries`, preserving the folder structure. Link to
`garden-dashboard.html` from your existing site nav/index page.

## 2. Weather and river data — no setup needed

These load live in the browser every time someone opens the page:

- **Weather**: NWS station `KCLL` (Easterwood Field, College Station).
  Public API, no key required.
- **River**: USGS site `08109500`, Brazos River near College Station.
  Public API, no key required.

Both station IDs are set as constants near the top of the `<script>` block
in `garden-dashboard.html` if you ever need to point at a different
station or gauge.

## 3. Garden sensor data — one-time Slack setup

Static GitHub Pages sites can't call the Slack API directly (it needs a
secret token), so new files have to be synced into the repo first. I set
this up as a scheduled GitHub Action that checks `#tgif`, and only
commits something if it finds a file it hasn't seen before — otherwise it
does nothing, per what you described.

To turn it on:

1. Create a Slack app at <https://api.slack.com/apps> in the Hu Lab
   workspace, add the bot scopes `channels:history` and `files:read`,
   install it, and invite it to `#tgif` (`/invite @your-bot-name`).
2. Copy the Bot User OAuth Token (starts with `xoxb-`).
3. In the GitHub repo: **Settings → Secrets and variables → Actions →
   New repository secret**, name it `SLACK_BOT_TOKEN`, paste the token.
4. That's it — the workflow runs every Friday at 11:30pm Central, or you
   can trigger it manually from the **Actions** tab (**Sync garden
   sensor data from Slack → Run workflow**). Note: the cron is pinned to
   CDT, so during Standard Time (roughly Nov–Mar) it'll actually fire at
   10:30pm local — see the comment in the workflow file if that matters.

## Important assumption to double-check

I could see that `#tgif` currently has files named like
`C - 35 2026-03-17 08_59_00 CDT (Data CDT).xlsx` — these look like
HOBO-logger exports, not CSVs, and they've shown up every 1–3 weeks
rather than monthly. I wasn't able to open the file contents (no network
access in this session), so I couldn't confirm the actual column
headers.

The sync script converts these to CSV as-is, and the dashboard's CSV
parser auto-detects a timestamp column (looks for "date"/"time" in the
header row) and treats every other numeric column as a plottable
variable — so it should work without hardcoding column names. Once the
first real sync runs, it's worth loading the page and sanity-checking
that the variable picker shows what you expect. Happy to adjust the
parser if the logger export has a different shape than assumed (e.g. a
title row, multiple sheets, or unit rows).

Also worth double-checking: I backed into `C - 35` being a garden site
sensor label — if it's actually a specific instrument you want labeled
differently on the dashboard, that's a one-line change.

## Backfilling old files

The four `.xlsx` files already sitting in `#tgif` (Feb 24 – Mar 17, 2026)
will get picked up the first time the sync script runs, since it treats
"in the channel but not in the manifest yet" as new.
