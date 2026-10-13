"""Regression checks for engine loading contracts, not simulated game rules."""
from pathlib import Path
import re
import unittest
from check_upstream_overrides import definitions, tokens

ROOT = Path(__file__).resolve().parents[1]


class JudicialLoadingTests(unittest.TestCase):
    def test_review_linked_tooltip_does_not_require_event_role_aliases(self):
        # #tooltip localization has no inherited event actor/recipient context.
        for language in ('english', 'simp_chinese'):
            text = (ROOT / f'localization/{language}/tca_custody_review_l_{language}.yml').read_text(encoding='utf-8-sig')
            linked_keys = set(re.findall(r'#tooltip:(tca_review_\w+)', text))
            self.assertTrue(linked_keys)
            entries = dict(re.findall(r'^\s*(tca_review_\w+):\s*"(.*)"$', text, re.MULTILINE))
            for key in linked_keys:
                self.assertIn(key, entries)
                self.assertNotRegex(entries[key], r'(?<![\w.])(?:actor|recipient)\.', key)

    def test_native_naming_override_changes_only_title_capital_link(self):
        native = (ROOT / 'tools/baselines/tgp_chinese_naming_tier_trigger.txt').read_text()
        mod = definitions((ROOT / 'common/scripted_triggers/zz_tca_chinese_naming_triggers.txt').read_text(encoding='utf-8-sig'))
        corrected = native.replace('scope:title ?= {\n\t\t\tcapital_county.title_province',
                                   'scope:title ?= {\n\t\t\ttitle_capital_county.title_province')
        self.assertNotEqual(corrected, native)
        self.assertEqual(mod['tgp_chinese_naming_tier_trigger'],
                         definitions(corrected)['tgp_chinese_naming_tier_trigger'])

    def test_native_unique_naming_helper_changes_only_title_capital_link(self):
        native = (ROOT / 'tools/baselines/tgp_has_unique_chinese_naming.txt').read_text()
        mod = definitions((ROOT / 'common/scripted_triggers/zz_tca_chinese_naming_triggers.txt').read_text(encoding='utf-8-sig'))
        corrected = native.replace('scope:title.capital_county.title_province',
                                   'scope:title.title_capital_county.title_province')
        self.assertNotEqual(corrected, native)
        self.assertEqual(mod['tgp_has_unique_chinese_naming'],
                         definitions(corrected)['tgp_has_unique_chinese_naming'])

    def test_native_event_cases_are_registered_in_dispatcher(self):
        from check_test_run import expected_cases
        expected = expected_cases(ROOT)
        suite = (ROOT / 'events/tca_tests_events.txt').read_text(encoding='utf-8-sig')
        total = re.search(r'name = tca_test_suite_expected value = (\d+)', suite)
        self.assertEqual(int(total.group(1)), len(expected))
        logged_total = re.search(r'TCA_TEST SUITE_DISPATCH (\d+) cases', suite)
        self.assertIsNotNone(logged_total)
        self.assertEqual(int(logged_total.group(1)), len(expected))
        entries = set()
        for path in (ROOT / 'events').glob('tca_*test*_events.txt'):
            entries.update(re.findall(r'TCA_TEST BEGIN (\S+) tca_test_', path.read_text(encoding='utf-8-sig')))
        for entry in entries:
            self.assertEqual(len(re.findall(r'trigger_event\s*=\s*'+re.escape(entry)+r'(?![\d.])', suite)), 1, entry)
        self.assertFalse((ROOT / 'tools/build_test_events.py').exists())
        self.assertFalse((ROOT / 'tools/test_sources').exists())
        self.assertFalse(list((ROOT / 'tests').glob('tca_*_tests.txt')))

    def test_serial_dispatch_reaches_all_delayed_cases_before_summary(self):
        # Count registration alone cannot catch a premature summary in the wait chain.
        suite = definitions((ROOT / 'events/tca_tests_events.txt').read_text(encoding='utf-8-sig'))
        stages = {}
        delayed_entries = set()
        for event, body in suite.items():
            text = ' '.join(body)
            stage = re.search(r'name = tca_test_suite_delayed_next value = (\d+)', text)
            if stage:
                self.assertNotIn(int(stage[1]), stages)
                stages[int(stage[1])] = event
                target = re.search(r'trigger_event = (tca_\w+_test\.\d+)', text)
                self.assertIsNotNone(target, event)
                delayed_entries.add(target[1])
        self.assertEqual(set(stages), set(range(len(stages))))
        effects = definitions((ROOT / 'common/scripted_effects/tca_test_delayed_dispatch_effects.txt').read_text(encoding='utf-8-sig'))
        edges = dict((int(n), event) for n, event in re.findall(
            r'limit = \{ var:tca_test_suite_delayed_next = (\d+) \} trigger_event = (tca_tests\.\d+)',
            ' '.join(effects['tca_test_continue_delayed_effect'])))
        self.assertEqual(set(edges), set(stages))
        for index in range(len(stages) - 1):
            self.assertEqual(edges[index], stages[index + 1], index)
        self.assertEqual(edges[len(stages) - 1], 'tca_tests.2')
        declared = set()
        for path in (ROOT / 'events').glob('tca_*test*_events.txt'):
            for event, body in definitions(path.read_text(encoding='utf-8-sig')).items():
                text = ' '.join(body)
                if 'TCA_TEST BEGIN' in text and 'add_character_flag = tca_test_delayed_case_active' in text:
                    declared.add(event)
        self.assertEqual(delayed_entries, declared)

    def test_known_circuit_name_keys_resolve_without_transient_scopes(self):
        from check_upstream_overrides import localization_values
        titles = definitions((ROOT / 'common/landed_titles/tca_judicial_titles.txt').read_text(encoding='utf-8-sig'))
        naming = (ROOT / 'common/scripted_effects/tca_judicial_title_name_effects.txt').read_text(encoding='utf-8-sig')
        for language in ['english', 'simp_chinese']:
            path = ROOT / f'localization/{language}/tca_judicial_static_titles_l_{language}.yml'
            self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf'))
            loc = localization_values(path)
            for title in titles:
                circuit = title.replace('d_tca_judicial_', 'k_')
                self.assertIn(f'var:song_judicial_circuit = title:{circuit}', naming)
                self.assertIn(f'set_title_name = {title}', naming)
                self.assertIn(f"GetTitleByKey('{circuit}')", loc[title])
                self.assertNotIn('tca_circuit.', loc[title])

    def test_request_arrest_cannot_auto_approve_intermediary(self):
        interactions = definitions((ROOT / 'common/character_interactions/tca_judicial_arrest_interactions.txt').read_text(encoding='utf-8-sig'))
        request = ' '.join(interactions['tca_request_imprison_interaction'])
        self.assertIn('auto_accept = no', request)
        self.assertNotRegex(request, r'(?<!\w)auto_accept = \{')
        # The direct interaction keeps the native auto-accept rule.
        self.assertIn('auto_accept = {', ' '.join(interactions['tca_judicial_imprison_interaction']))
        # Apply ordinary scoring first; reset and set the recipient endpoint last.
        self.assertRegex(request, r'ai_accept = \{ base = 0 tca_judicial_target_acceptance = yes modifier = \{ factor = 0 scope:recipient = \{ tca_judicial_arrest_ai_cannot_refuse_trigger = yes \} \} modifier = \{ add = 100 desc = tca_judicial_arrest_cannot_refuse_reason scope:recipient = \{ tca_judicial_arrest_ai_cannot_refuse_trigger = yes \} \} \}')

    def test_modifier_calls_only_pass_declared_arguments(self):
        modifiers = definitions((ROOT / 'common/scripted_modifiers/tca_judicial_prison_modifiers.txt').read_text(encoding='utf-8-sig'))
        interactions = definitions((ROOT / 'common/character_interactions/tca_judicial_arrest_interactions.txt').read_text(encoding='utf-8-sig'))
        seen = 0
        for interaction, body in interactions.items():
            for i, token in enumerate(body):
                if token not in modifiers or body[i + 1] != '=':
                    continue
                seen += 1
                allowed = set(re.findall(r'\$([A-Z_]+)\$', ' '.join(modifiers[token])))
                if body[i + 2] == '{':
                    depth, j = 1, i + 3
                    while depth:
                        if depth == 1 and body[j + 1] == '=':
                            self.assertIn(body[j], allowed, (interaction, token, body[j]))
                        depth += (body[j] == '{') - (body[j] == '}')
                        j += 1
                else:
                    self.assertFalse(allowed, (interaction, token))
        self.assertEqual(seen, 4)

    def test_optional_mod_detection_does_not_reference_unloaded_law_flags(self):
        entry = definitions((ROOT / 'common/scripted_triggers/tca_court_system_triggers.txt').read_text(encoding='utf-8-sig'))['tca_external_official_names_trigger']
        self.assertNotIn('has_realm_law_flag', entry)
        self.assertIn('orient_empires_loaded', entry)
        self.assertIn('hanfan_loaded', entry)

    def test_optional_hook_comparisons_are_guarded(self):
        for filename in ['common/scripted_effects/tca_judicial_arrest_native_effects.txt',
                         'common/scripted_modifiers/tca_judicial_prison_modifiers.txt']:
            seq = tokens((ROOT / filename).read_text(encoding='utf-8-sig'))
            for i, token in enumerate(seq):
                if token == 'scope:hook':
                    self.assertNotEqual(seq[i + 1], '=', filename)

    def test_title_hooks_use_coalesced_maintenance(self):
        hooks = (ROOT / 'common/on_action/tca_judicial_title_on_actions.txt').read_text(encoding='utf-8-sig')
        self.assertNotIn('trigger_event', hooks)
        self.assertNotIn('events = { tca_judicial_titles.1 }', hooks)
        self.assertEqual(hooks.count('tca_request_judicial_maintenance_effect = yes'), 4)
        effects = definitions((ROOT / 'common/scripted_effects/tca_judicial_title_effects.txt').read_text(encoding='utf-8-sig'))
        request = effects['tca_request_judicial_maintenance_effect']
        self.assertIn('has_variable', request)
        self.assertLess(request.index('set_variable'), request.index('trigger_event'))
        worker = effects['tca_run_judicial_maintenance_effect']
        self.assertLess(worker.index('tca_refresh_held_judicial_positions_effect'), worker.index('remove_variable'))

    def test_reform_laws_use_shared_permission_triggers(self):
        laws = definitions((ROOT / 'common/laws/tca_court_system_laws.txt').read_text(encoding='utf-8-sig'))
        for name, body in laws.items():
            if name.startswith('tca_judicial_institutions_'):
                self.assertIn('tca_judicial_reform_can_pass_trigger', body)
            elif name.startswith(('tca_local_names_', 'tca_central_names_')):
                self.assertIn('tca_names_reform_can_pass_trigger', body)



if __name__ == '__main__':
    unittest.main()
