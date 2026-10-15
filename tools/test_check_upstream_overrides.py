import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from check_upstream_overrides import body, check, main, definitions

NATIVE = "sample_override"


class UpstreamCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name) / "game"
        self.mod = Path(self.tmp.name) / "mod"
        self.write(self.mod / "tools/upstream_overrides.json", json.dumps({
            "schema_version": 1, "overrides": [], "known_extensions": []}))

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_check(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = check(self.game, self.mod)
        return result, output.getvalue()

    def test_additive_extension_checks_reviewed_native_baseline(self):
        vanilla = 'common/on_action/council.txt'
        mod = 'common/on_action/tca_council.txt'
        baseline = 'tools/baselines/council.txt'
        self.write(self.game / vanilla, 'on_fired_from_council = { native = yes }')
        self.write(self.mod / baseline, 'on_fired_from_council = { native = yes }')
        self.write(self.mod / mod, 'on_fired_from_council = { on_actions = { tca_callback } }')
        self.write(self.mod / 'tools/upstream_overrides.json', json.dumps({
            'schema_version': 1, 'overrides': [], 'known_extensions': [{
                'key': 'on_fired_from_council', 'vanilla': vanilla,
                'mod': mod, 'baseline': baseline}]}))
        self.assertEqual(self.run_check()[0], 0)
        before = (self.mod / baseline).read_bytes()
        self.write(self.game / vanilla, 'on_fired_from_council = { native = no }')
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn('NEEDS REVIEW', output)
        self.assertEqual((self.mod / baseline).read_bytes(), before)

    def test_auxiliary_extension_checks_native_drift_without_refreshing_baseline(self):
        vanilla = 'common/on_action/game_start.txt'
        adapter = 'tools/cli_adapter/common/on_action/start.txt'
        baseline = 'tools/baselines/start.txt'
        self.write(self.mod / 'common/empty.txt', '')
        self.write(self.game / vanilla, 'on_game_start_after_lobby = { effect = { native = yes } }')
        self.write(self.mod / baseline, 'on_game_start_after_lobby = { effect = { native = yes } }')
        self.write(self.mod / adapter, 'on_game_start_after_lobby = { on_actions = { tca_cli_start } }')
        self.write(self.mod / 'tools/upstream_overrides.json', json.dumps({
            'schema_version': 1, 'overrides': [], 'known_extensions': [],
            'auxiliary_extensions': [{'key': 'on_game_start_after_lobby', 'vanilla': vanilla,
                                      'mod': adapter, 'baseline': baseline}]}))
        self.assertEqual(self.run_check()[0], 0)
        before = (self.mod / baseline).read_bytes()
        self.write(self.game / vanilla, 'on_game_start_after_lobby = { effect = { native = no } }')
        self.assertEqual(self.run_check()[0], 1)
        self.assertEqual((self.mod / baseline).read_bytes(), before)
        self.write(self.mod / adapter, 'tca_cli_start = {}')
        with self.assertRaisesRegex(ValueError, 'auxiliary extension missing'):
            self.run_check()

    def test_unregistered_scalar_override_is_reported(self):
        self.write(self.game / "common/script_values/native.txt", "threshold = 30")
        self.write(self.mod / "common/script_values/mod.txt", "threshold = 80")
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("UNREGISTERED SAME-NAME DEFINITION: threshold", output)

    def test_registered_scalar_baseline_detects_value_and_expression_drift(self):
        vanilla = "common/script_values/native.txt"
        mod = "common/script_values/mod.txt"
        baseline = "tools/baselines/threshold.txt"
        self.write(self.mod / "tools/upstream_overrides.json", json.dumps({
            "schema_version": 1, "overrides": [{"key": "threshold", "vanilla": vanilla,
                "mod": mod, "baseline": baseline}], "known_extensions": []}))
        self.write(self.mod / mod, "threshold = 80")
        for expected, changed in (("30", "31"), ("@[base * 3]", "@[base * 4]")):
            with self.subTest(expected=expected):
                self.write(self.mod / baseline, f"threshold = {expected}")
                self.write(self.game / vanilla, f"threshold = {expected}")
                self.assertEqual(self.run_check()[0], 0)
                self.write(self.game / vanilla, f"threshold = {changed}")
                result, output = self.run_check()
                self.assertEqual(result, 1)
                self.assertIn("NEEDS REVIEW", output)

    def test_inline_math_spacing_and_comments_do_not_change_tokens(self):
        self.assertEqual(definitions("threshold = @[base * (3 + -2)]"),
                         definitions("threshold=@[ base*(3+-2) # note\n]"))
        self.assertNotEqual(definitions("threshold = @[base*3]"),
                            definitions("threshold = @[base*4]"))

    def event_override(self):
        vanilla, mod = "events/native.txt", "events/mod.txt"
        baseline = "tools/baselines/sample_event.txt"
        self.write(self.mod / "tools/upstream_overrides.json", json.dumps({
            "schema_version": 1, "overrides": [{"key": "sample.1", "vanilla": vanilla,
                "mod": mod, "baseline": baseline}], "known_extensions": []}))
        self.write(self.mod / baseline, "sample.1 = { hidden = yes }")
        self.write(self.game / vanilla, "namespace = sample\nnamespace = other\nsample.1 = { hidden = yes }")
        self.write(self.mod / mod, "namespace = sample\nnamespace = other\nsample.1 = { hidden = no }")
        for root in (self.game, self.mod):
            (root / "common").mkdir(exist_ok=True)
        return self.game / vanilla

    def test_registered_event_allows_multiple_namespace_declarations(self):
        source = self.event_override()
        self.assertEqual(self.run_check()[0], 0)
        self.write(source, "namespace = sample\nnamespace = other\nsample.1 = { hidden = no }")
        self.assertEqual(self.run_check()[0], 1)

    def test_registered_event_duplicate_id_remains_an_error(self):
        source = self.event_override()
        self.write(source, source.read_text() + "\nsample.1 = { hidden = yes }")
        with self.assertRaisesRegex(ValueError, "duplicate top-level definition sample.1"):
            self.run_check()

    def test_different_script_types_do_not_collide(self):
        for native_type, mod_type in (("scripted_triggers", "scripted_effects"),
                                      ("subject_contracts/contracts", "subject_contracts/groups")):
            self.write(self.game / f"common/{native_type}/native.txt", "sample = {}")
            self.write(self.mod / f"common/{mod_type}/mod.txt", "sample = {}")
        self.assertEqual(self.run_check()[0], 0)

    def test_same_script_type_in_subdirectories_still_collides(self):
        self.write(self.game / "common/script_values/native.txt", "threshold = 30")
        self.write(self.mod / "common/script_values/subdir/mod.txt", "threshold = 80")
        self.assertEqual(self.run_check()[0], 1)

    def test_file_local_variables_are_not_global_overrides(self):
        self.write(self.game / "common/script_values/native.txt", "@local = 30")
        self.write(self.mod / "common/script_values/mod.txt", "@local = 80")
        self.assertEqual(self.run_check()[0], 0)

    def test_malformed_tokens_fail_instead_of_disappearing(self):
        for script in ('sample = { flag ! = yes }', 'sample = { flag ? = yes }',
                       'sample = { text = "broken }'):
            with self.subTest(script=script), self.assertRaises(ValueError):
                body(script, "sample")
        self.assertEqual(body('sample = { text = "escaped \\\"#{}" }', "sample"),
                         ["text", "=", '"escaped \\\"#{}"'])

    def test_malformed_source_returns_exit_two_with_file_context(self):
        self.write(self.game / "common/script_values/native.txt", "threshold = 30")
        source = self.mod / "common/script_values/mod.txt"
        for script in ('sample = { flag ! = yes }', 'sample = { text = "broken }',
                       'threshold = @[base * 3', 'threshold ='):
            with self.subTest(script=script):
                self.write(source, script)
                error = io.StringIO()
                with contextlib.redirect_stderr(error):
                    result = main(["--game-dir", str(self.game), "--mod-dir", str(self.mod)])
                self.assertEqual(result, 2)
                self.assertIn(str(source), error.getvalue())

    def test_scalar_to_block_change_requires_review(self):
        vanilla = "common/script_values/native.txt"
        mod = "common/script_values/mod.txt"
        baseline = "tools/baselines/threshold.txt"
        self.write(self.mod / "tools/upstream_overrides.json", json.dumps({
            "schema_version": 1, "overrides": [{"key": "threshold", "vanilla": vanilla,
                "mod": mod, "baseline": baseline}], "known_extensions": []}))
        self.write(self.mod / baseline, "threshold = 30")
        self.write(self.game / vanilla, "threshold = { 30 }")
        self.write(self.mod / mod, "threshold = 80")
        self.assertEqual(self.run_check()[0], 1)

    def test_malformed_registry_returns_exit_two(self):
        valid = {"schema_version": 1, "overrides": [], "known_extensions": []}
        malformed = [[], None, dict(valid, overrides=[{}]),
                     dict(valid, overrides=[None]),
                     dict(valid, known_extensions=["invalid"]),
                     dict(valid, known_extensions=[{}]), dict(valid, schema_version=True),
                     dict(valid, schema_version=2), dict(valid, overrides={})]
        entry = {"key": "sample", "vanilla": "common/script_values/native.txt",
                 "mod": "common/script_values/mod.txt", "baseline": "tools/baselines/sample.txt"}
        for field in entry:
            for value in (None, 3, [], "", " "):
                malformed.append(dict(valid, overrides=[dict(entry, **{field: value})]))
        malformed.append(dict(valid, overrides=[dict(entry, native_copy_key=[])]))
        for data in malformed:
            with self.subTest(data=data):
                self.write(self.mod / "tools/upstream_overrides.json", json.dumps(data))
                error = io.StringIO()
                with contextlib.redirect_stderr(error):
                    result = main(["--game-dir", str(self.game), "--mod-dir", str(self.mod)])
                self.assertEqual(result, 2)
                self.assertIn("CHECK FAILED", error.getvalue())

    def test_whitespace_and_comments_do_not_change_script(self):
        a = f'{NATIVE} = {{ flag = yes # old comment\n value = "#{{}}" }}'
        b = f'{NATIVE}={{\n flag=yes\n# new comment\nvalue="#{{}}"\n}}'
        self.assertEqual(body(a, NATIVE), body(b, NATIVE))

    def test_nested_names_are_not_top_level_definitions(self):
        self.assertEqual(body(f'other = {{ {NATIVE} = {{ flag = no }} }}\n{NATIVE} = {{ flag = yes }}', NATIVE),
                         ["flag", "=", "yes"])

    def test_missing_duplicate_and_unbalanced_are_failures(self):
        for text in ("other = {}", f'{NATIVE}={{}}\n{NATIVE}={{}}', f'{NATIVE}={{flag=yes'):
            with self.assertRaises(ValueError):
                body(text, NATIVE)

    def test_operators_and_string_content_are_significant(self):
        self.assertNotEqual(body(f'{NATIVE}={{scope:actor ?= scope:recipient}}', NATIVE),
                            body(f'{NATIVE}={{scope:actor = scope:recipient}}', NATIVE))
        self.assertNotEqual(body(f'{NATIVE}={{text="old"}}', NATIVE),
                            body(f'{NATIVE}={{text="new"}}', NATIVE))

    def test_upstream_and_local_drift_reported_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            game, mod = Path(tmp) / "game", Path(tmp) / "mod"
            baseline = Path("tools/baselines/sample_override.txt")
            vanilla = Path("common/sample_native.txt")
            mod_copy = Path("common/sample_mod.txt")
            files = {mod / baseline: f'{NATIVE}={{flag=yes}}',
                     game / vanilla: f'{NATIVE}={{flag=yes}}',
                     mod / mod_copy: f'{NATIVE}={{added=yes}} sample_native_copy={{flag=yes}}',
                     mod / Path("tools/upstream_overrides.json"): (
                         '{"schema_version":1,"overrides":[{"key":"sample_override",'
                         '"vanilla":"common/sample_native.txt","mod":"common/sample_mod.txt",'
                         '"baseline":"tools/baselines/sample_override.txt",'
                         '"native_copy_key":"sample_native_copy"}],"known_extensions":[]}')}
            for p, text in files.items():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(check(game, mod), 0)
            for changed_path, key in ((game / vanilla, NATIVE), (mod / mod_copy, NATIVE)):
                if changed_path == game / vanilla:
                    changed_path.write_text(f'{key}={{flag=no}}')
                else:
                    changed_path.write_text(f'{NATIVE}={{added=yes}} sample_native_copy={{flag=no}}')
                snapshot = {p: p.read_bytes() for p in files}
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(check(game, mod), 1)
                self.assertIn("NEEDS REVIEW", output.getvalue())
                self.assertEqual(snapshot, {p: p.read_bytes() for p in files})
                changed_path.write_text(files[changed_path])


    def test_all_localization_files_have_utf8_bom(self):
        mod_root = Path(__file__).resolve().parent.parent
        loc_files = list((mod_root / "localization").rglob("*.yml"))
        self.assertGreater(len(loc_files), 0)
        for loc_file in loc_files:
            with self.subTest(file=loc_file.name):
                self.assertTrue(
                    loc_file.read_bytes().startswith(b"\xef\xbb\xbf"),
                    f"Localization file {loc_file} must start with UTF-8 BOM"
                )


if __name__ == "__main__":
    unittest.main()
