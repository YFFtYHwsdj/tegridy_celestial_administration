import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace

from run_diarchy_ui_probe import EXPECTED, ROOT, inspect_probe, tab_probe_templates, bind_tab_selections


class DiarchyGuiEvidenceTests(unittest.TestCase):
    def test_probe_reuses_actual_tab_callbacks_and_rejects_missing_templates(self):
        window = (ROOT / 'gui/window_diarchy.gui').read_text(encoding='utf-8-sig')
        generated = tab_probe_templates(window)
        self.assertEqual(generated.count('on_start ='), 6)
        self.assertNotIn('onclick', generated)
        self.assertIn("OpenGameViewData('diarchy', GetPlayer.GetID)", generated)
        with self.assertRaises(ValueError):
            tab_probe_templates('')

    def test_selection_binding_tracks_actual_predicates_and_rejects_missing(self):
        window = (ROOT / 'gui/window_diarchy.gui').read_text(encoding='utf-8-sig')
        source = (ROOT / 'tools/diarchy_ui_probe/gui/tca_diarchy_ui_probe.gui').read_text(encoding='utf-8-sig')
        rendered = bind_tab_selections(source, window)
        self.assertNotIn('@SELECT_', rendered)
        self.assertIn('Nor(', rendered)
        changed = window.replace('down = "[DiarchyWindow.GetDiarchyOwner.IsLocalPlayer]"',
                                 'down = "[TEST_SELECTION_SENTINEL]"')
        self.assertIn('TEST_SELECTION_SENTINEL', bind_tab_selections(source, changed))
        with self.assertRaises(ValueError):
            bind_tab_selections(source, '')
        with self.assertRaises(ValueError):
            bind_tab_selections('@SELECT_UNKNOWN@', window)

    def test_prepared_probe_registers_startup_and_seals_actual_callbacks(self):
        from run_diarchy_ui_probe import prepare_probe
        from run_game_tests import verify_snapshot
        with tempfile.TemporaryDirectory() as temp:
            run = prepare_probe(SimpleNamespace(run_root=Path(temp), settings=Path(temp)/'missing'))
            adapter = run / 'mod/tca_cli_adapter'
            registration = (adapter/'gui/scripted_widgets/tca_cli_widgets.txt').read_text(encoding='utf-8-sig')
            self.assertIn('gui/tca_diarchy_ui_probe.gui = tca_gui_probe_start', registration)
            rendered = (adapter/'gui/tca_diarchy_ui_probe.gui').read_text(encoding='utf-8-sig')
            self.assertNotIn('@SELECT_', rendered)
            self.assertIn('on_start = "[OpenGameViewData', rendered)
            self.assertEqual(verify_snapshot(run), [])

    def test_native_failure_is_rejected_even_if_pass_markers_are_present(self):
        log = self.complete() + '\n[D][jomini_effect_impl.cpp:450]: TCA_GUI_FAIL_END_SYSTEM_STATE'
        self.assertTrue(any('acceptance assertion failed' in x for x in inspect_probe(log, '')[0]))
        echo = self.complete() + '\n[console.cpp:1]: TCA_GUI_FAIL_END_SYSTEM_STATE'
        self.assertEqual(inspect_probe(echo, '')[0], [])

    def test_sequence_advances_independently_and_uses_native_end_interaction(self):
        from check_upstream_overrides import definitions
        source = (ROOT/'tools/diarchy_ui_probe/gui/tca_diarchy_ui_probe.gui').read_text(encoding='utf-8-sig')
        controller = source.split('template tca_gui_probe_sequence {', 1)[1]
        self.assertNotIn('ExecuteConsoleCommand', controller)
        for stage in ('governor', 'self', 'liege', 'tongpan', 'return'):
            self.assertIn('name = tca_gui_check_' + stage, controller)
            self.assertIn("'tca_gui_fail_" + stage + "'", controller)
        events = definitions((ROOT/'tools/diarchy_ui_probe/events/tca_diarchy_ui_probe_events.txt').read_text(encoding='utf-8-sig'))
        operation = ' '.join(events['tca_diarchy_ui_probe.2'])
        continuation = ' '.join(events['tca_diarchy_ui_probe.3'])
        self.assertIn('run_interaction', operation)
        self.assertIn('tca_tongpan_end_interaction', operation)
        self.assertNotIn('add_realm_law', operation + continuation)
        self.assertNotIn('tca_refresh_tongpan', operation + continuation)
        self.assertIn('has_diarchy_type = tca_tongpan', continuation)
        self.assertIn('tca_tongpan_efficiency_value = 0', continuation)

    def test_named_widget_reader_cannot_leak_from_next_widget(self):
        from run_diarchy_ui_probe import named_widget_tokens
        source = 'button = { name = "first" size = { 90 90 } } button = { onclick = "NEXT" }'
        self.assertNotIn('onclick', named_widget_tokens(source, 'first'))
        with self.assertRaises(ValueError):
            named_widget_tokens(source, 'missing')

    def test_play_bootstrap_does_not_require_already_being_fixture_player(self):
        text = (ROOT/'tools/diarchy_ui_probe/gui/tca_diarchy_ui_probe.gui').read_text(encoding='utf-8-sig')
        before_play = text.split('ExecuteConsoleCommand(Localize', 1)[0]
        self.assertIn('visible = "[IsInGame]"', before_play)
        self.assertNotIn('tca_ui_player', before_play)
        startup = text.split('template tca_gui_probe_sequence {', 1)[0]
        self.assertNotIn("datacontext = \"[GetPlayer.GetPrimaryTitle", startup)

    def test_grid_guard_detects_the_reported_vertical_overflow_regression(self):
        from run_diarchy_ui_probe import validate_succession_geometry
        source = (ROOT/'gui/window_diarchy.gui').read_text(encoding='utf-8-sig')
        validate_succession_geometry(source)
        broken = source.replace('flipdirection = yes', 'flipdirection = no', 1)
        with self.assertRaisesRegex(ValueError, 'flipdirection'):
            validate_succession_geometry(broken)
        broken = source.replace('maxhorizontalslots = 4', 'maxhorizontalslots = 1', 1)
        with self.assertRaisesRegex(ValueError, 'maxhorizontalslots'):
            validate_succession_geometry(broken)
        cell = source.index('widget = {', source.index('name = "tca_tongpan_title_succession"'))
        broken = source[:cell] + source[cell:].replace('widget = {', 'vbox = {', 1)
        with self.assertRaisesRegex(ValueError, 'bounded widget'):
            validate_succession_geometry(broken)

    def complete(self):
        lines = ['TCA_GUI_FIXTURE_READY']
        lines += [f'[00:00:00][D][jomini_effect_impl.cpp:450]: TCA_GUI_PASS_{s}'
                  for s in EXPECTED]
        lines += ['[00:00:00][D][jomini_effect_impl.cpp:450]: TCA_GUI_COMPLETE']
        return '\n'.join(lines)

    def test_requires_each_gui_result_once(self):
        self.assertEqual(inspect_probe(self.complete(), '')[0], [])
        missing = self.complete().replace('TCA_GUI_PASS_SELF', 'OTHER')
        self.assertTrue(any('SELF' in issue for issue in inspect_probe(missing, '')[0]))
        duplicate = self.complete() + '\n[D][jomini_effect_impl.cpp:450]: TCA_GUI_PASS_SELF'
        self.assertTrue(any('SELF' in issue for issue in inspect_probe(duplicate, '')[0]))

    def test_console_echo_is_not_gui_evidence(self):
        text = self.complete().replace('[jomini_effect_impl.cpp:450]', '[console.cpp:1]')
        self.assertTrue(inspect_probe(text, '')[0])

    def test_checks_initialization_completion_and_same_run_errors(self):
        for removed in ('TCA_GUI_FIXTURE_READY', 'TCA_GUI_COMPLETE'):
            self.assertTrue(inspect_probe(self.complete().replace(removed, ''), '')[0])
        error = "[00:00:00][E]: gui/window_diarchy.gui:10 Could not find data system function 'Bad'"
        self.assertTrue(inspect_probe(self.complete(), error)[0])
