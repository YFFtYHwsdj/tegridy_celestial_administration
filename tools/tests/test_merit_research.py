"""研究运行入口应隔离产物、冻结源码并拒绝混用版本。"""
from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'merit_research' / 'run.py'
REPO = RUNNER.parents[2]

class MeritResearchRunnerChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'output'

    def call(self, *args):
        return subprocess.run([sys.executable, str(RUNNER), *map(str, args)], capture_output=True, text=True)

    def test_rejects_output_inside_repository(self):
        result = self.call('controller', '--output-dir', REPO / 'tools' / 'research-output')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('产物目录必须位于仓库外', result.stderr)

    def test_freezes_sources_without_running_study(self):
        result = self.call('occupancy', '--output-dir', self.output, '--prepare-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        for folder, filename in [('merit-occupancy-study', 'simulate.py'), ('merit-buffer-study', 'model.py')]:
            self.assertTrue((self.output / folder / filename).is_file())
        self.assertEqual((self.output / 'merit-occupancy-study' / 'simulate.py').read_bytes(),
                         (RUNNER.parent / 'occupancy' / 'simulate.py').read_bytes())
        self.assertFalse((self.output / 'merit-occupancy-study' / 'results.json').exists())
        self.assertTrue((self.output / 'source-manifest.json').is_file())

    def test_joint_freezes_references_without_old_results(self):
        result = self.call('joint', '--output-dir', self.output, '--prepare-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        for folder, filename in [('merit-occupancy-study', 'aging.py'),
                                 ('merit-buffer-study', 'model.py'),
                                 ('merit-controller-study', 'study.py')]:
            self.assertTrue((self.output / folder / filename).is_file())
        result = self.call('joint', '--output-dir', self.output, '--check-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('joint/results.json', result.stderr)

    def test_existing_output_is_not_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / 'sentinel.txt'
        sentinel.write_text('保留')
        result = self.call('controller', '--output-dir', self.output, '--prepare-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('目录必须为空', result.stderr)
        self.assertEqual(sentinel.read_text(), '保留')

    def test_check_rejects_changed_snapshot_before_running(self):
        prepared = self.call('controller', '--output-dir', self.output, '--prepare-only')
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        source = self.output / 'merit-controller-study' / 'study.py'
        source.write_text('raise RuntimeError("不应执行")\n')
        result = self.call('controller', '--output-dir', self.output, '--check-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('源码不一致', result.stderr)
        self.assertNotIn('RuntimeError', result.stderr)

    def test_missing_results_are_not_claimed_as_checked(self):
        prepared = self.call('controller', '--output-dir', self.output, '--prepare-only')
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        result = self.call('controller', '--output-dir', self.output, '--check-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('缺少研究结果', result.stderr)

    def test_failed_subprocess_preserves_failure_and_logs(self):
        spec = importlib.util.spec_from_file_location('merit_research_runner', RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        (self.output / 'merit-controller-study').mkdir(parents=True)
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, '退出码7'):
                module.execute(self.output, 'controller', ['-c', 'print("真实失败"); raise SystemExit(7)'], 1, 'check')
        logs = list((self.output / 'run-logs').glob('*.log'))
        self.assertEqual(len(logs), 2)
        self.assertTrue(all('真实失败' in log.read_text() for log in logs))

    def test_check_requires_existing_output(self):
        result = self.call('controller', '--check-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('必须指定已有', result.stderr)

class MeritJointDiagnosticsChecks(unittest.TestCase):
    def test_recovery_requires_complete_window_and_start_boundary(self):
        spec=importlib.util.spec_from_file_location('merit_joint_diagnostics',RUNNER.parent/'analyze_joint.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        rows=[{'year':year,'tail_error':[.1]*6} for year in range(59,66)]
        self.assertEqual(module.first_window(rows,range(6)),0)
        rows[3]['tail_error'][0]=.3
        self.assertIsNone(module.first_window(rows,range(6)))
        self.assertEqual(module.first_window(rows,[5]),0)
        self.assertIsNone(module.first_window(rows[:5],[5]))

class MeritCalibrationChecks(unittest.TestCase):
    def test_general_mapping_matches_existing_and_scales_without_double_count(self):
        code="""
import sys
from pathlib import Path
import calibrate_joint as c
sys.path.insert(0,str(Path('joint').resolve()))
import capacity
for J in [[0,0,0,0],[100,0,0,5],[3,1,1,1],[348,59,15,8]]:
 a=c.mapping(capacity.targets,[2]*4)(J)
 b=capacity.targets(J)
 for key in ['K','target','B']:
  assert all(abs(x-y)<1e-10 for x,y in zip(a[key],b[key]))
a=c.mapping(capacity.targets,[2,4,6,1.5])([10,2,1,1],r=.06)
b=c.mapping(capacity.targets,[2,4,6,1.5])([30,6,3,3],r=.06)
assert all(abs(y-3*x)<1e-10 for x,y in zip(a['target'],b['target']))
assert abs(sum(a['target'])-1.1*sum(a['K']))<1e-10
assert abs(a['target'][1]/sum(a['target'][:2])-.6)<1e-10
assert a['feasible_at_candidate_fraction']
from types import SimpleNamespace
world=SimpleNamespace(JOBS={route:{'base':[100,20,5,2]} for route in ['civil','military']},
                      pr=SimpleNamespace(BASE={'civil':{'birth':26},'military':{'birth':8}}))
config={'coefficients':[2.5,4,8,1.5],'r':.06,'gain':.6}
a=c.external_config(config,'civil',world);b=c.external_config(config,'military',world)
assert a['annual_entrants']==b['annual_entrants']==10
assert a['coefficients']==b['coefficients']==config['coefficients']
assert round(a['entry_mult']*26)==round(b['entry_mult']*8)==10
try:c.external_config({**config,'military_low':3.5},'military',world)
except ValueError:pass
else:raise AssertionError('路线专属参数未被拒绝')
"""
        completed=subprocess.run([sys.executable,'-c',code],cwd=RUNNER.parent,capture_output=True,text=True)
        self.assertEqual(completed.returncode,0,completed.stderr)

if __name__ == '__main__':
    unittest.main()
