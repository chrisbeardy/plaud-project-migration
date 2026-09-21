#!/usr/bin/env python3
"""
Extract Plaud recording <-> project membership from a browser HAR capture.

No Plaud interface (official API, CLI, or MCP server) exposes which project/folder
a recording belongs to. The Plaud web app's own network calls do, via two endpoints:

    GET /file/simple/web   -- every recording, each carrying a filetag_id_list
    GET /filetag/          -- id -> project/tag name mapping

This script finds both responses inside a HAR file and combines them into a single
JSON grouped by project, so the grouping survives even where no export/API does.
See README.md for how to capture the HAR.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse


def find_json_response(entries, path_suffix, pick="last"):
    """Return the parsed JSON body of the GET response whose URL path ends with
    path_suffix. If the endpoint was captured more than once (e.g. re-fired on
    every UI interaction), pick="last" takes the most recent capture and
    pick="most_entries" takes whichever response contains the most items under
    a *_list key -- used for the file-list endpoint, where a stray early/partial
    capture could otherwise win just by being the last one in the HAR.
    """
    candidates = []
    for entry in entries:
        req, resp = entry["request"], entry["response"]
        if req["method"] != "GET" or resp["status"] != 200:
            continue
        if urlparse(req["url"]).path.rstrip("/") != path_suffix.rstrip("/"):
            continue
        text = resp.get("content", {}).get("text")
        if not text:
            continue
        try:
            candidates.append(json.loads(text))
        except json.JSONDecodeError:
            continue

    if not candidates:
        return None
    if pick == "most_entries":
        def item_count(data):
            for value in data.values():
                if isinstance(value, list):
                    return len(value)
            return 0
        return max(candidates, key=item_count)
    return candidates[-1]


def build_migration_data(har, untagged_label):
    entries = har["log"]["entries"]

    files_data = find_json_response(entries, "/file/simple/web", pick="most_entries")
    tags_data = find_json_response(entries, "/filetag/", pick="last")

    missing = []
    if files_data is None:
        missing.append("/file/simple/web")
    if tags_data is None:
        missing.append("/filetag/")
    if missing:
        raise SystemExit(
            "Could not find the following endpoint(s) in this HAR: "
            + ", ".join(missing)
            + "\nThis usually means the capture was started after the page had already "
            "loaded, or was saved before the page finished loading. See README.md step 1 "
            "and try again: open DevTools with Preserve Log ticked *before* loading the "
            "page, then reload."
        )

    tag_map = {t["id"]: t["name"] for t in tags_data["data_filetag_list"]}
    files = files_data["data_file_list"]

    projects = {name: [] for name in tag_map.values()}
    projects[untagged_label] = []

    orphan_tags = set()

    for f in files:
        tags = f.get("filetag_id_list") or []
        start_iso = datetime.fromtimestamp(f["start_time"] / 1000, tz=timezone.utc).isoformat()
        record = {
            "id": f["id"],
            "name": f["filename"],
            "start_time": start_iso,
            "duration_seconds": round(f["duration"] / 1000),
            "is_trash": bool(f["is_trash"]),
        }

        if not tags:
            projects[untagged_label].append(record)
            continue

        for tag_id in tags:
            project_name = tag_map.get(tag_id)
            if project_name is None:
                orphan_tags.add(tag_id)
                project_name = untagged_label
            projects.setdefault(project_name, []).append(record)

    for name in projects:
        projects[name].sort(key=lambda r: r["start_time"])

    return {
        "captured_from": None,  # filled in by caller with the HAR filename
        "total_recordings": len(files),
        "total_active": sum(1 for f in files if not f["is_trash"]),
        "total_trash": sum(1 for f in files if f["is_trash"]),
        "orphan_tag_ids": sorted(orphan_tags),
        "projects": projects,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract Plaud recording/project groupings from a HAR capture."
    )
    parser.add_argument("har_file", help="Path to the HAR file (see README.md to capture one)")
    parser.add_argument(
        "-o", "--output", default="plaud-migration.json",
        help="Output JSON path (default: plaud-migration.json)",
    )
    parser.add_argument(
        "--untagged-label", default="Unorganised",
        help="Group name for recordings with no project/tag (default: Unorganised)",
    )
    args = parser.parse_args()

    with open(args.har_file) as f:
        har = json.load(f)

    output = build_migration_data(har, args.untagged_label)
    output["captured_from"] = args.har_file

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {args.output}")
    print(
        f"Total recordings: {output['total_recordings']} "
        f"(active {output['total_active']}, trash {output['total_trash']})"
    )
    print(f"Projects: {len(output['projects'])}")
    for name, recs in sorted(output["projects"].items(), key=lambda kv: -len(kv[1])):
        active = sum(1 for r in recs if not r["is_trash"])
        trash = sum(1 for r in recs if r["is_trash"])
        print(f"  {name}: {len(recs)} (active {active}, trash {trash})")
    if output["orphan_tag_ids"]:
        print(
            "WARNING: recordings referenced tag IDs not present in /filetag/:",
            output["orphan_tag_ids"],
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
