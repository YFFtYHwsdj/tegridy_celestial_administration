"""运行队列与隔离汇总；锁只约束本工具，不查找或终止外部游戏。"""
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import tempfile
import time
import sys

ENGINE_LOCK = Path(tempfile.gettempdir()) / 'tca-ck3-engine.lock'


def file_lock(handle, unlock=False):
    """同一文件首字节使用 Windows 区域锁，其他平台使用 flock；均非阻塞。"""
    handle.seek(0)
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK if unlock else msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN if unlock else fcntl.LOCK_EX | fcntl.LOCK_NB)


@contextmanager
def engine_lock(path=ENGINE_LOCK, task_id=''):
    """跨输出目录使用同机锁；进程结束自动释放，等待可中断。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 不截断已有文件、不替换其 inode，保证其他任务仍竞争同一把锁。
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(fd, 'r+b') as handle:
        announced = False
        while True:
            try:
                file_lock(handle)
                break
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if not announced:
                    print(f'Queued task {task_id}; waiting for CK3 test engine', flush=True)
                    announced = True
                time.sleep(0.5)
        try:
            # Windows 锁可以覆盖空文件之外的区域；取得后再写入首字节。
            # 更新元数据时保留这个字节，不能截断正在锁定的区域。
            handle.seek(0)
            handle.write(b' ')
            handle.flush()
            handle.truncate(1)
            handle.write(json.dumps({'pid': os.getpid(), 'task_id': task_id}).encode('utf-8'))
            handle.flush()
            yield
        finally:
            file_lock(handle, unlock=True)


def aggregate_runs(runs):
    """所有子运行均有成功终局才通过；缺失或损坏证据均为未验证。"""
    children = []
    for run in runs:
        try:
            terminal = json.loads((Path(run) / 'terminal.json').read_text(encoding='utf-8'))
            code = terminal['runner_exit']
            if type(code) is not int or code not in (0, 1, 2):
                raise ValueError('invalid runner exit')
        except (OSError, ValueError, KeyError, TypeError):
            code = 2
        children.append({'run_id': Path(run).name, 'run_dir': str(run), 'runner_exit': code})
    return {'runner_exit': max((child['runner_exit'] for child in children), default=2),
            'runs': children}
