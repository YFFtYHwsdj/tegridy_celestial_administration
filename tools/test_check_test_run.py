import unittest
import tempfile
from pathlib import Path
from check_test_run import inspect_run, expected_cases


class RunEvidenceTests(unittest.TestCase):
    def test_orphan_with_callers_invalidates_pass(self):
        error = "[21:57:29][E][jomini_eventmanager.cpp:368]: Event tca_cli.1 is scripted as an orphan, but has callers"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('tca_cli.1' in issue for issue in issues))

    def test_wrong_mod_value_type_invalidates_pass(self):
        error = "[15:44:33][E][jomini_scriptvalue.cpp:1499]: Value of wrong type in 'file: common/scripted_effects/tca_judicial_arrest_test_effects.txt line: 30'. Got value of type 'none'"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('value type' in issue.lower() for issue in issues))

    def test_unset_mod_variable_invalidates_pass(self):
        error = "[15:07:35][E][jomini_effect.cpp:1162]: Variable 'tca_official_military' is used but is never set. Setting it in an unused scripted trigger or effect does not count"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('tca_official_military' in issue for issue in issues))

    def test_unused_mod_variable_invalidates_pass(self):
        error = "[15:07:35][E][jomini_effect.cpp:1146]: Variable 'tca_generated_initial_judicial_holder' is set but is never used."
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('tca_generated_initial_judicial_holder' in issue for issue in issues))

    def test_unset_mod_event_target_invalidates_pass(self):
        error = "[15:07:35][E][jomini_effect.cpp:1162]: Event target 'tca_test_law_subgovernor' is used but is never set."
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('tca_test_law_subgovernor' in issue for issue in issues))

    def test_unmarked_orphan_mod_event_invalidates_pass(self):
        error = "[15:07:40][E][jomini_eventmanager.cpp:368]: Event tca_court_test.100 is orphaned"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('tca_court_test.100' in issue for issue in issues))

    def test_duplicate_perk_in_test_fixture_invalidates_pass(self):
        error = ("[15:08:23][E][jomini_script_system.cpp:304]: Script system error!\n"
                 "  Error: add_perk effect [ Test governor already has the perk prison_feudal_complex_perk ]\n"
                 "  Script location: file: common/scripted_effects/tca_judicial_arrest_test_effects.txt line: 62\n")
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('prison_feudal_complex_perk' in issue for issue in issues))

    def test_unrelated_native_diagnostics_are_not_attributed_to_mod(self):
        error = ("[15:07:35][E]: Variable 'native_unused' is set but is never used.\n"
                 "[15:07:40][E]: Event native_debug.1 is orphaned\n")
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertEqual(issues, [])

    def test_invalid_value_event_target_link_invalidates_pass(self):
        error = "[13:58:52][E][jomini_eventtarget.cpp:325]: Scope type 'value' can not be used in event target links, link compare_value infile: events/tca_custody_review_test_events.txt line: 97"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('event target' in issue.lower() for issue in issues))

    def test_aborted_environment_cannot_pass_even_with_complete_assertions(self):
        log = self.run_log() + '\nTCA_TEST SUITE_ABORTED monitored character died'
        issues, _ = inspect_run(log, '', {'tca_test_example'})
        self.assertTrue(any('aborted' in issue.lower() for issue in issues))

    def test_script_bom_error_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(),
                               "[10:00:00][E]: File 'common/script_values/tca_custody_review_values.txt' should be in utf8-bom encoding (will try to use it anyways)",
                               {'tca_test_example'})
        self.assertTrue(any('encoding failure' in issue for issue in issues))

    def test_invalid_exclusive_send_option_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(),
                               "[10:00:00][E]: Exclusive send options should at least be two, in interaction 'tca_custody_review_interaction'",
                               {'tca_test_example'})
        self.assertTrue(any('send-option configuration failure' in issue for issue in issues))

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

    def test_rejected_observer_entry_cannot_reuse_old_pass(self):
        log = self.run_log() + '\nTCA_TEST OBSERVER_ENTRY_REJECTED valid 1066 China host required'
        issues, _ = inspect_run(log, '', {'tca_test_example'})
        self.assertTrue(any('observer entry' in issue.lower() for issue in issues))

    def test_observer_entry_requires_a_new_suite_dispatch(self):
        log = self.run_log() + '\nTCA_TEST OBSERVER_ENTRY_DISPATCH'
        issues, _ = inspect_run(log, '', {'tca_test_example'})
        self.assertTrue(any('observer entry' in issue.lower() for issue in issues))

    def test_busy_observer_retry_does_not_invalidate_completed_suite(self):
        log = self.run_log().replace('TCA_TEST SUITE_ALL_PASSED',
                                    'TCA_TEST OBSERVER_ENTRY_BUSY\nTCA_TEST SUITE_ALL_PASSED')
        issues, _ = inspect_run(log, '', {'tca_test_example'})
        self.assertEqual(issues, [])

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
