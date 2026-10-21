import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from check_upstream_overrides import localization_values, check_localization_overrides


class LocalizationOverrideTests(unittest.TestCase):
    def test_parser_keeps_escaped_quotes_and_versioned_entries(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'loc.yml'
            p.write_text('l_english:\n title:0 "A \\"quote\\"" # note\n alias: "$title$"\n', encoding='utf-8-sig')
            self.assertEqual(localization_values(p), {'title': 'A \\"quote\\"', 'alias': '$title$'})

    def test_duplicate_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'loc.yml'
            p.write_text('x: "a"\nx: "b"\n')
            with self.assertRaises(ValueError):
                localization_values(p)

    def test_native_drift_is_reported_without_refreshing_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'native.yml').write_text('title: "new"\n')
            (root / 'mod.yml').write_text('title: "custom"\n')
            baseline = root / 'base.json'
            baseline.write_text(json.dumps({'title': 'old'}))
            registry = {'localization_overrides': [{'key': 'title', 'vanilla': 'native.yml', 'mod': 'mod.yml', 'baseline': 'base.json'}]}
            before = baseline.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(check_localization_overrides(registry, root, root), 1)
            self.assertEqual(baseline.read_bytes(), before)
            (root / 'native.yml').write_text('title: "old"\n')
            self.assertEqual(check_localization_overrides(registry, root, root), 0)


if __name__ == '__main__':
    unittest.main()
