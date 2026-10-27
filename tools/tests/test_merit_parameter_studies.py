"""参数研究的文件边界与数学检查入口，不运行长时生涯演算。"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FOLDER=Path(__file__).resolve().parents[1]/'merit_research/parameters'


class MeritParameterStudiesChecks(unittest.TestCase):
    def test_mathematical_and_orchestration_invariants(self):
        for name in ['math_checks.py','study_checks.py']:
            with self.subTest(name=name):
                result=subprocess.run([sys.executable,str(FOLDER/name)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)

    def test_selector_can_run_in_spawned_processes(self):
        script=FOLDER.parent/'parameter_analysis.py'
        result=subprocess.run([sys.executable,str(script),'self-test'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('"spawn_importable": true',result.stdout)

    def test_scalar_output_rejects_repository(self):
        result=subprocess.run([sys.executable,str(FOLDER/'scalar_study.py'),
                               '--output-dir',str(FOLDER/'forbidden-output')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('仓库外',result.stderr)
        self.assertFalse((FOLDER/'forbidden-output').exists())

    def test_scalar_output_does_not_overwrite_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            sentinel=Path(folder)/'keep.txt';sentinel.write_text('保留')
            result=subprocess.run([sys.executable,str(FOLDER/'scalar_study.py'),
                                   '--output-dir',folder],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(sentinel.read_text(),'保留')

if __name__=='__main__':unittest.main()
