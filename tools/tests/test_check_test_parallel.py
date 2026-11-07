"""并行静态检查器的正反与边界回归；全部使用临时合成测试源，不启动游戏。"""
import json
from pathlib import Path
import tempfile
import unittest

from check_test_parallel import inspect, load_whitelist, main

BASE_FILES = {
    'events/tests/tca_tests_events.txt': (
        'namespace = tca_tests\n'
        'tca_tests.1 = { immediate = { '
        'add_character_flag = tca_test_delayed_case_active '
        'tca_test_continue_delayed_effect = yes debug_log = "TCA_TEST FRAMEWORK_ONLY" } }\n'),
    'events/tests/tca_alpha_test_events.txt': (
        'namespace = tca_alpha_test\n'
        'tca_alpha_test.1 = { immediate = {\n'
        '    remove_character_flag = tca_test_tca_alpha_test_case_failed\n'
        '    if = { limit = { has_character_flag = tca_test_tca_alpha_test_case_failed } '
        'debug_log = "TCA_TEST FAIL tca_test_alpha" }\n'
        '    add_character_flag = tca_test_lane_tca_alpha_test_active\n'
        '    remove_character_flag = tca_test_lane_tca_alpha_test_active\n'
        '    title:h_china = { set_variable = { name = tca_alpha_shared_value value = 1 } }\n'
        '    tca_alpha_cleanup_effect = yes\n'
        '    trigger_event = tca_alpha_test.1001\n'
        '    tca_test_lane_end_effect = { GROUP = tca_alpha_test }\n'
        '} }\n'
        'tca_alpha_test.1001 = { immediate = {\n'
        '    remove_character_flag = tca_test_tca_alpha_test_case_failed\n'
        '} }\n'
        'tca_alpha_test.2 = { immediate = {\n'
        '    remove_character_flag = tca_test_tca_alpha_test_case_failed\n'
        '    if = { limit = { has_character_flag = tca_test_tca_alpha_test_case_failed } '
        'debug_log = "TCA_TEST FAIL tca_test_alpha_immediate" }\n'
        '    set_variable = { name = tca_alpha_immediate_value value = 1 }\n'
        '} }\n'),
    'events/tests/tca_beta_test_events.txt': (
        'namespace = tca_beta_test\n'
        'tca_beta_test.1 = { immediate = {\n'
        '    remove_character_flag = tca_test_tca_beta_test_case_failed\n'
        '    set_variable = { name = tca_beta_value value = 1 }\n'
        '    if = { limit = { has_character_flag = tca_test_tca_beta_test_case_failed } '
        'debug_log = "TCA_TEST FAIL tca_test_beta" }\n'
        '} }\n'),
    'common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt': (
        'tca_test_module_alpha_effect = {\n'
        '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.1 CASE = tca_test_alpha '
        'DELAYED = yes GROUP = tca_alpha_test EXCLUSIVE = yes }\n'
        '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.2 CASE = tca_test_alpha_immediate '
        'DELAYED = no GROUP = tca_alpha_test EXCLUSIVE = no }\n'
        '}\n'),
    'common/scripted_effects/tests/modules/tca_test_modules_beta_effects.txt': (
        'tca_test_module_beta_effect = {\n'
        '    tca_test_visit_case_effect = { EVENT = tca_beta_test.1 CASE = tca_test_beta '
        'DELAYED = no GROUP = tca_beta_test EXCLUSIVE = no }\n'
        '}\n'),
    'common/scripted_effects/tests/fixtures/tca_alpha_test_effects.txt': (
        'tca_alpha_cleanup_effect = {\n'
        '    remove_character_flag = tca_test_tca_alpha_test_case_failed\n'
        '}\n'),
}

EMPTY_WHITELIST = {'format': 1, 'variables': [], 'character_flags': [],
                   'bare_global_references': []}


class ParallelCheckerTests(unittest.TestCase):
    """覆盖检查 1–7 的通过、违规与边界分支。"""

    def write_root(self, temp, overrides=None, whitelist=None):
        """写出合成测试源并返回 (root, whitelist 路径)。"""
        files = dict(BASE_FILES)
        files.update(overrides or {})
        root = Path(temp)
        for relative, text in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
        path = root / 'parallel_whitelist.json'
        path.write_text(json.dumps(whitelist or EMPTY_WHITELIST, ensure_ascii=False),
                        encoding='utf-8')
        return root, path

    def checks(self, violations):
        return {item['check'] for item in violations}

    def test_synthetic_workspace_passes_every_check(self):
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(temp)
            report = inspect(root, whitelist)
            self.assertEqual(report['violations'], [], report['violations'])
            self.assertEqual(report['registrations'], 3)
            self.assertEqual(main(['--root', str(root), '--whitelist', str(whitelist)]), 0)

    def test_missing_and_invalid_metadata_are_reported_as_check_one(self):
        missing = BASE_FILES['common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt']
        broken = missing.replace(' GROUP = tca_alpha_test EXCLUSIVE = yes', '')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt': broken})
            report = inspect(root, whitelist)
            self.assertIn(1, self.checks(report['violations']))
            self.assertTrue(any('缺少 GROUP/EXCLUSIVE' in item['message']
                                for item in report['violations']))
        invalid = missing.replace('GROUP = tca_alpha_test EXCLUSIVE = yes',
                                  'GROUP = TCA-Alpha EXCLUSIVE = yes')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt': invalid})
            report = inspect(root, whitelist)
            self.assertIn(1, self.checks(report['violations']))
            self.assertIn('Invalid GROUP', report['violations'][0]['message'])

    def test_delayed_registration_requires_lane_end_in_trigger_closure(self):
        alpha = BASE_FILES['events/tests/tca_alpha_test_events.txt']
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt':
                       alpha.replace('    tca_test_lane_end_effect = { GROUP = tca_alpha_test }\n', '')})
            report = inspect(root, whitelist)
            self.assertEqual(self.checks(report['violations']), {1})
            self.assertIn('未调用 tca_test_lane_end_effect', report['violations'][0]['message'])
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt':
                       alpha.replace('    set_variable = { name = tca_alpha_immediate_value value = 1 }\n',
                                     '    set_variable = { name = tca_alpha_immediate_value value = 1 }\n'
                                     '    tca_test_lane_end_effect = { GROUP = tca_alpha_test }\n')})
            report = inspect(root, whitelist)
            self.assertIn('即时用例', ' '.join(item['message'] for item in report['violations']))

    def test_bare_global_identifiers_are_rejected_but_framework_file_is_exempt(self):
        # 基础夹具的 tca_tests_events.txt 已含裸标识且整体通过，说明框架入口被排除。
        alpha = BASE_FILES['events/tests/tca_alpha_test_events.txt']
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt':
                       alpha.replace('    set_variable = { name = tca_alpha_immediate_value value = 1 }\n',
                                     '    set_variable = { name = tca_alpha_immediate_value value = 1 }\n'
                                     '    tca_test_continue_delayed_effect = yes\n')})
            report = inspect(root, whitelist)
            self.assertEqual(self.checks(report['violations']), {2})
            self.assertIn('tca_test_continue_delayed_effect', report['violations'][0]['message'])

    def test_lane_flag_and_lane_end_group_must_match_registration(self):
        alpha = BASE_FILES['events/tests/tca_alpha_test_events.txt']
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt':
                       alpha.replace('tca_test_lane_tca_alpha_test_active',
                                     'tca_test_lane_tca_beta_test_active')})
            report = inspect(root, whitelist)
            self.assertEqual(self.checks(report['violations']), {3})
            self.assertIn('tca_test_lane_tca_beta_test_active', report['violations'][0]['message'])
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt':
                       alpha.replace('tca_test_lane_end_effect = { GROUP = tca_alpha_test }',
                                     'tca_test_lane_end_effect = { GROUP = tca_beta_test }')})
            report = inspect(root, whitelist)
            self.assertIn(3, self.checks(report['violations']))
            self.assertIn('GROUP = tca_beta_test', ' '.join(
                item['message'] for item in report['violations']))

    def test_reporter_state_conflict_across_groups_is_rejected_unless_whitelisted(self):
        beta = BASE_FILES['events/tests/tca_beta_test_events.txt']
        conflict = beta.replace(
            '    set_variable = { name = tca_beta_value value = 1 }\n',
            '    set_variable = { name = tca_beta_value value = 1 }\n'
            '    set_variable = { name = tca_alpha_immediate_value value = 2 }\n')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_beta_test_events.txt': conflict})
            report = inspect(root, whitelist)
            self.assertEqual(self.checks(report['violations']), {4})
            self.assertIn('tca_alpha_immediate_value', report['violations'][0]['message'])
        whitelist = dict(EMPTY_WHITELIST,
                         variables=[{'name': 'tca_alpha_immediate_value',
                                     'reason': '合成夹具：该变量已由用例串行维护'}])
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist_path = self.write_root(
                temp, {'events/tests/tca_beta_test_events.txt': conflict}, whitelist=whitelist)
            self.assertEqual(inspect(root, whitelist_path)['violations'], [])

    def test_single_group_delayed_shared_write_is_allowed_and_immediate_is_ignored(self):
        # a) 单个 GROUP 的延迟非独占用例写共享变量：同 GROUP 串行，不构成冲突。
        module = BASE_FILES['common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt']
        alpha = BASE_FILES['events/tests/tca_alpha_test_events.txt']
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt':
                       module.replace('EXCLUSIVE = yes', 'EXCLUSIVE = no')})
            self.assertEqual(inspect(root, whitelist)['violations'], [])
        # d) 即时用例写共享作用域先于延迟阶段同步执行，不要求独占。
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt':
                       alpha.replace('    set_variable = { name = tca_alpha_immediate_value value = 1 }\n',
                                     '    set_variable = { name = tca_alpha_immediate_value value = 1 }\n'
                                     '    title:h_china.holder = { add_character_flag = tca_alpha_immediate_flag }\n')})
            self.assertEqual(inspect(root, whitelist)['violations'], [])

    def beta_delayed_events(self, shared_write):
        """把 beta 用例改为延迟调用，并在用例体追加指定的共享写入与 lane 结束。"""
        beta = BASE_FILES['events/tests/tca_beta_test_events.txt']
        return beta.replace(
            '    if = { limit = { has_character_flag = tca_test_tca_beta_test_case_failed } '
            'debug_log = "TCA_TEST FAIL tca_test_beta" }\n',
            '    if = { limit = { has_character_flag = tca_test_tca_beta_test_case_failed } '
            'debug_log = "TCA_TEST FAIL tca_test_beta" }\n'
            + shared_write +
            '    tca_test_lane_end_effect = { GROUP = tca_beta_test }\n')

    def beta_delayed_module(self):
        """把 beta 登记改为延迟、非独占。"""
        return BASE_FILES['common/scripted_effects/tests/modules/tca_test_modules_beta_effects.txt'].replace(
            'DELAYED = no', 'DELAYED = yes')

    def test_shared_write_conflicts_when_two_groups_write_same_key(self):
        # b) 两个 GROUP 的延迟非独占用例写同一共享变量 → 检查5 报冲突并列出两个 GROUP。
        alpha_module = BASE_FILES['common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt']
        shared_write = ('    title:h_china = { set_variable = '
                        '{ name = tca_alpha_shared_value value = 2 } }\n')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(temp, {
                'common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt':
                    alpha_module.replace('EXCLUSIVE = yes', 'EXCLUSIVE = no'),
                'events/tests/tca_beta_test_events.txt': self.beta_delayed_events(shared_write),
                'common/scripted_effects/tests/modules/tca_test_modules_beta_effects.txt':
                    self.beta_delayed_module()})
            report = inspect(root, whitelist)
            self.assertEqual(self.checks(report['violations']), {5})
            message = report['violations'][0]['message']
            self.assertIn('tca_alpha_shared_value', message)
            self.assertIn('tca_alpha_test', message)
            self.assertIn('tca_beta_test', message)
            # 冲突说明必须给出可操作建议：合并 GROUP 或保持独占。
            self.assertIn('合并', message)
            self.assertIn('EXCLUSIVE = yes', message)

    def test_exclusive_group_does_not_join_shared_write_conflict(self):
        # c) 一个非独占 GROUP 加一个独占 GROUP 写同一共享键：独占用例与其它延迟
        # 用例互斥，不参与冲突集合，因此通过。
        shared_write = ('    title:h_china = { set_variable = '
                        '{ name = tca_alpha_shared_value value = 2 } }\n')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(temp, {
                'events/tests/tca_beta_test_events.txt': self.beta_delayed_events(shared_write),
                'common/scripted_effects/tests/modules/tca_test_modules_beta_effects.txt':
                    self.beta_delayed_module()})
            self.assertEqual(inspect(root, whitelist)['violations'], [])

    def test_immediate_shared_write_does_not_join_conflict_set(self):
        # d 边界：即时用例与延迟非独占 GROUP 写同一共享键时，即时写入发生在
        # 同步阶段，不属于并发写集合；只有延迟侧 GROUP 参与判断。
        alpha = BASE_FILES['events/tests/tca_alpha_test_events.txt']
        alpha_immediate = alpha.replace(
            '    set_variable = { name = tca_alpha_immediate_value value = 1 }\n',
            '    set_variable = { name = tca_alpha_immediate_value value = 1 }\n'
            '    title:h_china = { set_variable = { name = tca_alpha_shared_value value = 3 } }\n')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt': alpha_immediate})
            self.assertEqual(inspect(root, whitelist)['violations'], [])

    def test_fixture_shared_write_conflict_follows_calling_group(self):
        # e) 夹具间接写共享：冲突集合按调用用例的 GROUP 归属，而非夹具名。
        fixture = (
            'tca_alpha_cleanup_effect = {\n'
            '    remove_character_flag = tca_test_tca_alpha_test_case_failed\n'
            '}\n'
            'tca_shared_fixture_effect = {\n'
            '    title:h_china = { set_variable = { name = tca_fixture_shared_value value = 1 } }\n'
            '}\n')
        alpha = BASE_FILES['events/tests/tca_alpha_test_events.txt']
        alpha_fixture = alpha.replace(
            '    tca_alpha_cleanup_effect = yes\n',
            '    tca_alpha_cleanup_effect = yes\n'
            '    tca_shared_fixture_effect = yes\n')
        alpha_module = BASE_FILES['common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt']
        alpha_second = (
            'tca_alpha_test.3 = { immediate = {\n'
            '    remove_character_flag = tca_test_tca_alpha_test_case_failed\n'
            '    tca_shared_fixture_effect = yes\n'
            '    tca_test_lane_end_effect = { GROUP = tca_alpha_test }\n'
            '} }\n')
        module_second = alpha_module.replace(
            '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.2',
            '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.3 '
            'CASE = tca_test_alpha_second DELAYED = yes GROUP = tca_alpha_test EXCLUSIVE = no }\n'
            '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.2')
        # 同一 GROUP 的两个延迟用例调用同一夹具 → 通过。
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(temp, {
                'common/scripted_effects/tests/fixtures/tca_alpha_test_effects.txt': fixture,
                'events/tests/tca_alpha_test_events.txt': alpha_fixture + alpha_second,
                'common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt':
                    module_second.replace('EXCLUSIVE = yes', 'EXCLUSIVE = no')})
            self.assertEqual(inspect(root, whitelist)['violations'], [])
        # 两个 GROUP 的延迟用例调用同一夹具 → 报冲突并列出两个 GROUP。
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(temp, {
                'common/scripted_effects/tests/fixtures/tca_alpha_test_effects.txt': fixture,
                'events/tests/tca_alpha_test_events.txt': alpha_fixture,
                'common/scripted_effects/tests/modules/tca_test_modules_alpha_effects.txt':
                    alpha_module.replace('EXCLUSIVE = yes', 'EXCLUSIVE = no'),
                'events/tests/tca_beta_test_events.txt':
                    self.beta_delayed_events('    tca_shared_fixture_effect = yes\n'),
                'common/scripted_effects/tests/modules/tca_test_modules_beta_effects.txt':
                    self.beta_delayed_module()})
            report = inspect(root, whitelist)
            self.assertEqual(self.checks(report['violations']), {5})
            message = report['violations'][0]['message']
            self.assertIn('tca_fixture_shared_value', message)
            self.assertIn('tca_alpha_test', message)
            self.assertIn('tca_beta_test', message)

    def test_failure_flag_requires_both_write_and_read(self):
        alpha = BASE_FILES['events/tests/tca_alpha_test_events.txt']
        orphan = alpha.replace(
            '    set_variable = { name = tca_alpha_immediate_value value = 1 }\n',
            '    set_variable = { name = tca_alpha_immediate_value value = 1 }\n'
            '    add_character_flag = tca_test_tca_alpha_test_orphan_case_failed\n')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt': orphan})
            report = inspect(root, whitelist)
            self.assertIn(6, self.checks(report['violations']))
            messages = ' '.join(item['message'] for item in report['violations'])
            self.assertIn('tca_test_tca_alpha_test_orphan_case_failed', messages)
            self.assertIn('缺少读取', messages)

    def test_trigger_chain_must_report_to_the_case_flag_and_lane_group(self):
        alpha = BASE_FILES['events/tests/tca_alpha_test_events.txt']
        wrong_flag = alpha.replace(
            'tca_alpha_test.1001 = { immediate = {\n'
            '    remove_character_flag = tca_test_tca_alpha_test_case_failed\n',
            'tca_alpha_test.1001 = { immediate = {\n'
            '    remove_character_flag = tca_test_tca_beta_test_case_failed\n'
            '    add_character_flag = tca_test_tca_beta_test_case_failed\n')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt': wrong_flag})
            report = inspect(root, whitelist)
            self.assertIn(7, self.checks(report['violations']))
            self.assertIn('与链内主用例失败 flag', ' '.join(
                item['message'] for item in report['violations'] if item['check'] == 7))
        wrong_lane = alpha.replace(
            'tca_alpha_test.1001 = { immediate = {\n'
            '    remove_character_flag = tca_test_tca_alpha_test_case_failed\n',
            'tca_alpha_test.1001 = { immediate = {\n'
            '    remove_character_flag = tca_test_tca_alpha_test_case_failed\n'
            '    tca_test_lane_end_effect = { GROUP = tca_beta_test }\n')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt': wrong_lane})
            report = inspect(root, whitelist)
            self.assertIn(7, self.checks(report['violations']))

    def test_chain_event_shared_by_multiple_groups_cannot_reference_flag_or_lane(self):
        beta = BASE_FILES['events/tests/tca_beta_test_events.txt']
        shared = beta.replace(
            '    if = { limit = { has_character_flag = tca_test_tca_beta_test_case_failed } '
            'debug_log = "TCA_TEST FAIL tca_test_beta" }\n',
            '    if = { limit = { has_character_flag = tca_test_tca_beta_test_case_failed } '
            'debug_log = "TCA_TEST FAIL tca_test_beta" }\n'
            '    trigger_event = tca_alpha_test.1001\n')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_beta_test_events.txt': shared})
            report = inspect(root, whitelist)
            messages = [item['message'] for item in report['violations'] if item['check'] == 7]
            self.assertTrue(any('无法安全共享' in message for message in messages), messages)

    def test_parameterized_fixture_identifiers_are_accepted(self):
        fixture = ('tca_alpha_cleanup_effect = {\n'
                   '    add_character_flag = tca_test_$GROUP$_case_failed\n'
                   '    remove_character_flag = tca_test_$GROUP$_case_failed\n'
                   '    if = { limit = { has_character_flag = tca_test_lane_$GROUP$_active } '
                   'tca_test_lane_end_effect = { GROUP = $GROUP$ } }\n'
                   '}\n')
        beta = BASE_FILES['events/tests/tca_beta_test_events.txt'].replace(
            '    if = { limit = { has_character_flag = tca_test_tca_beta_test_case_failed } ',
            '    tca_alpha_cleanup_effect = yes\n'
            '    if = { limit = { has_character_flag = tca_test_tca_beta_test_case_failed } ')
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'common/scripted_effects/tests/fixtures/tca_alpha_test_effects.txt': fixture,
                       'events/tests/tca_beta_test_events.txt': beta})
            report = inspect(root, whitelist)
            self.assertEqual(report['violations'], [], report['violations'])

    def test_whitelist_entries_must_explain_their_reason(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'whitelist.json'
            path.write_text(json.dumps({'format': 1, 'variables': [{'name': 'tca_shared'}]}),
                            encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '理由'):
                load_whitelist(path)
            path.write_text(json.dumps({'format': 1, 'bare_global_references': [
                {'name': 'tca_test_case_failed', 'reason': 'x'}]}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '文件'):
                load_whitelist(path)

    def test_main_writes_json_and_fails_on_violations(self):
        alpha = BASE_FILES['events/tests/tca_alpha_test_events.txt']
        with tempfile.TemporaryDirectory() as temp:
            root, whitelist = self.write_root(
                temp, {'events/tests/tca_alpha_test_events.txt':
                       alpha + 'tca_alpha_test.3 = { immediate = { '
                               'tca_test_continue_delayed_effect = yes } }\n'})
            output = Path(temp) / 'parallel.json'
            self.assertEqual(main(['--root', str(root), '--whitelist', str(whitelist),
                                   '--json', str(output)]), 1)
            data = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(data['registrations'], 3)
            self.assertTrue(any(item['check'] == 2 for item in data['violations']))


if __name__ == '__main__':
    unittest.main()
