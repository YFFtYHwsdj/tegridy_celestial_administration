"""核对退休契约的界面结构与原版覆盖范围；不模拟待遇或引擎显示规则。"""
from pathlib import Path
import unittest

from check_upstream_overrides import definitions, tokens

ROOT = Path(__file__).resolve().parents[2]


class RetirementContractDisplayTests(unittest.TestCase):
    def test_treasury_override_preserves_native_levels(self):
        # 官署预算隔离及退休排除仅改变显示／授权，不能顺便改写原版发展金档位。
        actual = definitions((ROOT / 'common/subject_contracts/contracts/zz_tca_celestial_treasury.txt').read_text(encoding='utf-8-sig'))['celestial_treasury']
        native = definitions((ROOT / 'tools/baselines/celestial_treasury.txt').read_text(encoding='utf-8-sig'))['celestial_treasury']
        for addition in (
            'scope:subject = { NOT = { tca_is_landless_official_trigger = yes } NOT = { tca_retirement_is_exited_trigger = yes } }',
            'can_be_changed = { scope:subject = { OR = { NOT = { tca_retirement_is_exited_trigger = yes } has_character_flag = tca_retirement_updating_contract } } }',
        ):
            seq = tokens(addition)
            matches = [i for i in range(len(actual)) if actual[i:i + len(seq)] == seq]
            self.assertEqual(len(matches), 1, addition)
            start = matches[0]
            actual = actual[:start] + actual[start + len(seq):]
        self.assertEqual(actual, native)

    def test_salary_override_preserves_native_levels(self):
        # 只排除退休者的显示和人工改约；原版五档数值、好感与AI分值必须保留。
        actual = definitions((ROOT / 'common/subject_contracts/contracts/zz_tca_retirement_salary.txt').read_text(encoding='utf-8-sig'))['celestial_salary']
        native = definitions((ROOT / 'tools/baselines/tca_retirement_salary.txt').read_text(encoding='utf-8-sig'))['celestial_salary']
        for addition in (
            'scope:subject = { NOT = { tca_retirement_is_exited_trigger = yes } }',
            'can_be_changed = { scope:subject = { OR = { NOT = { tca_retirement_is_exited_trigger = yes } has_character_flag = tca_retirement_updating_contract } } }',
        ):
            seq = tokens(addition)
            matches = [i for i in range(len(actual)) if actual[i:i + len(seq)] == seq]
            self.assertEqual(len(matches), 1, addition)
            start = matches[0]
            actual = actual[:start] + actual[start + len(seq):]
        self.assertEqual(actual, native)

    def test_retirement_types_are_separate_readonly_entries(self):
        source = (ROOT / 'common/subject_contracts/contracts/tca_retirement_contracts.txt').read_text(encoding='utf-8-sig')
        contracts = definitions(source)
        group = definitions((ROOT / 'common/subject_contracts/groups/zz_tca_celestial_contract_group.txt').read_text(encoding='utf-8-sig'))['celestial_vassal']
        self.assertNotIn('tca_retirement_salary', contracts)
        self.assertNotIn('tca_retirement_salary', group)
        for name, trait in (('tca_fengci_salary', 'tca_fengci'), ('tca_zhishi_salary', 'tca_retired')):
            self.assertIn(name, group)
            body = ' '.join(contracts[name])
            self.assertIn('is_shown = { scope:subject = { has_trait = ' + trait, body)
            self.assertIn('can_be_changed = { scope:subject = { has_character_flag = tca_retirement_updating_contract } }', body)


if __name__ == '__main__':
    unittest.main()
