#!/usr/bin/env python3
"""启动独立的 CK3 图形观察者测试局，适用于 macOS 与 Windows，不使用界面自动化。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from collections import deque

from check_upstream_overrides import definitions
from platform_paths import default_game_dir, default_settings, game_executable
from testing.runtime import engine_lock, aggregate_runs

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAME = default_game_dir()
DEFAULT_SETTINGS = default_settings()
SUMMARY_MARKERS = ('TCA_TEST SUITE_ALL_PASSED', 'TCA_TEST SUITE_NOT_ALL_PASSED',
                   'TCA_TEST SUITE_ABORTED')
# 增量轮询每次最多读取的块大小，以及无换行长行的内存上限；避免日志膨胀后单轮轮询过大。
READ_CHUNK = 1 << 20
MAX_LINE_BYTES = 1 << 20


def write_json(path, data):
    # 同目录原子替换，避免并发浏览 latest 或进度时读到半份 JSON。
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def descriptor(name, path):
    # Paradox 引号字符串不使用 JSON 的 ASCII 转义约定。
    value = path.as_posix()
    if any(char in value for char in ('"', '\n', '\r')):
        raise ValueError('mod path contains an unsupported quote or newline')
    return f'name="{name}"\npath="{value}"\n'


def isolated_settings(source):
    """仅复制游戏／图形偏好，不复制账户或云凭据。"""
    parsed = definitions(source.read_text(encoding='utf-8-sig')) if source.is_file() else {}
    game = ' '.join(parsed.get('"game"', ['{', '}']))
    graphics = ' '.join(parsed.get('"Graphics"', ['{', '}']))
    for key, value in (('cloud_save', 'enabled = no'),):
        game = re.sub(r'"' + key + r'"\s*=\s*\{[^{}]*\}', '', game)
        game = game[:-1] + f' "{key}" = {{ version = 0 {value} }} }}'
    for key, value in (('display_mode', 'windowed'), ('windowed_resolution', '1280x800')):
        graphics = re.sub(r'"' + key + r'"\s*=\s*\{[^{}]*\}', '', graphics)
        graphics = graphics[:-1] + f' "{key}" = {{ version = 0 value = "{value}" }} }}'
    return f'"game" = {game}\n"Graphics" = {graphics}\n'


def snapshot_files(run):
    files = {}
    for folder, prefix in (('tca_main', ''), ('tca_cli_adapter', '@adapter/')):
        base = run / 'mod' / folder
        for path in sorted(base.rglob('*')):
            if path.is_file():
                files[prefix + path.relative_to(base).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((run / 'tools').rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            files['@tools/' + path.relative_to(run / 'tools').as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((run / 'inputs').glob('*')):
        if path.is_file():
            files['@inputs/' + path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('selection.json', 'metadata.json', 'dlc_load.json', 'execution.json'):
        if (run / name).is_file():
            files['@' + name] = hashlib.sha256((run / name).read_bytes()).hexdigest()
    for name in ('tca_main.mod', 'tca_cli_adapter.mod'):
        path = run / 'mod' / name
        files['@' + name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def content_digest(files, version=2):
    content = files if version == 1 else {key: value for key, value in files.items()
                                         if key not in {'@tca_main.mod', '@tca_cli_adapter.mod', '@metadata.json'}}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def seal_run(run, source_root=None):
    files = snapshot_files(run)
    digest = content_digest(files)
    write_json(run / 'source_manifest.json', {'format': 3, 'source_root': str(source_root or ROOT),
                                             'sha256': digest, 'files': files})
    return digest


def verify_snapshot(run):
    try:
        manifest = json.loads((run / 'source_manifest.json').read_text(encoding='utf-8'))
        files = snapshot_files(run)
        # 旧清单仅保护游戏脚本及描述文件，不能将后来新增的保护范围倒套为旧源码变化。
        if manifest.get('format', 1) < 3 and not any(key.startswith('@tools/') for key in manifest['files']):
            files = {key: value for key, value in files.items()
                     if not key.startswith('@') or key.startswith('@adapter/')
                     or key in {'@tca_main.mod', '@tca_cli_adapter.mod'}}
        digest = content_digest(files, manifest.get('format', 1))
        issues = [] if manifest['files'] == files and manifest['sha256'] == digest else ['Runtime snapshot changed after sealing']
        # 引擎启动后会写回运行偏好；不可变原件始终验收，启动前还须确认实际输入未被改动。
        settings = run / 'inputs/pdx_settings.txt'
        if settings.is_file() and not (run / 'process.json').exists():
            if settings.read_bytes() != (run / 'pdx_settings.txt').read_bytes():
                issues.append('Runtime preferences changed before launch')
        return issues
    except (OSError, ValueError, KeyError) as error:
        return ['Runtime snapshot cannot be verified: ' + str(error)]


TOOL_FILES = ('run_game_tests.py', 'check_test_run.py', 'check_upstream_overrides.py',
              'testing/__init__.py', 'testing/catalog.py', 'testing/runtime.py', 'platform_paths.py',
              'upstream_overrides.json')


def source_files(repo):
    """记录实际复制的源文件，比较复制前后及目标，检测准备期间修改。"""
    files = {}
    for item in repo.iterdir():
        if item.name.startswith('.') or item.name in {'tools', 'docs'}:
            continue
        paths = item.rglob('*') if item.is_dir() else [item] if item.name == 'descriptor.mod' else []
        for path in paths:
            if path.is_file() and '.DS_Store' not in path.parts and '__pycache__' not in path.parts:
                files[path.relative_to(repo).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    adapter = repo / 'tools/cli_adapter'
    for path in adapter.rglob('*'):
        if path.is_file() and '.DS_Store' not in path.parts and '__pycache__' not in path.parts:
            files['@adapter/' + path.relative_to(adapter).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in TOOL_FILES:
        path = repo / 'tools' / name
        if path.is_file():
            files['@tools/' + name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def configure_selection(run, rows, selected, parallel=1):
    """配置适配模组的选择标记与并发上限；正式测试源保持原样。

    无论全量还是选择都注入 tca_test_max_active，保证显式选择局也能复现 K>1；
    注入点必须在观察者入口之前，且入口标记只能出现一次。
    """
    if type(parallel) is not int or not 1 <= parallel <= 32:
        raise ValueError('parallel must be between 1 and 32')
    plan = {'format': 1, 'scope': 'selection' if selected else 'full', 'cases': rows}
    write_json(run / 'selection.json', plan)
    events = run / 'mod/tca_cli_adapter/events/tca_cli_events.txt'
    text = events.read_text(encoding='utf-8-sig')
    if selected:
        # 克隆已选择运行时先撤去旧标记，再安装本子运行的范围。
        text = re.sub(r'\s*set_variable = \{ name = tca_test_(?:selected_run|max_active|\w+_selected) '
                      r'value = (?:yes|\d+) \}', '', text)
    marker = 'tca_run_observer_tests_effect = yes'
    if text.count(marker) != 1:
        raise ValueError('CLI observer entry must occur exactly once')
    flags = [f'set_variable = {{ name = tca_test_max_active value = {parallel} }}']
    if selected:
        flags.append('set_variable = { name = tca_test_selected_run value = yes }')
        flags += [f"   set_variable = {{ name = {row['name']}_selected value = yes }}" for row in rows]
    events.write_text(text.replace(marker, '\n'.join(flags) + '\n   ' + marker), encoding='utf-8-sig')


def prepare_run(repo, run_root, settings, selected_case=None, suites=(), cases=(), execution=None, parallel=1):
    if run_root.resolve().is_relative_to(repo.resolve()):
        raise ValueError('Run root must be outside the source directory')
    run_root.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='run-', dir=run_root))
    before = source_files(repo)
    (run / 'mod').mkdir()
    shutil.copytree(repo / 'tools/cli_adapter', run / 'mod/tca_cli_adapter',
                    ignore=shutil.ignore_patterns('.DS_Store', '__pycache__'))
    snapshot = run / 'mod/tca_main'
    snapshot.mkdir()
    for path in sorted(repo.iterdir()):
        if path.name.startswith('.') or path.name in {'tools', 'docs'}:
            continue
        if path.is_dir():
            shutil.copytree(path, snapshot / path.name, ignore=shutil.ignore_patterns('.DS_Store', '__pycache__'))
        elif path.name == 'descriptor.mod':
            shutil.copy2(path, snapshot / path.name)
    (run / 'tools').mkdir()
    for name in TOOL_FILES:
        if (repo / 'tools' / name).is_file():
            (run / 'tools' / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo / 'tools' / name, run / 'tools' / name)
    (run / 'mod/tca_main.mod').write_text(descriptor('TCA Main', snapshot), encoding='utf-8')
    (run / 'mod/tca_cli_adapter.mod').write_text(descriptor('TCA CLI Adapter', run / 'mod/tca_cli_adapter'), encoding='utf-8')
    copied = {key: value for key, value in snapshot_files(run).items()
              if key not in {'@tca_main.mod', '@tca_cli_adapter.mod'}}
    if before != source_files(repo) or before != copied:
        raise ValueError('Source changed during preparation; submit a new run')
    requested = list(cases) + ([selected_case] if selected_case else [])
    if list((snapshot / 'common/scripted_effects').rglob('tca_test_catalog_effects.txt')):
        from testing.catalog import select_cases
        rows = select_cases(snapshot, suites, requested)
        configure_selection(run, rows, bool(suites or requested), parallel)
    elif suites or requested:
        raise ValueError('Native catalog missing')
    write_json(run / 'dlc_load.json', {'disabled_dlcs': [], 'enabled_mods': [
        'mod/tca_main.mod', 'mod/tca_cli_adapter.mod']})
    (run / 'pdx_settings.txt').write_text(isolated_settings(settings), encoding='utf-8')
    (run / 'inputs').mkdir()
    shutil.copy2(run / 'pdx_settings.txt', run / 'inputs/pdx_settings.txt')
    git = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    status = subprocess.run(['git', '-C', str(repo), 'status', '--porcelain'], capture_output=True, text=True)
    write_json(run / 'metadata.json', {'run_id': run.name, 'source_root': str(repo),
               'commit': git.stdout.strip() if git.returncode == 0 else None,
               'working_tree_status': status.stdout.splitlines() if status.returncode == 0 else None})
    if execution is not None:
        write_json(run / 'execution.json', execution)
    seal_run(run, repo)
    write_json(run_root / 'latest.json', {'run_dir': str(run), 'run_id': run.name})
    return run


def clone_run(base, run_root, rows, parallel=None):
    """隔离子运行只从已封存任务复制，不能重新读取持续变化的工作目录。

    并发上限沿用父任务的 execution.json；缺失时回退 1，保证子运行与父任务同口径。
    """
    issues = verify_snapshot(base)
    if issues:
        raise ValueError('; '.join(issues))
    if parallel is None:
        execution_path = base / 'execution.json'
        execution = json.loads(execution_path.read_text(encoding='utf-8')) if execution_path.is_file() else {}
        parallel = execution.get('parallel', 1)
    run = Path(tempfile.mkdtemp(prefix='run-', dir=run_root))
    for name in ('mod', 'tools', 'inputs'):
        shutil.copytree(base / name, run / name)
    for name in ('pdx_settings.txt', 'dlc_load.json', 'metadata.json', 'selection.json', 'execution.json'):
        if not (base / name).is_file():
            continue
        shutil.copy2(base / name, run / name)
    if verify_snapshot(base) or snapshot_files(run) != snapshot_files(base):
        raise ValueError('Frozen source changed while cloning')
    shutil.copy2(run / 'inputs/pdx_settings.txt', run / 'pdx_settings.txt')
    for name, label in (('tca_main', 'TCA Main'), ('tca_cli_adapter', 'TCA CLI Adapter')):
        (run / 'mod' / (name + '.mod')).write_text(descriptor(label, run / 'mod' / name), encoding='utf-8')
    configure_selection(run, rows, True, parallel)
    metadata = json.loads((run / 'metadata.json').read_text(encoding='utf-8'))
    metadata.update(run_id=run.name, parent_task=base.name)
    write_json(run / 'metadata.json', metadata)
    seal_run(run, metadata['source_root'])
    return run


def decode_log_line(data):
    # 只有凑齐换行才解码整行，跨轮询截断的多字节字符因此不会被替换字符污染。
    return data.decode('utf-8', errors='replace').rstrip('\r')


class LogTailReader:
    """增量日志读取器：只读上次偏移之后的新增字节，按完整行返回文本。

    文件未创建时返回空；文件被替换、截断或 logs/ 目录重建时自动重置偏移。
    无换行的超长单行按上限分段返回，保证轮询期间内存有界。
    """

    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self.bytes_read = 0
        self._handle = None
        self._pending = b''

    def poll(self):
        """返回本轮新增的完整行；不读取整份文件。"""
        if not self._sync():
            return []
        try:
            size = os.fstat(self._handle.fileno()).st_size
        except OSError:
            self.reset()
            return []
        lines = []
        # 以轮询开始时的文件大小为准，单轮读取量有界；轮询期间追加的字节留到下一轮。
        remaining = max(0, size - self.offset)
        try:
            while remaining > 0:
                chunk = self._handle.read(min(READ_CHUNK, remaining))
                if not chunk:
                    break
                self.offset += len(chunk)
                self.bytes_read += len(chunk)
                remaining -= len(chunk)
                self._feed(chunk, lines)
        except OSError:
            self.reset()
        return lines

    def flush(self):
        """进程退出后补齐未带换行的末行；文件轮转或截断时丢弃旧尾部。"""
        if not self._pending:
            return []
        line = decode_log_line(self._pending)
        self._pending = b''
        return [line]

    def reset(self):
        # 只重置偏移与未成行缓冲；bytes_read 保留为本次运行的累计读取量。
        if self._handle is not None:
            try:
                self._handle.close()
            finally:
                self._handle = None
        self.offset = 0
        self._pending = b''

    def close(self):
        self.reset()

    def _feed(self, chunk, lines):
        data = self._pending + chunk if self._pending else chunk
        parts = data.split(b'\n')
        self._pending = parts.pop()
        lines.extend(decode_log_line(part) for part in parts)
        if len(self._pending) >= MAX_LINE_BYTES:
            # 无换行的超长单行分段送出；行内标记仍可在当前片段中匹配。
            lines.append(decode_log_line(self._pending))
            self._pending = b''

    def _sync(self):
        """确认句柄仍指向当前日志文件；文件轮转、截断或消失时重置偏移。"""
        try:
            info = self.path.stat()
        except OSError:
            self.reset()
            return False
        if self._handle is not None:
            try:
                opened = os.fstat(self._handle.fileno())
            except OSError:
                self.reset()
                return False
            # 目录重建会换 inode；同一 inode 下文件变短则是就地截断。
            if self._identity(opened) != self._identity(info) or info.st_size < self.offset:
                self.reset()
        if self._handle is None:
            try:
                self._handle = self.path.open('rb')
            except OSError:
                return False
        return True

    @staticmethod
    def _identity(info):
        # 部分 Windows 文件系统不提供 inode；此时退回按文件大小判断截断。
        return (info.st_dev, info.st_ino) if info.st_ino else None


class RunLogMonitor:
    """运行期增量进度：跨 phase 累计通过数、标记与观察者确认，不保留历史全文。

    每轮只消费新增完整行；phase 归档后调用 next_phase() 重置字节偏移并记录本阶段
    观察者确认。progress()/terminal_condition() 与模块级同名函数语义一致。
    """

    def __init__(self, path):
        self.tail = LogTailReader(path)
        self._pass_count = 0
        self._markers = deque(maxlen=8)
        self._summary = False
        self._entry_rejected = False
        self._not_observer = False
        self._phase_confirmed = []
        self._observer = False
        self._reload_lines = []

    @property
    def pass_count(self):
        return self._pass_count

    @property
    def markers(self):
        return list(self._markers)

    @property
    def observer_confirmed(self):
        # 每个实际运行过的 phase 都要独立确认；续局重新确认前保持 false。
        return all(self._phase_confirmed + [self._observer])

    @property
    def bytes_read(self):
        return self.tail.bytes_read

    @property
    def offset(self):
        return self.tail.offset

    def poll(self):
        lines = self.tail.poll()
        self._consume(lines)
        return lines

    def flush(self):
        lines = self.tail.flush()
        self._consume(lines)
        return lines

    def progress(self, elapsed, running):
        # 字段与 progress() 完全一致，供 progress.json 与 terminal.json 沿用。
        return {'seconds': round(elapsed, 1), 'running': running, 'pass_count': self._pass_count,
                'observer_confirmed': self.observer_confirmed, 'markers': list(self._markers)}

    def terminal_condition(self, process_code):
        # 顺序必须与 terminal_condition() 一致：汇总 > 入口拒绝 > 非观察者 > 进程退出。
        if self._summary:
            return 'summary'
        if self._entry_rejected:
            return 'entry_rejected'
        if self._not_observer:
            return 'not_observer'
        if process_code is not None:
            return 'process_exit'
        return None

    def reload_log(self):
        """只回放检查点相关行，供既有 reload_request(log, run) 校验。"""
        return '\n'.join(self._reload_lines)

    def next_phase(self):
        """归档并重建 logs/ 目录后进入下一阶段；偏移与检查点证据按阶段重置。"""
        self._phase_confirmed.append(self._observer)
        self._observer = False
        self._reload_lines = []
        self.tail.reset()

    def close(self):
        self.tail.close()

    def _consume(self, lines):
        for line in lines:
            if 'TCA_TEST PASS ' in line:
                self._pass_count += 1
            if 'TCA_CLI' in line or 'TCA_TEST SUITE_' in line:
                self._markers.append(line)
            if 'console_success: Going to observe mode' in line:
                self._observer = True
            if any(marker in line for marker in SUMMARY_MARKERS):
                self._summary = True
            if 'TCA_TEST OBSERVER_ENTRY_REJECTED' in line:
                self._entry_rejected = True
            if 'TCA_CLI NOT_OBSERVER' in line:
                self._not_observer = True
            if 'TCA_CLI RELOAD_SAVE' in line or 'console_success: Game saved to ' in line:
                self._reload_lines.append(line)


def progress(log, elapsed, running):
    lines = log.splitlines()
    return {'seconds': round(elapsed, 1), 'running': running,
            'pass_count': sum('TCA_TEST PASS ' in line for line in lines),
            'observer_confirmed': 'console_success: Going to observe mode' in log,
            'markers': [line for line in lines if 'TCA_CLI' in line or 'TCA_TEST SUITE_' in line][-8:]}


def terminal_condition(log, process_code):
    if any(marker in log for marker in SUMMARY_MARKERS):
        return 'summary'
    if 'TCA_TEST OBSERVER_ENTRY_REJECTED' in log:
        return 'entry_rejected'
    if 'TCA_CLI NOT_OBSERVER' in log:
        return 'not_observer'
    if process_code is not None:
        return 'process_exit'
    return None


def outcome(condition, observer_confirmed, checker_code):
    return checker_code if condition == 'summary' and observer_confirmed else 2


def stop_owned_process(process, require_running=False):
    before = process.poll()
    if require_running and before is not None:
        raise ValueError('Checkpoint process exited before the requested stop')
    if before is None:
        process.terminate()
        try:
            process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        # POSIX下正常响应本工具信号的退出必须可辨认；自行退出不能被后半段成功掩盖。
        if require_running and sys.platform != 'win32' and process.returncode not in (-15, -9):
            raise ValueError('Checkpoint process exit cannot be attributed to the requested stop')


def game_command(args, run, save_name=None):
    executable = game_executable(args.game_dir)
    command = [str(executable), '-debug_mode', '-develop', '-skip',
               '-suppress_error_log',
               f'-userdir={run.as_posix()}/']
    if save_name is not None:
        if not re.fullmatch(r'[A-Za-z0-9_]+', save_name):
            raise ValueError('Invalid local checkpoint save name')
        # 指定存档仍需选择测试君主才自动进入游戏；随后由原有CLI观察者入口接管。
        # 不重新生成世界、指定书签或重置随机种子。
        return command + [f'-loadsave={save_name}.ck3', '-play=h_china']
    command[4:4] = ['-bookmark=bm_1066_china', '-play=h_china']
    seed = getattr(args, 'seed', None)
    if seed is not None:
        if not 0 <= seed <= 0xFFFFFFFF:
            raise ValueError('--seed must be between 0 and 4294967295')
        command.append(f'-random_seed={seed}')
    return command


def reload_request(log, run):
    """只接受原生保存成功后的一次本地检查点请求，不执行日志中的任意命令。"""
    names = re.findall(r'TCA_CLI RELOAD_SAVE ([^\r\n]+)', log)
    if not names:
        return None
    if len(names) != 1 or not re.fullmatch(r'[A-Za-z0-9_]+', names[0]):
        raise ValueError('Invalid or repeated checkpoint request')
    name = names[0]
    save = run / 'save games' / (name + '.ck3')
    if ('console_success: Game saved to ' + name) not in log or not save.is_file():
        raise ValueError('Checkpoint requested without a completed local save')
    if save.resolve().parent != (run / 'save games').resolve() or save.stat().st_size < 32:
        raise ValueError('Checkpoint is not a nonempty local save')
    with save.open('rb') as handle:
        if not handle.read(3).startswith((b'SAV', b'PK')):
            raise ValueError('Checkpoint has no native save header')
    return name


def archive_phase_logs(run, phase):
    """进程退出后移动整份原始日志；续局进程不能覆盖上一阶段证据。"""
    target = run / 'phases' / str(phase)
    target.mkdir(parents=True)
    (run / 'logs').rename(target / 'logs')
    (run / 'logs').mkdir()
    if (run / 'process.json').is_file():
        shutil.copy2(run / 'process.json', target / 'process.json')
    if (run / 'phase_terminal.json').is_file():
        shutil.copy2(run / 'phase_terminal.json', target / 'terminal.json')


def merge_phase_logs(run, count):
    """逐字节连接原日志供既有验收器检查；不插入或删改任何断言及错误。"""
    phases = [run / 'phases' / str(index) / 'logs' for index in range(1, count + 1)]
    evidence = []
    for name in ('debug.log', 'error.log'):
        chunks = []
        for phase in phases:
            path = phase / name
            data = path.read_bytes() if path.is_file() else b''
            chunks.append(data)
            evidence.append({'path': str(path.relative_to(run)), 'sha256': hashlib.sha256(data).hexdigest()})
        (run / 'logs' / name).write_bytes(b''.join(chunks))
    write_json(run / 'reload_evidence.json', {'phases': count, 'raw_logs': evidence})


def game_environment(game_dir):
    """记录外部安装版本与执行文件状态；不宣称 Steam／DLC 已完全封闭。"""
    launcher = game_dir / 'launcher/launcher-settings.json'
    executable = game_executable(game_dir)
    settings = json.loads(launcher.read_text(encoding='utf-8')) if launcher.is_file() else {}
    stat = executable.stat() if executable.is_file() else None
    return {'game_dir': str(game_dir), 'version': settings.get('version'),
            'executable_size': stat.st_size if stat else None,
            'executable_mtime_ns': stat.st_mtime_ns if stat else None,
            'platform': sys.platform, 'python': sys.version}


def run_game(args, run):
    issues = verify_snapshot(run)
    if issues:
        raise ValueError('; '.join(issues))
    if (run / 'execution.json').is_file():
        execution = json.loads((run / 'execution.json').read_text(encoding='utf-8'))
        if execution['environment'] != game_environment(args.game_dir):
            raise ValueError('Game installation changed while queued')
    command = game_command(args, run)
    env = os.environ.copy()
    env['SteamAppId'] = '1158310'
    start = time.monotonic()
    condition, last = None, None
    phase = 1
    # 轮询只读取日志新增字节；跨 phase 的累计状态由监视器保存，不拼接旧阶段全文。
    monitor = RunLogMonitor(run / 'logs/debug.log')
    with (run / 'stdout.txt').open('w', encoding='utf-8') as stdout:
        process = subprocess.Popen(command, cwd=args.game_dir / 'binaries', env=env,
                                   stdout=stdout, stderr=subprocess.STDOUT)
        try:
            write_json(run / 'process.json', {'pid': process.pid, 'args': command, 'owned': True,
                       'environment': game_environment(args.game_dir),
                       'seed': getattr(args, 'seed', None), 'strict_title_heir': getattr(args, 'strict_title_heir', False)})
            print(f'Started isolated CK3 PID {process.pid}', flush=True)
            while time.monotonic() - start < args.timeout:
                exited = process.poll()
                monitor.poll()
                if exited is not None:
                    # 进程退出后补齐未换行的末行，避免漏掉最终汇总标记。
                    monitor.flush()
                state = monitor.progress(time.monotonic() - start, exited is None)
                write_json(run / 'progress.json', state)
                current = (state['markers'][-1:] or ['Initializing'], state['pass_count'] // 20)
                if current != last:
                    print(f"{state['seconds']}s; PASS {state['pass_count']}; {current[0][0]}", flush=True)
                    last = current
                condition = monitor.terminal_condition(exited)
                if condition:
                    break
                try:
                    save_name = reload_request(monitor.reload_log(), run)
                    if save_name and phase != 1:
                        raise ValueError('A checkpoint may only reload once per run')
                except ValueError as error:
                    print(str(error), flush=True)
                    condition = 'invalid_reload_request'
                    break
                if save_name:
                    # 只退出本工具拥有的进程；不修改存档、不重派发事件、不修复游戏状态。
                    try:
                        stop_owned_process(process, require_running=True)
                    except ValueError as error:
                        print(str(error), flush=True)
                        condition = 'checkpoint_process_exit'
                        break
                    write_json(run / 'phase_terminal.json', {'condition': 'requested_checkpoint_stop',
                               'process_exit': process.returncode})
                    # 归档会移动 logs/ 目录；先释放读取句柄，避免 Windows 上目录无法重命名。
                    monitor.close()
                    archive_phase_logs(run, phase)
                    monitor.next_phase()
                    phase += 1
                    command = game_command(args, run, save_name=save_name)
                    try:
                        process = subprocess.Popen(command, cwd=args.game_dir / 'binaries', env=env,
                                                   stdout=stdout, stderr=subprocess.STDOUT)
                    except OSError as error:
                        condition = 'reload_launch_failed'
                        write_json(run / 'process.json', {'pid': None, 'args': command, 'owned': False,
                                   'phase': phase, 'error': str(error)})
                        break
                    write_json(run / 'process.json', {'pid': process.pid, 'args': command, 'owned': True,
                               'environment': game_environment(args.game_dir), 'phase': phase,
                               'checkpoint_sha256': hashlib.sha256((run / 'save games' / (save_name + '.ck3')).read_bytes()).hexdigest()})
                    print(f'Reloading native checkpoint in isolated CK3 PID {process.pid}', flush=True)
                time.sleep(2)
        except KeyboardInterrupt:
            condition = 'interrupted'
        finally:
            stop_owned_process(process)
            monitor.close()
    if phase > 1:
        write_json(run / 'phase_terminal.json', {'condition': condition or 'timeout',
                   'process_exit': None if condition == 'reload_launch_failed' else process.returncode})
        archive_phase_logs(run, phase)
        merge_phase_logs(run, phase)
    condition = condition or 'timeout'
    # 读取最终已刷新的日志，包括退出期间产生的错误。
    debug = run / 'logs/debug.log'
    log = debug.read_text(encoding='utf-8', errors='replace') if debug.exists() else ''
    state = progress(log, time.monotonic() - start, False)
    # 每个实际游戏进程都必须独立确认观察者；合并日志中的首阶段确认不能覆盖续局。
    phase_logs = [run / 'phases' / str(index) / 'logs/debug.log' for index in range(1, phase + 1)] if phase > 1 else [debug]
    phase_observers = [path.is_file() and 'console_success: Going to observe mode' in
                       path.read_text(encoding='utf-8', errors='replace') for path in phase_logs]
    state['observer_confirmed'] = all(phase_observers)
    state['phase_observer_confirmed'] = phase_observers
    write_json(run / 'progress.json', state)
    checker_command = [sys.executable, str(run / 'tools/check_test_run.py'), '--logs', str(run / 'logs'),
                       '--source-root', str(run / 'mod/tca_main')]
    if getattr(args, 'strict_title_heir', False):
        checker_command += ['--strict-title-heir']
    checker = subprocess.run(checker_command, capture_output=True, text=True)
    (run / 'result.txt').write_text(checker.stdout + checker.stderr, encoding='utf-8')
    snapshot_issues = verify_snapshot(run)
    code = outcome(condition, state['observer_confirmed'], checker.returncode)
    if not state['observer_confirmed']:
        with (run / 'result.txt').open('a') as result:
            result.write('NOT VERIFIED\nObserver not confirmed in every process phase\n')
    if not (run / 'verification.json').is_file():
        code = 2
    if snapshot_issues:
        code = 2
        with (run / 'result.txt').open('a') as result:
            result.write('NOT VERIFIED\n' + '\n'.join(snapshot_issues) + '\n')
    write_json(run / 'terminal.json', {**state, 'condition': condition,
               'process_exit': None if condition == 'reload_launch_failed' else process.returncode,
               'phases': phase, 'parallel': getattr(args, 'parallel', 1),
               'verification_exit': checker.returncode,
               'runner_exit': code, 'snapshot_issues': snapshot_issues,
               'source_sha256': json.loads((run / 'source_manifest.json').read_text(encoding='utf-8'))['sha256'],
               'scope': json.loads((run / 'selection.json').read_text(encoding='utf-8'))['scope']})
    print(f"Terminal: {condition}; observer confirmed: {state['observer_confirmed']}", flush=True)
    print(checker.stdout + checker.stderr, end='', flush=True)
    return code


def timeout_warning(scope, timeout):
    """全量运行使用过短超时时给出中文提示；只提示，不改变执行与退出逻辑。"""
    if scope == 'full' and timeout < 1200:
        return ('警告：全量测试通常需要 1200–1800 秒，当前 --timeout 可能提前终止；'
                '超时只计单次游戏运行，不包含 engine lock 排队与 checker 验收时间。')
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, default=DEFAULT_GAME, help='CK3 安装根目录')
    parser.add_argument('--run-root', type=Path, default=Path(tempfile.gettempdir()) / 'tca-game-tests', help='独立运行输出根目录')
    parser.add_argument('--settings', type=Path, default=DEFAULT_SETTINGS, help='只读图形与游戏偏好来源')
    parser.add_argument('--timeout', type=float, default=240, help='每局启动及执行超时秒数，不包含排队')
    parser.add_argument('--prepare-only', action='store_true', help='封存任务但不启动游戏')
    parser.add_argument('--seed', type=int, help='原生新局随机种子')
    parser.add_argument('--parallel', type=int, default=1,
                        help='同一进程内并发延迟用例上限（1–32，默认 1 保持串行语义）')
    parser.add_argument('--strict-title-heir', action='store_true', help='首位继任不符也验收失败')
    parser.add_argument('--case', action='append', default=[], help='选择原生用例，可重复')
    parser.add_argument('--suite', action='append', default=[], help='选择模块或模块前缀，可重复')
    parser.add_argument('--list', action='store_true', help='列出所选范围，不启动游戏')
    parser.add_argument('--isolate', choices=('none', 'suite'), default='none', help='默认同局；suite 按模块分别开局')
    args = parser.parse_args(argv)
    args.game_dir = args.game_dir.expanduser().resolve()
    args.run_root = args.run_root.expanduser().resolve()
    if args.seed is not None and not 0 <= args.seed <= 0xFFFFFFFF:
        parser.error('--seed 必须介于 0 和 4294967295')
    if not 1 <= args.parallel <= 32:
        parser.error('--parallel 必须介于 1 和 32')
    if args.timeout <= 0:
        parser.error('--timeout 必须为正数')
    base, runs, task = None, [], None
    try:
        from testing.catalog import select_cases
        rows = select_cases(ROOT, args.suite, args.case)
        if args.list:
            for row in rows:
                print(f"{row['suite']}  {row['event']}  {'delayed' if row['delayed'] else 'immediate'}  {row['checks']} checks")
            print(f'{len(rows)} cases; {sum(row["checks"] for row in rows)} assertions')
            return 0
        if not args.prepare_only and not (game_executable(args.game_dir)).is_file():
            raise ValueError('找不到 CK3，请设置 --game-dir')
        execution = {'environment': game_environment(args.game_dir), 'seed': args.seed,
                     'strict_title_heir': args.strict_title_heir, 'timeout': args.timeout,
                     'parallel': args.parallel}
        base = prepare_run(ROOT, args.run_root, args.settings.expanduser(), suites=args.suite, cases=args.case,
                           execution=execution, parallel=args.parallel)
        rows = json.loads((base / 'selection.json').read_text(encoding='utf-8'))['cases']
        if args.isolate == 'suite':
            for suite in dict.fromkeys(row['suite'] for row in rows):
                runs.append(clone_run(base, args.run_root, [row for row in rows if row['suite'] == suite]))
        else:
            runs = [base]
        task = {'task_id': base.name, 'execution': 'isolated' if args.isolate == 'suite' else 'same_world',
                'scope': json.loads((base / 'selection.json').read_text(encoding='utf-8'))['scope'],
                'parallel': args.parallel,
                'runs': [str(run) for run in runs], 'state': 'prepared'}
        write_json(base / 'task.json', task)
        print(f'Task {base.name}: {base}', flush=True)
        for run in runs:
            print(f'Frozen run: {run}', flush=True)
        if args.prepare_only:
            return 0
        warning = timeout_warning(task['scope'], args.timeout)
        if warning:
            print(warning, file=sys.stderr, flush=True)
        task['state'] = 'queued'
        write_json(base / 'task.json', task)
        with engine_lock(task_id=base.name):
            task['state'] = 'running'
            write_json(base / 'task.json', task)
            for run in runs:
                code = run_game(args, run)
                terminal = json.loads((run / 'terminal.json').read_text(encoding='utf-8'))
                if terminal['condition'] == 'interrupted':
                    break
        result = aggregate_runs(runs)
        interrupted = any((run / 'terminal.json').is_file() and
                          json.loads((run / 'terminal.json').read_text(encoding='utf-8')).get('condition') == 'interrupted'
                          for run in runs)
        task.update(state='interrupted' if interrupted else 'finished', **result)
        write_json(base / 'task.json', task)
        write_json(base / 'task_result.json', result)
        print(f"Task {base.name}: {task['scope']} / {task['execution']}; exit {result['runner_exit']}", flush=True)
        return result['runner_exit']
    except (OSError, ValueError, KeyboardInterrupt) as error:
        if base:
            result = aggregate_runs(runs)
            result.update(runner_exit=2, error=str(error) or 'interrupted')
            task = task or {'task_id': base.name}
            task.update(state='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', **result)
            write_json(base / 'task.json', task)
            write_json(base / 'task_result.json', result)
        print(f'RUN FAILED: {str(error) or "interrupted"}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
