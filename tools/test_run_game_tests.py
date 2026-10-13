"""Launcher isolation and outcome tests; these do not simulate CK3 rules."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

from run_game_tests import (ROOT, descriptor, isolated_settings, outcome, prepare_run,
                            progress, stop_owned_process, terminal_condition)
from check_upstream_overrides import definitions


class GameRunnerTests(unittest.TestCase):
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
            self.assertIn(str(ROOT), (second / 'mod/tca_main.mod').read_text())
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
        for condition in ('timeout', 'process_exit', 'interrupted', 'not_observer'):
            self.assertEqual(outcome(condition, True, 0), 2)
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
