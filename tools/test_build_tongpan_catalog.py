import tempfile
from pathlib import Path
import unittest
from build_tongpan_catalog import counties_in, write_assets


class TongpanCatalogTests(unittest.TestCase):
    def test_only_provincial_counties_are_offices(self):
        self.assertEqual(counties_in('d_a = { capital = c_a c_a = { b_a = { province = 1 } } c_office = { landless = yes } }'), {'c_a'})

    def test_comments_and_strings_are_not_counties(self):
        self.assertEqual(counties_in('# c_bad = { province = 1 }\nc_a = { name = "c_bad = { province = 1 }" b_a = { province = 1 } }'), {'c_a'})

    def test_missing_end_is_rejected(self):
        with self.assertRaises(ValueError):
            counties_in('c_a = { b_a = { province = 1 }')

    def test_assets_have_fixed_mapping_and_bounded_reserve_without_test_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / 'game'
            (game / 'common/landed_titles').mkdir(parents=True)
            (game / 'common/landed_titles/a.txt').write_text('c_a = { b_a = { province = 1 } }')
            mod = root / 'mod'
            self.assertEqual(write_assets(game, mod, 2), 1)
            title = mod / 'common/landed_titles/tca_tongpan_catalog.txt'
            self.assertTrue(title.read_bytes().startswith(b'\xef\xbb\xbf'))
            self.assertEqual(title.read_text(encoding='utf-8-sig').count('delete_on_destroy = no'), 3)
            effect = (mod / 'common/scripted_effects/tca_tongpan_catalog_effects.txt').read_text(encoding='utf-8-sig')
            self.assertIn('value = title:c_tca_tongpan_a', effect)
            self.assertEqual(effect.count('name = tca_tongpan_reserve'), 2)
            flavor = (mod / 'common/flavorization/tca_tongpan_holder_flavorization.txt').read_text(encoding='utf-8-sig')
            self.assertEqual(flavor.count('c_tca_tongpan_a'), 2)
            self.assertEqual(flavor.count('c_tca_tongpan_reserve_002'), 2)
            self.assertNotIn('        c_a', flavor)
            self.assertIn('gender = female', flavor)
            self.assertFalse((mod / 'events').exists())
            self.assertFalse((mod / 'tools/baselines').exists())

    def test_hash_collision_uses_alias_without_changing_office_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / 'game'
            (game / 'common/landed_titles').mkdir(parents=True)
            (game / 'common/landed_titles/a.txt').write_text('c_yingzhou_2 = { b_a = { province = 1 } }')
            mod = root / 'mod'
            write_assets(game, mod, 1)
            titles = (mod / 'common/landed_titles/tca_tongpan_catalog.txt').read_text(encoding='utf-8-sig')
            self.assertIn('c_tca_tongpan_yingzhou_2 = {', titles)
            for lang in ('english', 'simp_chinese'):
                loc = (mod / f'localization/{lang}/tca_tongpan_catalog_l_{lang}.yml').read_text(encoding='utf-8-sig')
                self.assertNotIn(' c_tca_tongpan_yingzhou_2:', loc)
                self.assertIn(' tca_tongpan_name_yingzhou_2:', loc)
            effects = (mod / 'common/scripted_effects/tca_tongpan_catalog_effects.txt').read_text(encoding='utf-8-sig')
            self.assertIn('this = title:c_tca_tongpan_yingzhou_2', effects)
            self.assertIn('set_title_name = tca_tongpan_name_yingzhou_2', effects)

    def test_invalid_reserve_size_rejected_without_writing(self):
        for size in (0, 4097):
            with self.assertRaises(ValueError):
                write_assets(Path('/nonexistent'), Path('/nonexistent'), size)
