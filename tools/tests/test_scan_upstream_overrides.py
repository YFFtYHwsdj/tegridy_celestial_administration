"""独立于审阅基线文件的发现／登记覆盖检查。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scan_upstream_overrides import main, scan


class CoverageScanTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.game = Path(tmp.name) / "game"
        self.mod = Path(tmp.name) / "mod"
        for root in (self.game, self.mod):
            (root / "common").mkdir(parents=True)
        self.registry = {"schema_version": 1, "overrides": [], "known_extensions": []}
        self.save_registry()

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def save_registry(self):
        self.write(self.mod / "tools/upstream_overrides.json", json.dumps(self.registry))

    def run_cli(self, *extra):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(["--game-dir", str(self.game), "--mod-dir", str(self.mod), *extra])
        return code, output.getvalue(), error.getvalue()

    def test_inventory_is_independent_of_missing_baselines_and_read_only(self):
        native, mod = "common/script_values/native.txt", "common/script_values/mod.txt"
        self.write(self.game / native, "threshold = 30")
        self.write(self.mod / mod, "threshold = 80")
        self.registry["overrides"].append({"key": "threshold", "vanilla": native,
            "mod": mod, "baseline": "tools/baselines/missing.txt"})
        self.save_registry()
        snapshot = {p: p.read_bytes() for root in (self.game, self.mod)
                    for p in root.rglob("*") if p.is_file()}
        code, output, error = self.run_cli("--json")
        self.assertEqual(code, 0, error)
        report = json.loads(output)
        self.assertEqual(report["counts"]["registered_override"], 1)
        self.assertEqual(report["objects"][0]["status"], "registered_override")
        after = {p: p.read_bytes() for root in (self.game, self.mod)
                 for p in root.rglob("*") if p.is_file()}
        self.assertEqual(after, snapshot)

    def test_unregistered_events_detected_without_namespace_metadata_collisions(self):
        self.write(self.game / "events/native.txt", 'namespace = sample\nsample.1 = { type = character_event }')
        self.write(self.mod / "events/mod.txt", 'namespace = sample\nsample.1 = { type = character_event hidden = yes }\nsample.2 = {}')
        code, output, error = self.run_cli()
        self.assertEqual(code, 1, error)
        self.assertIn("UNREGISTERED: sample.1", output)
        self.assertNotIn("UNREGISTERED: namespace", output)
        self.assertNotIn("UNREGISTERED: sample.2", output)

    def test_registered_extension_and_stale_registration_are_distinguished(self):
        native, mod = "common/on_action/native.txt", "common/on_action/mod.txt"
        self.write(self.game / native, "on_death = {}")
        self.write(self.mod / mod, "on_death = { on_actions = { tca_callback } }")
        self.registry["known_extensions"] = [
            {"key": key, "vanilla": native, "mod": mod} for key in ("on_death", "on_missing")]
        self.save_registry()
        code, output, error = self.run_cli("--json")
        self.assertEqual(code, 1, error)
        report = json.loads(output)
        self.assertEqual(report["counts"]["registered_extension"], 1)
        self.assertEqual(report["counts"]["unregistered"], 0)
        self.assertEqual(report["stale_registrations"][0]["key"], "on_missing")

    def test_same_path_file_warns_even_when_no_definition_ids_overlap(self):
        path = "common/script_values/replaced.txt"
        self.write(self.game / path, "original = 30")
        self.write(self.mod / path, "tca_added = 80")
        code, output, error = self.run_cli("--json")
        self.assertEqual(code, 1, error)
        report = json.loads(output)
        self.assertEqual(report["counts"]["unregistered"], 0)
        self.assertEqual(report["same_path_files"], [path])

    def test_bad_directory_and_duplicate_registry_exit_two(self):
        (self.game / "common").rmdir()
        code, output, error = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("missing script directory", error)
        (self.game / "common").mkdir()
        entry = {"key": "sample", "vanilla": "common/script_values/native.txt",
                 "mod": "common/script_values/mod.txt", "baseline": "tools/baselines/sample.txt"}
        self.registry["overrides"] = [entry, entry]
        self.save_registry()
        code, output, error = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("classified more than once", error)


if __name__ == "__main__":
    unittest.main()
