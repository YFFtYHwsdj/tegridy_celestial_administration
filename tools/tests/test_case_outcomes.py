"""逐项报告必须与日志验收使用同一轮，不继承旧结果。"""
import unittest
import check_test_run


class CaseOutcomeTests(unittest.TestCase):
    def test_earlier_pass_does_not_cover_latest_unexecuted_case(self):
        self.assertTrue(hasattr(check_test_run, 'case_outcomes'))
        name = 'tca_test_example'
        old = f'TCA_TEST SUITE_DISPATCH\nTCA_TEST BEGIN tca_example.1 {name}\nTCA_TEST CHECK_PASS {name} 1\nTCA_TEST PASS {name}\n'
        debug = old + 'TCA_TEST SUITE_DISPATCH\nTCA_TEST SUITE_ABORTED\n'
        self.assertEqual(check_test_run.case_outcomes(debug, {name: 1}), {name: 'NOT_RUN'})

    def test_pass_without_all_assertions_is_unverified(self):
        self.assertTrue(hasattr(check_test_run, 'case_outcomes'))
        debug = 'TCA_TEST SUITE_DISPATCH\nTCA_TEST BEGIN tca_example.1 tca_test_example\nTCA_TEST PASS tca_test_example\n'
        self.assertEqual(check_test_run.case_outcomes(debug, {'tca_test_example': 1}),
                         {'tca_test_example': 'NOT_VERIFIED'})
