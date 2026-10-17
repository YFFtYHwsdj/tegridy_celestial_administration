#!/usr/bin/env python3
"""Launch an isolated graphical CK3 observer test game (macOS, no UI automation)."""
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

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAME = Path.home() / 'Library/Application Support/Steam/steamapps/common/Crusader Kings III'
DEFAULT_SETTINGS = Path.home() / 'Documents/Paradox Interactive/Crusader Kings III/pdx_settings.txt'
SUMMARY_MARKERS = ('TCA_TEST SUITE_ALL_PASSED', 'TCA_TEST SUITE_NOT_ALL_PASSED',
                   'TCA_TEST SUITE_ABORTED')


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def descriptor(name, path):
    # Paradox quoted strings do not use JSON's ASCII escape conventions.
    value = path.as_posix()
    if any(char in value for char in ('"', '\n', '\r')):
        raise ValueError('mod path contains an unsupported quote or newline')
    return f'name="{name}"\npath="{value}"\n'


def isolated_settings(source):
    """Copy only game/graphics preferences, never account or cloud credentials."""
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


def selected_stage(repo, entry):
    from check_test_run import selected_case_expectations
    selected_case_expectations(entry, repo)
    stages = definitions((repo / 'events/tca_tests_events.txt').read_text(encoding='utf-8-sig'))
    for stage, body in stages.items():
        text = ' '.join(body)
        if 'name = tca_test_suite_delayed_next' in text and re.search(r'trigger_event = ' + re.escape(entry) + r'(?![\d.])', text):
            return stage.split('.')[1]
    raise ValueError('Focused CLI currently supports registered delayed cases only')


def snapshot_files(run):
    files = {}
    for folder, prefix in (('tca_main', ''), ('tca_cli_adapter', '@adapter/')):
        base = run / 'mod' / folder
        for path in sorted(base.rglob('*')):
            if path.is_file():
                files[prefix + path.relative_to(base).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('tca_main.mod', 'tca_cli_adapter.mod'):
        path = run / 'mod' / name
        files['@' + name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def content_digest(files, version=2):
    content = files if version == 1 else {key: value for key, value in files.items()
                                         if key not in {'@tca_main.mod', '@tca_cli_adapter.mod'}}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def seal_run(run, source_root=None):
    files = snapshot_files(run)
    digest = content_digest(files)
    write_json(run / 'source_manifest.json', {'format': 2, 'source_root': str(source_root or ROOT),
                                             'sha256': digest, 'files': files})
    return digest


def verify_snapshot(run):
    try:
        manifest = json.loads((run / 'source_manifest.json').read_text())
        files = snapshot_files(run)
        digest = content_digest(files, manifest.get('format', 1))
        return [] if manifest['files'] == files and manifest['sha256'] == digest else ['Runtime snapshot changed after sealing']
    except (OSError, ValueError, KeyError) as error:
        return ['Runtime snapshot cannot be verified: ' + str(error)]


def prepare_run(repo, run_root, settings, selected_case=None):
    run_root.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='run-', dir=run_root))
    (run / 'mod').mkdir()
    adapter = run / 'mod/tca_cli_adapter'
    shutil.copytree(repo / 'tools/cli_adapter', adapter)
    if selected_case:
        stage = selected_stage(repo, selected_case)
        events = adapter / 'events/tca_cli_events.txt'
        text = events.read_text(encoding='utf-8-sig').replace(
            'tca_run_observer_tests_effect = yes',
            f'tca_run_focused_observer_test_effect = {{ STAGE = {stage} }}')
        events.write_text(text, encoding='utf-8-sig')
        write_json(run / 'selection.json', {'case': selected_case, 'stage': stage})
    snapshot = run / 'mod/tca_main'
    snapshot.mkdir()
    # Copy game content, never Git metadata, editor state, tools or reports.
    for path in sorted(repo.iterdir()):
        if path.name.startswith('.') or path.name in {'tools', 'docs'}:
            continue
        if path.is_dir():
            shutil.copytree(path, snapshot / path.name, ignore=shutil.ignore_patterns('.DS_Store', '__pycache__'))
        elif path.name == 'descriptor.mod':
            shutil.copy2(path, snapshot / path.name)
    (run / 'mod/tca_main.mod').write_text(descriptor('TCA Main', snapshot), encoding='utf-8')
    (run / 'mod/tca_cli_adapter.mod').write_text(descriptor('TCA CLI Adapter', adapter), encoding='utf-8')
    write_json(run / 'dlc_load.json', {'disabled_dlcs': [], 'enabled_mods': [
        'mod/tca_main.mod', 'mod/tca_cli_adapter.mod']})
    (run / 'pdx_settings.txt').write_text(isolated_settings(settings), encoding='utf-8')
    seal_run(run, repo)
    write_json(run_root / 'latest.json', {'run_dir': str(run)})
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
    executable = args.game_dir / 'binaries/ck3.app/Contents/MacOS/ck3'
    command = [str(executable), '-debug_mode', '-develop', '-skip',
               '-bookmark=bm_1066_china', '-play=h_china', '-suppress_error_log',
               f'-userdir={run}/']
    seed = getattr(args, 'seed', None)
    if seed is not None:
        if not 0 <= seed <= 0xFFFFFFFF:
            raise ValueError('--seed must be between 0 and 4294967295')
        command.append(f'-random_seed={seed}')
    return command


def run_game(args, run):
    issues = verify_snapshot(run)
    if issues:
        raise ValueError('; '.join(issues))
    command = game_command(args, run)
    env = os.environ.copy()
    env['SteamAppId'] = '1158310'
    start = time.monotonic()
    condition, log, last = None, '', None
    with (run / 'stdout.txt').open('w', encoding='utf-8') as stdout:
        process = subprocess.Popen(command, cwd=args.game_dir / 'binaries', env=env,
                                   stdout=stdout, stderr=subprocess.STDOUT)
        try:
            write_json(run / 'process.json', {'pid': process.pid, 'args': command, 'owned': True})
            print(f'Started isolated CK3 PID {process.pid}', flush=True)
            while time.monotonic() - start < args.timeout:
                debug = run / 'logs/debug.log'
                log = debug.read_text(errors='replace') if debug.exists() else ''
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
    # Read the final flushed log, including errors emitted during shutdown.
    debug = run / 'logs/debug.log'
    log = debug.read_text(errors='replace') if debug.exists() else ''
    state = progress(log, time.monotonic() - start, False)
    write_json(run / 'progress.json', state)
    checker_command = [sys.executable, str(ROOT / 'tools/check_test_run.py'), '--logs', str(run / 'logs'),
                       '--source-root', str(run / 'mod/tca_main')]
    if getattr(args, 'strict_title_heir', False):
        checker_command += ['--strict-title-heir']
    if getattr(args, 'case', None):
        checker_command += ['--case', args.case]
    checker = subprocess.run(checker_command, capture_output=True, text=True)
    (run / 'result.txt').write_text(checker.stdout + checker.stderr, encoding='utf-8')
    snapshot_issues = verify_snapshot(run)
    code = outcome(condition, state['observer_confirmed'], checker.returncode)
    if snapshot_issues:
        code = 2
        with (run / 'result.txt').open('a') as result:
            result.write('NOT VERIFIED\n' + '\n'.join(snapshot_issues) + '\n')
    write_json(run / 'terminal.json', {**state, 'condition': condition,
               'process_exit': process.returncode, 'verification_exit': checker.returncode,
               'runner_exit': code, 'snapshot_issues': snapshot_issues,
               'source_sha256': json.loads((run / 'source_manifest.json').read_text())['sha256']})
    print(f"Terminal: {condition}; observer confirmed: {state['observer_confirmed']}", flush=True)
    print(checker.stdout + checker.stderr, end='', flush=True)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, default=DEFAULT_GAME, help='CK3 installation root')
    parser.add_argument('--run-root', type=Path, default=Path(tempfile.gettempdir()) / 'tca-game-tests',
                        help='parent directory for fresh isolated runs (default: temporary directory)')
    parser.add_argument('--settings', type=Path, default=DEFAULT_SETTINGS,
                        help='read-only graphics/game preferences source; absent file uses defaults')
    parser.add_argument('--timeout', type=float, default=240, help='total startup/test timeout in seconds')
    parser.add_argument('--prepare-only', action='store_true', help='prepare isolated files without launching')
    parser.add_argument('--seed', type=int, help='native new-game random seed for reproducible regressions')
    parser.add_argument('--strict-title-heir', action='store_true', help='include strict preview-head succession acceptance')
    parser.add_argument('--case', help='run one registered delayed native case; default runs the full suite')
    args = parser.parse_args(argv)
    args.game_dir = args.game_dir.expanduser().resolve()
    if args.seed is not None and not 0 <= args.seed <= 0xFFFFFFFF:
        parser.error('--seed must be between 0 and 4294967295')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    try:
        if not args.prepare_only and not (args.game_dir / 'binaries/ck3.app/Contents/MacOS/ck3').is_file():
            raise ValueError('macOS CK3 executable missing; set --game-dir to the installation root')
        run = prepare_run(ROOT, args.run_root.expanduser().resolve(), args.settings.expanduser(), args.case)
        print(f'Fresh run directory: {run}', flush=True)
        if args.prepare_only:
            return 0
        return run_game(args, run)
    except (OSError, ValueError) as error:
        print(f'RUN FAILED: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
