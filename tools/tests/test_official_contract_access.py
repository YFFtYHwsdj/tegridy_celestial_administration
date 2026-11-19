"""检查官署改约的原版保留范围及两侧接受路径；不模拟游戏权限规则。"""
from pathlib import Path
import unittest

from check_upstream_overrides import definitions, tokens

ROOT = Path(__file__).resolve().parents[2]


class OfficialContractAccessTests(unittest.TestCase):
    def test_funding_request_does_not_invalidate_its_own_pending_proposal(self):
        # 原生延迟回复曾因on_send先写入冷却而失效；发起时只绑定官署，结果确定后记冷却。
        source = (ROOT / 'common/character_interactions/tca_office_budget_interactions.txt').read_text(encoding='utf-8-sig')
        request = source.split('tca_request_office_budget_interaction = {', 1)[1]
        sending = request.split('on_send = {', 1)[1].split('on_decline = {', 1)[0]
        self.assertIn('tca_office_budget_requested_office', sending)
        self.assertNotIn('tca_office_budget_request_cooldown', sending)
        accepting = request.split('on_accept = {', 1)[1].split('ai_accept = {', 1)[0]
        self.assertIn('primary_title = var:tca_office_budget_requested_office', accepting)
        self.assertIn('remove_variable = tca_office_budget_requested_office', accepting)

    def test_request_override_preserves_native_behavior(self):
        # 仅放宽授权、保存经费及转发行省改约，费用、选项、冷却及AI接受逻辑保持原版。
        key = 'admin_vassal_modify_vassal_contract_interaction'
        native = definitions((ROOT / 'tools/baselines/admin_vassal_modify_vassal_contract_interaction.txt').read_text(encoding='utf-8-sig'))[key]
        actual = definitions((ROOT / 'common/character_interactions/zz_tca_official_request_contract_interactions.txt').read_text(encoding='utf-8-sig'))[key]
        for addition in (
            'tca_can_edit_admin_contract_trigger = { EDITOR = scope:recipient }',
            'tca_record_changed_office_budget_effect = yes',
        ):
            sequence = tokens(addition)
            matches = [i for i in range(len(actual)) if actual[i:i + len(sequence)] == sequence]
            self.assertEqual(len(matches), 1, addition)
            start = matches[0]
            actual = actual[:start] + actual[start + len(sequence):]
        setter = 'vassal_contract_set_obligation_level = { type = scope:obligation.vassal_contract_type level = scope:obligation }'
        forward = (
            'if = { limit = { scope:obligation.vassal_contract_type = vassal_contract:celestial_provinces } '
            'tca_road_contract_apply_effect = { LEVEL = scope:obligation } } '
            f'else = {{ {setter} }}'
        )
        sequence = tokens(forward)
        matches = [i for i in range(len(actual)) if actual[i:i + len(sequence)] == sequence]
        self.assertEqual(len(matches), 1)
        start = matches[0]
        actual = actual[:start] + tokens(setter) + actual[start + len(sequence):]
        desc = 'desc = admin_vassal_modify_vassal_contract_interaction_desc'
        warning = (
            f'desc = {{ {desc} triggered_desc = {{ trigger = {{ scope:puppet_or_actor = {{ '
            'tca_road_contract_managed_trigger = yes vassal_contract_has_flag = celestial_military_appointment '
            'primary_title ?= { any_owned_title_maa_regiment = { count >= 1 } } '
            '} } desc = tca_road_contract_disband_warning } }'
        )
        sequence = tokens(warning)
        matches = [i for i in range(len(actual)) if actual[i:i + len(sequence)] == sequence]
        self.assertEqual(len(matches), 1)
        start = matches[0]
        actual = actual[:start] + tokens(desc) + actual[start + len(sequence):]
        on_send = tokens(
            'on_send = { scope:puppet_or_actor = { if = { limit = { '
            'tca_road_contract_managed_trigger = yes tca_road_contract_selected_trigger = yes '
            '} primary_title = { save_scope_as = tca_road_contract_requested_title } } } }'
        )
        wrapper = tokens(
            'on_accept = { if = { limit = { scope:puppet_or_actor = { '
            'tca_road_contract_pending_request_safe_trigger = yes } }'
        )
        on_decline = tokens('on_decline = {')
        rejected = tokens(
            '} else = { scope:puppet_or_actor = { send_interface_message = { '
            'type = msg_vassal_contract_change title = tca_road_contract_request_lapsed '
            'right_icon = scope:recipient } } } }'
        )
        start = actual.index('on_accept') - len(on_send)
        self.assertEqual(actual[start:start + len(on_send) + len(wrapper)], on_send + wrapper)
        end = actual.index('on_decline')
        self.assertEqual(actual[end - len(rejected):end + len(on_decline)], rejected + on_decline)
        actual = (
            actual[:start] + tokens('on_accept = {') +
            actual[start + len(on_send) + len(wrapper):end - len(rejected)] +
            tokens('}') + actual[end:]
        )
        self.assertEqual(actual, native)

    def test_both_accept_paths_record_office_budget(self):
        # 约束两条真实互动的接受路径接入同一个保存入口，防止只修领主路径。
        for name in ('zz_tca_official_contract_interactions.txt', 'zz_tca_official_request_contract_interactions.txt'):
            source = (ROOT / 'common/character_interactions' / name).read_text(encoding='utf-8-sig')
            self.assertIn('tca_can_edit_admin_contract_trigger =', source)
            accept = source.split('on_accept = {', 1)[1]
            self.assertEqual(accept.count('tca_record_changed_office_budget_effect = yes'), 1)
            self.assertIn('list = changed_obligations', accept)


if __name__ == '__main__':
    unittest.main()
