"""启动隔离及结果测试，不模拟 CK3 规则。"""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from run_game_tests import (ROOT, game_command, descriptor, isolated_settings, outcome, prepare_run,
                            progress, stop_owned_process, terminal_condition)
from check_upstream_overrides import definitions


class GameRunnerTests(unittest.TestCase):
    def test_frozen_checker_imports_nested_helpers_without_source_checkout(self):
        # 在源码目录之外执行封存验收器，防止导入意外回退到工作目录。
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_run(ROOT, Path(temp), Path(temp)/'absent', 'tca_exam_test.1')
            logs = run/'logs'
            logs.mkdir()
            name = 'tca_test_exam_contract'
            lines = ['TCA_TEST SUITE_DISPATCH', f'TCA_TEST BEGIN tca_exam_test.1 {name}']
            lines += [f'TCA_TEST CHECK_PASS {name} {i}' for i in range(1, 39)]
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
            self.assertEqual(len(selection['cases']), 4)
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
            self.assertIn('tca_test_exam_contract_selected', text)
            self.assertNotIn('tca_test_exam_pending_selected', text)

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


if __name__ == '__main__':
    unittest.main()
