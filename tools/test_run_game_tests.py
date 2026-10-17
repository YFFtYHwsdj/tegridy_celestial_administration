"""启动隔离及结果测试，不模拟 CK3 规则。"""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

from run_game_tests import (ROOT, game_command, descriptor, isolated_settings, outcome, prepare_run,
                            progress, selected_stage, stop_owned_process, terminal_condition)
from check_upstream_overrides import definitions


class GameRunnerTests(unittest.TestCase):
    def test_native_seed_is_optional_and_preserves_isolated_command(self):
        args = SimpleNamespace(game_dir=Path('/tmp/game with spaces'), seed=None)
        default = game_command(args, Path('/tmp/run with spaces'))
        self.assertFalse(any(arg.startswith('-random_seed=') for arg in default))
        self.assertIn('-userdir=/tmp/run with spaces/', default)
        self.assertIn('-bookmark=bm_1066_china', default)
        args.seed = 2878361204
        self.assertEqual(game_command(args, Path('/tmp/run with spaces')), default + ['-random_seed=2878361204'])

    def test_native_seed_bounds_are_checked_before_launch(self):
        for seed in (-1, 4294967296):
            with self.assertRaises(ValueError):
                game_command(SimpleNamespace(game_dir=Path('/tmp/game'), seed=seed), Path('/tmp/run'))
        for seed in (0, 4294967295):
            self.assertIn(f'-random_seed={seed}', game_command(SimpleNamespace(game_dir=Path('/tmp/game'), seed=seed), Path('/tmp/run')))

    def test_focused_run_selects_registered_event_and_only_changes_adapter_copy(self):
        source = ROOT / 'tools/cli_adapter/events/tca_cli_events.txt'
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp) / 'absent', 'tca_judicial_imperial_test.1')
            selection = json.loads((run / 'selection.json').read_text())
            self.assertEqual(selection, {'case': 'tca_judicial_imperial_test.1', 'stage': '1022'})
            copied = (run / 'mod/tca_cli_adapter/events/tca_cli_events.txt').read_text(encoding='utf-8-sig')
            self.assertIn('tca_run_focused_observer_test_effect = { STAGE = 1022 }', copied)
            self.assertNotIn('tca_run_observer_tests_effect = yes', copied)
        self.assertEqual(source.read_bytes(), original)

    def test_run_uses_immutable_runtime_snapshot_with_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / 'repo'
            (repo / 'events').mkdir(parents=True)
            (repo / 'tools/cli_adapter/events').mkdir(parents=True)
            source = repo / 'events/tca_fixture_events.txt'
            source.write_text('original')
            run = prepare_run(repo, Path(temp) / 'runs', Path(temp) / 'absent')
            snapshot = run / 'mod/tca_main'
            self.assertEqual((snapshot / 'events/tca_fixture_events.txt').read_text(), 'original')
            source.write_text('changed after preparation')
            self.assertEqual((snapshot / 'events/tca_fixture_events.txt').read_text(), 'original')
            self.assertIn(str(snapshot), (run / 'mod/tca_main.mod').read_text())
            manifest = json.loads((run / 'source_manifest.json').read_text())
            self.assertIn('events/tca_fixture_events.txt', manifest['files'])
            self.assertEqual(len(manifest['sha256']), 64)

    def test_identical_content_has_same_digest_in_different_run_dirs(self):
        with tempfile.TemporaryDirectory() as temp:
            a = prepare_run(ROOT, Path(temp), Path(temp)/'absent')
            b = prepare_run(ROOT, Path(temp), Path(temp)/'absent')
            self.assertEqual(json.loads((a/'source_manifest.json').read_text())['sha256'],
                             json.loads((b/'source_manifest.json').read_text())['sha256'])

    def test_seal_rejects_modified_deleted_and_added_runtime_files(self):
        from run_game_tests import seal_run, verify_snapshot
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp) / 'absent')
            target = run / 'mod/tca_main/events/tca_tongpan_test_events.txt'
            self.assertEqual(verify_snapshot(run), [])
            target.write_text('tampered')
            self.assertTrue(verify_snapshot(run))
            seal_run(run)
            target.unlink()
            self.assertTrue(verify_snapshot(run))
            seal_run(run)
            target.write_text('added')
            self.assertTrue(verify_snapshot(run))

    def test_focused_run_rejects_unknown_and_continuation_events(self):
        for entry in ('not_an_event', 'tca_judicial_imperial_test.1005'):
            with self.assertRaises(ValueError):
                selected_stage(ROOT, entry)

    def test_adapter_does_not_override_native_prison_interactions(self):
        adapter = ROOT / 'tools/cli_adapter'
        self.assertFalse(list((adapter / 'common/character_interactions').glob('*.txt')))
        self.assertNotIn('tca_cli_arrest_isolated', (adapter / 'events/tca_cli_events.txt').read_text(encoding='utf-8-sig'))

    def test_each_run_has_fresh_logs_and_adapter_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = prepare_run(ROOT, root, root / 'absent-settings')
            (first / 'logs').mkdir()
            (first / 'logs/debug.log').write_text('TCA_TEST SUITE_ALL_PASSED')
            second = prepare_run(ROOT, root, root / 'absent-settings')
            self.assertNotEqual(first, second)
            self.assertFalse((second / 'logs').exists())
            self.assertEqual(json.loads((root / 'latest.json').read_text())['run_dir'], str(second))
            mods = json.loads((second / 'dlc_load.json').read_text())['enabled_mods']
            self.assertEqual(mods, ['mod/tca_main.mod', 'mod/tca_cli_adapter.mod'])
            self.assertIn(str(second / 'mod/tca_main'), (second / 'mod/tca_main.mod').read_text())
            self.assertIn(str(second), (second / 'mod/tca_cli_adapter.mod').read_text())
            self.assertTrue((second / 'mod/tca_cli_adapter/events/tca_cli_events.txt').is_file())

    def test_settings_do_not_copy_account_and_disable_cloud_in_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'settings.txt'
            original = ('"Account"={ secret="private" } '
                        '"game"={ "cloud_save"={version=0 enabled=yes} "autosave"={value="YEARLY"} } '
                        '"Graphics"={ "display_mode"={value="fullscreen"} "device"={value="GPU"} }')
            source.write_text(original)
            text = isolated_settings(source)
            self.assertNotIn('private', text)
            self.assertNotIn('fullscreen', text)
            self.assertIn('GPU', text)
            self.assertIn('enabled = no', text)
            self.assertEqual(text.count('"cloud_save"'), 1)
            self.assertEqual(source.read_text(), original)
            self.assertEqual(set(definitions(text)), {'"game"', '"Graphics"'})

    def test_engine_errors_and_incomplete_runs_never_report_success(self):
        self.assertEqual(outcome('summary', True, 0), 0)
        self.assertEqual(outcome('summary', True, 1), 1)
        self.assertEqual(outcome('summary', False, 0), 2)
        for condition in ('timeout', 'process_exit', 'interrupted', 'not_observer', 'entry_rejected'):
            self.assertEqual(outcome(condition, True, 0), 2)
        self.assertEqual(terminal_condition('TCA_TEST OBSERVER_ENTRY_REJECTED focused world invalid', None), 'entry_rejected')
        self.assertIsNone(terminal_condition('TCA_TEST PASS example', None))
        self.assertEqual(terminal_condition('TCA_TEST SUITE_ABORTED death', None), 'summary')
        self.assertEqual(terminal_condition('', 0), 'process_exit')

    def test_observer_confirmation_requires_console_success(self):
        self.assertFalse(progress('Running console command: observe', 2, True)['observer_confirmed'])
        state = progress('console_success: Going to observe mode\nTCA_TEST PASS a', 2, False)
        self.assertTrue(state['observer_confirmed'])
        self.assertEqual(state['pass_count'], 1)
        self.assertFalse(state['running'])

    def test_cleanup_targets_only_owned_child_and_falls_back_to_kill(self):
        child = Mock()
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired('ck3', 6), -9]
        stop_owned_process(child)
        child.terminate.assert_called_once_with()
        child.kill.assert_called_once_with()
        self.assertEqual(child.wait.call_count, 2)
        exited = Mock()
        exited.poll.return_value = 0
        stop_owned_process(exited)
        exited.terminate.assert_not_called()

    def test_paths_with_spaces_are_preserved_and_quotes_rejected(self):
        self.assertIn('path="/tmp/mod with spaces"', descriptor('TCA', Path('/tmp/mod with spaces')))
        with self.assertRaises(ValueError):
            descriptor('TCA', Path('/tmp/mod"bad'))


if __name__ == '__main__':
    unittest.main()
