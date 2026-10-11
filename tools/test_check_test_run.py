import unittest
from check_test_run import inspect_run


class RunEvidenceTests(unittest.TestCase):
    def run_log(self, name='tca_test_example'):
        return f'TCA_TEST SUITE_DISPATCH\nTCA_TEST BEGIN tca_example_test.1 {name}\nTCA_TEST CHECK_PASS {name} 1\nTCA_TEST PASS {name}\nTCA_TEST SUITE_ALL_PASSED'

    def test_complete_pass(self):
        issues, counts = inspect_run(self.run_log(), '', {'tca_test_example'})
        self.assertEqual(issues, [])
        self.assertEqual(counts['PASS'], 1)

    def test_new_source_cases_cannot_reuse_old_run(self):
        issues, _ = inspect_run(self.run_log(), '', {'tca_test_example', 'tca_test_new'})
        self.assertTrue(any('tca_test_new' in x for x in issues))

    def test_startup_compilation_failure_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(), '[10:00:00][E]: Compiling source for tca_score failed for unknown arguments: GOVERNOR', {'tca_test_example'})
        self.assertTrue(any('compilation' in x for x in issues))

    def test_native_error_in_mod_call_chain_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(), '[10:00:00][E]: Script system error!\nError: wrong scope\nfile: common/scripted_effects/tca_example.txt', {'tca_test_example'})
        self.assertTrue(any('wrong scope' in x for x in issues))

    def test_only_latest_dispatch_counts(self):
        issues, counts = inspect_run(self.run_log() + '\n' + self.run_log(), '', {'tca_test_example'})
        self.assertEqual(issues, [])
        self.assertEqual(counts['BEGIN'], 1)

    def test_precondition_failure_is_not_pass(self):
        log = self.run_log().replace('TCA_TEST PASS tca_test_example', 'TCA_TEST PRECONDITION_FAIL tca_test_example')
        issues, _ = inspect_run(log, '', {'tca_test_example'})
        self.assertTrue(issues)

    def test_duplicate_pass_is_not_complete_evidence(self):
        issues, _ = inspect_run(self.run_log() + '\nTCA_TEST PASS tca_test_example', '', {'tca_test_example'})
        self.assertTrue(issues)

    def test_mod_duplicate_queue_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(), "[10:00:00][E]: Event tca_judicial_titles.2 has been queued twice with same data including delay", {'tca_test_example'})
        self.assertTrue(any('queued' in x for x in issues))

    def test_unrelated_native_queue_is_not_a_mod_error(self):
        issues, _ = inspect_run(self.run_log(), "[10:00:00][E]: Event diarchy.0011 has been queued twice with same data including delay", {'tca_test_example'})
        self.assertEqual(issues, [])

    def test_current_source_assertions_are_all_required(self):
        issues, _ = inspect_run(self.run_log(), '', {'tca_test_example': 2})
        self.assertTrue(any('assertion 2' in x for x in issues))

    def test_duplicate_assertion_cannot_replace_missing_assertion(self):
        issues, _ = inspect_run(self.run_log() + '\nTCA_TEST CHECK_PASS tca_test_example 1', '', {'tca_test_example': 2})
        self.assertTrue(any('assertion 1' in x for x in issues))
        self.assertTrue(any('assertion 2' in x for x in issues))

    def test_complete_assertion_sequence(self):
        issues, _ = inspect_run(self.run_log(), '', {'tca_test_example': 1})
        self.assertEqual(issues, [])


if __name__ == '__main__':
    unittest.main()
