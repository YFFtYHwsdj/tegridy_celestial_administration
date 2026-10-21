"""引擎加载约定的回归检查，不模拟游戏规则。"""
from pathlib import Path
import re
import unittest
from check_upstream_overrides import definitions, tokens

ROOT = Path(__file__).resolve().parents[2]


class JudicialLoadingTests(unittest.TestCase):
    def test_review_linked_tooltip_does_not_require_event_role_aliases(self):
        # #tooltip 本地化不继承事件 actor／recipient 上下文。
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
        from testing.catalog import catalog
        expected = expected_cases(ROOT)
        rows = catalog(ROOT)
        self.assertEqual({row['name']: row['checks'] for row in rows}, expected)
        suite = (ROOT / 'events/tests/tca_tests_events.txt').read_text(encoding='utf-8-sig')
        self.assertIn('name = tca_test_suite_expected value = 0', suite)
        self.assertIn('tca_test_catalog_effect = yes', suite)
        self.assertNotIn('tca_test_suite_delayed_next', suite)
        self.assertFalse((ROOT / 'tools/build_test_events.py').exists())
        self.assertFalse((ROOT / 'tools/test_sources').exists())
        self.assertFalse(list((ROOT / 'tests').glob('tca_*_tests.txt')))

    def test_serial_dispatch_claims_before_execution_and_resumes_through_catalog(self):
        from testing.catalog import catalog
        rows = catalog(ROOT)
        declared = set()
        for path in (ROOT / 'events').rglob('tca_*test*_events.txt'):
            for event, body in definitions(path.read_text(encoding='utf-8-sig')).items():
                text = ' '.join(body)
                if 'TCA_TEST BEGIN' in text and 'add_character_flag = tca_test_delayed_case_active' in text:
                    declared.add(event)
        self.assertEqual({row['event'] for row in rows if row['delayed']}, declared)
        dispatcher = definitions((ROOT / 'common/scripted_effects/tests/framework/tca_test_dispatch_effects.txt').read_text(encoding='utf-8-sig'))
        visit = ' '.join(dispatcher['tca_test_visit_case_effect'])
        self.assertIn('NOT = { has_character_flag = tca_test_delayed_case_active }', visit)
        self.assertIn('NOT = { has_character_flag = tca_test_dispatch_claimed }', visit)
        self.assertLess(visit.index('add_character_flag = $CASE$_dispatched'), visit.index('trigger_event = $EVENT$'))
        continuation = (ROOT / 'common/scripted_effects/tests/framework/tca_test_delayed_dispatch_effects.txt').read_text(encoding='utf-8-sig')
        self.assertIn('tca_test_validate_environment_effect = yes', continuation)
        self.assertIn('trigger_event = tca_tests.3', continuation)
        self.assertNotIn('tca_test_suite_delayed_next', continuation)
        suite = definitions((ROOT / 'events/tests/tca_tests_events.txt').read_text(encoding='utf-8-sig'))
        scan = ' '.join(suite['tca_tests.3'])
        self.assertLess(scan.index('tca_test_catalog_effect'), scan.index('trigger_event = tca_tests.2'))
        self.assertIn('NOT = { has_character_flag = tca_test_dispatch_claimed }', scan)

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
        # 直接互动保留原生自动接受规则。
        self.assertIn('auto_accept = {', ' '.join(interactions['tca_judicial_imprison_interaction']))
        # 先应用普通评分，最后重置并设置目标接受度终值。
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
        self.assertEqual(hooks.count('tca_request_judicial_maintenance_effect = yes'), 8)
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
