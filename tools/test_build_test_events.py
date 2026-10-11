import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_test_events as builder


class BuildTestEventsTests(unittest.TestCase):
    def write_suite(self, root, filename, name):
        path = root / 'tests' / filename
        path.parent.mkdir(exist_ok=True)
        path.write_text(f'{name} = {{ name = "{name}" assert = {{ always = yes }} '
                        'effect = { add_character_flag = tca_fixture } '
                        'expect = { has_character_flag = tca_fixture } }')

    def test_future_groups_are_dispatched_and_total_is_derived(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_suite(root, 'tca_court_system_tests.txt', 'tca_test_court_example')
            self.write_suite(root, 'tca_judicial_tests.txt', 'tca_test_judicial_example')
            self.write_suite(root, 'vanilla_tests.txt', 'unrelated')
            with patch.object(builder, 'ROOT', root):
                result = builder.render()
            dispatcher = result[root / 'events/tca_tests_events.txt']
            self.assertIn('name = tca_test_suite_expected value = 2', dispatcher)
            self.assertIn('trigger_event = tca_court_test.1', dispatcher)
            self.assertIn('trigger_event = tca_judicial_test.1', dispatcher)
            self.assertNotIn('unrelated', dispatcher)
            self.assertIn('tca_test_notify_results_effect = yes', dispatcher)

    def test_duplicate_names_across_groups_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_suite(root, 'tca_a_tests.txt', 'tca_test_duplicate')
            self.write_suite(root, 'tca_b_tests.txt', 'tca_test_duplicate')
            with patch.object(builder, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'Duplicate'):
                    builder.render()

    def test_unsupported_target_is_rejected_instead_of_silently_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_suite(root, 'tca_a_tests.txt', 'tca_test_target')
            path = root / 'tests/tca_a_tests.txt'
            path.write_text(path.read_text().replace('assert =', 'character_target = 122 assert ='))
            with patch.object(builder, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'leading assert'):
                    builder.render()

    def delayed_suite(self, root, value='2'):
        self.write_suite(root, 'tca_timing_tests.txt', 'tca_test_delayed')
        p = root / 'tests/tca_timing_tests.txt'
        p.write_text(p.read_text().replace('expect =', f'wait_days = {value} expect ='))

    def test_wait_splits_case_without_early_pass(self):
        from check_upstream_overrides import definitions
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.delayed_suite(root)
            with patch.object(builder, 'ROOT', root):
                result = builder.render()
            cases = definitions(result[root / 'events/tca_timing_test_events.txt'])
            entry = ' '.join(cases['tca_timing_test.1'])
            resume = ' '.join(cases['tca_timing_test.1101'])
            self.assertIn('days = 2', entry)
            self.assertNotIn('TCA_TEST PASS', entry)
            self.assertIn('TCA_TEST PASS', resume)
            self.assertNotIn('remove_character_flag = tca_test_case_failed', resume[:resume.index('CHECK_PASS')])
            self.assertIn('tca_test_delayed_case_active', entry)
            dispatcher = definitions(result[root / 'events/tca_tests_events.txt'])
            self.assertNotIn('tca_test_notify_results_effect', ' '.join(dispatcher['tca_tests.1000']))
            self.assertIn('tca_test_notify_results_effect', ' '.join(dispatcher['tca_tests.2']))
            self.assertIn('tca_test_notify_waiting_effect', ' '.join(dispatcher['tca_tests.1']))

    def test_invalid_waits_are_rejected(self):
        for value in ['0', '-1', '31', '1.5', '{ days = 2 }']:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.delayed_suite(root, value)
                with patch.object(builder, 'ROOT', root):
                    with self.assertRaisesRegex(ValueError, 'wait_days'):
                        builder.render()

    def test_delayed_cases_are_chained_not_dispatched_together(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.delayed_suite(root)
            self.write_suite(root, 'tca_z_tests.txt', 'tca_test_second')
            p = root / 'tests/tca_z_tests.txt'
            p.write_text(p.read_text().replace('expect =', 'wait_days = 2 expect ='))
            with patch.object(builder, 'ROOT', root):
                result = builder.render()
            from check_upstream_overrides import definitions
            events = definitions(result[root / 'events/tca_tests_events.txt'])
            self.assertNotIn('tca_z_test.1', events['tca_tests.1'])
            self.assertIn('tca_timing_test.1', events['tca_tests.1000'])
            self.assertIn('tca_z_test.1', events['tca_tests.1001'])
            effect = result[root / 'common/scripted_effects/tca_test_delayed_dispatch_effects.txt']
            self.assertIn('trigger_event = tca_tests.1001', effect)
            self.assertIn('trigger_event = tca_tests.2', effect)

    def test_business_source_cannot_modify_framework_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_suite(root, 'tca_a_tests.txt', 'tca_test_bookkeeping')
            p = root / 'tests/tca_a_tests.txt'
            p.write_text(p.read_text().replace('tca_fixture', 'tca_test_case_failed'))
            with patch.object(builder, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'reserved'):
                    builder.render()

    def test_multiple_waits_keep_sequential_assertion_numbers(self):
        from check_upstream_overrides import definitions
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.delayed_suite(root)
            p = root / 'tests/tca_timing_tests.txt'
            p.write_text(p.read_text()[:-1] + 'wait_days = 1 expect = { always = yes } }')
            with patch.object(builder, 'ROOT', root):
                result = builder.render()
            cases = definitions(result[root / 'events/tca_timing_test_events.txt'])
            middle = ' '.join(cases['tca_timing_test.1101'])
            last = ' '.join(cases['tca_timing_test.1102'])
            self.assertIn('CHECK_PASS tca_test_delayed 1', middle)
            self.assertNotIn('TCA_TEST PASS', middle)
            self.assertIn('CHECK_PASS tca_test_delayed 2', last)
            self.assertIn('TCA_TEST PASS', last)


if __name__ == '__main__':
    unittest.main()
