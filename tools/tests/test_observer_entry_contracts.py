"""面向引擎的入口约定；玩法断言位于原生事件中。"""
from pathlib import Path
import unittest
from check_upstream_overrides import definitions

ROOT = Path(__file__).resolve().parents[2]


class ObserverEntryContracts(unittest.TestCase):
    def test_lifecycle_character_fixtures_declare_gender(self):
        import re
        text = (ROOT / 'events/tests/tca_test_lifecycle_test_events.txt').read_text(encoding='utf-8-sig')
        fixtures = re.findall(r'create_character = \{([^{}]+)\}', text)
        self.assertEqual(len(fixtures), 4)
        for fixture in fixtures:
            self.assertRegex(fixture, r'\b(?:gender|gender_female_chance)\s*=')

    def test_death_results_are_read_from_living_reporter(self):
        events = definitions((ROOT / 'events/tests/tca_test_lifecycle_test_events.txt').read_text(encoding='utf-8-sig'))
        continuation = ' '.join(events['tca_test_lifecycle_test.1102'])
        self.assertNotRegex(continuation, r'scope:tca_test_death_fixture_target = \{[^{}]*(?:has_variable|var:)')
        self.assertIn('tca_test_lifecycle_cleanup_observed', continuation)

    def test_delayed_continuations_validate_environment_before_running(self):
        checked = 0
        for path in (ROOT / 'events').rglob('tca_*test*_events.txt'):
            for event, body in definitions(path.read_text(encoding='utf-8-sig')).items():
                if not event.startswith('tca_') or int(event.rsplit('.', 1)[1]) < 1000:
                    continue
                checked += 1
                text = ' '.join(body)
                self.assertIn('immediate = { tca_test_validate_environment_effect = yes if = { limit = { NOT = { has_character_flag = tca_test_suite_aborted } }', text, event)
        self.assertGreater(checked, 0)

    def test_test_protection_has_no_native_immortal_side_effects(self):
        trait = definitions((ROOT / 'common/traits/tca_test_traits.txt').read_text(encoding='utf-8-sig'))['tca_test_death_protection']
        self.assertIn('immortal', trait)
        for entry in ('opposites', 'long_reign_bonus_mult', 'fertility', 'health'):
            self.assertNotIn(entry, trait)

    def test_observer_entry_does_not_depend_on_console_player(self):
        effects = definitions((ROOT / 'common/scripted_effects/tests/framework/tca_test_observer_entry_effects.txt').read_text(encoding='utf-8-sig'))
        entry = effects['tca_run_observer_tests_effect']
        resolver = effects['tca_test_resolve_observer_host_effect']
        for body in (entry, resolver):
            self.assertNotIn('root', body)
            self.assertNotIn('is_ai', body)
            self.assertNotIn('is_local_player', body)
        self.assertIn('title:h_china', resolver)
        self.assertIn('clear_saved_scope', resolver)
        self.assertIn('scope:tca_test_observer_host', entry)
        self.assertIn('tca_tests.1', entry)

    def test_observer_rejection_does_not_reset_suite_statistics(self):
        effects = definitions((ROOT / 'common/scripted_effects/tests/framework/tca_test_observer_entry_effects.txt').read_text(encoding='utf-8-sig'))
        entry = effects['tca_run_observer_tests_effect']
        self.assertIn('debug_only', entry)
        self.assertIn('tca_test_observer_world_ready_trigger', entry)
        self.assertIn('any_living_character', entry)
        self.assertIn('tca_test_suite_running', entry)
        self.assertIn('tca_test_delayed_case_active', entry)
        for mutation in ('set_variable', 'change_variable', 'remove_variable', 'add_character_flag', 'remove_character_flag'):
            self.assertNotIn(mutation, entry)


if __name__ == '__main__':
    unittest.main()
