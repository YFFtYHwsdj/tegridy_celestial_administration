#!/usr/bin/env python3
"""Inventory common/ objects and event IDs shared by the mod and vanilla.

This read-only scan compares discovery with the manual registry. It does not
read or refresh reviewed baselines. Same-path script files need separate review.
"""
import argparse
import json
from pathlib import Path
import sys

from check_upstream_overrides import ROOT, discover_collisions, load_registry, script_files


def scan(game_dir, mod_dir):
    registry = load_registry(mod_dir)
    classified = {}
    for section, status in (("overrides", "registered_override"),
                            ("known_extensions", "registered_extension")):
        for entry in registry[section]:
            identity = (entry["key"], entry["mod"], entry["vanilla"])
            if identity in classified:
                raise ValueError(f"definition classified more than once: {identity}")
            classified[identity] = status

    collisions = discover_collisions(game_dir, mod_dir)
    objects = [{"key": key, "mod": mod, "vanilla": vanilla,
                "status": classified.get((key, mod, vanilla), "unregistered")}
               for key, mod, vanilla in sorted(collisions)]
    stale = [{"key": key, "mod": mod, "vanilla": vanilla,
              "status": classified[(key, mod, vanilla)]}
             for key, mod, vanilla in sorted(set(classified) - collisions)]
    same_path_files = [path.relative_to(mod_dir).as_posix()
                       for path in script_files(mod_dir)
                       if (game_dir / path.relative_to(mod_dir)).is_file()]
    counts = {status: sum(item["status"] == status for item in objects)
              for status in ("registered_override", "registered_extension", "unregistered")}
    counts["stale_registration"] = len(stale)
    counts["same_path_files"] = len(same_path_files)
    return {"scope": ["common/**/*.txt", "events/**/*.txt"], "counts": counts,
            "objects": objects, "stale_registrations": stale,
            "same_path_files": same_path_files}


def print_report(report):
    print("SCAN SCOPE: common/**/*.txt and events/**/*.txt; reviewed baselines are not checked.")
    labels = {"registered_override": "REGISTERED OVERRIDE",
              "registered_extension": "REGISTERED EXTENSION", "unregistered": "UNREGISTERED"}
    for item in report["objects"]:
        print(f"{labels[item['status']]}: {item['key']}: "
              f"mod/{item['mod']} <> game/{item['vanilla']}")
    for item in report["stale_registrations"]:
        print(f"STALE REGISTRATION: {item['key']}: "
              f"mod/{item['mod']} <> game/{item['vanilla']}")
    for path in report["same_path_files"]:
        print(f"SAME-PATH FILE (review whole-file replacement separately): {path}")
    counts = report["counts"]
    print(f"SUMMARY: {counts['registered_override']} registered overrides; "
          f"{counts['registered_extension']} registered extensions; "
          f"{counts['unregistered']} unregistered definitions; "
          f"{counts['stale_registration']} stale registrations; "
          f"{counts['same_path_files']} same-path script files.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path,
                        default=Path.home() / "Library/Application Support/Steam/steamapps/common/Crusader Kings III/game")
    parser.add_argument("--mod-dir", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", help="print a machine-readable inventory")
    args = parser.parse_args(argv)
    try:
        report = scan(args.game_dir, args.mod_dir)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"SCAN FAILED: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    counts = report["counts"]
    return int(bool(counts["unregistered"] or counts["stale_registration"] or counts["same_path_files"]))


if __name__ == "__main__":
    sys.exit(main())
