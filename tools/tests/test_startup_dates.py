"""双开局启动选择与冻结记录，不模拟游戏规则。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from run_game_tests import ROOT, game_command, prepare_run


class StartupDatesTests(unittest.TestCase):
    def test_1178_command_uses_frozen_date(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = prepare_run(ROOT, root/'runs', root/'absent', 'tca_exam_test.1',
                              execution={'start_date': '1178.10.1', 'bookmark': 'bm_1178_china'})
            command = game_command(SimpleNamespace(game_dir=root, seed=None), run)
            self.assertIn('-bookmark=bm_1178_china', command)
            self.assertNotIn('-bookmark=bm_1066_china', command)
            self.assertEqual(json.loads((run/'metadata.json').read_text())['start_date'], '1178.10.1')

    def test_both_freezes_two_separate_worlds(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, str(ROOT/'tools/run_game_tests.py'),
                '--start-date', 'both', '--prepare-only', '--case', 'tca_exam_test.1',
                '--run-root', temp], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            tasks = list(Path(temp).glob('run-*/task.json'))
            self.assertEqual(len(tasks), 1)
            task = json.loads(tasks[0].read_text())
            self.assertEqual(len(task['runs']), 2)
            dates = [json.loads((Path(run)/'execution.json').read_text())['start_date'] for run in task['runs']]
            self.assertEqual(dates, ['1066.9.15', '1178.10.1'])

    def test_actual_date_must_match_frozen_plan(self):
        from run_game_tests import start_date_issues
        self.assertEqual(start_date_issues({'start_date': '1178.10.1'}, 'TCA_CLI START_DATE 1178.10.1'), [])
        self.assertTrue(start_date_issues({'start_date': '1178.10.1'}, 'TCA_CLI START_DATE 1066.9.15'))
        self.assertTrue(start_date_issues({'start_date': '1178.10.1'}, ''))
