"""知贡举与会试自动链的静态契约检查。

只验证脚本对象、覆盖范围和本地化键的登记关系，不模拟引擎行为。
"""
import json
from pathlib import Path
import re
import unittest

from check_upstream_overrides import definitions, localization_values, tokens

ROOT = Path(__file__).resolve().parents[2]


class ExamContractTests(unittest.TestCase):
    def test_native_exam_entry_points_share_official_gate(self):
        # 缺少任一入口会让玩家意图、AI收集或随行补入绕过官员排除。
        registry = json.loads((ROOT / 'tools/upstream_overrides.json').read_text(encoding='utf-8'))
        entries = {entry['key']: entry for entry in registry['overrides']}
        expected = {
            'imperial_exam_taker_intent': 1,
            'local_exam_taker_intent': 1,
            'imperial_examination_gather_entrants_effect': 1,
            'local_examination_gather_entrants_effect': 1,
            'imperial_examination_gather_stray_entrants_effect': 3,
            'activity_local_examination': 1,
            'travel_start_event.1100': 2,
        }
        for key, count in expected.items():
            with self.subTest(key=key):
                self.assertTrue(key in entries, '原版应试入口必须接入统一官员限制并登记覆盖')
                entry = entries[key]
                actual = definitions((ROOT / entry['mod']).read_text(encoding='utf-8-sig'))[key]
                native = definitions((ROOT / entry['baseline']).read_text(encoding='utf-8-sig'))[key]
                patched = ' '.join(actual)
                gate = 'tca_exam_can_take_exam_trigger = yes'
                if key.endswith('_intent'):
                    gate = 'custom_tooltip = { text = tca_exam_not_serving_tt ' + gate + ' }'
                self.assertEqual(patched.count(gate), count)
                # 只增设资格门槛，保留原版其余效果及非考生身份。
                if key.endswith('stray_entrants_effect'):
                    patched = patched.replace('limit = { ' + gate + ' }', '')
                if key == 'travel_start_event.1100':
                    self.assertIn('id_override_priority = 1', patched)
                    patched = patched.replace('id_override_priority = 1', '')
                self.assertEqual(tokens(patched.replace(gate, '')), native)

    def test_family_notification_actor_and_bilingual_keys_are_wired(self):
        # 只检查通知的引用契约，不把静态通过当作头像、姓名或送达已经实机验证。
        effects = definitions((ROOT / 'common/scripted_effects/tca_exam_effects.txt').read_text(encoding='utf-8-sig'))
        award = ' '.join(effects['tca_exam_award_candidate_effect'])
        self.assertIn('save_scope_as = tca_exam_result_candidate', award)
        self.assertEqual(award.count('right_icon = scope:tca_exam_result_candidate'), 3)
        self.assertNotIn('right_icon = root', award)
        # 自动链没有原版家主汇总，因此三种逐人通知都不能再排除家主。
        self.assertNotIn('is_house_head', award)
        for language in ('english', 'simp_chinese'):
            loc = localization_values(ROOT / f'localization/{language}/tca_exam_l_{language}.yml')
            for result in ('failed', 'metropolitan', 'palace'):
                for field in ('title', 'desc'):
                    key = f'tca_exam_family_{result}_{field}'
                    self.assertIn(f'{field} = {key}', award)
                    self.assertIn('tca_exam_result_candidate', loc[key])
                    self.assertNotIn('ROOT.Char', loc[key])

    def test_exam_objects_parse_and_are_registered(self):
        position = definitions((ROOT / 'common/court_positions/types/tca_exam_court_positions.txt').read_text(encoding='utf-8-sig'))
        self.assertIn('tca_exam_commissioner_court_position', position)
        tasks = definitions((ROOT / 'common/court_positions/tasks/tca_exam_tasks.txt').read_text(encoding='utf-8-sig'))
        self.assertEqual(set(tasks), {'tca_exam_commissioner_auto_exam', 'tca_exam_commissioner_manual_exam'})
        events = definitions((ROOT / 'events/tca_exam_events.txt').read_text(encoding='utf-8-sig'))
        self.assertEqual({'tca_exam.1', 'tca_exam.2', 'tca_exam.3', 'tca_exam.4', 'tca_exam.5'}, {key for key in events if key.startswith('tca_exam.')})

    def test_position_uses_expected_eligibility_and_salary(self):
        body = ' '.join(definitions((ROOT / 'common/court_positions/types/tca_exam_court_positions.txt').read_text(encoding='utf-8-sig'))['tca_exam_commissioner_court_position'])
        self.assertIn('merit_level >= 4', body)
        self.assertIn('learning >= 16', body)
        self.assertIn('is_landed = no', body)
        self.assertIn('tgp_passed_metropolitan_examination = yes', body)
        self.assertIn('trait_third_of_five_level_value', body)
        self.assertIn('merit_level >= 7', body)
        self.assertNotIn('has_any_court_position', body)
        self.assertNotIn('is_courtier', body)
        self.assertIn('treasury = { value = major_court_position_salary }', body)
        self.assertIn('prestige = { value = major_court_position_prestige_salary }', body)
        self.assertIn('monthly_influence = 0.2', body)
        self.assertIn('monthly_influence = 0.3', body)
        self.assertNotIn('monthly_prestige', body)

    def test_candidate_trigger_matches_design(self):
        triggers = definitions((ROOT / 'common/scripted_triggers/tca_exam_triggers.txt').read_text(encoding='utf-8-sig'))
        body = ' '.join(triggers['tca_exam_candidate_trigger'])
        self.assertIn('tca_exam_can_take_exam_trigger = yes', body)
        gate = ' '.join(triggers['tca_exam_can_take_exam_trigger'])
        self.assertIn('is_landed = no', gate)
        self.assertIn('tca_exam_is_official_trigger = yes', gate)
        self.assertIn('has_court_position = tca_exam_commissioner_court_position', gate)
        self.assertNotIn('passed_provincial_exam', body)
        self.assertIn('tgp_gender_can_be_exam_entrant_trigger = yes', body)
        official = ' '.join(definitions((ROOT / 'common/scripted_triggers/tca_exam_triggers.txt').read_text(encoding='utf-8-sig'))['tca_exam_is_official_trigger'])
        self.assertIn('is_councillor = yes', official)
        self.assertIn('tgp_has_minister_title = yes', official)
        self.assertIn('tca_is_landless_official_trigger = yes', official)
        self.assertIn('government_is_landless_adventurer', official)
        self.assertIn('is_noble_family_title = yes', official)
        priority = ' '.join(definitions((ROOT / 'common/scripted_triggers/tca_exam_triggers.txt').read_text(encoding='utf-8-sig'))['tca_exam_close_kin_priority_trigger'])
        self.assertIn('is_close_family_of = scope:host', priority)

    def test_events_do_not_use_ai_or_hard_provincial_gate(self):
        events = definitions((ROOT / 'events/tca_exam_events.txt').read_text(encoding='utf-8-sig'))
        first = ' '.join(events['tca_exam.1'])
        self.assertIn('tca_exam_event_trigger = yes', first)
        self.assertNotIn('is_ai = yes', first)
        self.assertIn('tca_exam_delegate_effect = { BREADTH = 0 }', first)
        self.assertIn('tca_exam_delegate_effect = { BREADTH = 2 }', first)
        self.assertIn('open_view_data = {', first)
        self.assertIn('activity_list_detail_host_window', first)
        # 原生条件仍是自动链的硬前提。
        trigger = definitions((ROOT / 'common/scripted_triggers/tca_exam_triggers.txt').read_text(encoding='utf-8-sig'))['tca_exam_event_trigger']
        self.assertIn('is_ai = no', ' '.join(trigger))
        self.assertIn('is_activity_type_on_cooldown', trigger)
        self.assertIn('tca_exam_cooldown', trigger)

    def test_activity_override_contains_only_exam_cooldown_change(self):
        baseline = definitions((ROOT / 'tools/baselines/imperial_examination_activity.txt').read_text(encoding='utf-8-sig'))
        actual = definitions((ROOT / 'common/activities/activity_types/zz_tca_imperial_examination.txt').read_text(encoding='utf-8-sig'))
        self.assertEqual(set(baseline), {'activity_imperial_examination'})
        self.assertEqual(set(actual), {'activity_imperial_examination'})
        native = ' '.join(baseline['activity_imperial_examination'])
        patched = ' '.join(actual['activity_imperial_examination'])
        self.assertNotIn('tca_exam_cooldown_tt', native)
        self.assertIn('tca_exam_cooldown_tt', patched)
        self.assertIn('tca_exam_cooldown', patched)
        # 冷却检查由 custom_tooltip 自身承担；AI 不受该自定义冷却约束。
        self.assertIn('is_ai = yes', patched)
        self.assertIn('text = tca_exam_cooldown_tt', patched)
        self.assertEqual(patched.count('tca_exam_can_take_exam_trigger = yes'), 1)
        self.assertIn('on_enter_passive_state = { imperial_examination_gather_stray_entrants_effect = yes if = { limit = { tca_exam_can_take_exam_trigger = yes is_ai = no', patched)
        registry = json.loads((ROOT / 'tools/upstream_overrides.json').read_text(encoding='utf-8'))
        entry = next(item for item in registry['overrides'] if item['key'] == 'activity_imperial_examination')
        self.assertEqual(entry['mod'], 'common/activities/activity_types/zz_tca_imperial_examination.txt')

    def test_localization_has_all_custom_keys_in_both_languages(self):
        keys = set()
        for path in [
            'common/court_positions/types/tca_exam_court_positions.txt',
            'common/court_positions/tasks/tca_exam_tasks.txt',
        ]:
            keys.update(definitions((ROOT / path).read_text(encoding='utf-8-sig')))
        keys.update({
            'tca_exam.1.t', 'tca_exam.1.desc', 'tca_exam.1.focus_learning',
            'tca_exam.1.focus_martial', 'tca_exam.1.focus_stewardship',
            'tca_exam.1.scale_note', 'tca_exam.1.count',
            'tca_exam.1.option_small', 'tca_exam.1.option_standard',
            'tca_exam.1.option_grand',
            'tca_exam.1.option_postpone',
            'tca_exam.host_button', 'tca_exam.host_button_tt', 'tca_exam_cooldown_tt',
            'tca_exam.2.t', 'tca_exam.2.desc', 'tca_exam.2.a',
            'tca_exam.3.t', 'tca_exam.3.desc', 'tca_exam.3.first',
            'tca_exam.3.second', 'tca_exam.3.third', 'tca_exam.3.a',
            'tca_exam.1.delegate_tt', 'tca_exam.1.postpone_tt',
            'tca_exam.2.passed', 'tca_exam.2.no_pass', 'tca_exam.2.count',
            'tca_exam.2.a_no_pass', 'tca_exam.2.a_tt', 'tca_exam.2.a_no_pass_tt',
            'tca_exam.3.a_tt', 'tca_exam.5.t', 'tca_exam.5.desc',
            'tca_exam.5.a', 'tca_exam.5.a_tt',
        })
        keys.update({f'tca_exam.2.top_{index}' for index in range(1, 11)})
        for language in ('english', 'simp_chinese'):
            path = ROOT / f'localization/{language}/tca_exam_l_{language}.yml'
            self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf'))
            loc = set(re.findall(r'^\s*([A-Za-z0-9_.]+):(?:\d+)?\s*"(?:\\.|[^"\\])*"', path.read_text(encoding='utf-8-sig'), re.MULTILINE))
            missing = sorted(keys - loc)
            self.assertEqual(missing, [], language)
        # 侧重动态文本只选择显示名称，三种名称必须都已登记在双语键集合中。
        custom = definitions((ROOT / 'common/customizable_localization/tca_exam_custom_loc.txt').read_text(encoding='utf-8-sig'))
        focus = ' '.join(custom['tca_exam_focus_label'])
        labels = set(re.findall(r'localization_key = ([A-Za-z0-9_.]+)', focus))
        self.assertEqual(labels, {'tca_exam.1.focus_learning', 'tca_exam.1.focus_martial', 'tca_exam.1.focus_stewardship'})
        self.assertTrue(labels <= keys)

    def test_candidate_list_adds_participant_and_resolution_is_in_results_event(self):
        effects = definitions((ROOT / 'common/scripted_effects/tca_exam_effects.txt').read_text(encoding='utf-8-sig'))
        gather = ' '.join(effects['tca_exam_collect_candidates_effect'])
        # 与原版一致，从当前考生作用域加入事件上下文的临时名单。
        self.assertIn('every_situation_group_participant = { limit = { tca_exam_candidate_trigger = yes', gather)
        self.assertIn('add_to_list = tca_exam_candidates', gather)
        self.assertNotIn('root = { add_to_list = tca_exam_candidates }', gather)
        self.assertIn('tca_exam_collect_candidates_effect = yes', ' '.join(effects['tca_exam_gather_candidates_effect']))
        self.assertIn('tca_exam_sample_candidates_effect = yes', ' '.join(effects['tca_exam_gather_candidates_effect']))
        delegate = ' '.join(effects['tca_exam_delegate_effect'])
        self.assertNotIn('tca_exam_resolve_effect = yes', delegate)
        events = definitions((ROOT / 'events/tca_exam_events.txt').read_text(encoding='utf-8-sig'))
        results = ' '.join(events['tca_exam.4'])
        self.assertIn('tca_exam_resolve_effect = yes', results)
        display = ' '.join(events['tca_exam.2'])
        self.assertNotIn('tca_exam_resolve_effect = yes', display)
        ceremony = ' '.join(events['tca_exam.3'])
        self.assertIn('medium_legitimacy_gain', ceremony)
        self.assertIn('change_merit = 2000', ceremony)

    def test_option_tooltip_uses_cost_variables_and_hides_grade_roll(self):
        # 选项效果里的 random 会被引擎展开成“X%概率”，录取尺度不应暴露给玩家。
        events = definitions((ROOT / 'events/tca_exam_events.txt').read_text(encoding='utf-8-sig'))
        first = ' '.join(events['tca_exam.1'])
        for variable in ('tca_exam_cost_small', 'tca_exam_cost_standard', 'tca_exam_cost_grand'):
            self.assertIn(f'name = {variable}', first)
            self.assertIn(f'remove_treasury = {{ value = var:{variable} }}', first)
        self.assertIn('show_as_tooltip = {', first)
        self.assertNotIn('custom_tooltip = tca_exam.1.option', first)
        effects = definitions((ROOT / 'common/scripted_effects/tca_exam_effects.txt').read_text(encoding='utf-8-sig'))
        delegate = ' '.join(effects['tca_exam_delegate_effect'])
        self.assertIn('hidden_effect = {', delegate)
        self.assertIn('tca_exam_select_grade_effect = yes', delegate)
        self.assertIn('tca_exam_selected_cost_value', delegate)
        values = (ROOT / 'common/script_values/tca_exam_values.txt').read_text(encoding='utf-8-sig')
        self.assertIn('tca_exam_selected_cost_value', values)
        self.assertIn("value = var:tca_exam_cost_small", values)
        # 费用在事件立即效果里取好，悬浮只读变量，避免保存作用域求值空白。
        for language in ('english', 'simp_chinese'):
            path = ROOT / f'localization/{language}/tca_exam_l_{language}.yml'
            body = path.read_text(encoding='utf-8-sig')
            self.assertNotIn('tca_exam.1.option_small_tt', body)
            self.assertNotIn('抽取', body)
            self.assertNotIn('Draw 150 candidates', body)

    def test_auto_task_prompts_on_start_without_liege_scope(self):
        # 无地知贡举的 liege 作用域不可靠，任务启动时应直接落在 h_china 持有者身上。
        raw = (ROOT / 'common/court_positions/tasks/tca_exam_tasks.txt').read_text(encoding='utf-8-sig')
        auto = ' '.join(definitions(raw)['tca_exam_commissioner_auto_exam'])
        self.assertIn('title:h_china.holder ?= {', auto)
        self.assertIn('set_variable = tca_exam_automation', auto)
        self.assertIn('tca_exam_can_prompt_trigger = yes', auto)
        self.assertIn('trigger_event = { id = tca_exam.1 days = 2 }', auto)
        self.assertNotIn('scope:liege', auto)
        self.assertTrue((ROOT / 'common/court_positions/tasks/tca_exam_tasks.txt').read_bytes().startswith(b'\xef\xbb\xbf'))
        self.assertTrue((ROOT / 'common/on_action/tca_exam_on_actions.txt').read_bytes().startswith(b'\xef\xbb\xbf'))
        pulse = ' '.join(definitions((ROOT / 'common/on_action/tca_exam_on_actions.txt').read_text(encoding='utf-8-sig'))['tca_exam_yearly_pulse'])
        self.assertIn('tca_exam_can_prompt_trigger = yes', pulse)
        self.assertIn('trigger_event = tca_exam.1', pulse)

    def test_delayed_prompt_rechecks_automation_and_empty_result_has_own_event(self):
        # 静态登记只约束入口与事件路由；真实任务切换和可见弹窗仍需玩家界面验收。
        triggers = definitions((ROOT / 'common/scripted_triggers/tca_exam_triggers.txt').read_text(encoding='utf-8-sig'))
        self.assertIn('has_variable = tca_exam_automation', ' '.join(triggers['tca_exam_event_trigger']))
        events = definitions((ROOT / 'events/tca_exam_events.txt').read_text(encoding='utf-8-sig'))
        result = ' '.join(events['tca_exam.4'])
        self.assertIn('if = { limit = { var:tca_exam_num_candidates > 0 } trigger_event = { id = tca_exam.2 days = 0 } } else = { trigger_event = { id = tca_exam.5 days = 0 } }', result)
        empty = ' '.join(events['tca_exam.5'])
        self.assertNotIn('trigger_event', empty)
        self.assertNotIn('add_legitimacy', empty)
        self.assertNotIn('change_merit', empty)
        for language in ('english', 'simp_chinese'):
            source = (ROOT / f'localization/{language}/tca_exam_l_{language}.yml').read_text(encoding='utf-8-sig')
            loc = set(re.findall(r'^\s*([A-Za-z0-9_.]+):', source, re.MULTILINE))
            self.assertTrue({'tca_exam.5.t', 'tca_exam.5.desc', 'tca_exam.5.a'} <= loc)

    def test_focus_and_cost_values_keep_native_focus_gate(self):
        values = (ROOT / 'common/script_values/tca_exam_values.txt').read_text(encoding='utf-8-sig')
        self.assertIn('tca_exam_focus', values)
        self.assertIn('imperial_examination_breadth_restricted_value', values)
        self.assertIn('factor_zero_if_entitled_to_freebie_activity_trigger', values)
        self.assertIn('divide = 3', values)
        self.assertNotIn('involved_activity', values)
        effects = (ROOT / 'common/scripted_effects/tca_exam_effects.txt').read_text(encoding='utf-8-sig')
        self.assertIn('chance = 75', effects)
        self.assertIn('set_variable = { name = tca_exam_focus value = 1 }', effects)
        self.assertIn('set_variable = { name = tca_exam_focus value = 2 }', effects)
        self.assertIn('tca_exam_cooldown_years', effects)

    def test_pending_guard_is_wired_to_prompt_delegate_and_settlement(self):
        # 只核对防重标记接入位置；真正扣费、延迟清理和重复事件由原生回归验证。
        triggers = definitions((ROOT / 'common/scripted_triggers/tca_exam_triggers.txt').read_text(encoding='utf-8-sig'))
        for key in ('tca_exam_can_prompt_trigger', 'tca_exam_event_trigger'):
            self.assertIn('NOT = { has_variable = tca_exam_pending }', ' '.join(triggers[key]))
        effects = definitions((ROOT / 'common/scripted_effects/tca_exam_effects.txt').read_text(encoding='utf-8-sig'))
        self.assertIn('set_variable = tca_exam_pending', ' '.join(effects['tca_exam_delegate_effect']))
        events = definitions((ROOT / 'events/tca_exam_events.txt').read_text(encoding='utf-8-sig'))
        settlement = ' '.join(events['tca_exam.4'])
        self.assertIn('trigger = { has_variable = tca_exam_pending }', settlement)
        self.assertIn('remove_variable = tca_exam_pending', settlement)


if __name__ == '__main__':
    unittest.main()
