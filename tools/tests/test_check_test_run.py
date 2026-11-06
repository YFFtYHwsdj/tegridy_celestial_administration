import unittest
import tempfile
from pathlib import Path
from check_test_run import (inspect_run, inspect_engine_errors, case_outcomes,
                            expected_cases, selected_case_expectations)


class RunEvidenceTests(unittest.TestCase):
    def test_owned_gui_property_failure_invalidates_pass(self):
        # 实际经费面板把背景纹理模板挂到vbox时产生此错误，不能因业务断言通过而忽略。
        error = "[10:20:17][E][pdx_gui_factory.cpp:1557]: gui/tca_office_budget_interaction.gui:37 - Error setting properties for '' (vbox)"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example': 1})
        self.assertTrue(any('GUI property' in issue for issue in issues))

    def test_owned_gui_malformed_token_invalidates_pass(self):
        error = '[10:20:17][E]: Error: "Malformed token: expression" in file: "gui/tca_office_budget_interaction.gui"'
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example': 1})
        self.assertTrue(any('parsing failure' in issue for issue in issues))

    def test_debug_only_contract_window_error_invalidates_pass(self):
        # 原生窗口曾只在debug日志拒绝非直属通判；两份日志必须共同检查。
        error = "[10:20:17][E][modify_subject_contract_interaction_window.cpp:297]: Invalid actor & recipient 'county / c_tca_tongpan_county' in interaction with modify_vassal_contract interface."
        issues, _ = inspect_run(self.run_log() + '\n' + error, '', {'tca_test_example': 1})
        self.assertTrue(any('contract window' in issue for issue in issues))

    def test_retirement_default_visibility_error_invalidates_pass(self):
        # 两类退休契约的默认档都不得带 is_shown，否则引擎报错且本次运行不能判通过。
        for contract, level in (('tca_zhishi_salary', 'tca_zhishi_salary_none'),
                                ('tca_fengci_salary', 'tca_fengci_salary_none')):
            error = (f"[14:48:17][E][subject_contract_type.cpp:436]: Obligation level '{level}' "
                     f"in '{contract}' is marked as default but has an is_shown trigger, "
                     "the default must always be visible to the player!")
            issues, _ = inspect_run(self.run_log(), error, {'tca_test_example': 1})
            self.assertTrue(any('contract default' in issue for issue in issues))
        # 不将无关原版契约错误认作当前模组错误。
        unrelated = ("[14:48:17][E][subject_contract_type.cpp:436]: Obligation level 'unrelated_none' "
                     "in 'unrelated_salary' is marked as default but has an is_shown trigger, "
                     "the default must always be visible to the player!")
        clean, _ = inspect_run(self.run_log(), unrelated, {'tca_test_example': 1})
        self.assertEqual(clean, [])

    def test_gui_file_shadow_error_without_custom_identifier_invalidates_pass(self):
        error = "[10:00:00][E]: gui/window_diarchy.gui:123 Could not find data system function 'BrokenNativeName'"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example': 1})
        self.assertTrue(any('data binding' in issue for issue in issues))

    def test_native_mandate_tooltip_error_in_owned_window_invalidates_pass(self):
        error = "[10:04:13][E][pdx_data_localize.cpp:161]: Data error in loc string 'DIARCHY_WINDOW_MANDATE_TOOLTIP'"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example': 1})
        self.assertTrue(any('localization evaluation failure' in issue for issue in issues))
        unrelated = error.replace('DIARCHY_WINDOW_MANDATE_TOOLTIP', 'game_concept_unrelated_desc')
        self.assertEqual(inspect_run(self.run_log(), unrelated, {'tca_test_example': 1})[0], [])

    def test_focused_selection_counts_actual_continuation_assertions(self):
        self.assertEqual(selected_case_expectations('tca_judicial_imperial_test.1'), {'tca_test_imperial_circuit_lifecycle': 15})
        with self.assertRaises(ValueError):
            selected_case_expectations('tca_judicial_imperial_test.1005')

    def test_focused_evidence_rejects_extra_cases_and_launch_errors(self):
        extra = self.run_log() + '\nTCA_TEST BEGIN tca_extra_test.1 tca_test_extra\nTCA_TEST CHECK_PASS tca_test_extra 1\nTCA_TEST PASS tca_test_extra'
        issues, _ = inspect_run(extra, '', {'tca_test_example': 1})
        self.assertTrue(any('tca_test_extra' in issue for issue in issues))
        issues, _ = inspect_run(self.run_log(), "[00:00:00][E]: Event tca_broken.1 is orphaned", {'tca_test_example': 1})
        self.assertTrue(any('tca_broken' in issue for issue in issues))

    def test_invalid_numeric_event_id_invalidates_engine_evidence(self):
        issues, _ = inspect_run(self.run_log(), "[00:00:00][E]: '10045' is not a valid event ID, has to be < 10000", {'tca_test_example': 1})
        self.assertTrue(any('Invalid numeric event ID' in issue for issue in issues))

    def test_event_reader_rejects_engine_numeric_id_overflow(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.event_fixture(root, 'debug_log = "TCA_TEST CHECK_PASS tca_test_fixture 2"')
            path = root / 'events/tca_fixture_test_events.txt'
            path.write_text(path.read_text().replace('tca_fixture_test.2 =', 'tca_fixture_test.10000 ='))
            with self.assertRaisesRegex(ValueError, 'below 10000'):
                expected_cases(root)

    def test_orphan_with_callers_invalidates_pass(self):
        error = "[21:57:29][E][jomini_eventmanager.cpp:368]: Event tca_cli.1 is scripted as an orphan, but has callers"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('tca_cli.1' in issue for issue in issues))

    def test_wrong_mod_value_type_invalidates_pass(self):
        error = "[15:44:33][E][jomini_scriptvalue.cpp:1499]: Value of wrong type in 'file: common/scripted_effects/tca_judicial_arrest_test_effects.txt line: 30'. Got value of type 'none'"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('value type' in issue.lower() for issue in issues))

    def test_duplicate_on_action_effect_invalidates_pass(self):
        error = "[14:51:42][E][jomini_onaction.cpp:161]: There is more than one 'effect' defined using most recent:file: common/on_action/zz_tca_tongpan_diarchy_death_guard.txt line: 3 (on_left_diarchy)"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('duplicate on_action effect' in issue for issue in issues))

    def test_duplicate_event_override_priority_invalidates_pass(self):
        error = ("[11:43:09][E][jomini_eventmanager.cpp:452]: Duplicated event ID travel_start_event.1100 with the same override priority 0 found:\n"
                 " Location A: file: events/travel_events/zz_tca_exam_travel_events.txt line: 6 (travel_start_event.1100)\n"
                 " Location B: file: events/travel_events/travel_start_events.txt line: 3279 (travel_start_event.1100)\n")
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('duplicate event' in issue.lower() for issue in issues))

    def test_registered_vanilla_named_shadow_error_is_owned(self):
        error = "[14:51:42][E][jomini_onaction.cpp:161]: There is more than one 'effect' defined using most recent:file: common/on_action/diarchy_on_action.txt line: 3 (on_left_diarchy)"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('duplicate on_action effect' in issue for issue in issues))

    def test_unset_mod_variable_invalidates_pass(self):
        error = "[15:07:35][E][jomini_effect.cpp:1162]: Variable 'tca_official_military' is used but is never set. Setting it in an unused scripted trigger or effect does not count"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('tca_official_military' in issue for issue in issues))

    def test_unused_mod_variable_invalidates_pass(self):
        error = "[15:07:35][E][jomini_effect.cpp:1146]: Variable 'tca_generated_initial_judicial_holder' is set but is never used."
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('tca_generated_initial_judicial_holder' in issue for issue in issues))

    def test_unset_mod_event_target_invalidates_pass(self):
        error = "[15:07:35][E][jomini_effect.cpp:1162]: Event target 'tca_test_law_subgovernor' is used but is never set."
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('tca_test_law_subgovernor' in issue for issue in issues))

    def test_unmarked_orphan_mod_event_invalidates_pass(self):
        error = "[15:07:40][E][jomini_eventmanager.cpp:368]: Event tca_court_test.100 is orphaned"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('tca_court_test.100' in issue for issue in issues))

    def test_duplicate_perk_in_test_fixture_invalidates_pass(self):
        error = ("[15:08:23][E][jomini_script_system.cpp:304]: Script system error!\n"
                 "  Error: add_perk effect [ Test governor already has the perk prison_feudal_complex_perk ]\n"
                 "  Script location: file: common/scripted_effects/tca_judicial_arrest_test_effects.txt line: 62\n")
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('prison_feudal_complex_perk' in issue for issue in issues))

    def test_unrelated_native_diagnostics_are_not_attributed_to_mod(self):
        error = ("[15:07:35][E]: Variable 'native_unused' is set but is never used.\n"
                 "[15:07:40][E]: Event native_debug.1 is orphaned\n")
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertEqual(issues, [])

    def test_invalid_value_event_target_link_invalidates_pass(self):
        error = "[13:58:52][E][jomini_eventtarget.cpp:325]: Scope type 'value' can not be used in event target links, link compare_value infile: events/tca_custody_review_test_events.txt line: 97"
        issues, _ = inspect_run(self.run_log(), error, {'tca_test_example'})
        self.assertTrue(any('event target' in issue.lower() for issue in issues))

    def test_aborted_environment_cannot_pass_even_with_complete_assertions(self):
        log = self.run_log() + '\nTCA_TEST SUITE_ABORTED monitored character died'
        issues, _ = inspect_run(log, '', {'tca_test_example'})
        self.assertTrue(any('aborted' in issue.lower() for issue in issues))

    def test_script_bom_error_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(),
                               "[10:00:00][E]: File 'common/script_values/tca_custody_review_values.txt' should be in utf8-bom encoding (will try to use it anyways)",
                               {'tca_test_example'})
        self.assertTrue(any('encoding failure' in issue for issue in issues))

    def test_invalid_exclusive_send_option_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(),
                               "[10:00:00][E]: Exclusive send options should at least be two, in interaction 'tca_custody_review_interaction'",
                               {'tca_test_example'})
        self.assertTrue(any('send-option configuration failure' in issue for issue in issues))

    def event_fixture(self, root, checks):
        path = root / 'events/tca_fixture_test_events.txt'
        path.parent.mkdir()
        path.write_text('namespace = tca_fixture_test\n'
                        'tca_fixture_test.1 = { immediate = { '
                        'debug_log = "TCA_TEST BEGIN tca_fixture_test.1 tca_test_fixture" '
                        'debug_log = "TCA_TEST CHECK_PASS tca_test_fixture 1" } }\n'
                        'tca_fixture_test.2 = { immediate = { ' + checks + ' } }')

    def test_event_reader_includes_delayed_continuation_assertions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.event_fixture(root, 'debug_log = "TCA_TEST CHECK_PASS tca_test_fixture 2"')
            self.assertEqual(expected_cases(root), {'tca_test_fixture': 2})

    def test_event_reader_includes_gui_synchronous_fixture_assertions(self):
        # 重载首帧检查在夹具效果中同步执行；静态索引也必须读取，不能靠孤立占位事件。
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.event_fixture(root, '')
            fixture = root / 'common/scripted_effects/tests/fixtures/tca_fixture_effects.txt'
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_text('tca_fixture_effect = { '
                               'debug_log = "TCA_TEST CHECK_PASS tca_test_fixture 2" }\n',
                               encoding='utf-8')
            self.assertEqual(expected_cases(root), {'tca_test_fixture': 2})

    def test_event_reader_rejects_missing_assertion_numbers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.event_fixture(root, 'debug_log = "TCA_TEST CHECK_PASS tca_test_fixture 3"')
            with self.assertRaisesRegex(ValueError, 'consecutive'):
                expected_cases(root)

    def test_event_reader_rejects_duplicate_assertions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.event_fixture(root, 'debug_log = "TCA_TEST CHECK_PASS tca_test_fixture 1"')
            with self.assertRaisesRegex(ValueError, 'duplicate assertion'):
                expected_cases(root)

    def test_localization_evaluation_error_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(),
                                "[10:00:00][E]: Data error in loc string 'tca_judicial_title_name'",
                                {'tca_test_example'})
        self.assertTrue(any('localization evaluation' in issue for issue in issues))

    def run_log(self, name='tca_test_example'):
        return f'TCA_TEST SUITE_DISPATCH\nTCA_TEST BEGIN tca_example_test.1 {name}\nTCA_TEST CHECK_PASS {name} 1\nTCA_TEST PASS {name}\nTCA_TEST SUITE_ALL_PASSED'

    def test_strict_preview_head_gate_rejects_diagnostic_even_when_business_passes(self):
        diagnostic = 'TCA: native Tongpan appointment differs from pre-death title preview head'
        log = self.run_log() + '\n' + diagnostic
        self.assertEqual(inspect_run(log, '', {'tca_test_example': 1})[0], [])
        self.assertTrue(any('Strict title succession failed' in x for x in
                            inspect_run(log, '', {'tca_test_example': 1}, strict_title_heir=True)[0]))
        self.assertEqual(inspect_run(diagnostic + '\n' + self.run_log(), '',
                                     {'tca_test_example': 1}, strict_title_heir=True)[0], [])

    def test_complete_pass(self):
        issues, counts = inspect_run(self.run_log(), '', {'tca_test_example'})
        self.assertEqual(issues, [])
        self.assertEqual(counts['PASS'], 1)

    def test_new_source_cases_cannot_reuse_old_run(self):
        issues, _ = inspect_run(self.run_log(), '', {'tca_test_example', 'tca_test_new'})
        self.assertTrue(any('tca_test_new' in x for x in issues))

    def test_startup_compilation_failure_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(), '[10:00:00][E]: Compiling source for tca_score failed for unknown arguments: GOVERNOR', {'tca_test_example'})
        self.assertTrue(any('compilation' in x for x in issues))

    def test_native_test_parser_failure_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(),
                                '[10:00:00][E]: Error: "Unexpected token: wait_days" '
                                'in file: "tests/tca_judicial_timing_tests.txt"',
                                {'tca_test_example'})
        self.assertTrue(any('parsing failure' in issue for issue in issues))

    def test_unknown_trigger_in_native_event_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(),
                                '[22:35:56][E][pdx_persistent_reader.cpp:216]: '
                                'Error: "Unknown trigger: any_de_jure_vassal_title, near line: 281" '
                                'in file: "events/tca_judicial_de_jure_test_events.txt" near line: 281',
                                {'tca_test_example'})
        self.assertTrue(any('parsing failure' in issue for issue in issues))

    def test_native_error_in_mod_call_chain_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(), '[10:00:00][E]: Script system error!\nError: wrong scope\nfile: common/scripted_effects/tca_example.txt', {'tca_test_example'})
        self.assertTrue(any('wrong scope' in x for x in issues))

    def test_interleaved_cohort_results_are_order_independent(self):
        # 单实例并行下不同 lane 的 BEGIN/CHECK/PASS 会交错出现；验收按名字统计，不依赖先后。
        first, second = 'tca_test_cohort_a', 'tca_test_cohort_b'
        log = ('TCA_TEST SUITE_DISPATCH\n'
               f'TCA_TEST BEGIN tca_cohort_test.1 {first}\n'
               f'TCA_TEST BEGIN tca_cohort_test.2 {second}\n'
               f'TCA_TEST CHECK_PASS {second} 2\n'
               f'TCA_TEST CHECK_PASS {first} 1\n'
               f'TCA_TEST CHECK_PASS {second} 1\n'
               f'TCA_TEST PASS {second}\n'
               f'TCA_TEST CHECK_PASS {first} 2\n'
               f'TCA_TEST PASS {first}\n'
               'TCA_TEST SUITE_ALL_PASSED')
        expected = {first: 2, second: 2}
        issues, counts = inspect_run(log, '', expected)
        self.assertEqual(issues, [])
        self.assertEqual(counts['PASS'], 2)
        self.assertEqual(case_outcomes(log, expected), {first: 'PASS', second: 'PASS'})

    def test_only_latest_dispatch_counts(self):
        issues, counts = inspect_run(self.run_log() + '\n' + self.run_log(), '', {'tca_test_example'})
        self.assertEqual(issues, [])
        self.assertEqual(counts['BEGIN'], 1)

    def test_rejected_observer_entry_cannot_reuse_old_pass(self):
        log = self.run_log() + '\nTCA_TEST OBSERVER_ENTRY_REJECTED valid 1066 China host required'
        issues, _ = inspect_run(log, '', {'tca_test_example'})
        self.assertTrue(any('observer entry' in issue.lower() for issue in issues))

    def test_observer_entry_requires_a_new_suite_dispatch(self):
        log = self.run_log() + '\nTCA_TEST OBSERVER_ENTRY_DISPATCH'
        issues, _ = inspect_run(log, '', {'tca_test_example'})
        self.assertTrue(any('observer entry' in issue.lower() for issue in issues))

    def test_busy_observer_retry_does_not_invalidate_completed_suite(self):
        log = self.run_log().replace('TCA_TEST SUITE_ALL_PASSED',
                                    'TCA_TEST OBSERVER_ENTRY_BUSY\nTCA_TEST SUITE_ALL_PASSED')
        issues, _ = inspect_run(log, '', {'tca_test_example'})
        self.assertEqual(issues, [])

    def test_precondition_failure_is_not_pass(self):
        log = self.run_log().replace('TCA_TEST PASS tca_test_example', 'TCA_TEST PRECONDITION_FAIL tca_test_example')
        issues, _ = inspect_run(log, '', {'tca_test_example'})
        self.assertTrue(issues)

    def test_duplicate_pass_is_not_complete_evidence(self):
        issues, _ = inspect_run(self.run_log() + '\nTCA_TEST PASS tca_test_example', '', {'tca_test_example'})
        self.assertTrue(issues)

    def test_mod_duplicate_queue_invalidates_pass(self):
        issues, _ = inspect_run(self.run_log(), "[10:00:00][E]: Event tca_judicial_titles.2 has been queued twice with same data including delay", {'tca_test_example'})
        self.assertTrue(any('queued' in x for x in issues))

    def test_unrelated_native_queue_is_not_a_mod_error(self):
        issues, _ = inspect_run(self.run_log(), "[10:00:00][E]: Event diarchy.0011 has been queued twice with same data including delay", {'tca_test_example'})
        self.assertEqual(issues, [])

    def test_current_source_assertions_are_all_required(self):
        issues, _ = inspect_run(self.run_log(), '', {'tca_test_example': 2})
        self.assertTrue(any('assertion 2' in x for x in issues))

    def test_duplicate_assertion_cannot_replace_missing_assertion(self):
        issues, _ = inspect_run(self.run_log() + '\nTCA_TEST CHECK_PASS tca_test_example 1', '', {'tca_test_example': 2})
        self.assertTrue(any('assertion 1' in x for x in issues))
        self.assertTrue(any('assertion 2' in x for x in issues))

    def test_complete_assertion_sequence(self):
        issues, _ = inspect_run(self.run_log(), '', {'tca_test_example': 1})
        self.assertEqual(issues, [])

    # 以下用例固定单遍/流式解析的等价语义：最新派发边界、逐行首个结果、
    # 逐项重复结果、错误条目分块与去重，均须与原先整段正则扫描逐字一致。

    def case_log(self, lines):
        return 'TCA_TEST SUITE_DISPATCH\n' + '\n'.join(lines) + '\nTCA_TEST SUITE_ALL_PASSED'

    def test_no_dispatch_skips_engine_errors(self):
        # 没有派发时即使 error.log 有模组错误也只报告缺少派发，保持原返回。
        issues, counts = inspect_run('', '[10:00:00][E]: Event tca_x.1 is orphaned', {'tca_test_example': 1})
        self.assertEqual(issues, ['No suite dispatch found'])
        self.assertEqual(dict(counts), {})
        self.assertEqual(case_outcomes('', {'tca_test_example': 1}), {'tca_test_example': 'NOT_RUN'})

    def test_summary_keeps_zero_result_kinds(self):
        # 汇总始终包含四类原生结果键，便于 verification.json 计数稳定。
        _, counts = inspect_run(self.run_log(), '', {'tca_test_example': 1})
        self.assertEqual(dict(counts), {'BEGIN': 1, 'PASS': 1, 'FAIL': 0,
                                        'PRECONDITION_FAIL': 0, 'CHECK_PASS': 1})

    def test_case_outcomes_ignores_text_before_dispatch_substring(self):
        # 逐项状态从最近一次派发子串处起算；同一行派发之前的旧结果不得沿用。
        name = 'tca_test_example'
        log = (f'TCA_TEST PASS {name} TCA_TEST SUITE_DISPATCH\n'
               f'TCA_TEST BEGIN tca_a.1 {name}\n'
               f'TCA_TEST CHECK_PASS {name} 1\n'
               'TCA_TEST SUITE_ALL_PASSED')
        self.assertEqual(case_outcomes(log, {name: 1}), {name: 'NOT_VERIFIED'})
        # 断言核对按整行解析最新派发行，因此该行的 PASS 仍被计入。
        issues, counts = inspect_run(log, '', {name: 1})
        self.assertEqual(issues, [])
        self.assertEqual(counts['PASS'], 1)

    def test_case_outcomes_uses_last_dispatch_on_same_line(self):
        name = 'tca_test_example'
        log = (f'TCA_TEST SUITE_DISPATCH TCA_TEST BEGIN tca_a.1 {name} TCA_TEST SUITE_DISPATCH\n'
               f'TCA_TEST CHECK_PASS {name} 1\nTCA_TEST PASS {name}\nTCA_TEST SUITE_ALL_PASSED')
        self.assertEqual(case_outcomes(log, {name: 1}), {name: 'NOT_RUN'})
        self.assertEqual(inspect_run(log, '', {name: 1})[0], [])

    def test_case_outcomes_counts_repeated_results_on_one_line(self):
        name = 'tca_test_example'
        log = self.case_log([f'TCA_TEST BEGIN tca_a.1 {name}',
                             f'TCA_TEST CHECK_PASS {name} 1',
                             f'TCA_TEST PASS {name} TCA_TEST PASS {name}'])
        self.assertEqual(case_outcomes(log, {name: 1}), {name: 'NOT_VERIFIED'})

    def test_inspect_run_counts_first_result_per_line_only(self):
        name = 'tca_test_example'
        log = ('TCA_TEST SUITE_DISPATCH\n'
               f'TCA_TEST BEGIN tca_a.1 {name} TCA_TEST PASS {name}\n'
               'TCA_TEST SUITE_ALL_PASSED')
        issues, counts = inspect_run(log, '', {name: 1})
        self.assertEqual(issues, [f'{name}: begin=1, pass=0',
                                  f'{name}: assertion 1 missing or duplicated'])
        self.assertEqual(counts['BEGIN'], 1)

    def test_case_outcomes_counts_all_assertions_on_one_line(self):
        # 与断言核对不同，逐项统计允许同一行出现多条 CHECK_PASS，且不应吞掉后续标记。
        name = 'tca_test_example'
        log = ('TCA_TEST SUITE_DISPATCH\n'
               f'TCA_TEST BEGIN tca_a.1 {name}\n'
               f'TCA_TEST PASS {name}\n'
               f'TCA_TEST CHECK_PASS {name} 1 TCA_TEST CHECK_PASS {name} 2\n'
               'TCA_TEST SUITE_ALL_PASSED')
        self.assertEqual(case_outcomes(log, {name: 2}), {name: 'PASS'})
        # 逐行只取首个结果，故步骤 2 仍算缺失。
        self.assertEqual(inspect_run(log, '', {name: 2})[0],
                         [f'{name}: assertion 2 missing or duplicated'])

    def test_case_outcomes_requires_token_boundaries(self):
        name = 'tca_test_example'
        prefixed = self.case_log([f'TCA_TEST BEGIN tca_a.1 {name}',
                                  f'TCA_TEST CHECK_PASS {name} 1',
                                  f'TCA_TEST PASS {name}2'])
        self.assertEqual(case_outcomes(prefixed, {name: 1}), {name: 'NOT_VERIFIED'})
        spaced = self.case_log([f'TCA_TEST BEGIN tca_a.1  {name}',
                                f'TCA_TEST PASS {name}'])
        self.assertEqual(case_outcomes(spaced, {name: 1}), {name: 'NOT_RUN'})
        suffixed = self.case_log([f'TCA_TEST BEGIN tca_a.1 {name}',
                                  f'TCA_TEST CHECK_PASS {name} 12x',
                                  f'TCA_TEST PASS {name}'])
        self.assertEqual(case_outcomes(suffixed, {name: 1}), {name: 'NOT_VERIFIED'})

    def test_case_outcomes_begin_name_is_second_token(self):
        name = 'tca_test_example'
        log = self.case_log([f'TCA_TEST BEGIN tca_a.1 {name} trailing',
                             f'TCA_TEST CHECK_PASS {name} 1',
                             f'TCA_TEST PASS {name}'])
        self.assertEqual(case_outcomes(log, {name: 1}), {name: 'PASS'})

    def test_case_outcomes_failure_kinds_take_priority(self):
        name = 'tca_test_example'
        precondition = self.case_log([f'TCA_TEST BEGIN tca_a.1 {name}',
                                      f'TCA_TEST PRECONDITION_FAIL {name}'])
        self.assertEqual(case_outcomes(precondition, {name: 1}), {name: 'PRECONDITION_FAIL'})
        check_fail = self.case_log([f'TCA_TEST CHECK_FAIL {name} 1'])
        self.assertEqual(case_outcomes(check_fail, {name: 1}), {name: 'FAIL'})
        both = self.case_log([f'TCA_TEST PRECONDITION_FAIL {name}',
                              f'TCA_TEST CHECK_FAIL {name} 1'])
        self.assertEqual(case_outcomes(both, {name: 1}), {name: 'PRECONDITION_FAIL'})

    def test_case_outcomes_rejects_duplicate_assertion(self):
        name = 'tca_test_example'
        log = self.case_log([f'TCA_TEST BEGIN tca_a.1 {name}',
                             f'TCA_TEST PASS {name}',
                             f'TCA_TEST CHECK_PASS {name} 1 TCA_TEST CHECK_PASS {name} 1'])
        self.assertEqual(case_outcomes(log, {name: 1}), {name: 'NOT_VERIFIED'})

    def test_aborted_and_completion_markers_only_apply_after_latest_dispatch(self):
        aborted = 'TCA_TEST SUITE_ABORTED\n' + self.run_log()
        self.assertEqual(inspect_run(aborted, '', {'tca_test_example': 1})[0], [])
        completed = 'TCA_TEST SUITE_ALL_PASSED\n' + self.run_log().replace('TCA_TEST SUITE_ALL_PASSED', '')
        self.assertEqual(inspect_run(completed, '', {'tca_test_example': 1})[0],
                         ['No SUITE_ALL_PASSED completion'])
        rejected = 'TCA_TEST OBSERVER_ENTRY_REJECTED old stale reason\n' + self.run_log()
        self.assertEqual(inspect_run(rejected, '', {'tca_test_example': 1})[0], [])

    def test_engine_error_entries_keep_error_log_order_before_debug_only(self):
        first = '[10:00:00][E]: Event tca_first.1 is orphaned'
        second = '[10:01:00][E]: Event tca_second.1 is orphaned'
        self.assertEqual(inspect_run(self.run_log(), first, {'tca_test_example': 1})[0],
                         ['Engine error (1): Event tca_first.1 is orphaned'])
        self.assertEqual(inspect_run(self.run_log() + '\n' + second, first, {'tca_test_example': 1})[0],
                         ['Engine error (1): Event tca_first.1 is orphaned',
                          'Engine error (1): Event tca_second.1 is orphaned'])

    def test_debug_multiline_error_entry_keeps_context_and_requires_exact_dedupe(self):
        error = ('[10:00:00][E]: Script system error!\n'
                 '  Error: tca scope mismatch\n'
                 '  Script location: file: common/scripted_effects/tca_x.txt line: 3\n')
        self.assertEqual(inspect_run(self.run_log(), error, {'tca_test_example': 1})[0],
                         ['Engine error (1): tca scope mismatch'])
        # error.log 与 debug 记录同一条目时只计一次，不得重复计入。
        self.assertEqual(inspect_run(self.run_log() + '\n' + error, error,
                                     {'tca_test_example': 1})[0],
                         ['Engine error (1): tca scope mismatch'])
        # debug 条目多出续行即视为不同条目，不能按首行静默去重。
        self.assertEqual(inspect_run(self.run_log() + '\n' + error + '  extra line\n', error,
                                     {'tca_test_example': 1})[0],
                         ['Engine error (2): tca scope mismatch'])

    def test_debug_error_entries_require_severity_marker_at_entry_start(self):
        log = self.run_log() + '\n[10:00:00][W]: tca_warning_only\n[10:00:01] plain tca_line'
        self.assertEqual(inspect_run(log, '', {'tca_test_example': 1})[0], [])

    def test_mid_line_timestamp_error_entry_is_captured(self):
        log = self.run_log() + '\nmid[10:00:00][E]: Event tca_mid.1 is orphaned'
        self.assertEqual(inspect_run(log, '', {'tca_test_example': 1})[0],
                         ['Engine error (1): Event tca_mid.1 is orphaned'])

    def test_repeated_debug_errors_are_counted_separately(self):
        entry = '[10:00:00][E]: Event tca_dup.1 is orphaned'
        log = self.run_log() + '\n' + entry + '\n' + entry
        self.assertEqual(inspect_run(log, '', {'tca_test_example': 1})[0],
                         ['Engine error (2): Event tca_dup.1 is orphaned'])

    def test_error_entry_before_first_timestamp_is_still_classified(self):
        issues, _ = inspect_run(self.run_log(), 'boot[10:00:00][E]: Event tca_p.1 is orphaned',
                                {'tca_test_example': 1})
        self.assertEqual(issues, ['Engine error (1): Event tca_p.1 is orphaned'])

    def test_engine_error_inspection_api_stays_public(self):
        # run_diarchy_ui_probe 直接复用该入口，签名与输出文本不得变化。
        self.assertEqual(inspect_engine_errors('[10:00:00][E]: Event tca_api.1 is orphaned'),
                         ['Engine error (1): Event tca_api.1 is orphaned'])
        self.assertEqual(inspect_engine_errors('[10:00:00][E]: Event vanilla.1 is orphaned'), [])
        self.assertEqual(inspect_engine_errors(''), [])


if __name__ == '__main__':
    unittest.main()
