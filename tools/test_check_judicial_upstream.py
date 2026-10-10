import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from check_judicial_upstream import BASELINE, COPY, NATIVE, OVERRIDE, SOURCE, body, check


class UpstreamCheckTests(unittest.TestCase):
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
            files = {mod / BASELINE: f'{NATIVE}={{flag=yes}}',
                     game / SOURCE: f'{NATIVE}={{flag=yes}}',
                     mod / OVERRIDE: f'{COPY}={{flag=yes}}'}
            for p, text in files.items():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(check(game, mod), 0)
            for changed_path, key in ((game / SOURCE, NATIVE), (mod / OVERRIDE, COPY)):
                changed_path.write_text(f'{key}={{flag=no}}')
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
