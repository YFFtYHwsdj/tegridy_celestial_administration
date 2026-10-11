"""Regression checks for engine loading contracts, not simulated game rules."""
from pathlib import Path
import re
import unittest
from check_upstream_overrides import definitions, tokens

ROOT = Path(__file__).resolve().parents[1]


class JudicialLoadingTests(unittest.TestCase):
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
