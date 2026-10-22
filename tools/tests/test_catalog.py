"""验证原生登记读取与范围选择，不执行或模拟游戏规则。"""
import unittest
from pathlib import Path
import importlib.util
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
