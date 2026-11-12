"""启动隔离及结果测试，不模拟 CK3 规则。"""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from run_game_tests import (ROOT, LogTailReader, RunLogMonitor, game_command, descriptor, isolated_settings,
                            outcome, prepare_run, progress, reload_request, stop_owned_process,
                            terminal_condition, timeout_warning)
from check_upstream_overrides import definitions


class GameRunnerTests(unittest.TestCase):
    def test_checkpoint_stop_rejects_already_exited_or_unexpected_exit(self):
        process = Mock()
        process.poll.return_value = 0
        with self.assertRaises(ValueError):
            stop_owned_process(process, require_running=True)
        process.terminate.assert_not_called()
        if sys.platform != 'win32':
            process.poll.return_value = None
            process.returncode = 42
            with self.assertRaises(ValueError):
                stop_owned_process(process, require_running=True)

    def test_reload_launch_failure_keeps_raw_evidence_and_terminal(self):
        from run_game_tests import run_game
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'binaries').mkdir()
            run = prepare_run(ROOT, root/'runs', root/'absent', 'tca_exam_test.1')
            (run/'logs').mkdir()
            (run/'logs/debug.log').write_text('console_success: Going to observe mode\n'
                'console_success: Game saved to probe\nTCA_CLI RELOAD_SAVE probe\n')
            (run/'save games').mkdir()
            (run/'save games/probe.ck3').write_bytes(b'SAV' + b'x'*100)
            args = SimpleNamespace(game_dir=root, seed=None, timeout=30, strict_title_heir=False)
            def command(_args, target, save_name=None):
                return [str(root/'missing-executable')] if save_name else [sys.executable, '-c', 'import time; time.sleep(20)']
            with patch('run_game_tests.game_command', side_effect=command):
                self.assertEqual(run_game(args, run), 2)
            terminal = json.loads((run/'terminal.json').read_text())
            self.assertEqual(terminal['condition'], 'reload_launch_failed')
            self.assertIsNone(terminal['process_exit'])
            self.assertTrue((run/'phases/1/logs/debug.log').is_file())
            self.assertIn('RELOAD_SAVE probe', (run/'logs/debug.log').read_text())

    def test_resume_command_loads_named_save_with_same_test_ruler_without_new_world_or_seed(self):
        args = SimpleNamespace(game_dir=Path('/tmp/game'), seed=123)
        command = game_command(args, Path('/tmp/run'), save_name='probe')
        self.assertIn('-loadsave=probe.ck3', command)
        self.assertIn('-play=h_china', command)
        self.assertFalse(any(arg.startswith(('-bookmark=', '-random_seed=')) for arg in command))
        with self.assertRaises(ValueError):
            game_command(args, Path('/tmp/run'), save_name='../outside')

    def test_reload_request_requires_successful_save_and_existing_local_file(self):
        from run_game_tests import reload_request
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            log = 'TCA_CLI RELOAD_SAVE probe'
            with self.assertRaises(ValueError):
                reload_request(log, run)
            log = 'console_success: Game saved to probe\n' + log
            with self.assertRaises(ValueError):
                reload_request(log, run)
            (run/'save games').mkdir()
            (run/'save games/probe.ck3').write_bytes(b'SAV' + b'x'*100)
            self.assertEqual(reload_request(log, run), 'probe')
            self.assertIsNone(reload_request('ordinary output', run))
            with self.assertRaises(ValueError):
                reload_request(log + '\nTCA_CLI RELOAD_SAVE probe', run)
            with self.assertRaises(ValueError):
                reload_request('TCA_CLI RELOAD_SAVE ../outside', run)

    def test_checkpoint_tokens_are_independently_single_use_and_human_is_last(self):
        from run_game_tests import checkpoint_request
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run/'save games').mkdir()
            for name in ('probe', 'tca_cli_human_session'):
                (run/'save games'/f'{name}.ck3').write_bytes(b'SAV' + b'x'*100)
            (run/'selection.json').write_text(json.dumps({'cases': [{'event': 'tca_retirement_session.1'}]}))
            regular = 'console_success: Game saved to probe\nTCA_CLI RELOAD_SAVE probe'
            human = 'console_success: Game saved to tca_cli_human_session\nTCA_CLI HUMAN_SAVE tca_cli_human_session'
            self.assertEqual(checkpoint_request(regular, run, set()), ('reload', 'probe'))
            self.assertEqual(checkpoint_request(human, run, {'reload'}), ('human', 'tca_cli_human_session'))
            self.assertEqual(checkpoint_request(human, run, set()), ('human', 'tca_cli_human_session'))
            for log, used in ((regular, {'reload'}), (human, {'human'}),
                              (regular, {'human'}), (regular+'\n'+human, set())):
                with self.subTest(log=log, used=used), self.assertRaises(ValueError):
                    checkpoint_request(log, run, used)
            with self.assertRaises(ValueError):
                checkpoint_request(human.replace('tca_cli_human_session', 'wrong'), run, set())
            (run/'selection.json').write_text(json.dumps({'cases': []}))
            with self.assertRaises(ValueError):
                checkpoint_request(human, run, set())

    def test_checkpoint_parser_counts_native_output_without_console_command_echo(self):
        from run_game_tests import checkpoint_request
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run/'save games').mkdir()
            (run/'save games/tca_cli_human_session.ck3').write_bytes(b'SAV' + b'x'*100)
            (run/'selection.json').write_text(json.dumps({'cases': [{'event': 'tca_retirement_session.1'}]}))
            saved = '[08:55:39][D][console.cpp:1193]: console_success: Game saved to tca_cli_human_session'
            # 实际run-esbkntx5的命令回显与debug_log输出是两条不同日志；回显本身不是请求。
            echo = '[08:55:44][D][console.cpp:1164]: Running console command: effect title:h_china = { debug_log = "TCA_CLI HUMAN_SAVE tca_cli_human_session" }'
            native = '[08:55:44][D][jomini_effect_impl.cpp:450]: file: effect console command line: 1: TCA_CLI HUMAN_SAVE tca_cli_human_session'
            self.assertIsNone(checkpoint_request(saved+'\n'+echo, run, set()))
            self.assertEqual(checkpoint_request('\n'.join((saved, echo, native)), run, set()),
                             ('human', 'tca_cli_human_session'))
            with self.assertRaises(ValueError):
                checkpoint_request('\n'.join((saved, echo, native, native)), run, set())
            # 原生输出中的非法路径仍须报错，不能被锚定规则静默忽略。
            with self.assertRaises(ValueError):
                reload_request('[D][jomini_effect_impl.cpp:450]: TCA_CLI RELOAD_SAVE ../outside', run)

    def test_human_phase_requires_native_identity_then_transfer_then_observer(self):
        from run_game_tests import human_phase_issues
        log = '\n'.join(['TCA_RETIREMENT_HUMAN INITIAL_PLAYER_CONFIRMED',
            'TCA_TEST BEGIN tca_retirement_session.1 tca_test_retirement_player_session',
            'TCA_RETIREMENT_SESSION PLAYER_CONFIRMED',
            'TCA_TEST CHECK_PASS tca_test_retirement_player_session 4',
            'console_success: Going to observe mode',
            'TCA_TEST CHECK_PASS tca_test_retirement_player_session 5'])
        self.assertEqual(human_phase_issues(log), [])
        self.assertTrue(human_phase_issues(log.replace('INITIAL_PLAYER_CONFIRMED', 'NOT_HUMAN')))
        self.assertTrue(human_phase_issues(log.replace('TCA_RETIREMENT_SESSION PLAYER_CONFIRMED', '')))
        self.assertTrue(human_phase_issues('console_success: Going to observe mode\n'+log))
        self.assertTrue(human_phase_issues(log.replace('console_success: Going to observe mode', '')))

    def test_cli_human_stage_is_wired_without_an_early_observe_or_suite_redispatch(self):
        # 冻结适配器只在原生确认人类身份后续接被认领的同一个用例。
        events = definitions((ROOT/'tools/cli_adapter/events/tca_cli_events.txt').read_text(encoding='utf-8-sig'))
        boot = ' '.join(events['tca_cli.2'])
        self.assertIn('orphan = yes', boot)
        self.assertIn('is_ai = no', boot)
        self.assertIn('INITIAL_PLAYER_CONFIRMED', boot)
        self.assertIn('trigger_event = tca_retirement_session.1', boot)
        self.assertNotIn('tca_run_observer_tests_effect', boot)
        gui = (ROOT/'tools/cli_adapter/gui/tca_cli_widgets.gui').read_text(encoding='utf-8-sig')
        self.assertIn("Var('tca_cli_human_phase')", gui)
        native = definitions((ROOT/'events/tests/tca_retirement_session_test_events.txt').read_text(encoding='utf-8-sig'))
        session = ' '.join(native['tca_retirement_session.1'])
        self.assertIn('tca_cli_human_phase', session)
        self.assertIn('debug_only = yes is_ai = no title:h_china.holder = root', session)
        self.assertIn('TCA_TEST BEGIN tca_retirement_session.1', session)

    def test_human_event_handlers_live_in_native_windows_and_preserve_original_bytes(self):
        # 顶层自动widget没有EventWindow实例；适配器只在两个真实窗口内添加同一控件。
        import hashlib
        expected = {
            'letter_event': 'eb141a50868cd0f32cb9327630a895024edaa9e7580ab4520be88032bfc4ee8c',
            'character_event': 'b0c3efdd81d08e4682c6bdfa9c4fff76351083359b642e9420b8b9d389c6f2e9',
        }
        for name, digest in expected.items():
            raw = (ROOT / f'tools/cli_adapter/gui/event_windows/{name}.gui').read_bytes()
            start = raw.index(b'\t# TCA_CLI_NATIVE_EVENT_BEGIN')
            end = raw.index(b'\t# TCA_CLI_NATIVE_EVENT_END', start)
            end = raw.index(b'\n', end) + 1
            block = raw[start:end].decode('utf-8')
            self.assertIn('EventWindow.IsOnTop', block)
            self.assertIn('EventOption.IsValid', block)
            self.assertIn("'(CFixedPoint)3'", block)
            self.assertIn('EventOption.Select', block)
            self.assertIn('PdxGuiWidget.GetIndexInDataModel', block)
            commands = [line.strip() for line in block.splitlines() if 'ExecuteConsoleCommand' in line]
            self.assertEqual(len(commands), 1)
            self.assertIn(f'TCA_CLI HUMAN_NATIVE_OPTION {name}', commands[0])
            self.assertIn('effect debug_log =', commands[0])
            self.assertNotIn('trigger_event', block)
            self.assertNotIn('OnPause', block)
            self.assertEqual(hashlib.sha256(raw[:start] + raw[end:]).hexdigest(), digest)
        registration = (ROOT / 'tools/cli_adapter/gui/scripted_widgets/tca_cli_widgets.txt').read_text(encoding='utf-8-sig')
        self.assertNotIn('= tca_cli_human_event_continue', registration)

    def test_human_entry_explicitly_exercises_native_letter_and_character_windows(self):
        # 两个原版debug事件均只有无副作用的真实选项；必须在is_ai确认后才触发。
        native = ' '.join(definitions((ROOT/'tools/cli_adapter/events/tca_cli_events.txt').read_text(encoding='utf-8-sig'))['tca_cli.2'])
        for event in ('debug.1004', 'debug.1005'):
            call = f'trigger_event = {event}'
            self.assertIn(call, native)
            self.assertLess(native.index('is_ai = no'), native.index(call))
            self.assertLess(native.index('name = tca_cli_human_phase value = 3'), native.index(call))
            self.assertLess(native.index(call), native.index('trigger_event = tca_retirement_session.1'))

    def test_human_checkpoint_widget_survives_prepare_and_cannot_restart_after_load(self):
        # 此处检查GUI生命周期接线；原生保存与实际续局仍必须由引擎验收。
        gui = (ROOT/'tools/cli_adapter/gui/tca_cli_human_checkpoint.gui').read_text(encoding='utf-8-sig')
        widget = gui.split('name = "tca_cli_human_checkpoint"', 1)[1].split('# 关闭CLI自动恢复暂停后才停靠', 1)[0]
        visible = next(line for line in widget.splitlines() if line.strip().startswith('visible ='))
        self.assertIn("Or(EqualTo_CFixedPoint(Title.MakeScope.Var('tca_cli_human_phase').GetValue, '(CFixedPoint)1'), And(EqualTo_CFixedPoint(Title.MakeScope.Var('tca_cli_human_phase').GetValue, '(CFixedPoint)2'), GetVariableSystem.HasValue('tca_cli_human_started', 'yes')))", visible)
        show = widget.split('name = _show', 1)[1].split('next = tca_cli_human_prepare', 1)[0]
        self.assertIn("GetVariableSystem.Set('tca_cli_human_started', 'yes')", show)
        request = widget.split('name = tca_cli_human_request', 1)[1]
        self.assertIn("Not(GetVariableSystem.HasValue('tca_cli_human_requested', 'yes'))", request)
        self.assertIn("GetVariableSystem.Set('tca_cli_human_requested', 'yes')", request)
        self.assertIn('TCA_CLI HUMAN_SAVE tca_cli_human_session', request)

    def test_native_load_human_boot_uses_fresh_gui_and_confirms_before_phase_three(self):
        # -loadsave不依赖退出新开局大厅的回调；新进程UI不带首进程started标记。
        gui = (ROOT/'tools/cli_adapter/gui/tca_cli_human_checkpoint.gui').read_text(encoding='utf-8-sig')
        boot = gui.split('name = "tca_cli_human_load_boot"', 1)[1]
        self.assertIn("EqualTo_CFixedPoint(Title.MakeScope.Var('tca_cli_human_phase').GetValue, '(CFixedPoint)2')", boot)
        self.assertIn("Not(GetVariableSystem.HasValue('tca_cli_human_started', 'yes'))", boot)
        self.assertIn("Not(GetVariableSystem.HasValue('tca_cli_human_booted', 'yes'))", boot)
        self.assertIn('trigger_event = tca_cli.2', boot)
        self.assertNotIn('tca_retirement_human_run', boot)
        self.assertNotIn('name = tca_cli_human_phase value = 3', boot)
        events = definitions((ROOT/'tools/cli_adapter/events/tca_cli_events.txt').read_text(encoding='utf-8-sig'))
        native = ' '.join(events['tca_cli.2'])
        self.assertIn('var:tca_cli_human_phase ?= 2', native)
        self.assertIn('is_ai = no', native)
        self.assertIn('has_character_flag = tca_test_lane_tca_retirement_session_active', native)
        self.assertLess(native.index('is_ai = no'), native.index('name = tca_cli_human_phase value = 3'))
        action = (ROOT/'tools/cli_adapter/common/on_action/tca_cli_on_actions.txt').read_text(encoding='utf-8-sig')
        self.assertNotIn('name = tca_cli_human_phase value = 3', action)

    def test_player_transfer_request_is_consumed_by_original_native_reporter_once(self):
        # GUI只提交请求，原生链负责保持原报告者、消费防重及真实两日等待。
        effects = definitions((ROOT/'common/scripted_effects/tests/fixtures/tca_retirement_session_probe_effects.txt').read_text(encoding='utf-8-sig'))
        gui = ' '.join(effects['tca_retirement_session_gui_transfer_effect'])
        self.assertNotIn('trigger_event', gui)
        self.assertIn('name = tca_retirement_session_transfer_request value = 1', gui)
        self.assertIn('tca_retirement_session_transfer_queued', gui)
        events = definitions((ROOT/'events/tests/tca_retirement_session_test_events.txt').read_text(encoding='utf-8-sig'))
        prepare = ' '.join(events['tca_retirement_session.1001'])
        self.assertIn('id = tca_retirement_session.1010 days = 1', prepare)
        watcher = ' '.join(events['tca_retirement_session.1010'])
        self.assertIn('tca_test_validate_environment_effect = yes', watcher)
        self.assertIn('has_character_flag = tca_test_lane_tca_retirement_session_active', watcher)
        self.assertIn('name = tca_retirement_session_transfer_request value = 0', watcher)
        self.assertIn('name = tca_retirement_session_transfer_queued value = 1', watcher)
        self.assertIn('id = tca_retirement_session.1002 days = 2', watcher)
        transfer = ' '.join(events['tca_retirement_session.1002'])
        # 延迟入口先通过共同环境守门，再记录业务入口；不能为诊断绕过统一中止契约。
        self.assertLess(transfer.index('tca_test_validate_environment_effect'), transfer.index('TRANSFER_EVENT_ENTERED'))
        self.assertLess(transfer.index('TRANSFER_EVENT_ENTERED'), transfer.index('name = tca_retirement_session_phase value = 2'))
        self.assertIn('is_ai = no', transfer)

    def test_phase_archive_and_merge_preserve_every_raw_error_and_assertion(self):
        from run_game_tests import archive_phase_logs, merge_phase_logs
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run/'logs').mkdir()
            first = {'debug.log': b'BEGIN\nCHECK_PASS 1\n', 'error.log': b'first error\n'}
            second = {'debug.log': b'CHECK_FAIL 2\n', 'error.log': b'second error\n'}
            for name, data in first.items():
                (run/'logs'/name).write_bytes(data)
            archive_phase_logs(run, 1)
            for name, data in second.items():
                (run/'logs'/name).write_bytes(data)
            archive_phase_logs(run, 2)
            merge_phase_logs(run, 2)
            for name in first:
                self.assertEqual((run/'logs'/name).read_bytes(), first[name] + second[name])
                self.assertEqual((run/'phases/1/logs'/name).read_bytes(), first[name])
                self.assertEqual((run/'phases/2/logs'/name).read_bytes(), second[name])

    def test_two_real_processes_resume_log_protocol_without_redispatch(self):
        self._check_two_process_resume(True)

    def test_resume_cannot_reuse_first_process_observer_confirmation(self):
        self._check_two_process_resume(False)

    def _check_two_process_resume(self, resume_observer):
        """用短命子进程验证续局控制器与冻结验收器，不模拟任何游戏规则。"""
        from run_game_tests import run_game
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'binaries').mkdir()
            emitter = root/'emit.py'
            emitter.write_text('''from pathlib import Path
import json, sys, time
run = Path(sys.argv[1])
resume = sys.argv[2] == 'resume'
(run/'logs').mkdir(exist_ok=True)
name = 'tca_test_exam_contract'
# 日志夹具按冻结计划分成两段，科举扩充断言不会使控制器测试读到旧总数。
checks = json.loads((run/'selection.json').read_text())['cases'][0]['checks']
split = checks // 2 + 1
lines = []
if not resume:
    (run/'save games').mkdir()
    (run/'save games/probe.ck3').write_bytes(b'SAV' + b'x'*100)
    lines += ['TCA_TEST SUITE_DISPATCH',
              'TCA_TEST BEGIN tca_exam_test.1 ' + name]
if not resume or sys.argv[3] == 'yes':
    lines += ['console_success: Going to observe mode']
lines += [f'TCA_TEST CHECK_PASS {name} {i}' for i in (range(split, checks + 1) if resume else range(1, split))]
lines += ([f'TCA_TEST PASS {name}', 'TCA_TEST SUITE_ALL_PASSED'] if resume else
          ['console_success: Game saved to probe', 'TCA_CLI RELOAD_SAVE probe'])
(run/'logs/debug.log').write_text('\\n'.join(lines) + '\\n')
(run/'logs/error.log').write_text('')
time.sleep(20)
''', encoding='utf-8')
            run = prepare_run(ROOT, root/'runs', root/'absent', 'tca_exam_test.1')
            args = SimpleNamespace(game_dir=root, seed=None, timeout=30, strict_title_heir=False)
            def command(_args, target, save_name=None):
                return [sys.executable, str(emitter), str(target), 'resume' if save_name else 'start',
                        'yes' if resume_observer else 'no']
            with patch('run_game_tests.game_command', side_effect=command):
                self.assertEqual(run_game(args, run), 0 if resume_observer else 2)
            self.assertEqual(json.loads((run/'terminal.json').read_text())['observer_confirmed'], resume_observer)
            log = (run/'logs/debug.log').read_text()
            self.assertEqual(log.count('TCA_TEST SUITE_DISPATCH'), 1)
            self.assertEqual(log.count('TCA_TEST BEGIN'), 1)
            self.assertEqual(log.count('TCA_TEST CHECK_PASS'),
                             json.loads((run/'selection.json').read_text())['cases'][0]['checks'])
            self.assertEqual(json.loads((run/'terminal.json').read_text())['phases'], 2)
            evidence = json.loads((run/'reload_evidence.json').read_text())
            self.assertEqual(len(evidence['raw_logs']), 4)

    def test_three_processes_keep_both_checkpoint_tokens_and_native_human_evidence(self):
        self._check_human_process_protocol(False)

    def test_human_process_early_observe_cannot_be_hidden_by_final_observe(self):
        self._check_human_process_protocol(True)

    def _check_human_process_protocol(self, early_observe):
        """只用日志协议夹具验证进程、封存与验收控制器；不模拟玩家或退休业务。"""
        from run_game_tests import run_game
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'binaries').mkdir()
            emitter = root/'emit.py'
            emitter.write_text('''from pathlib import Path
import sys, time
run = Path(sys.argv[1])
phase = sys.argv[2]
(run/'logs').mkdir(exist_ok=True)
(run/'save games').mkdir(exist_ok=True)
name = 'tca_test_retirement_player_session'
if phase == 'start':
    (run/'save games/probe.ck3').write_bytes(b'SAV' + b'x'*100)
    lines = ['TCA_TEST SUITE_DISPATCH', 'console_success: Going to observe mode',
             'console_success: Game saved to probe', 'TCA_CLI RELOAD_SAVE probe']
elif phase == 'probe':
    (run/'save games/tca_cli_human_session.ck3').write_bytes(b'SAV' + b'x'*100)
    lines = ['console_success: Going to observe mode',
             'console_success: Game saved to tca_cli_human_session',
             'TCA_CLI HUMAN_SAVE tca_cli_human_session']
else:
    lines = ['console_success: Going to observe mode'] if sys.argv[3] == 'early' else []
    lines += ['TCA_RETIREMENT_HUMAN INITIAL_PLAYER_CONFIRMED',
              'TCA_TEST BEGIN tca_retirement_session.1 ' + name,
              'TCA_RETIREMENT_SESSION PLAYER_CONFIRMED']
    lines += [f'TCA_TEST CHECK_PASS {name} {i}' for i in range(1, 5)]
    lines += ['console_success: Going to observe mode',
              f'TCA_TEST CHECK_PASS {name} 5', f'TCA_TEST PASS {name}', 'TCA_TEST SUITE_ALL_PASSED']
(run/'logs/debug.log').write_text('\\n'.join(lines) + '\\n')
(run/'logs/error.log').write_text('')
time.sleep(20)
''', encoding='utf-8')
            run = prepare_run(ROOT, root/'runs', root/'absent', 'tca_retirement_session.1')
            args = SimpleNamespace(game_dir=root, seed=None, timeout=30, strict_title_heir=False)
            def command(_args, target, save_name=None):
                return [sys.executable, str(emitter), str(target), save_name or 'start',
                        'early' if early_observe else 'normal']
            with patch('run_game_tests.game_command', side_effect=command):
                self.assertEqual(run_game(args, run), 2 if early_observe else 0)
            terminal = json.loads((run/'terminal.json').read_text())
            self.assertEqual(terminal['phases'], 3)
            self.assertEqual(terminal['phase_modes'], ['observer', 'observer', 'human'])
            self.assertEqual(terminal['human_phases'], [3])
            self.assertEqual(terminal['snapshot_issues'] == [], not early_observe)
            log = (run/'logs/debug.log').read_text()
            self.assertEqual(log.count('TCA_TEST BEGIN '), 1)
            self.assertEqual(log.count('TCA_TEST CHECK_PASS '), 5)
            self.assertEqual(len(json.loads((run/'reload_evidence.json').read_text())['raw_logs']), 6)

    def test_frozen_checker_imports_nested_helpers_without_source_checkout(self):
        # 在源码目录之外执行封存验收器，防止导入意外回退到工作目录。
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp)/'absent', 'tca_exam_test.1')
            logs = run/'logs'
            logs.mkdir()
            name = 'tca_test_exam_contract'
            lines = ['TCA_TEST SUITE_DISPATCH', f'TCA_TEST BEGIN tca_exam_test.1 {name}']
            checks = json.loads((run/'selection.json').read_text())['cases'][0]['checks']
            lines += [f'TCA_TEST CHECK_PASS {name} {i}' for i in range(1, checks + 1)]
            lines += [f'TCA_TEST PASS {name}', 'TCA_TEST SUITE_ALL_PASSED']
            (logs/'debug.log').write_text('\n'.join(lines))
            (logs/'error.log').write_text('')
            result = subprocess.run([sys.executable, str(run/'tools/check_test_run.py'), '--logs', str(logs)],
                                    cwd=temp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads((run/'source_manifest.json').read_text())
            self.assertIn('@tools/testing/catalog.py', manifest['files'])
            self.assertIn('@tools/testing/runtime.py', manifest['files'])
            self.assertIn('@tools/platform_paths.py', manifest['files'])
            self.assertFalse((run/'tools/tests').exists())

    def test_windows_command_and_metadata_use_same_executable(self):
        """Windows 启动与环境封存应共同使用真实的 ck3.exe。"""
        from run_game_tests import game_environment
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = root/'binaries/ck3.exe'
            binary.parent.mkdir()
            binary.write_bytes(b'windows fixture')
            with patch.object(sys, 'platform', 'win32'):
                command = game_command(SimpleNamespace(game_dir=root, seed=None), root/'run')
                environment = game_environment(root)
            self.assertEqual(command[0], str(binary))
            self.assertEqual(environment['executable_size'], binary.stat().st_size)
            self.assertIn('-userdir='+(root/'run').as_posix()+'/', command)

    def test_non_utf8_locale_preserves_chinese_paths_while_cloning_and_launching(self):
        """UTF-8冻结记录不能按Windows系统代码页重解码或误判安装变化。"""
        from run_game_tests import clone_run, write_json, seal_run, run_game, game_environment
        original_read = Path.read_text
        def codepage_read(path, *args, **kwargs):
            if not args and kwargs.get('encoding') is None:
                kwargs['encoding'] = 'cp1252'
            return original_read(path, *args, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = SimpleNamespace(game_dir=root/'游戏', seed=None)
            base = prepare_run(ROOT, root/'测试输出', root/'absent', 'tca_exam_test.1',
                               execution={'environment': game_environment(args.game_dir)})
            metadata = json.loads((base/'metadata.json').read_bytes().decode('utf-8'))
            metadata['note'] = '中文路径'
            write_json(base/'metadata.json', metadata)
            seal_run(base)
            rows = json.loads((base/'selection.json').read_bytes().decode('utf-8'))['cases']
            with patch.object(Path, 'read_text', codepage_read):
                child = clone_run(base, root/'测试输出', rows)
                cloned = json.loads((child/'metadata.json').read_bytes().decode('utf-8'))
                self.assertEqual(cloned['note'], '中文路径')
                with patch('run_game_tests.subprocess.Popen', side_effect=RuntimeError('launch reached')):
                    with self.assertRaisesRegex(RuntimeError, 'launch reached'):
                        run_game(args, child)

    def test_native_seed_is_optional_and_preserves_isolated_command(self):
        args = SimpleNamespace(game_dir=Path('/tmp/game with spaces'), seed=None)
        default = game_command(args, Path('/tmp/run with spaces'))
        self.assertFalse(any(arg.startswith('-random_seed=') for arg in default))
        self.assertIn('-userdir=/tmp/run with spaces/', default)
        self.assertIn('-bookmark=bm_1066_china', default)
        args.seed = 2878361204
        self.assertEqual(game_command(args, Path('/tmp/run with spaces')), default + ['-random_seed=2878361204'])

    def test_native_seed_bounds_are_checked_before_launch(self):
        for seed in (-1, 4294967296):
            with self.assertRaises(ValueError):
                game_command(SimpleNamespace(game_dir=Path('/tmp/game'), seed=seed), Path('/tmp/run'))
        for seed in (0, 4294967295):
            self.assertIn(f'-random_seed={seed}', game_command(SimpleNamespace(game_dir=Path('/tmp/game'), seed=seed), Path('/tmp/run')))

    def test_focused_run_selects_registered_event_and_only_changes_adapter_copy(self):
        source = ROOT / 'tools/cli_adapter/events/tca_cli_events.txt'
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp) / 'absent', 'tca_judicial_imperial_test.1')
            selection = json.loads((run / 'selection.json').read_text())
            self.assertEqual([row['event'] for row in selection['cases']], ['tca_judicial_imperial_test.1'])
            self.assertEqual(selection['scope'], 'selection')
            copied = (run / 'mod/tca_cli_adapter/events/tca_cli_events.txt').read_text(encoding='utf-8-sig')
            self.assertIn('name = tca_test_selected_run value = yes', copied)
            self.assertIn('name = tca_test_imperial_circuit_lifecycle_selected value = yes', copied)
            self.assertIn('tca_run_observer_tests_effect = yes', copied)
        self.assertEqual(source.read_bytes(), original)

    def test_run_uses_immutable_runtime_snapshot_with_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / 'repo'
            (repo / 'events').mkdir(parents=True)
            (repo / 'tools/cli_adapter/events').mkdir(parents=True)
            source = repo / 'events/tca_fixture_events.txt'
            source.write_text('original')
            run = prepare_run(repo, Path(temp) / 'runs', Path(temp) / 'absent')
            snapshot = run / 'mod/tca_main'
            self.assertEqual((snapshot / 'events/tca_fixture_events.txt').read_text(), 'original')
            source.write_text('changed after preparation')
            self.assertEqual((snapshot / 'events/tca_fixture_events.txt').read_text(), 'original')
            self.assertIn(snapshot.as_posix(), (run / 'mod/tca_main.mod').read_text())
            manifest = json.loads((run / 'source_manifest.json').read_text())
            self.assertIn('events/tca_fixture_events.txt', manifest['files'])
            self.assertEqual(len(manifest['sha256']), 64)

    def test_identical_content_has_same_digest_in_different_run_dirs(self):
        with tempfile.TemporaryDirectory() as temp:
            a = prepare_run(ROOT, Path(temp), Path(temp)/'absent')
            b = prepare_run(ROOT, Path(temp), Path(temp)/'absent')
            self.assertEqual(json.loads((a/'source_manifest.json').read_text())['sha256'],
                             json.loads((b/'source_manifest.json').read_text())['sha256'])

    def test_legacy_manifest_is_checked_with_its_original_protection_scope(self):
        from run_game_tests import verify_snapshot, content_digest
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp)/'absent')
            manifest = json.loads((run/'source_manifest.json').read_text())
            files = {key: value for key, value in manifest['files'].items()
                     if not key.startswith('@') or key.startswith('@adapter/')
                     or key in {'@tca_main.mod', '@tca_cli_adapter.mod'}}
            manifest.update(format=2, files=files, sha256=content_digest(files, 2))
            (run/'source_manifest.json').write_text(json.dumps(manifest))
            self.assertEqual(verify_snapshot(run), [])
            (run/'mod/tca_main/events/tests/tca_exam_test_events.txt').write_text('changed')
            self.assertTrue(verify_snapshot(run))

    def test_seal_rejects_modified_deleted_and_added_runtime_files(self):
        from run_game_tests import seal_run, verify_snapshot
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp) / 'absent')
            target = run / 'mod/tca_main/events/tests/tca_tongpan_test_events.txt'
            self.assertEqual(verify_snapshot(run), [])
            target.write_text('tampered')
            self.assertTrue(verify_snapshot(run))
            seal_run(run)
            target.unlink()
            self.assertTrue(verify_snapshot(run))
            seal_run(run)
            target.write_text('added')
            self.assertTrue(verify_snapshot(run))

    def test_focused_run_rejects_unknown_and_continuation_events(self):
        for entry in ('not_an_event', 'tca_judicial_imperial_test.1005'):
            with self.assertRaises(ValueError):
                from testing.catalog import select_cases
                select_cases(ROOT, [], [entry])

    def test_immediate_selection_is_prepared_and_tool_changes_are_detected(self):
        from run_game_tests import verify_snapshot
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp)/'absent', 'tca_exam_test.1')
            selection = json.loads((run/'selection.json').read_text())
            self.assertEqual([row['event'] for row in selection['cases']], ['tca_exam_test.1'])
            checker = run/'tools/check_test_run.py'
            self.assertTrue(checker.is_file())
            checker.write_text('changed validator')
            self.assertTrue(verify_snapshot(run))

    def test_added_tool_package_cannot_override_frozen_dependency(self):
        from run_game_tests import verify_snapshot
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp)/'absent')
            package = run/'tools/testing/catalog'
            package.mkdir()
            (package/'__init__.py').write_text('unexpected import replacement')
            self.assertTrue(verify_snapshot(run))

    def test_module_selection_uses_one_run_and_seals_its_plan(self):
        from run_game_tests import verify_snapshot
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp)/'absent', suites=['exam', 'confucian'])
            selection = json.loads((run/'selection.json').read_text())
            from testing.catalog import catalog
            expected = [row for row in catalog(ROOT) if row['suite'] in ('exam', 'confucian_statistics', 'confucian_strength')]
            self.assertEqual(selection['cases'], expected)
            self.assertEqual(len(list(Path(temp).glob('run-*'))), 1)
            (run/'selection.json').write_text('{}')
            self.assertTrue(verify_snapshot(run))

    def test_source_change_while_copying_rejects_preparation(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)/'repo'
            (repo/'events').mkdir(parents=True)
            (repo/'tools/cli_adapter').mkdir(parents=True)
            source = repo/'events/fixture.txt'
            source.write_text('before')
            copy = shutil.copytree
            def changing_copy(src, dst, *args, **kwargs):
                result = copy(src, dst, *args, **kwargs)
                if Path(src) == repo/'events':
                    source.write_text('after')
                return result
            with patch('run_game_tests.shutil.copytree', side_effect=changing_copy):
                with self.assertRaisesRegex(ValueError, 'Source changed'):
                    prepare_run(repo, Path(temp)/'runs', Path(temp)/'absent')

    def test_isolated_children_reuse_frozen_input_and_own_selection(self):
        from run_game_tests import clone_run, verify_snapshot
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = prepare_run(ROOT, root, root/'absent', suites=['exam'])
            rows = json.loads((base/'selection.json').read_text())['cases']
            child = clone_run(base, root, rows[:1])
            selected = json.loads((child/'selection.json').read_text())['cases']
            self.assertEqual(selected, rows[:1])
            self.assertEqual(verify_snapshot(base), [])
            self.assertEqual(verify_snapshot(child), [])
            text = (child/'mod/tca_cli_adapter/events/tca_cli_events.txt').read_text(encoding='utf-8-sig')
            self.assertIn(rows[0]['name'] + '_selected', text)
            for row in rows[1:]:
                self.assertNotIn(row['name'] + '_selected', text)

    def test_run_root_inside_source_is_rejected_before_recursive_copy(self):
        with patch('run_game_tests.source_files', side_effect=AssertionError('must reject before reading')):
            with self.assertRaisesRegex(ValueError, 'outside'):
                prepare_run(ROOT, ROOT/'test-output', ROOT/'absent')

    def test_launch_configuration_is_included_in_snapshot(self):
        from run_game_tests import verify_snapshot
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp)/'absent')
            (run/'dlc_load.json').write_text('{}')
            self.assertTrue(verify_snapshot(run))

    def test_engine_can_update_runtime_preferences_but_not_frozen_input(self):
        from run_game_tests import verify_snapshot
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp)/'absent')
            (run/'pdx_settings.txt').write_text('changed before launch')
            self.assertTrue(verify_snapshot(run))
            (run/'process.json').write_text('{}')
            self.assertEqual(verify_snapshot(run), [])
            (run/'inputs/pdx_settings.txt').write_text('changed frozen input')
            self.assertTrue(verify_snapshot(run))

    def test_interrupt_while_queued_records_terminal_task_state(self):
        from run_game_tests import main
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            from platform_paths import game_executable
            binary = game_executable(root/'game')
            binary.parent.mkdir(parents=True)
            binary.write_text('not launched')
            with patch('run_game_tests.engine_lock', side_effect=KeyboardInterrupt):
                code = main(['--game-dir', str(root/'game'), '--run-root', str(root/'runs'), '--suite', 'exam'])
            self.assertEqual(code, 2)
            run = next((root/'runs').glob('run-*'))
            task = json.loads((run/'task.json').read_text())
            self.assertEqual(task['state'], 'interrupted')
            self.assertEqual(task['runner_exit'], 2)

    def test_change_during_clone_cannot_be_resealed_as_valid(self):
        import shutil
        from run_game_tests import clone_run
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = prepare_run(ROOT, root, root/'absent', suites=['exam'])
            rows = json.loads((base/'selection.json').read_text())['cases']
            copy = shutil.copytree
            def changing_copy(src, dst, *args, **kwargs):
                if Path(src) == base/'mod':
                    (base/'mod/tca_main/events/tests/tca_exam_test_events.txt').write_text('changed')
                return copy(src, dst, *args, **kwargs)
            with patch('run_game_tests.shutil.copytree', side_effect=changing_copy):
                with self.assertRaisesRegex(ValueError, 'changed while cloning'):
                    clone_run(base, root, rows)

    def test_adapter_does_not_override_native_prison_interactions(self):
        adapter = ROOT / 'tools/cli_adapter'
        self.assertFalse(list((adapter / 'common/character_interactions').glob('*.txt')))
        self.assertNotIn('tca_cli_arrest_isolated', (adapter / 'events/tca_cli_events.txt').read_text(encoding='utf-8-sig'))

    def test_each_run_has_fresh_logs_and_adapter_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = prepare_run(ROOT, root, root / 'absent-settings')
            (first / 'logs').mkdir()
            (first / 'logs/debug.log').write_text('TCA_TEST SUITE_ALL_PASSED')
            second = prepare_run(ROOT, root, root / 'absent-settings')
            self.assertNotEqual(first, second)
            self.assertFalse((second / 'logs').exists())
            self.assertEqual(json.loads((root / 'latest.json').read_text())['run_dir'], str(second))
            mods = json.loads((second / 'dlc_load.json').read_text())['enabled_mods']
            self.assertEqual(mods, ['mod/tca_main.mod', 'mod/tca_cli_adapter.mod'])
            self.assertIn((second / 'mod/tca_main').as_posix(), (second / 'mod/tca_main.mod').read_text())
            self.assertIn(second.as_posix(), (second / 'mod/tca_cli_adapter.mod').read_text())
            self.assertTrue((second / 'mod/tca_cli_adapter/events/tca_cli_events.txt').is_file())

    def test_settings_do_not_copy_account_and_disable_cloud_in_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'settings.txt'
            original = ('"Account"={ secret="private" } '
                        '"game"={ "cloud_save"={version=0 enabled=yes} "autosave"={value="YEARLY"} } '
                        '"Graphics"={ "display_mode"={value="fullscreen"} "device"={value="GPU"} }')
            source.write_text(original)
            text = isolated_settings(source)
            self.assertNotIn('private', text)
            self.assertNotIn('fullscreen', text)
            self.assertIn('GPU', text)
            self.assertIn('enabled = no', text)
            self.assertEqual(text.count('"cloud_save"'), 1)
            self.assertEqual(source.read_text(), original)
            self.assertEqual(set(definitions(text)), {'"game"', '"Graphics"'})

    def test_engine_errors_and_incomplete_runs_never_report_success(self):
        self.assertEqual(outcome('summary', True, 0), 0)
        self.assertEqual(outcome('summary', True, 1), 1)
        self.assertEqual(outcome('summary', False, 0), 2)
        for condition in ('timeout', 'process_exit', 'interrupted', 'not_observer', 'entry_rejected'):
            self.assertEqual(outcome(condition, True, 0), 2)
        self.assertEqual(terminal_condition('TCA_TEST OBSERVER_ENTRY_REJECTED focused world invalid', None), 'entry_rejected')
        self.assertIsNone(terminal_condition('TCA_TEST PASS example', None))
        self.assertEqual(terminal_condition('TCA_TEST SUITE_ABORTED death', None), 'summary')
        self.assertEqual(terminal_condition('', 0), 'process_exit')

    def test_observer_confirmation_requires_console_success(self):
        self.assertFalse(progress('Running console command: observe', 2, True)['observer_confirmed'])
        state = progress('console_success: Going to observe mode\nTCA_TEST PASS a', 2, False)
        self.assertTrue(state['observer_confirmed'])
        self.assertEqual(state['pass_count'], 1)
        self.assertFalse(state['running'])

    def test_cleanup_targets_only_owned_child_and_falls_back_to_kill(self):
        child = Mock()
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired('ck3', 6), -9]
        stop_owned_process(child)
        child.terminate.assert_called_once_with()
        child.kill.assert_called_once_with()
        self.assertEqual(child.wait.call_count, 2)
        exited = Mock()
        exited.poll.return_value = 0
        stop_owned_process(exited)
        exited.terminate.assert_not_called()

    def test_paths_with_spaces_are_preserved_and_quotes_rejected(self):
        self.assertIn('path="/tmp/mod with spaces"', descriptor('TCA', Path('/tmp/mod with spaces')))
        with self.assertRaises(ValueError):
            descriptor('TCA', Path('/tmp/mod"bad'))


class IncrementalLogTests(unittest.TestCase):
    """增量日志监视器单测：只用临时文件，不启动游戏。"""

    def _append(self, path, text):
        with path.open('a', encoding='utf-8') as handle:
            handle.write(text)

    def test_tail_reads_only_appended_bytes_and_tracks_offset(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'debug.log'
            reader = LogTailReader(path)
            self.addCleanup(reader.close)
            self.assertEqual(reader.poll(), [])
            path.write_text('one\ntwo\n', encoding='utf-8')
            self.assertEqual(reader.poll(), ['one', 'two'])
            size = path.stat().st_size
            self.assertEqual(reader.offset, size)
            self.assertEqual(reader.bytes_read, size)
            self.assertEqual(reader.poll(), [])
            self.assertEqual(reader.bytes_read, size)
            self._append(path, 'three\n')
            self.assertEqual(reader.poll(), ['three'])
            self.assertEqual(reader.bytes_read, size + len('three\n'))
            self.assertEqual(reader.offset, path.stat().st_size)

    def test_tail_buffers_partial_multibyte_and_crlf_lines(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'debug.log'
            # 故意在“中”的多字节编码中间截断，验证下一轮补齐后才解码。
            path.write_bytes(b'TCA_TEST PASS \xe4\xb8')
            reader = LogTailReader(path)
            self.addCleanup(reader.close)
            self.assertEqual(reader.poll(), [])
            with path.open('ab') as handle:
                handle.write(b'\xad whole\r\n')
            self.assertEqual(reader.poll(), ['TCA_TEST PASS 中 whole'])
            path.write_bytes(b'no trailing newline')
            reader.reset()
            self.assertEqual(reader.poll(), [])
            self.assertEqual(reader.flush(), ['no trailing newline'])
            self.assertEqual(reader.poll(), [])

    def test_tail_resets_after_log_rotation_and_truncation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'debug.log'
            path.write_text('old phase line\n', encoding='utf-8')
            reader = LogTailReader(path)
            self.addCleanup(reader.close)
            self.assertEqual(reader.poll(), ['old phase line'])
            replacement = root / 'replacement.log'
            replacement.write_text('new phase line\n', encoding='utf-8')
            try:
                replacement.replace(path)
            except OSError:
                self.skipTest('当前平台不允许替换仍被读取的日志；运行器归档前会显式 close()')
            # 目录重建后 inode 变化：重置偏移并从新文件开头读取。
            self.assertEqual(reader.poll(), ['new phase line'])
            self.assertEqual(reader.offset, path.stat().st_size)
            # 同一 inode 下变短视为截断：重置偏移。
            path.write_text('short\n', encoding='utf-8')
            self.assertEqual(reader.poll(), ['short'])

    def test_monitor_reconfirms_observer_and_accumulates_across_phases(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'logs/debug.log'
            path.parent.mkdir()
            path.write_text('console_success: Going to observe mode\n'
                            'TCA_TEST PASS first\n'
                            'TCA_TEST PASS second\n'
                            'TCA_TEST SUITE_DISPATCH\n', encoding='utf-8')
            monitor = RunLogMonitor(path)
            self.addCleanup(monitor.close)
            monitor.poll()
            self.assertEqual(monitor.progress(1.24, True),
                             {'seconds': 1.2, 'running': True, 'pass_count': 2,
                              'observer_confirmed': True, 'markers': ['TCA_TEST SUITE_DISPATCH']})
            # phase 切换：归档后 logs/ 目录重建，续局必须重新确认观察者。
            monitor.next_phase()
            path.unlink()
            path.write_text('TCA_TEST PASS third\nTCA_TEST SUITE_ALL_PASSED\n', encoding='utf-8')
            monitor.poll()
            state = monitor.progress(12.0, True)
            self.assertEqual(state['pass_count'], 3)
            self.assertFalse(state['observer_confirmed'])
            self.assertEqual(state['markers'], ['TCA_TEST SUITE_DISPATCH', 'TCA_TEST SUITE_ALL_PASSED'])
            self._append(path, 'console_success: Going to observe mode\n')
            monitor.poll()
            self.assertTrue(monitor.observer_confirmed)

    def test_monitor_reload_evidence_is_scoped_to_current_phase(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            (run / 'logs').mkdir(parents=True)
            (run / 'save games').mkdir()
            (run / 'save games/probe.ck3').write_bytes(b'SAV' + b'x'*100)
            path = run / 'logs/debug.log'
            path.write_text('console_success: Game saved to probe\nTCA_CLI RELOAD_SAVE probe\n',
                            encoding='utf-8')
            monitor = RunLogMonitor(path)
            self.addCleanup(monitor.close)
            monitor.poll()
            self.assertEqual(reload_request(monitor.reload_log(), run), 'probe')
            monitor.next_phase()
            path.unlink()
            path.write_text('TCA_CLI RELOAD_SAVE other\n', encoding='utf-8')
            monitor.poll()
            self.assertNotIn('probe', monitor.reload_log())
            with self.assertRaises(ValueError):
                reload_request(monitor.reload_log(), run)

    def test_monitor_flush_picks_terminal_marker_without_trailing_newline(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'debug.log'
            path.write_text('TCA_TEST SUITE_ALL_PASSED', encoding='utf-8')
            monitor = RunLogMonitor(path)
            self.addCleanup(monitor.close)
            self.assertEqual(monitor.poll(), [])
            self.assertEqual(monitor.flush(), ['TCA_TEST SUITE_ALL_PASSED'])
            self.assertEqual(monitor.terminal_condition(None), 'summary')

    def test_monitor_terminal_condition_matches_existing_priority(self):
        cases = (
            ('TCA_CLI NOT_OBSERVER\n', None, 'not_observer'),
            ('TCA_CLI NOT_OBSERVER\nTCA_TEST OBSERVER_ENTRY_REJECTED\n', None, 'entry_rejected'),
            ('TCA_TEST OBSERVER_ENTRY_REJECTED\nTCA_TEST SUITE_ALL_PASSED\n', None, 'summary'),
            ('TCA_TEST SUITE_ABORTED death\n', 0, 'summary'),
            ('', 0, 'process_exit'),
            ('', None, None),
        )
        for text, process_code, expected in cases:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'debug.log'
                path.write_text(text, encoding='utf-8')
                monitor = RunLogMonitor(path)
                self.addCleanup(monitor.close)
                monitor.poll()
                self.assertEqual(monitor.terminal_condition(process_code), expected, text)

    def test_large_log_poll_reads_only_new_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'debug.log'
            line = 'x' * 99 + '\n'
            with path.open('w', encoding='utf-8') as handle:
                for _ in range(110_000):
                    handle.write(line)
            size = path.stat().st_size
            self.assertGreaterEqual(size, 10 * 1024 * 1024)
            monitor = RunLogMonitor(path)
            self.addCleanup(monitor.close)
            monitor.poll()
            self.assertEqual(monitor.bytes_read, size)
            self.assertEqual(monitor.offset, size)
            # 第二轮没有新增，不应重读旧内容。
            monitor.poll()
            self.assertEqual(monitor.bytes_read, size)
            self._append(path, 'TCA_TEST PASS large\n')
            self.assertEqual(monitor.poll(), ['TCA_TEST PASS large'])
            self.assertEqual(monitor.bytes_read, size + len('TCA_TEST PASS large\n'))
            self.assertEqual(monitor.offset, path.stat().st_size)
            self.assertEqual(monitor.pass_count, 1)

    def test_timeout_warning_only_applies_to_short_full_runs(self):
        warning = timeout_warning('full', 240)
        self.assertIn('1200', warning)
        self.assertIn('checker', warning)
        self.assertIsNone(timeout_warning('full', 1200))
        self.assertIsNone(timeout_warning('selection', 240))


if __name__ == '__main__':
    unittest.main()


class ParallelOptionTests(unittest.TestCase):
    """--parallel 注入与落盘字段：只验证准备阶段，不启动游戏。"""

    def test_full_and_selected_runs_inject_limit_before_observer_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            full = prepare_run(ROOT, root, root / 'absent', parallel=3)
            text = (full / 'mod/tca_cli_adapter/events/tca_cli_events.txt').read_text(encoding='utf-8-sig')
            self.assertEqual(text.count('set_variable = { name = tca_test_max_active value = 3 }'), 1)
            self.assertLess(text.index('tca_test_max_active'),
                            text.index('tca_run_observer_tests_effect = yes'))
            self.assertNotIn('tca_test_selected_run', text)
            selected = prepare_run(ROOT, root, root / 'absent', 'tca_exam_test.1', parallel=4)
            text = (selected / 'mod/tca_cli_adapter/events/tca_cli_events.txt').read_text(encoding='utf-8-sig')
            self.assertEqual(text.count('set_variable = { name = tca_test_max_active value = 4 }'), 1)
            self.assertIn('set_variable = { name = tca_test_selected_run value = yes }', text)
            self.assertLess(text.index('tca_test_max_active'),
                            text.index('tca_run_observer_tests_effect = yes'))

    def test_clone_replaces_parent_limit_instead_of_duplicating(self):
        from run_game_tests import clone_run
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = prepare_run(ROOT, root, root / 'absent', suites=['exam'], parallel=2,
                               execution={'environment': {}, 'parallel': 2})
            rows = json.loads((base / 'selection.json').read_text())['cases']
            child = clone_run(base, root, rows[:1])
            text = (child / 'mod/tca_cli_adapter/events/tca_cli_events.txt').read_text(encoding='utf-8-sig')
            self.assertEqual(text.count('name = tca_test_max_active'), 1)
            self.assertIn('name = tca_test_max_active value = 2', text)
            self.assertIn(rows[0]['name'] + '_selected', text)

    def test_prepare_only_records_parallel_in_execution_and_task(self):
        from run_game_tests import main
        from platform_paths import game_executable
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = game_executable(root / 'game')
            binary.parent.mkdir(parents=True)
            binary.write_text('not launched')
            code = main(['--game-dir', str(root / 'game'), '--run-root', str(root / 'runs'),
                         '--suite', 'exam', '--prepare-only', '--parallel', '3'])
            self.assertEqual(code, 0)
            run = next((root / 'runs').glob('run-*'))
            self.assertEqual(json.loads((run / 'execution.json').read_text())['parallel'], 3)
            self.assertEqual(json.loads((run / 'task.json').read_text())['parallel'], 3)

    def test_parallel_bounds_are_checked_before_preparation(self):
        from run_game_tests import main
        for value in ('0', '33', '1.5'):
            with self.assertRaises(SystemExit):
                main(['--run-root', '/tmp/tca-parallel-check', '--prepare-only', '--parallel', value])
