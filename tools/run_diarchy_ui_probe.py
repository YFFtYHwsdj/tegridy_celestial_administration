#!/usr/bin/env python3
"""在可丢弃的图形游戏局中运行可选原生 GUI 控制器回归。"""
import argparse
import json
from collections import Counter
from pathlib import Path
import shutil
import subprocess
import os
import re
import tempfile
import time

from check_test_run import inspect_engine_errors
from check_upstream_overrides import tokens
from run_game_tests import (ROOT, DEFAULT_GAME, DEFAULT_SETTINGS, prepare_run,
                            game_command, stop_owned_process, write_json, seal_run, verify_snapshot)

EXPECTED = ('WINDOW', 'GOVERNOR', 'SELF', 'LIEGE', 'TONGPAN', 'RETURN', 'END_SYSTEM')


def inspect_probe(debug, errors):
    issues = inspect_engine_errors(errors)
    if any('jomini_effect_impl.cpp' in line and 'TCA_GUI_FAIL_' in line for line in debug.splitlines()):
        issues.append('GUI acceptance assertion failed')
    if debug.count('TCA_GUI_FIXTURE_READY') != 1:
        issues.append('Three-owner fixture was not confirmed exactly once')
    if 'TCA_GUI_PRECONDITION_FAIL' in debug:
        issues.append('Fixture preconditions failed')
    counts = Counter()
    for line in debug.splitlines():
        # 控制台命令跟踪可能回显命令文本，只有效果输出才算证据。
        if 'jomini_effect_impl.cpp' in line and 'TCA_GUI_PASS_' in line:
            counts[line.rsplit('TCA_GUI_PASS_', 1)[1].strip()] += 1
    for step in EXPECTED:
        if counts[step] != 1:
            issues.append(f'{step}: expected one GUI result, got {counts[step]}')
    if any(step not in EXPECTED for step in counts):
        issues.append('Unexpected GUI results')
    if not any('jomini_effect_impl.cpp' in line and line.rstrip().endswith('TCA_GUI_COMPLETE')
               for line in debug.splitlines()):
        issues.append('GUI sequence did not complete')
    return issues, counts


def tab_probe_templates(window):
    """复用实际 GUI 回调，不在探针中重新实现控制器逻辑。"""
    result = []
    for name in ('self', 'liege', 'tongpan'):
        match = re.search(r'template tca_diarchy_select_' + name + r' \{([^{}]+)\}', window)
        if match is None or len(re.findall(r'\bonclick\s*=', match[1])) != 2:
            raise ValueError(f'Missing or unexpected tab callbacks: {name}')
        result.append('template tca_gui_probe_select_' + name + ' {' +
                      match[1].replace('onclick', 'on_start') + '}')
    return '\n'.join(result) + '\n'


def named_widget_tokens(source, name):
    stream = tokens(source)
    stack = []
    for index, token in enumerate(stream):
        if token == '{':
            stack.append(index)
        elif token == '}':
            stack.pop()
        elif stream[index:index + 3] == ['name', '=', '"' + name + '"']:
            opening = stack[-1]
            depth = 1
            end = opening + 1
            while end < len(stream) and depth:
                depth += (stream[end] == '{') - (stream[end] == '}')
                end += 1
            return stream[opening:end]
    raise ValueError('Missing widget: ' + name)



def validate_succession_geometry(window):
    custom = named_widget_tokens(window, 'tca_tongpan_title_succession')
    native = named_widget_tokens(window, 'regent_succession_tutorial_uses_this')
    for field in ('addcolumn', 'addrow', 'flipdirection', 'maxhorizontalslots'):
        def values(body):
            return [body[i+2] for i in range(len(body)-2) if body[i:i+2] == [field, '=']]
        if not values(native) or values(custom) != values(native):
            raise ValueError('Succession grid differs from vanilla layout: ' + field)
    for body in (custom, native):
        item = body.index('item')
        if body[item:item+6] != ['item', '=', '{', 'widget', '=', '{']:
            raise ValueError('Succession cell must use a bounded widget, not a layout box')
    def cell_size(body):
        tail = body[body.index('item') + 6:]
        index = tail.index('size')
        return tail[index:index+6]
    if cell_size(custom) != cell_size(native):
        raise ValueError('Succession cell size differs from vanilla')


def bind_tab_selections(source, window):
    """断言实际按下状态条件，并拒绝多个标签同时选中。"""
    names = {'SELF': 'your_regent_tab_tutorial_uses_this',
             'LIEGE': 'liege_tab_tutorial_uses_this',
             'TONGPAN': 'tca_tongpan_relation_tab'}
    for key, name in names.items():
        match = re.search(r'name = "' + name + r'"([^{}]+)\}', window)
        predicates = re.findall(r'\bdown = "\[(.*?)\]"', match[1]) if match else []
        if len(predicates) != 1:
            raise ValueError(f'Missing or ambiguous tab selection: {name}')
        source = source.replace('@SELECT_' + key + '@', predicates[0])
    if '@SELECT_' in source:
        raise ValueError('Unbound tab selection placeholder')
    return source


def prepare_probe(args):
    run = prepare_run(ROOT, args.run_root, args.settings)
    adapter = run / 'mod/tca_cli_adapter'
    shutil.copytree(ROOT / 'tools/diarchy_ui_probe', adapter, dirs_exist_ok=True)
    # 在离开大厅后的初始化中准备原生夹具，早于 GUI 绑定建立。
    # 无需推进模拟日期，GUI 控制器序列在暂停状态下运行。
    startup = adapter / 'common/on_action/tca_cli_on_actions.txt'
    startup.write_text('on_game_start_after_lobby = { on_actions = { tca_cli_start } }\ntca_cli_start = { effect = { title:h_china.holder = { trigger_event = tca_diarchy_ui_probe.1 } } }\n', encoding='utf-8-sig')
    registration = adapter / 'gui/scripted_widgets/tca_cli_widgets.txt'
    registration.write_text('gui/tca_diarchy_ui_probe.gui = tca_gui_probe_start\ngui/tca_diarchy_ui_probe.gui = tca_gui_end_unpause\n', encoding='utf-8-sig')
    (adapter / 'events/tca_cli_events.txt').unlink()
    # 保留原生控制器上下文，把真实标签回调复制到
    # 可选断言状态中；阶段变量仅属于本窗口。
    window = (run / 'mod/tca_main/gui/window_diarchy.gui').read_text(encoding='utf-8-sig')
    validate_succession_geometry(window)
    probe_gui = adapter / 'gui/tca_diarchy_ui_probe.gui'
    probe_gui.write_text(bind_tab_selections(probe_gui.read_text(encoding='utf-8-sig'), window) +
                         tab_probe_templates(window), encoding='utf-8-sig')
    window = window.replace('widgetid = "diarchy_window"',
                            'widgetid = "diarchy_window"\n    using = tca_gui_probe_sequence', 1)
    (adapter / 'gui/window_diarchy.gui').write_text(window, encoding='utf-8-sig')
    seal_run(run)
    return run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, default=DEFAULT_GAME)
    parser.add_argument('--settings', type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument('--run-root', type=Path,
                        default=Path(tempfile.gettempdir()) / 'tca-diarchy-ui')
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--seed', type=int, default=1538798675)
    args = parser.parse_args(argv)
    if args.timeout <= 0 or not 0 <= args.seed <= 0xFFFFFFFF:
        parser.error('positive timeout and uint32 seed required')
    run = prepare_probe(args)
    print(f'Fresh GUI probe directory: {run}', flush=True)
    env = os.environ.copy()
    env['SteamAppId'] = '1158310'
    command = game_command(args, run)
    started = time.monotonic()
    condition = 'timeout'
    with (run / 'stdout.txt').open('w') as output:
        process = subprocess.Popen(command, cwd=args.game_dir / 'binaries', env=env,
                                   stdout=output, stderr=subprocess.STDOUT)
        write_json(run / 'process.json', {'pid': process.pid, 'args': command, 'owned': True})
        try:
            previous = None
            last_progress = time.monotonic()
            while time.monotonic() - started < args.timeout:
                path = run / 'logs/debug.log'
                debug = path.read_text(errors='replace') if path.exists() else ''
                markers = [line for line in debug.splitlines()
                           if 'TCA_GUI_' in line and 'jomini_effect_impl.cpp' in line]
                write_json(run / 'progress.json', {'seconds': round(time.monotonic() - started, 1),
                                                   'markers': markers[-8:]})
                if markers and markers[-1] != previous:
                    previous = markers[-1]
                    last_progress = time.monotonic()
                    print(previous, flush=True)
                if any(line.rstrip().endswith('TCA_GUI_COMPLETE') for line in markers):
                    condition = 'complete'
                    break
                if 'TCA_GUI_PRECONDITION_FAIL' in debug:
                    condition = 'precondition_failed'
                    break
                if markers and time.monotonic() - last_progress > 25:
                    condition = 'stalled'
                    break
                if process.poll() is not None:
                    condition = 'process_exit'
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            condition = 'interrupted'
        finally:
            stop_owned_process(process)
    path = run / 'logs/debug.log'
    debug = path.read_text(errors='replace') if path.exists() else ''
    path = run / 'logs/error.log'
    errors = path.read_text(errors='replace') if path.exists() else ''
    issues, counts = inspect_probe(debug, errors)
    issues.extend(verify_snapshot(run))
    if condition != 'complete':
        issues.append(f'Terminal condition: {condition}')
    result = ('NOT VERIFIED\n' + '\n'.join(issues)) if issues else 'OK: all GUI controller and end-system acceptance checks passed; no detected mod-related engine errors'
    (run / 'result.txt').write_text(result + '\n')
    code = 1 if issues else 0
    failures = [line for line in debug.splitlines()
                if 'jomini_effect_impl.cpp' in line and 'TCA_GUI_FAIL_' in line]
    coverage = {step: ('FAIL' if any('TCA_GUI_FAIL_' + step in line for line in failures)
                       else 'PASS' if counts[step] == 1 else 'NOT_VERIFIED') for step in EXPECTED}
    write_json(run / 'terminal.json', {'condition': condition, 'checks': dict(counts),
                                      'coverage': coverage, 'failures': failures,
                                      'source_sha256': json.loads((run / 'source_manifest.json').read_text())['sha256'],
                                      'verification_exit': code, 'runner_exit': code,
                                      'process_exit': process.returncode})
    print(result, flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
