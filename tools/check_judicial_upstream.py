#!/usr/bin/env python3
"""Read-only check of the native arrest trigger and our retained copy.

Exit 0: same script tokens; 1: drift needing review; 2: missing/unreadable input.
Comments and formatting are ignored, but quoted strings and operators are not.
The baseline is never refreshed automatically.
"""
import argparse
import difflib
from pathlib import Path
import re
import sys

NATIVE = "imprison_neutral_is_valid_showing_failures_only_triggers_trigger"
COPY = "tca_judicial_arrest_native_common_valid_trigger"
SOURCE = Path("common/scripted_triggers/00_interaction_triggers.txt")
OVERRIDE = Path("common/scripted_triggers/zz_tca_judicial_imprison_permission_triggers.txt")
BASELINE = Path("tools/baselines/imprison_neutral_trigger.txt")
# Lexer first: braces/# in strings cannot become structure/comments.
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\#[^\n]*|\s+|\?=|!=|>=|<=|[{}=<>]|[^\s{}=<>!"#?]+')


def tokens(text):
    return [m.group() for m in TOKEN.finditer(text)
            if not m.group().isspace() and not m.group().startswith("#")]


def body(text, name):
    seq = tokens(text)
    depth = 0
    matches = []
    for i, token in enumerate(seq):
        if depth == 0 and seq[i:i + 3] == [name, "=", "{"]:
            matches.append(i + 2)
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
        if depth < 0:
            raise ValueError("unexpected closing brace")
    if depth:
        raise ValueError("unclosed brace")
    if len(matches) != 1:
        raise ValueError(f"expected one top-level {name}, found {len(matches)}")
    start = matches[0]
    depth = 1
    for i in range(start + 1, len(seq)):
        if seq[i] == "{":
            depth += 1
        elif seq[i] == "}":
            depth -= 1
            if depth == 0:
                return seq[start + 1:i]
    raise ValueError("unclosed trigger")


def render(seq):
    # Stable token lines produce diffs unaffected by source formatting/comments.
    return [token + "\n" for token in seq]


def check(game_dir, mod_dir):
    expected = body((mod_dir / BASELINE).read_text(encoding="utf-8-sig"), NATIVE)
    upstream = body((game_dir / SOURCE).read_text(encoding="utf-8-sig"), NATIVE)
    retained = body((mod_dir / OVERRIDE).read_text(encoding="utf-8-sig"), COPY)
    changed = False
    for label, actual in [("installed-game", upstream), ("mod-native-copy", retained)]:
        if actual != expected:
            changed = True
            print(f"NEEDS REVIEW: {label} differs from the reviewed baseline.")
            print("".join(difflib.unified_diff(render(expected), render(actual),
                                              fromfile="reviewed-baseline", tofile=label)), end="")
    if not changed:
        print("OK: installed native trigger, reviewed baseline, and mod copy match.")
    return int(changed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=Path.home() / "Library/Application Support/Steam/steamapps/common/Crusader Kings III/game",
                        help="directory containing game/common")
    parser.add_argument("--mod-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        return check(args.game_dir, args.mod_dir)
    except (OSError, ValueError) as error:
        print(f"CHECK FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
