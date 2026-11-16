#!/usr/bin/env python3
"""在独立可丢弃局中通过原生GUI发送厚礼／重金，并重启真实待回复存档。"""
import argparse
from collections import Counter
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from check_test_run import inspect_engine_errors, _debug_error_entries, _engine_entries
from run_game_tests import (ROOT, DEFAULT_GAME, DEFAULT_SETTINGS, prepare_run,
                            game_command, stop_owned_process, write_json,
                            seal_run, verify_snapshot)
from testing.runtime import engine_lock

EXPECTED = ('PLAYER', 'THICK_THIN_SELECTED', 'THICK_SELECTED', 'THICK_PAYMENT',
            'LAVISH_THIN_SELECTED', 'LAVISH_SELECTED', 'RELOADED_STATE', 'LAVISH_PAYMENT')
SAVE = 'tca_bribery_ui_pending'


def prepare_probe(args):
    """只在冻结副本适配层接入GUI；不改写正式模组的窗口或生产互动。"""
    run = prepare_run(ROOT, args.run_root, args.settings)
    adapter = run / 'mod/tca_cli_adapter'
    shutil.copytree(ROOT / 'tools/bribery_ui_probe', adapter, dirs_exist_ok=True)
    (adapter / 'common/on_action/tca_cli_on_actions.txt').write_text(
        'on_game_start_after_lobby = { on_actions = { tca_cli_start } }\n'
        'tca_cli_start = { effect = { if = { limit = { title:h_china = { NOT = { has_variable = tca_bui_stage } } } title:h_china.holder = { trigger_event = tca_bribery_ui_test.1 } } } }\n',
        encoding='utf-8-sig')
    gui = (adapter / 'gui/tca_bribery_ui_probe.gui').read_text(encoding='utf-8-sig')
    # 仅冻结验收适配层挂载驱动，保留原生窗口及全部发送逻辑。
    start = gui.index('widget = {\n name = "tca_bui_option_driver"')
    end = gui.index('# 保存真实待回复', start)
    driver = gui[start:end]
    gui = gui[:start] + gui[end:]
    (adapter / 'gui/tca_bribery_ui_probe.gui').write_text(gui, encoding='utf-8-sig')
    original = args.game_dir / 'game/gui/interaction_confirmation.gui'
    window = original.read_text(encoding='utf-8-sig')
    offset = window.index('{') + 1
    (adapter / 'gui/interaction_confirmation.gui').write_text(window[:offset] + '\n' + driver + window[offset:], encoding='utf-8-sig')
    intro = (args.game_dir / 'game/gui/event_windows/fullscreen_event.gui').read_text(encoding='utf-8-sig')
    intro = intro.replace('button_eventoption = {}', '''button_eventoption = {
        widget = { size = { 1 1 } visible_at_creation = no
          visible = "[And(GreaterThan_CFixedPoint(GetTitleByKey('h_china').MakeScope.Var('tca_bui_stage').GetValue, '(CFixedPoint)0'), LessThan_CFixedPoint(GetTitleByKey('h_china').MakeScope.Var('tca_bui_stage').GetValue, '(CFixedPoint)9'))]"
          state = { name = _show duration = 1 next = tca_bui_dismiss_intro }
          state = { name = tca_bui_dismiss_intro on_start = "[EventOption.Select]" }
        } }''')
    (adapter / 'gui/event_windows').mkdir(exist_ok=True)
    (adapter / 'gui/event_windows/fullscreen_event.gui').write_text(intro, encoding='utf-8-sig')
    # 此专用适配层不派发通用CLI入口；保留其变量声明与人工入口，标明首入口刻意闲置。
    cli_events = adapter / 'events/tca_cli_events.txt'
    cli_events.write_text(cli_events.read_text(encoding='utf-8-sig').replace(
        'tca_cli.1 = {', 'tca_cli.1 = {\n orphan = yes'), encoding='utf-8-sig')
    widgets = re.findall(r'^ name = "([^"]+)"', gui, re.M)
    (adapter / 'gui/scripted_widgets/tca_cli_widgets.txt').write_text(
        ''.join(f'gui/tca_bribery_ui_probe.gui = {name}\n' for name in widgets), encoding='utf-8-sig')
    shutil.copy2(Path(__file__), run / 'tools/run_bribery_ui_probe.py')
    seal_run(run)
    return run


def native_markers(log):
    """忽略控制台回显，仅认效果真正输出的协议行。"""
    return [line for line in log.splitlines()
            if 'jomini_effect_impl.cpp' in line and ': TCA_BUI_' in line]


def inspect(logs, errors, phases):
    entries = list(_engine_entries(errors))
    entries += list(_debug_error_entries(logs, set(entries)))
    issues = inspect_engine_errors(''.join(entries))
    # 两个临时原生窗口插桩只存在适配层；其错误也必须阻止验收。
    issues += [entry for entry in entries if any(path in entry for path in (
        'interaction_confirmation.gui', 'event_windows/fullscreen_event.gui'))]
    markers = native_markers(logs)
    counts = Counter(line.rsplit('TCA_BUI_PASS_', 1)[1].strip()
                     for line in markers if 'TCA_BUI_PASS_' in line)
    for key in EXPECTED:
        if counts[key] != 1:
            issues.append(f'{key}: expected once, got {counts[key]}')
    issues += [line for line in markers if 'TCA_BUI_FAIL_' in line or 'PRECONDITION_FAIL' in line]
    for key in ('TCA_BUI_FIXTURE_READY', 'TCA_BUI_RELOAD_READY',
                'TCA_BUI_DESTROYED_LIVE_STATE', 'TCA_BUI_COMPLETE'):
        if sum(line.endswith(key) for line in markers) != 1:
            issues.append(f'{key}: missing or duplicated')
    if phases != 2:
        issues.append('Expected two real process phases')
    return issues, dict(counts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, default=DEFAULT_GAME)
    parser.add_argument('--settings', type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument('--run-root', type=Path, default=Path(tempfile.gettempdir()) / 'tca-bribery-ui')
    parser.add_argument('--timeout', type=float, default=360)
    parser.add_argument('--seed', type=int, default=424242)
    args = parser.parse_args(argv)
    run = prepare_probe(args)
    print(f'GUI task {run.name}: {run}', flush=True)
    env = os.environ.copy()
    env['SteamAppId'] = '1158310'
    phase_logs, phase_errors = [], []
    condition, phases = 'timeout', 0
    with engine_lock(task_id=run.name):
        for phase in (1, 2):
            phases = phase
            if phase == 2:
                shutil.copy2(run / 'inputs/pdx_settings.txt', run / 'pdx_settings.txt')
            if (run / 'inputs/pdx_settings.txt').read_bytes() != (run / 'pdx_settings.txt').read_bytes():
                raise ValueError('Runtime preferences changed before launch')
            command = game_command(args, run, SAVE if phase == 2 else None)
            archive = run / f'phase-{phase}'
            archive.mkdir()
            with (archive / 'stdout.txt').open('w') as output:
                process = subprocess.Popen(command, cwd=args.game_dir / 'binaries', env=env,
                                           stdout=output, stderr=subprocess.STDOUT)
                process_record = {'pid': process.pid, 'args': command, 'owned': True}
                write_json(archive / 'process.json', process_record)
                write_json(run / 'process.json', process_record)
                started, previous = time.monotonic(), None
                try:
                    while time.monotonic() - started < args.timeout:
                        path = run / 'logs/debug.log'
                        debug = path.read_text(errors='replace') if path.exists() else ''
                        markers = native_markers(debug)
                        if markers and markers[-1] != previous:
                            previous = markers[-1]
                            print(f'phase {phase}: {previous}', flush=True)
                        if any('TCA_BUI_FAIL_' in line or 'TCA_BUI_PRECONDITION_FAIL' in line for line in markers):
                            condition = 'failed'
                            break
                        if any(line.endswith('TCA_BUI_COMPLETE') for line in markers):
                            condition = 'complete'
                            break
                        if phase == 1 and any(line.endswith('TCA_BUI_RELOAD_READY') for line in markers):
                            save = run / 'save games' / (SAVE + '.ck3')
                            if save.is_file() and 'console_success: Game saved to ' + SAVE in debug:
                                condition = 'checkpoint'
                                break
                        if process.poll() is not None:
                            condition = 'process_exit'
                            break
                        time.sleep(1)
                finally:
                    stop_owned_process(process)
            for name in ('debug.log', 'error.log', 'game.log'):
                path = run / 'logs' / name
                if path.exists():
                    shutil.copy2(path, archive / name)
            phase_logs.append((archive / 'debug.log').read_text(errors='replace') if (archive / 'debug.log').exists() else '')
            phase_errors.append((archive / 'error.log').read_text(errors='replace') if (archive / 'error.log').exists() else '')
            if phase == 1 and condition == 'checkpoint':
                continue
            break
    debug, errors = '\n'.join(phase_logs), '\n'.join(phase_errors)
    issues, counts = inspect(debug, errors, phases)
    issues += verify_snapshot(run)
    if condition != 'complete':
        issues.append(f'Terminal condition: {condition}')
    code = int(bool(issues))
    write_json(run / 'terminal.json', {'condition': condition, 'phases': phases, 'checks': counts,
                                      'issues': issues, 'runner_exit': code, 'verification_exit': code})
    result = ('NOT VERIFIED\n' + '\n'.join(issues)) if issues else 'OK: real GUI offers and pending-request reload passed; no detected mod-related engine errors'
    (run / 'result.txt').write_text(result + '\n')
    print(result, flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
