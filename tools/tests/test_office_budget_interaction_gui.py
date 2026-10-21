"""保护普通互动的原版内容及经费选档数据源；界面行为仍需引擎验证。"""
from pathlib import Path
import re
import unittest

from check_upstream_overrides import tokens

ROOT = Path(__file__).resolve().parents[2]


class OfficeBudgetInteractionGuiTests(unittest.TestCase):
    def test_other_interactions_preserve_native_window(self):
        # 专用双栏只对经费互动替换普通内容；移除新增内容后必须等于原版。
        actual = (ROOT / 'gui/interaction_confirmation.gui').read_text(encoding='utf-8-sig')
        condition = "Or(EqualTo_string(CharacterInteractionConfirmationWindow.GetSendName, Localize('tca_adjust_office_budget_interaction')), EqualTo_string(CharacterInteractionConfirmationWindow.GetSendName, Localize('tca_request_office_budget_interaction')))"
        self.assertEqual(actual.count(f'visible = "[Not({condition})]"'), 1)
        actual = actual.replace(f'visible = "[Not({condition})]"', '')
        for name, actor in [('adjust', 'GetRecipient'), ('request', 'GetPuppetOrActor')]:
            condition = f"EqualTo_string(CharacterInteractionConfirmationWindow.GetSendName, Localize('tca_{name}_office_budget_interaction'))"
            panel = f'tca_office_budget_window_content = {{ visible = "[{condition}]" datacontext = "[CharacterInteractionConfirmationWindow.{actor}]" }}'
            self.assertEqual(actual.count(panel), 1)
            actual = actual.replace(panel, '')
        native = (ROOT / 'tools/baselines/office_budget_interaction_confirmation.gui').read_text(encoding='utf-8-sig')
        self.assertEqual(tokens(actual), tokens(native))

    def test_native_contract_keeps_all_content_and_adds_funding_entry(self):
        # 防止只读档位再无操作入口，同时保护原生俸禄、身份及发送路径。
        actual = (ROOT / 'gui/interaction_modify_vassal_window.gui').read_text(encoding='utf-8-sig')
        start = actual.index('        button_standard = {\n            name = "tca_open_office_budget"')
        end = actual.index('\n\t\tbutton_standard = {\n\t\t\tname = "reset_button"', start)
        bridge = actual[start:end]
        self.assertIn("SubjectContract.GetSubject.MakeScope", bridge)
        self.assertIn("tca_open_office_budget_gui", bridge)
        native = (ROOT / 'tools/baselines/office_budget_modify_vassal_window.gui').read_text(encoding='utf-8-sig')
        self.assertEqual(tokens(actual[:start] + actual[end:]), tokens(native))

    def test_gui_expressions_and_native_send_options(self):
        # 防止表达式未闭合和误用原生契约窗口提供者再次阻断非直属管理者。
        source = (ROOT / 'gui/tca_office_budget_interaction.gui').read_text(encoding='utf-8-sig')
        self.assertNotIn('ModifySubjectContractInteractionWindow', source)
        for expression in re.findall(r'"(\[[^"\n]*\])"', source):
            self.assertEqual(expression.count('('), expression.count(')'), expression)
        self.assertIn('[OptionItem.OnClick]', source)
        self.assertIn('blockoverride "button_letter_current"', source)
        self.assertIn('[CharacterInteractionConfirmationWindow.GetOptionItems]', source)


if __name__ == '__main__':
    unittest.main()
