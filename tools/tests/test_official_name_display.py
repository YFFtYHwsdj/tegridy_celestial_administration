from pathlib import Path
import json
import unittest

from check_upstream_overrides import definitions, localization_values

ROOT = Path(__file__).resolve().parents[2]


class OfficialNameDisplayTests(unittest.TestCase):
    def test_central_names_match_office_titles_above_native_priority(self):
        entries = definitions((ROOT / 'common/flavorization/tca_song_official_names.txt').read_text(encoding='utf-8-sig'))
        for office, title in [('prime', 'e_minister_chancellor'), ('censor', 'e_minister_censor')]:
            for gender in ['male', 'female']:
                tokens = entries[f'tca_song_{office}_holder_{gender}']
                text = ' '.join(tokens)
                self.assertIn(f'titles = {{ {title} }}', text)
                self.assertNotIn('council_position', tokens)
                self.assertGreater(int(tokens[tokens.index('priority') + 2]), 500)
                self.assertIn('flag = tca_song_central_names', text)
                self.assertIn('spouse_takes_title = no', text)

    def test_native_council_keys_remain_available_to_external_laws(self):
        prefix = ('councillor_chancellor_celestial_government_imperial',
                  'councillor_spymaster_celestial_government_imperial')
        for language in ['english', 'simp_chinese']:
            for path in (ROOT / 'localization' / language).rglob('*.yml'):
                for key in localization_values(path):
                    self.assertFalse(key.startswith(prefix), (path, key))

    def test_council_positions_are_not_replaced_for_display_consistency(self):
        registry = json.loads((ROOT / 'tools/upstream_overrides.json').read_text())
        keys = {'councillor_chancellor', 'councillor_spymaster'}
        self.assertFalse(keys.intersection(entry['key'] for entry in registry['overrides']))
        for path in (ROOT / 'common/council_positions').rglob('*.txt'):
            entries = definitions(path.read_text(encoding='utf-8-sig'))
            self.assertFalse(keys.intersection(entries), path)

    def test_law_names_and_effects_are_left_to_native_or_external_mods(self):
        keys = {'grand_chancellor_law', 'grand_censor_law',
                'grand_chancellor_law_effects', 'grand_censor_law_effects'}
        registry = json.loads((ROOT / 'tools/upstream_overrides.json').read_text())
        self.assertFalse(keys.intersection(entry['key'] for entry in registry['localization_overrides']))
        for language in ['english', 'simp_chinese']:
            for path in (ROOT / 'localization' / language).rglob('*.yml'):
                self.assertFalse(keys.intersection(localization_values(path)), path)


if __name__ == '__main__':
    unittest.main()
