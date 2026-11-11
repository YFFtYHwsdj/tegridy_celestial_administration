"""离线人物资产的稳定性及写入保护；不复制游戏行为。"""
import copy
from pathlib import Path
import tempfile
import unittest
from startup_officials.builder import build_assets, write_assets


def config():
    return {'seed': 73, 'noble_probability': .1, 'offices': [
        {'date': '1066.9.15', 'office': 'c_tca_tongpan_demo', 'jurisdiction': 'c_demo',
         'kind': 'tongpan', 'liege': 'd_demo', 'capital': 'c_demo'},
        {'date': '1178.10.1', 'office': 'c_tca_tongpan_demo', 'jurisdiction': 'c_demo',
         'kind': 'tongpan', 'liege': 'd_demo', 'capital': 'c_demo'}]}


class StartupOfficialsTests(unittest.TestCase):
    def test_stable_and_new_office_does_not_reroll_old(self):
        a = build_assets(config())
        other = config(); row = dict(other['offices'][0], office='c_tca_tongpan_extra', jurisdiction='c_extra')
        other['offices'].append(row)
        b = build_assets(other)
        self.assertEqual(a['history/characters/tca_officials_generated_1066_tongpan.txt'],
                         b['history/characters/tca_officials_generated_1066_tongpan.txt'].split('# 下一人物')[0])
        self.assertEqual(a, build_assets(config()))

    def test_authored_holder_not_generated_or_overwritten(self):
        c = config(); c['offices'][0]['holder'] = 'tca_authored_person'
        a = build_assets(c)
        self.assertNotIn('history/characters/tca_officials_generated_1066_tongpan.txt', a)
        self.assertIn('holder = tca_authored_person', a['history/titles/tca_startup_office_titles.txt'])

    def test_duplicate_office_or_holder_is_rejected(self):
        for duplicate in ('office', 'holder'):
            c = config(); c['offices'].append(copy.deepcopy(c['offices'][0]))
            if duplicate == 'holder':
                c['offices'][-1]['office'] += '_other'
                c['offices'][0]['holder'] = c['offices'][-1]['holder'] = 'tca_same'
            with self.assertRaises(ValueError): build_assets(c)

    def test_explicit_empty_is_not_filled(self):
        c = config(); c['offices'][0].update(empty=True, reason='该开局停用')
        a = build_assets(c)
        self.assertNotIn('history/characters/tca_officials_generated_1066_tongpan.txt', a)

    def test_modified_output_blocks_all_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); assets = build_assets(config())
            write_assets(root, assets)
            first = root/next(iter(assets)); first.write_text('人工修改')
            before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with self.assertRaises(ValueError): write_assets(root, build_assets(dict(config(), seed=2)))
            self.assertEqual(before, {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_existing_unowned_file_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); assets = build_assets(config())
            path = root/next(iter(assets)); path.parent.mkdir(parents=True); path.write_text('人工')
            with self.assertRaises(ValueError): write_assets(root, assets)
            self.assertEqual(path.read_text(), '人工')

    def test_date_history_resets_absent_office_and_generated_people_die(self):
        c = config(); c['offices'] = c['offices'][:1]
        a = build_assets(c)
        self.assertIn('1178.10.1 = { holder = 0', a['history/titles/tca_startup_office_titles.txt'])
        self.assertIn('death = yes', a['history/characters/tca_officials_generated_1066_tongpan.txt'])

    def test_noble_zero_and_one_are_explicit(self):
        for prob, value in [(0, 'no'), (1, 'yes')]:
            a = build_assets(dict(config(), noble_probability=prob))
            self.assertIn('NOBLE = '+value, a['common/scripted_effects/tca_startup_officials_generated_effects.txt'])

    def test_stale_assets_are_removed_but_external_references_block(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); a = build_assets(config()); write_assets(root,a)
            path = root/'events/other.txt'; path.parent.mkdir();
            char = 'tca_gen_1066_c_tca_tongpan_demo'
            path.write_text('character:'+char)
            c=config(); c['offices'][0]['holder']='tca_authored'
            with self.assertRaises(ValueError): write_assets(root,build_assets(c))

    def test_missing_owned_asset_can_be_rebuilt(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); assets=build_assets(config()); write_assets(root,assets)
            name=next(iter(assets)); (root/name).unlink()
            write_assets(root,assets)
            self.assertEqual((root/name).read_text(encoding='utf-8-sig'),assets[name])

    def test_manifest_cannot_claim_path_outside_repository(self):
        import json
        from startup_officials.builder import MANIFEST
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/MANIFEST;path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'files':{'../outside':'fake'}}))
            with self.assertRaisesRegex(ValueError,'非法'):
                write_assets(root,build_assets(config()))

    def test_failed_commit_restores_all_previous_assets(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); write_assets(root,build_assets(config()))
            before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            original=Path.replace
            count=[0]
            def fail_second(path,target):
                count[0]+=1
                if count[0]==2:raise OSError('模拟磁盘提交失败')
                return original(path,target)
            with patch.object(Path,'replace',fail_second):
                with self.assertRaises(OSError):write_assets(root,build_assets(dict(config(),seed=300)))
            after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before,after)

    def test_authored_vanilla_numeric_id_is_accepted(self):
        c=config(); c['offices'][0]['holder']='248149'
        a=build_assets(c)
        self.assertIn('holder = 248149',a['history/titles/tca_startup_office_titles.txt'])

    def test_removed_dynasty_with_authored_reference_blocks_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);write_assets(root,build_assets(config()))
            authored=root/'history/characters/authored.txt'
            authored.write_text('custom = { dynasty = tca_dyn_tca_gen_1066_c_tca_tongpan_demo }')
            c=config();c['offices'][0]['holder']='authored'
            with self.assertRaisesRegex(ValueError,'引用'):write_assets(root,build_assets(c))

    def test_authored_person_gets_historical_candidate_exclusion(self):
        c=config();c['offices'][0]['holder']='tca_authored'
        a=build_assets(c)
        self.assertIn('add_character_flag = tca_history_defined_character',
                      a['common/scripted_effects/tca_startup_officials_generated_effects.txt'])

    def test_initialization_requires_start_day_and_expected_holder(self):
        a=build_assets(config())['common/scripted_effects/tca_startup_officials_generated_effects.txt']
        self.assertIn('current_date = 1066.9.15',a)
        self.assertIn('holder ?= character:tca_gen_1066_c_tca_tongpan_demo',a)
