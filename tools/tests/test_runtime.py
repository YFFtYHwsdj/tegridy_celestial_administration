"""运行封存、跨进程互斥及隔离汇总的回归，不启动游戏。"""
import importlib.util
import builtins
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace


class RuntimeTests(unittest.TestCase):
    def test_windows_import_and_lock_retry_do_not_require_fcntl(self):
        """模拟 Windows 缺少 fcntl，检查竞争重试、固定字节偏移和异常释放。"""
        original_import = builtins.__import__
        def without_fcntl(name, *args, **kwargs):
            if name == 'fcntl':
                raise ModuleNotFoundError('Windows has no fcntl')
            return original_import(name, *args, **kwargs)
        calls = []
        def locking(fd, mode, count):
            calls.append((mode, os.lseek(fd, 0, os.SEEK_CUR), count))
            if len(calls) == 1:
                raise OSError(errno.EACCES, 'locked by another process')
        windows = SimpleNamespace(locking=locking, LK_NBLCK=1, LK_UNLCK=2)
        spec = importlib.util.spec_from_file_location('windows_runtime_probe',
                  Path(__file__).resolve().parents[1]/'testing/runtime.py')
        module = importlib.util.module_from_spec(spec)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'engine.lock'
            with patch('builtins.__import__', side_effect=without_fcntl), \
                 patch.object(sys, 'platform', 'win32'), \
                 patch.dict(sys.modules, {'msvcrt': windows}), \
                 patch('time.sleep') as sleep:
                spec.loader.exec_module(module)
                with self.assertRaisesRegex(RuntimeError, 'case interrupted'):
                    with module.engine_lock(path, 'windows-job'):
                        raise RuntimeError('case interrupted')
                sleep.assert_called_once_with(0.5)
            self.assertEqual(calls, [(1, 0, 1), (1, 0, 1), (2, 0, 1)])
            self.assertEqual(json.loads(path.read_text())['task_id'], 'windows-job')

    def test_windows_lock_does_not_retry_unexpected_os_errors(self):
        """句柄等错误必须立即报告，不能当作竞争无限排队。"""
        api = self.api()
        def invalid_handle(*args):
            raise OSError(errno.EBADF, 'invalid handle')
        windows = SimpleNamespace(locking=invalid_handle, LK_NBLCK=1, LK_UNLCK=2)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'engine.lock'
            with patch.object(sys, 'platform', 'win32'), \
                 patch.dict(sys.modules, {'msvcrt': windows}), patch('time.sleep') as sleep:
                with self.assertRaises(OSError):
                    with api.engine_lock(path, 'job'):
                        self.fail('不能取得无效句柄锁')
                sleep.assert_not_called()

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('testing.runtime'), '需要运行管理工具')
        import testing.runtime as test_runtime
        return test_runtime

    def test_lock_excludes_other_process_and_releases_after_context(self):
        api = self.api()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'engine.lock'
            probe = ('import sys\nsys.path.insert(0, sys.argv[2])\n'
                     'from testing.runtime import engine_lock\n'
                     'with engine_lock(sys.argv[1], "child"):\n print("ACQUIRED", flush=True)\n')
            command = [sys.executable, '-c', probe, str(path), str(Path(api.__file__).parents[1])]
            with api.engine_lock(path, 'job-a'):
                with self.assertRaises(subprocess.TimeoutExpired) as waiting:
                    subprocess.run(command, capture_output=True, timeout=2)
                self.assertNotIn(b'ACQUIRED', waiting.exception.stdout or b'')
                self.assertIn(b'Queued task child', waiting.exception.stdout or b'')
            other = subprocess.run(command, capture_output=True, timeout=5)
            self.assertEqual(other.returncode, 0)
            self.assertIn(b'ACQUIRED', other.stdout)

    def test_isolated_aggregate_rejects_missing_or_failed_children(self):
        api = self.api()
        with tempfile.TemporaryDirectory() as temp:
            runs = [Path(temp)/'a', Path(temp)/'b']
            for run in runs:
                run.mkdir()
            (runs[0]/'terminal.json').write_text(json.dumps({'runner_exit': 0}))
            self.assertNotEqual(api.aggregate_runs(runs)['runner_exit'], 0)
            (runs[1]/'terminal.json').write_text(json.dumps({'runner_exit': 1}))
            self.assertNotEqual(api.aggregate_runs(runs)['runner_exit'], 0)
            (runs[1]/'terminal.json').write_text(json.dumps({'runner_exit': 0}))
            self.assertEqual(api.aggregate_runs(runs)['runner_exit'], 0)

    def test_killed_lock_owner_does_not_block_next_task(self):
        """持锁进程被终止后，下一任务仍能取得同一锁文件。"""
        api = self.api()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'engine.lock'
            ready = Path(temp)/'ready'
            owner_code = ('import sys,time\nfrom pathlib import Path\n'
                          'sys.path.insert(0, sys.argv[3])\nfrom testing.runtime import engine_lock\n'
                          'with engine_lock(sys.argv[1], "owner"):\n'
                          ' Path(sys.argv[2]).touch()\n time.sleep(60)\n')
            owner = subprocess.Popen([sys.executable, '-c', owner_code, str(path), str(ready),
                                      str(Path(api.__file__).parents[1])], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic()+5
                while not ready.exists() and owner.poll() is None and time.monotonic()<deadline:
                    time.sleep(0.02)
                self.assertTrue(ready.exists(), '子进程须先实际取得锁')
            finally:
                if owner.poll() is None:
                    owner.kill()
                owner.communicate(timeout=5)
            probe = ('import sys\nsys.path.insert(0, sys.argv[2])\n'
                     'from testing.runtime import engine_lock\n'
                     'with engine_lock(sys.argv[1], "next"):\n print("ACQUIRED")\n')
            result = subprocess.run([sys.executable, '-c', probe, str(path),
                                     str(Path(api.__file__).parents[1])], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'ACQUIRED', result.stdout)
