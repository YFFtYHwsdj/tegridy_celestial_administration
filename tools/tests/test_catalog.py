"""验证原生登记读取与范围选择，不执行或模拟游戏规则。"""
import unittest
from pathlib import Path
import importlib.util
import re
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[2]


class TestCatalogTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('testing.catalog'), '需要原生模块登记读取器')
        import testing.catalog as test_catalog
        return test_catalog

    def test_native_registration_covers_every_existing_assertion(self):
        from check_test_run import expected_cases
        rows = self.api().catalog(ROOT)
        self.assertEqual({r['name']: r['checks'] for r in rows}, expected_cases(ROOT))
        self.assertEqual(len({r['event'] for r in rows}), len(rows))
        # catalog() 字段保持冻结计划格式，lane 元数据只经 parallel_metadata() 暴露。
        self.assertEqual(set(rows[0]), {'suite', 'event', 'name', 'delayed', 'checks'})

    def test_nested_sources_are_discovered_and_duplicate_registration_is_rejected(self):
        api = self.api()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT/'events', root/'events/tests')
            shutil.copytree(ROOT/'common/scripted_effects', root/'common/scripted_effects/tests')
            self.assertEqual(api.catalog(root), api.catalog(ROOT))
            module = next((root/'common/scripted_effects').rglob('tca_test_modules_exam_effects.txt'))
            duplicate = module.parent/'duplicate'/module.name
            duplicate.parent.mkdir()
            shutil.copy2(module, duplicate)
            with self.assertRaisesRegex(ValueError, 'Duplicate module'):
                api.catalog(root)
            duplicate.unlink()
            entry = api.catalog_path(root)
            shutil.copy2(entry, duplicate.parent/entry.name)
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                api.catalog(root)

    def test_immediate_case_can_be_selected_without_delayed_stage(self):
        rows = self.api().select_cases(ROOT, [], ['tca_exam_test.1'])
        self.assertEqual([r['event'] for r in rows], ['tca_exam_test.1'])
        self.assertFalse(rows[0]['delayed'])

    def test_module_and_case_union_is_deduplicated(self):
        api = self.api()
        rows = api.select_cases(ROOT, ['exam'], ['tca_exam_test.1'])
        expected = [row for row in api.catalog(ROOT) if row['suite'] == 'exam']
        self.assertEqual(rows, expected)
        self.assertEqual(sum(row['event'] == 'tca_exam_test.1' for row in rows), 1)

    def test_judicial_group_includes_related_modules_and_unknown_selection_fails(self):
        api = self.api()
        rows = api.select_cases(ROOT, ['judicial'], [])
        self.assertTrue(any(r['suite'] == 'judicial_arrest' for r in rows))
        self.assertTrue(any(r['suite'] == 'judicial_law' for r in rows))
        for suites, cases in [(['missing'], []), ([], ['tca_exam_test.1002'])]:
            with self.assertRaises(ValueError):
                api.select_cases(ROOT, suites, cases)

    def test_plan_rejects_duplicate_incomplete_full_or_forged_counts(self):
        api = self.api()
        rows = api.select_cases(ROOT, [], ['tca_exam_test.1'])
        self.assertEqual(api.validate_plan({'scope': 'selection', 'cases': rows}, ROOT),
                         {rows[0]['name']: rows[0]['checks']})
        for plan in ({'scope': 'selection', 'cases': rows + rows},
                     {'scope': 'full', 'cases': rows},
                     {'scope': 'selection', 'cases': [{**rows[0], 'checks': 1}]},
                     {'scope': 'selection', 'cases': []}):
            with self.assertRaises(ValueError):
                api.validate_plan(plan, ROOT)


class ParallelMetadataTests(unittest.TestCase):
    """lane 元数据解析：迁移夹具、旧式容错与非法 GROUP 校验。"""

    def module_root(self, temp, registrations, extra_modules=()):
        root = Path(temp)
        modules = root / 'common/scripted_effects/tests/modules'
        modules.mkdir(parents=True)
        (modules / 'tca_test_modules_alpha_effects.txt').write_text(
            'tca_test_module_alpha_effect = {\n' + registrations + '}\n', encoding='utf-8')
        for name, text in extra_modules:
            (modules / name).write_text(text, encoding='utf-8')
        return root

    def test_migrated_registration_exposes_group_and_exclusive(self):
        import testing.catalog as api
        with tempfile.TemporaryDirectory() as temp:
            root = self.module_root(temp,
                '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.1 CASE = tca_test_alpha '
                'DELAYED = yes GROUP = tca_alpha_test EXCLUSIVE = yes }\n'
                '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.2 CASE = tca_test_alpha_second '
                'DELAYED = no GROUP = tca_alpha_test EXCLUSIVE = no }\n')
            metadata = api.parallel_metadata(root)
            self.assertEqual(metadata['tca_test_alpha'], {'group': 'tca_alpha_test', 'exclusive': True})
            self.assertEqual(metadata['tca_test_alpha_second'],
                             {'group': 'tca_alpha_test', 'exclusive': False})
            self.assertEqual(api.verify_registration_metadata(root), [])

    def test_legacy_registration_is_tolerated_and_reported_for_migration(self):
        import testing.catalog as api
        with tempfile.TemporaryDirectory() as temp:
            root = self.module_root(temp,
                '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.1 CASE = tca_test_alpha '
                'DELAYED = yes }\n')
            # 迁移窗口内按事件命名空间推导 GROUP、EXCLUSIVE 缺省为 no。
            self.assertEqual(api.parallel_metadata(root),
                             {'tca_test_alpha': {'group': 'tca_alpha_test', 'exclusive': False}})
            self.assertEqual(len(api.verify_registration_metadata(root)), 1)

    def test_invalid_group_and_partial_metadata_are_rejected(self):
        import testing.catalog as api
        cases = (
            ('EVENT = tca_alpha_test.1 CASE = tca_test_alpha DELAYED = no '
             'GROUP = Tca-Alpha EXCLUSIVE = no', 'Invalid GROUP'),
            ('EVENT = tca_alpha_test.1 CASE = tca_test_alpha DELAYED = no GROUP = tca_alpha_test',
             'Invalid module registration'),
            ('EVENT = tca_alpha_test.1 CASE = tca_test_alpha DELAYED = no '
             'EXCLUSIVE = no GROUP = tca_alpha_test', 'Invalid module registration'),
        )
        for registration, message in cases:
            with tempfile.TemporaryDirectory() as temp:
                root = self.module_root(temp, f'    tca_test_visit_case_effect = {{ {registration} }}\n')
                with self.assertRaisesRegex(ValueError, message):
                    api.parallel_metadata(root)

    def test_same_namespace_must_use_one_group(self):
        import testing.catalog as api
        with tempfile.TemporaryDirectory() as temp:
            root = self.module_root(temp,
                '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.1 CASE = tca_test_alpha '
                'DELAYED = no GROUP = tca_alpha_test EXCLUSIVE = no }\n'
                '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.2 CASE = tca_test_alpha_second '
                'DELAYED = no GROUP = tca_merged EXCLUSIVE = no }\n')
            with self.assertRaisesRegex(ValueError, 'Inconsistent GROUP'):
                api.parallel_metadata(root)

    def test_catalog_requires_completed_registration_migration(self):
        import testing.catalog as api
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'events', root / 'events/tests')
            shutil.copytree(ROOT / 'common/scripted_effects', root / 'common/scripted_effects/tests')
            module = next(root.rglob('tca_test_modules_exam_effects.txt'))
            text = module.read_text(encoding='utf-8-sig')
            module.write_text(re.sub(r' GROUP = \S+ EXCLUSIVE = (?:yes|no)', '', text),
                              encoding='utf-8-sig')
            # 运行入口（--list/准备任务）要求迁移完成；检查器仍用宽容接口报告缺失清单。
            with self.assertRaisesRegex(ValueError, 'GROUP/EXCLUSIVE'):
                api.catalog(root)
            self.assertTrue(api.verify_registration_metadata(root))

    def test_cross_namespace_group_merge_is_allowed(self):
        import testing.catalog as api
        with tempfile.TemporaryDirectory() as temp:
            root = self.module_root(temp,
                '    tca_test_visit_case_effect = { EVENT = tca_alpha_test.1 CASE = tca_test_alpha '
                'DELAYED = no GROUP = tca_merged EXCLUSIVE = no }\n',
                extra_modules=[('tca_test_modules_beta_effects.txt',
                                'tca_test_module_beta_effect = {\n'
                                '    tca_test_visit_case_effect = { EVENT = tca_beta_test.1 '
                                'CASE = tca_test_beta DELAYED = no GROUP = tca_merged EXCLUSIVE = no }\n'
                                '}\n')])
            self.assertEqual({row['group'] for row in api.registration_rows(root)}, {'tca_merged'})
