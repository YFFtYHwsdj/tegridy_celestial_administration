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

from check_upstream_overrides import definitions
from platform_paths import default_game_dir, default_settings, game_executable
from testing.runtime import engine_lock, aggregate_runs

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAME = default_game_dir()
DEFAULT_SETTINGS = default_settings()
SUMMARY_MARKERS = ('TCA_TEST SUITE_ALL_PASSED', 'TCA_TEST SUITE_NOT_ALL_PASSED',
                   'TCA_TEST SUITE_ABORTED')


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


def configure_selection(run, rows, selected):
    """只配置适配模组的选择标记；正式测试源保持原样。"""
    plan = {'format': 1, 'scope': 'selection' if selected else 'full', 'cases': rows}
    write_json(run / 'selection.json', plan)
    events = run / 'mod/tca_cli_adapter/events/tca_cli_events.txt'
    if selected:
        text = events.read_text(encoding='utf-8-sig')
        # 克隆已选择运行时先撤去旧标记，再安装本子运行的范围。
        text = re.sub(r'\s*set_variable = \{ name = tca_test_(?:selected_run|\w+_selected) value = yes \}', '', text)
        flags = 'set_variable = { name = tca_test_selected_run value = yes }\n' + ''.join(
            f"   set_variable = {{ name = {row['name']}_selected value = yes }}\n" for row in rows)
        marker = 'tca_run_observer_tests_effect = yes'
        if text.count(marker) != 1:
            raise ValueError('CLI observer entry must occur exactly once')
        events.write_text(text.replace(marker, flags + '   ' + marker), encoding='utf-8-sig')


def prepare_run(repo, run_root, settings, selected_case=None, suites=(), cases=(), execution=None):
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
        configure_selection(run, rows, bool(suites or requested))
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


def clone_run(base, run_root, rows):
    """隔离子运行只从已封存任务复制，不能重新读取持续变化的工作目录。"""
    issues = verify_snapshot(base)
    if issues:
        raise ValueError('; '.join(issues))
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
    configure_selection(run, rows, True)
    metadata = json.loads((run / 'metadata.json').read_text(encoding='utf-8'))
    metadata.update(run_id=run.name, parent_task=base.name)
    write_json(run / 'metadata.json', metadata)
    seal_run(run, metadata['source_root'])
    return run


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


def stop_owned_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def game_command(args, run):
    executable = game_executable(args.game_dir)
    command = [str(executable), '-debug_mode', '-develop', '-skip',
               '-bookmark=bm_1066_china', '-play=h_china', '-suppress_error_log',
               f'-userdir={run.as_posix()}/']
    seed = getattr(args, 'seed', None)
    if seed is not None:
        if not 0 <= seed <= 0xFFFFFFFF:
            raise ValueError('--seed must be between 0 and 4294967295')
        command.append(f'-random_seed={seed}')
    return command


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
    condition, log, last = None, '', None
    with (run / 'stdout.txt').open('w', encoding='utf-8') as stdout:
        process = subprocess.Popen(command, cwd=args.game_dir / 'binaries', env=env,
                                   stdout=stdout, stderr=subprocess.STDOUT)
        try:
            write_json(run / 'process.json', {'pid': process.pid, 'args': command, 'owned': True,
                       'environment': game_environment(args.game_dir),
                       'seed': getattr(args, 'seed', None), 'strict_title_heir': getattr(args, 'strict_title_heir', False)})
            print(f'Started isolated CK3 PID {process.pid}', flush=True)
            while time.monotonic() - start < args.timeout:
                debug = run / 'logs/debug.log'
                log = debug.read_text(encoding='utf-8', errors='replace') if debug.exists() else ''
                state = progress(log, time.monotonic() - start, process.poll() is None)
                write_json(run / 'progress.json', state)
                current = (state['markers'][-1:] or ['Initializing'], state['pass_count'] // 20)
                if current != last:
                    print(f"{state['seconds']}s; PASS {state['pass_count']}; {current[0][0]}", flush=True)
                    last = current
                condition = terminal_condition(log, process.poll())
                if condition:
                    break
                time.sleep(2)
        except KeyboardInterrupt:
            condition = 'interrupted'
        finally:
            stop_owned_process(process)
    condition = condition or 'timeout'
    # 读取最终已刷新的日志，包括退出期间产生的错误。
    debug = run / 'logs/debug.log'
    log = debug.read_text(encoding='utf-8', errors='replace') if debug.exists() else ''
    state = progress(log, time.monotonic() - start, False)
    write_json(run / 'progress.json', state)
    checker_command = [sys.executable, str(run / 'tools/check_test_run.py'), '--logs', str(run / 'logs'),
                       '--source-root', str(run / 'mod/tca_main')]
    if getattr(args, 'strict_title_heir', False):
        checker_command += ['--strict-title-heir']
    checker = subprocess.run(checker_command, capture_output=True, text=True)
    (run / 'result.txt').write_text(checker.stdout + checker.stderr, encoding='utf-8')
    snapshot_issues = verify_snapshot(run)
    code = outcome(condition, state['observer_confirmed'], checker.returncode)
    if not (run / 'verification.json').is_file():
        code = 2
    if snapshot_issues:
        code = 2
        with (run / 'result.txt').open('a') as result:
            result.write('NOT VERIFIED\n' + '\n'.join(snapshot_issues) + '\n')
    write_json(run / 'terminal.json', {**state, 'condition': condition,
               'process_exit': process.returncode, 'verification_exit': checker.returncode,
               'runner_exit': code, 'snapshot_issues': snapshot_issues,
               'source_sha256': json.loads((run / 'source_manifest.json').read_text(encoding='utf-8'))['sha256'],
               'scope': json.loads((run / 'selection.json').read_text(encoding='utf-8'))['scope']})
    print(f"Terminal: {condition}; observer confirmed: {state['observer_confirmed']}", flush=True)
    print(checker.stdout + checker.stderr, end='', flush=True)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, default=DEFAULT_GAME, help='CK3 安装根目录')
    parser.add_argument('--run-root', type=Path, default=Path(tempfile.gettempdir()) / 'tca-game-tests', help='独立运行输出根目录')
    parser.add_argument('--settings', type=Path, default=DEFAULT_SETTINGS, help='只读图形与游戏偏好来源')
    parser.add_argument('--timeout', type=float, default=240, help='每局启动及执行超时秒数，不包含排队')
    parser.add_argument('--prepare-only', action='store_true', help='封存任务但不启动游戏')
    parser.add_argument('--seed', type=int, help='原生新局随机种子')
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
                     'strict_title_heir': args.strict_title_heir, 'timeout': args.timeout}
        base = prepare_run(ROOT, args.run_root, args.settings.expanduser(), suites=args.suite, cases=args.case,
                           execution=execution)
        rows = json.loads((base / 'selection.json').read_text(encoding='utf-8'))['cases']
        if args.isolate == 'suite':
            for suite in dict.fromkeys(row['suite'] for row in rows):
                runs.append(clone_run(base, args.run_root, [row for row in rows if row['suite'] == suite]))
        else:
            runs = [base]
        task = {'task_id': base.name, 'execution': 'isolated' if args.isolate == 'suite' else 'same_world',
                'scope': json.loads((base / 'selection.json').read_text(encoding='utf-8'))['scope'],
                'runs': [str(run) for run in runs], 'state': 'prepared'}
        write_json(base / 'task.json', task)
        print(f'Task {base.name}: {base}', flush=True)
        for run in runs:
            print(f'Frozen run: {run}', flush=True)
        if args.prepare_only:
            return 0
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
