# TAMU Gardens in Focus — Data Dashboard: project status

## What this is
An interactive GitHub Pages dashboard (`garden-dashboard.html`) for the
`tamu-gardens-timeseries` repo, showing three live/synced data feeds:

1. **White Creek Temperature** — synced from HOBO-logger `.xlsx` files
   posted in Slack `#tgif`, converted to CSV, auto-plotted with a
   variable picker (defaults to the temperature column).
2. **Brazos River** — gage height (falls back to discharge if a site
   isn't reporting stage), live from the USGS Water Data API.
3. **Weather** — live from the NWS station KCLL (Easterwood Field).

Design: clean/minimal, Helvetica-only, white background, sage/sky/gold
category accents. All three charts support scroll/pinch zoom, drag-zoom,
and pan, with a "Reset zoom" control.

## Files (all in `/mnt/user-data/outputs/` as of this session)
```
garden-dashboard.html                     the dashboard page
data/garden/manifest.json                 index of synced sensor files (currently empty)
scripts/sync_garden_data.py               pulls new files from #tgif, converts xlsx->csv
.github/workflows/sync-garden-data.yml    runs the sync script Fridays 11:30pm Central
SETUP.md                                  Slack bot token + deployment setup instructions
```

## Current state / what's still open
- **Not yet deployed** — files need to be committed into the
  `tamu-gardens-timeseries` repo (see SETUP.md for exactly where).
- **No real sensor data synced yet** — `manifest.json` is still empty.
  The four existing HOBO files in `#tgif` (Feb 24 – Mar 17, 2026) haven't
  been pulled in. This needs the `SLACK_BOT_TOKEN` secret set up, then
  either running the GitHub Action manually (Actions tab → Run workflow)
  or waiting for the Friday 11:30pm schedule.
- **Column headers unverified** — the CSV parser auto-detects a
  timestamp column and treats the rest as plottable variables, but this
  hasn't been checked against a real converted file yet. Worth a look
  once the first sync runs.
- River and weather both use official current APIs (not the deprecated
  legacy USGS `waterservices.usgs.gov`, which is mid-decommission).

## Likely next steps
1. Commit files into the repo and confirm GitHub Pages serves the page.
2. Set the `SLACK_BOT_TOKEN` secret, run the sync workflow once, verify
   the White Creek section populates with real data and sane columns.
3. Sanity-check on a phone/small screen.
