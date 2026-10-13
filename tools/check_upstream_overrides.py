#!/usr/bin/env python3
"""Read-only drift check for reviewed CK3 vanilla object overrides.

The registry explicitly lists replaced vanilla objects and same-name additive
on_action extensions. Reviewed baselines are never refreshed automatically.
"""
import argparse
import difflib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = Path("tools/upstream_overrides.json")
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\#[^\n]*|\s+|\?=|!=|>=|<=|@\[|[{}\[\]=<>]|[^\s{}\[\]=<>!"#?]+')
MATH_TOKEN = re.compile(r'\#[^\n]*|\s+|@\[|[+\-*/%^(),\[\]]|[^\s+\-*/%^(),\[\]{}=<>!"#?]+')


def tokens(text):
    """Return tokens without silently skipping malformed quotes or operators."""
    result = []
    end = 0
    math_depth = 0
    while end < len(text):
        match = (MATH_TOKEN if math_depth else TOKEN).match(text, end)
        if match is None:
            line = text.count("\n", 0, end) + 1
            raise ValueError(f"invalid token at line {line}: {text[end:end + 30]!r}")
        token = match.group()
        if token == "@[" or (math_depth and token == "["):
            math_depth += 1
        elif math_depth and token == "]":
            math_depth -= 1
        if not token.isspace() and not token.startswith("#"):
            result.append(token)
        end = match.end()
    if math_depth:
        raise ValueError("unclosed inline expression")
    return result


def definitions(text, allow_duplicates=False, ignored_keys=()):
    """Extract complete RHS tokens for top-level blocks, scalars and expressions."""
    seq = tokens(text)
    found = {}
    i = 0
    depth = 0
    while i < len(seq):
        if depth == 0 and i + 1 < len(seq) and seq[i + 1] == "=":
            name = seq[i]
            if name in found and not allow_duplicates:
                raise ValueError(f"duplicate top-level definition {name}")
            start = i + 2
            if start == len(seq) or seq[start] in ("}", "=", "!=", "?=", ">", "<", ">=", "<="):
                raise ValueError(f"missing value for definition {name}")
            end = start + 1
            if seq[start] in ("{", "@["):
                openings = ("{",) if seq[start] == "{" else ("[", "@[")
                closing = "}" if seq[start] == "{" else "]"
                nested = 1
                while end < len(seq) and nested:
                    if seq[end] in openings:
                        nested += 1
                    elif seq[end] == closing:
                        nested -= 1
                    end += 1
                if nested:
                    raise ValueError(f"unclosed definition {name}")
            if name not in ignored_keys:
                found[name] = seq[start:end]
            i = end
            continue
        if seq[i] == "{":
            depth += 1
        elif seq[i] == "}":
            depth -= 1
            if depth < 0:
                raise ValueError("unexpected closing brace")
        i += 1
    if depth:
        raise ValueError("unbalanced braces")
    return found


def body(text, name):
    """Extract block contents for parser unit tests."""
    parsed = definitions(text)
    if name not in parsed:
        raise ValueError(f"expected top-level {name}, found none")
    value = parsed[name]
    if value[0] != "{" or value[-1] != "}":
        raise ValueError(f"expected block definition {name}")
    return value[1:-1]


def load_registry(mod_dir):
    data = json.loads((mod_dir / REGISTRY).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("registry must be a JSON object")
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported upstream override registry schema")
    if not isinstance(data.get("overrides"), list) or not isinstance(data.get("known_extensions"), list):
        raise ValueError("registry must contain overrides and known_extensions lists")
    if not isinstance(data.get("localization_overrides", []), list):
        raise ValueError("localization_overrides must be a list")
    if not isinstance(data.get("auxiliary_extensions", []), list):
        raise ValueError("auxiliary_extensions must be a list")
    for section in ("overrides", "known_extensions", "localization_overrides", "auxiliary_extensions"):
        required = ("key", "mod", "vanilla", "baseline") if section in ("overrides", "localization_overrides", "auxiliary_extensions") else ("key", "mod", "vanilla")
        for index, entry in enumerate(data.get(section, [])):
            label = f"{section}[{index}]"
            if not isinstance(entry, dict):
                raise ValueError(f"{label} must be an object")
            for field in required + ("native_copy_key", "reason"):
                if field not in required and field not in entry:
                    continue
                value = entry.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{label}.{field} must be a non-empty string")
    return data


def read_definitions(path, allow_duplicates=False, ignored_keys=()):
    try:
        return definitions(path.read_text(encoding="utf-8-sig"),
                           allow_duplicates=allow_duplicates, ignored_keys=ignored_keys)
    except ValueError as error:
        raise ValueError(f"{path}: {error}") from error


def script_type(relative_path):
    """Keep event IDs separate from common/ object types and their subfolders."""
    if relative_path.parts[0] == "events":
        return ("events",)
    directories = relative_path.parts[1:-1]
    # The native .info files define contract groups and obligations separately.
    category = directories[:2] if directories[:1] == ("subject_contracts",) else directories[:1]
    return ("common",) + category


def script_files(root):
    """Scan supported script roots, failing if the required common/ root is absent."""
    if not (root / "common").is_dir():
        raise ValueError(f"missing script directory: {root / 'common'}")
    return sorted(path for directory in ("common", "events")
                  for path in (root / directory).rglob("*.txt"))


def global_keys(path, relative_path):
    for key in read_definitions(path, allow_duplicates=True):
        if key.startswith("@") or (relative_path.parts[0] == "events" and key == "namespace"):
            continue
        yield key


def discover_collisions(game_dir, mod_dir):
    """Find same-named top-level definitions in mod and installed game scripts."""
    native_by_key = {}
    for path in script_files(game_dir):
        relative = path.relative_to(game_dir)
        for key in global_keys(path, relative):
            native_by_key.setdefault((script_type(relative), key), []).append(relative.as_posix())

    collisions = set()
    for path in script_files(mod_dir):
        relative = path.relative_to(mod_dir)
        for key in global_keys(path, relative):
            for native_path in native_by_key.get((script_type(relative), key), []):
                collisions.add((key, relative.as_posix(), native_path))
    return collisions


def _entry_identity(entry):
    return (entry["key"], entry["mod"], entry["vanilla"])


def entry_definitions(entry, path):
    # Multiple namespace declarations are valid metadata, not duplicate events.
    ignored = ("namespace",) if Path(entry["vanilla"]).parts[:1] == ("events",) else ()
    return read_definitions(path, ignored_keys=ignored)


def _compare_entry(entry, label, expected, source_path, definition_key):
    actual = entry_definitions(entry, source_path).get(definition_key)
    if actual is None:
        raise ValueError(f"{label}: missing top-level {definition_key} in {source_path}")
    if actual != expected:
        print(f"NEEDS REVIEW: {label} differs from its reviewed baseline.")
        print("".join(difflib.unified_diff(
            [f"{token}\n" for token in expected], [f"{token}\n" for token in actual],
            fromfile="reviewed-baseline", tofile=label)), end="")
        return 1
    return 0


def localization_values(path):
    """Read quoted localization entries, preserving literal escapes for drift checks."""
    result = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r'^\s*([A-Za-z0-9_]+):(?:\d+)?\s*"((?:\\.|[^"\\])*)"\s*(?:#.*)?$', line)
        if match:
            if match[1] in result:
                raise ValueError(f"duplicate localization key {match[1]} in {path}")
            result[match[1]] = match[2]
    return result


def check_localization_overrides(registry, game_dir, mod_dir):
    changed = 0
    for entry in registry.get("localization_overrides", []):
        baseline = json.loads((mod_dir / entry["baseline"]).read_text(encoding="utf-8"))
        key = entry["key"]
        if key not in baseline:
            raise ValueError(f"localization baseline missing {key}")
        native = localization_values(game_dir / entry["vanilla"])
        if native.get(key) != baseline[key]:
            print(f"NEEDS REVIEW: installed-game localization {key} differs from its reviewed baseline.")
            changed = 1
        replacement = localization_values(mod_dir / entry["mod"])
        if key not in replacement:
            raise ValueError(f"mod localization override missing {key}")
    return changed


def check(game_dir, mod_dir):
    registry = load_registry(mod_dir)
    known = {}
    changed = check_localization_overrides(registry, game_dir, mod_dir)
    # Separate opt-in adapter mods live under tools/, outside the normal mod roots.
    # Check their registered native callbacks and reviewed baselines explicitly.
    for entry in registry.get("auxiliary_extensions", []):
        baseline = entry_definitions(entry, mod_dir / entry["baseline"]).get(entry["key"])
        if baseline is None:
            raise ValueError(f"auxiliary baseline missing {entry['key']}")
        changed |= _compare_entry(entry, f"installed-game:{entry['key']}", baseline,
                                  game_dir / entry["vanilla"], entry["key"])
        if entry["key"] not in read_definitions(mod_dir / entry["mod"], allow_duplicates=True):
            raise ValueError(f"auxiliary extension missing {entry['key']}")
    for entry in registry["overrides"]:
        identity = _entry_identity(entry)
        if identity in known:
            raise ValueError(f"duplicate registry entry: {identity}")
        known[identity] = "override"
        baseline_path = mod_dir / entry["baseline"]
        baseline = entry_definitions(entry, baseline_path).get(entry["key"])
        if baseline is None:
            raise ValueError(f"baseline {baseline_path} has no top-level {entry['key']}")
        native_path = game_dir / entry["vanilla"]
        changed |= _compare_entry(entry, f"installed-game:{entry['key']}", baseline,
                                  native_path, entry["key"])
        mod_path = mod_dir / entry["mod"]
        mod_definitions = entry_definitions(entry, mod_path)
        if entry["key"] not in mod_definitions:
            raise ValueError(f"mod override {entry['key']} is missing from {mod_path}")
        # Some overrides retain an unmodified native helper under a separate
        # tca_* ID. Compare that helper to the vanilla baseline when declared.
        native_copy_key = entry.get("native_copy_key")
        if native_copy_key:
            changed |= _compare_entry(entry, f"mod-native-copy:{native_copy_key}", baseline,
                                      mod_path, native_copy_key)

    for entry in registry["known_extensions"]:
        identity = _entry_identity(entry)
        if identity in known:
            raise ValueError(f"definition classified more than once: {identity}")
        known[identity] = "extension"
        for label, path in (("installed-game", game_dir / entry["vanilla"]),
                            ("mod-extension", mod_dir / entry["mod"])):
            if entry["key"] not in read_definitions(path, allow_duplicates=True):
                print(f"NEEDS REVIEW: {label} definition {entry['key']} is missing from {path}")
                changed = 1

    collisions = discover_collisions(game_dir, mod_dir)
    unclassified = collisions - set(known)
    if unclassified:
        changed = 1
        for key, mod_path, vanilla_path in sorted(unclassified):
            print(f"UNREGISTERED SAME-NAME DEFINITION: {key}: mod/{mod_path} <> game/{vanilla_path}")

    if not changed:
        print(f"OK: {len(registry['overrides'])} vanilla overrides match reviewed baselines; "
              f"{len(registry['known_extensions'])} additive on_action definitions are classified; "
              f"{len(registry.get('localization_overrides', []))} localization overrides checked; "
              f"{len(registry.get('auxiliary_extensions', []))} auxiliary extensions checked; "
              "no unregistered same-name definitions found.")
    return int(bool(changed))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path,
                        default=Path.home() / "Library/Application Support/Steam/steamapps/common/Crusader Kings III/game",
                        help="directory containing common/")
    parser.add_argument("--mod-dir", type=Path, default=ROOT,
                        help="mod root containing tools/upstream_overrides.json")
    args = parser.parse_args(argv)
    try:
        return check(args.game_dir, args.mod_dir)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(f"CHECK FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
