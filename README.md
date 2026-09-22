# plaud-project-migration

Extract your [Plaud](https://plaud.ai) recording-to-project groupings before they get lost.

Plaud is replacing its current organisation model with a "Knowledge Base" organised by **Time** and
**Events** (rolling out from 12 October 2026). The announcement promises your recordings survive —
it never promises your existing **Projects** groupings do. Read the FAQ carefully:

> *"I had recordings organized by folder or saved to a specific device. What happens to that
> structure?"* → *"The new Knowledge base organizes everything by time and by Events. Your existing
> recordings are accessible through the Time view, and you can create Events to group related
> conversations, clients, or projects **going forward**."*

"Going forward" means: you rebuild it by hand, unless you get the grouping data out first.

## Why a HAR capture

No documented Plaud interface exposes which project a recording belongs to — not the official API,
not the official CLI, not the MCP server. All three return recordings and transcripts fine, with no
folder/project/tag field anywhere.

The Plaud **web app** knows it, though — it has to, to render your sidebar. Its own network calls
expose it in full, via two endpoints it doesn't publish anywhere:

- `GET /file/simple/web` — every recording (active and trashed), each carrying a `filetag_id_list`
  field.
- `GET /filetag/` — the id → project name mapping for that list.

A browser HAR capture of a normal page load contains both. This script finds them and combines them
into one JSON, grouped by project.

## Step 1 — capture a HAR

1. Open a desktop browser, log into the Plaud web app.
2. Open DevTools (`F12`) → **Network** tab, filter to **Fetch/XHR** — **do this before you load or
   reload the page**. Starting the capture after the page has already loaded is the single most
   common way this goes wrong: it looks fine (you'll see some requests) but silently misses the two
   you need. Tick **Preserve log** too if your browser offers it — it isn't always required, but it
   costs nothing and guards against the log clearing on reload.
3. Reload the page. You do **not** need to click into individual projects — one page load fetches
   everything.
4. Save the requests as a HAR **with response bodies included**. The exact menu wording differs by
   browser:
   - **Chrome / Edge**: right-click the request list → **Save all as HAR with content**. Use the
     *with content* variant specifically — the plain "Save all as HAR" option drops response bodies
     and the file is useless for this.
   - **Firefox**: right-click → **Save All As HAR**. Firefox only has the one option and it already
     includes response bodies.

**Credential warning:** a HAR captures request headers, so the saved file contains your live Plaud
auth token. Delete it once you've run the script below — don't commit it or leave it in a synced
folder. (This repo's `.gitignore` already excludes `*.har`.)

If you'd rather not do this by hand: paste these steps to your AI assistant and ask it to walk you
through the capture and run the script for you. If your assistant has browser/computer-use
capability, it may be able to drive the capture itself.

## Step 2 — run the script

No dependencies — just Python 3.9+.

```bash
python3 plaud_migration.py your-capture.har
```

Or ask your AI coding assistant to run it for you.

Options:

```
plaud_migration.py [-h] [-o OUTPUT] [--untagged-label UNTAGGED_LABEL] har_file

  -o, --output OUTPUT         Output JSON path (default: plaud-migration.json)
  --untagged-label LABEL      Group name for recordings with no project (default: Unorganised)
```

## Step 3 — sample output

```json
{
  "captured_from": "your-capture.har",
  "total_recordings": 5,
  "total_active": 4,
  "total_trash": 1,
  "orphan_tag_ids": [],
  "projects": {
    "Client Calls": [
      {
        "id": "a1b2c3d4",
        "name": "09-02 Kickoff: Q3 Roadmap",
        "start_time": "2026-09-02T09:15:00+00:00",
        "duration_seconds": 1820,
        "is_trash": false
      },
      {
        "id": "e5f6a7b8",
        "name": "09-10 Follow-up: Contract Terms",
        "start_time": "2026-09-10T14:02:00+00:00",
        "duration_seconds": 640,
        "is_trash": false
      }
    ],
    "Personal Journal": [
      {
        "id": "c9d0e1f2",
        "name": "09-05 Evening Notes",
        "start_time": "2026-09-05T21:40:00+00:00",
        "duration_seconds": 210,
        "is_trash": false
      },
      {
        "id": "b3c4d5e6",
        "name": "08-28 Old Draft",
        "start_time": "2026-08-28T11:05:00+00:00",
        "duration_seconds": 95,
        "is_trash": true
      }
    ],
    "Unorganised": [
      {
        "id": "f7a8b9c0",
        "name": "Untitled Recording",
        "start_time": "2026-09-15T08:00:00+00:00",
        "duration_seconds": 45,
        "is_trash": false
      }
    ]
  }
}
```

Recordings with no project tag land in `"Unorganised"` (or whatever `--untagged-label` you pass) —
in the new Knowledge Base these were always going to fall back to the Timeline view anyway, so
there's nothing to preserve for them beyond what's already here.

## What's next

This repo currently only covers **extracting** your existing structure before it's at risk. A
second piece — reimporting or rebuilding a similar grouping on the new Knowledge Base side — will
follow once Plaud's new Events/Knowledge Base structure is actually understood. Check back.

## License

MIT — see [LICENSE](LICENSE).
