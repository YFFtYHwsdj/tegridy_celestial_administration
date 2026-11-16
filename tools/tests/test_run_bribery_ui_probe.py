"""图形验收报告的证据门槛；不复制行贿业务规则。"""
import unittest
from run_bribery_ui_probe import EXPECTED, inspect, native_markers


class BriberyGuiEvidenceTests(unittest.TestCase):
    def complete_log(self):
        items = ['TCA_BUI_FIXTURE_READY', 'TCA_BUI_DESTROYED_LIVE_STATE',
                 'TCA_BUI_RELOAD_READY']
        items += ['TCA_BUI_PASS_' + name for name in EXPECTED]
        items += ['TCA_BUI_COMPLETE']
        return '\n'.join('[D][jomini_effect_impl.cpp:450]: file: fixture: ' + item for item in items)

    def test_complete_requires_both_real_process_phases(self):
        issues, counts = inspect(self.complete_log(), '', 2)
        self.assertEqual(issues, [])
        self.assertEqual(set(counts), set(EXPECTED))
        self.assertIn('Expected two real process phases', inspect(self.complete_log(), '', 1)[0])

    def test_console_echo_is_not_execution_evidence(self):
        log = '[D][console.cpp]: effect debug_log = "TCA_BUI_PASS_PLAYER"'
        self.assertEqual(native_markers(log), [])
        self.assertTrue(inspect(log, '', 2)[0])

    def test_duplicate_or_failed_checks_cannot_pass(self):
        log = self.complete_log() + '\n[D][jomini_effect_impl.cpp:450]: file: fixture: TCA_BUI_PASS_PLAYER'
        self.assertTrue(inspect(log, '', 2)[0])
        log = self.complete_log() + '\n[D][jomini_effect_impl.cpp:450]: file: fixture: TCA_BUI_FAIL_PAYMENT'
        self.assertTrue(inspect(log, '', 2)[0])

    def test_debug_only_engine_error_cannot_pass(self):
        log = self.complete_log() + "\n[12:00:00][E][gui.cpp:1]: Could not find data system function tca_bui_broken\n"
        self.assertTrue(inspect(log, '', 2)[0])

    def test_adapter_native_window_error_cannot_pass(self):
        log = self.complete_log() + "\n[12:00:00][E][gui.cpp:1]: interaction_confirmation.gui: Invalid binding\n"
        self.assertTrue(inspect(log, '', 2)[0])
