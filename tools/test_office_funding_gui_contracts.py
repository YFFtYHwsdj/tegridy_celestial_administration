"""约束国库提示框的数据上下文；不以静态检查代替游戏内布局验收。"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUI_PATH = ROOT / 'gui/tca_office_funding_types.gui'


class OfficeFundingGuiContracts(unittest.TestCase):
    def test_detached_tooltip_does_not_require_character_context(self):
        # 顶栏只给明细传入 ValueBreakdown；Character 曾让数值和条件同时失效。
        gui = GUI_PATH.read_text(encoding='utf-8-sig')
        self.assertNotRegex(gui, r'(?<![\w])Character\.')
        topbar = gui.split('type tca_office_funding_person_row =', 1)[0]
        expressions = re.findall(r'"(\[[^"\n]+\])"', topbar)
        funding = [expression for expression in expressions if 'tca_office_funding_' in expression]
        self.assertTrue(funding)
        for expression in funding:
            with self.subTest(expression=expression):
                self.assertNotRegex(expression, r'(?<![\w])Character\.')
                self.assertIn('GetPlayer.MakeScope', expression)

    def test_zero_rows_and_totals_use_same_player_as_topbar(self):
        # 约束明细与顶栏的绑定一致，不在 Python 中计算游戏经费。
        gui = GUI_PATH.read_text(encoding='utf-8-sig')
        hud = (ROOT / 'gui/hud.gui').read_text(encoding='utf-8-sig')
        self.assertIn("GetPlayer.MakeScope.ScriptValue('tca_office_funding_balance_value')", hud)
        for kind in ('income', 'expense'):
            value = f"GetPlayer.MakeScope.ScriptValue('tca_office_funding_{kind}_value')"
            self.assertIn(f'visible = "[NotEqualTo_CFixedPoint({value}, \'(CFixedPoint)0\')]"', gui)
            self.assertIn(f'EqualTo_CFixedPoint({value}, \'(CFixedPoint)0\')', gui)
            operation = 'Add' if kind == 'income' else 'Subtract'
            self.assertIn(f'{operation}_CFixedPoint(ValueBreakdown.GetFixedPointValue, {value})', gui)

    def test_detail_amounts_are_plain_and_outer_amounts_are_links(self):
        # 外层提示入口保留下划线；分项不再继承递归数值提示和收入着色。
        gui = GUI_PATH.read_text(encoding='utf-8-sig')
        self.assertIn('type tca_office_funding_income_breakdown =', gui)
        details = gui.split('type tca_office_funding_income_breakdown =', 1)[1]
        self.assertNotIn('ValueBreakdown.GetValue', details)
        self.assertEqual(details.count('name = "tca_funding_total"'), 2)
        self.assertEqual(details.count('text = "BREAKDOWN_ENTRY_TOTAL_TREASURY"'), 2)
        self.assertIn('fonttintcolor = "[TooltipInfo.GetTintColor]"', details)
        for label in ('receipt', 'payment'):
            self.assertRegex(details, r'align = left\s+text = "tca_office_funding_' + label + '"')
        row = gui.split('type tca_office_funding_person_row =', 1)[1].split('# 收入列', 1)[0]
        self.assertRegex(row, r'text_single = \{\s+layoutpolicy_horizontal = expanding\s+fonttintcolor = "\[TooltipInfo.GetTintColor\]"\s+align = right')

        self.assertNotIn('tooltipwidget', details)
        self.assertNotIn('#P', details)
        self.assertNotIn('|L', details)
        self.assertEqual(details.count('datamodel = "[GetPlayer.GetTitles]"'), 2)
        self.assertIn("tca_office_funding_amount_value')|1]", details)
        self.assertIn("tca_office_funding_judicial_expense_value'))|1]", details)
        self.assertIn("tca_office_funding_tongpan_expense_value'))|1]", details)
        self.assertIn("tca_office_funding_income_value')|+1L]", gui)
        self.assertIn("tca_office_funding_expense_value'))|1L]", gui)

    def test_empty_title_items_do_not_reserve_breakdown_spacing(self):
        # 每个头衔先筛选整项，再排除隐藏的类别行，避免零额头衔留下空行。
        gui = GUI_PATH.read_text(encoding='utf-8-sig')
        for kind in ('income', 'expense'):
            section = gui.split(f'type tca_office_funding_{kind}_breakdown =', 1)[1]
            section = section.split('# 总计与顶栏经费行', 1)[0]
            self.assertIn('ignoreinvisible = yes', section)
            item = section.split('item = {', 1)[1]
            wrapper = item.split('tca_office_funding_person_row =', 1)[0]
            self.assertIn('ignoreinvisible = yes', wrapper)
            self.assertIn('visible = "[', wrapper)
            if kind == 'income':
                self.assertIn("tca_office_funding_amount_value'), '(CFixedPoint)0'", wrapper)
            else:
                for office in ('judicial', 'tongpan'):
                    self.assertIn(f'tca_office_funding_{office}_expense_value', wrapper)

    def test_budget_contracts_are_separate_without_named_modifier_states(self):
        # 两类契约分别筛选官署；说明不再并列两类待遇或链接状态修正。
        contracts = (ROOT / 'common/subject_contracts/contracts/tca_official_contracts.txt').read_text(encoding='utf-8-sig')
        self.assertIn('tca_circuit_office_budget = {', contracts)
        self.assertIn('tca_tongpan_budget = {', contracts)
        self.assertNotIn('tca_official_budget = {', contracts)
        for kind in ('circuit', 'tongpan'):
            self.assertIn(f'tca_uses_{kind}_budget_trigger = yes', contracts)
        self.assertFalse((ROOT / 'common/modifiers/tca_office_funding_modifiers.txt').exists())
        rates = (ROOT / 'common/script_values/tca_office_funding_values.txt').read_text(encoding='utf-8-sig')
        self.assertNotIn('has_character_modifier', rates)
        for language in ('english', 'simp_chinese'):
            text = (ROOT / f'localization/{language}/tca_official_contracts_l_{language}.yml').read_text(encoding='utf-8-sig')
            self.assertNotIn('GetModifier(', text)
            self.assertIn('tca_circuit_office_budget_medium_desc:', text)
            self.assertIn('tca_tongpan_budget_medium_desc:', text)

    def test_person_links_and_concept_exist_in_both_languages(self):
        # 姓名必须保留人物链接；概念及说明须成对提供，保持本地化BOM。
        for language in ('english', 'simp_chinese'):
            path = ROOT / f'localization/{language}/tca_official_contracts_l_{language}.yml'
            self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf'))
            text = path.read_text(encoding='utf-8-sig')
            self.assertIn("tca_funding_display_office').GetHolder.GetName]", text)
            self.assertIn('game_concept_tca_local_office_funding:', text)
            self.assertIn('game_concept_tca_local_office_funding_desc:', text)
            self.assertIn('[tca_local_office_funding|E]', text)
        gui = GUI_PATH.read_text(encoding='utf-8-sig')
        for binding in ('song_judicial_title', 'tca_tongpan_office', 'song_judicial_circuit', 'tca_tongpan_county'):
            self.assertIn(f"Title.MakeScope.Var('{binding}').Title.GetHolder.GetName]", gui)

    def test_character_window_only_replaces_native_treasury_tooltip(self):
        from check_upstream_overrides import tokens
        gui = (ROOT / 'gui/window_character.gui').read_text(encoding='utf-8-sig')
        baseline = (ROOT / 'tools/baselines/office_funding_window_character.gui').read_text(encoding='utf-8-sig')
        key = '"tca_office_funding_character_treasury_tooltip"'
        self.assertEqual(gui.count(key), 1)
        self.assertEqual(tokens(gui.replace(key, '"[Character.GetTreasuryTooltipWithBalance]"')), tokens(baseline))

    def test_character_treasury_tooltip_reads_viewed_character(self):
        # 人物详情可以查看非玩家官员，不能拿顶栏玩家替代该人物。
        for language in ('english', 'simp_chinese'):
            text = (ROOT / f'localization/{language}/tca_official_contracts_l_{language}.yml').read_text(encoding='utf-8-sig')
            line = next(line for line in text.splitlines() if line.lstrip().startswith('tca_office_funding_character_treasury_tooltip:'))
            self.assertIn('Character.GetTreasury|V0', line)
            self.assertIn("Character.MakeScope.ScriptValue('tca_office_funding_balance_value')|V=1", line)
            self.assertNotIn('GetPlayer', line)


if __name__ == '__main__':
    unittest.main()
