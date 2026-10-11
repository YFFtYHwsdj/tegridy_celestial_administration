import unittest
import tempfile
from pathlib import Path
from check_test_run import inspect_run, expected_cases


class RunEvidenceTests(unittest.TestCase):
    def event_fixture(self, root, checks):
        path = root / 'events/tca_fixture_test_events.txt'
        path.parent.mkdir()
        path.write_text('namespace = tca_fixture_test\n'
                        'tca_fixture_test.1 = { immediate = { '
                        'debug_log = "TCA_TEST BEGIN tca_fixture_test.1 tca_test_fixture" '
                        'debug_log = "TCA_TEST CHECK_PASS tca_test_fixture 1" } }\n'
                        'tca_fixture_test.2 = { immediate = { ' + checks + ' } }')

    def test_event_reader_includes_delayed_continuation_assertions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.event_fixture(root, 'debug_log = "TCA_TEST CHECK_PASS tca_test_fixture 2"')
            self.assertEqual(expected_cases(root), {'tca_test_fixture': 2})

    def test_event_reader_rejects_missing_assertion_numbers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.event_fixture(root, 'debug_log = "TCA_TEST CHECK_PASS tca_test_fixture 3"')
            with self.assertRaisesRegex(ValueError, 'consecutive'):
                expected_cases(root)

    def test_event_reader_rejects_duplicate_assertions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.event_fixture(root, 'debug_log = "TCA_TEST CHECK_PASS tca_test_fixture 1"')
            with self.assertRaisesRegex(ValueError, 'duplicate assertion'):
                expected_cases(root)

    def test_localization_evaluation_error_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(),
                                "[10:00:00][E]: Data error in loc string 'tca_judicial_title_name'",
                                {'tca_test_example'})
        self.assertTrue(any('localization evaluation' in issue for issue in issues))

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

    def test_native_test_parser_failure_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(),
                                '[10:00:00][E]: Error: "Unexpected token: wait_days" '
                                'in file: "tests/tca_judicial_timing_tests.txt"',
                                {'tca_test_example'})
        self.assertTrue(any('parsing failure' in issue for issue in issues))

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
