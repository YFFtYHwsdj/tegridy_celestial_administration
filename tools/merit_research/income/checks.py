"""功绩来源账本的边界检查；不是游戏脚本的替代测试。"""
import unittest
from model import annual_components, event_reward, apply_event, initialize_exams


class IncomeChecks(unittest.TestCase):
    def test_no_universal_income(self):
        self.assertEqual(sum(annual_components().values()), 0)

    def test_tax_is_separate_from_monthly_multiplier(self):
        result=annual_components(role='civil_standard',paid_tax=100,monthly_mult=1)
        self.assertAlmostEqual(result['tax'],960)
        self.assertEqual(result['fixed'],0)

    def test_military_uses_recruitment_value(self):
        self.assertAlmostEqual(annual_components(role='military',maa_value=1000)['maa'],288)

    def test_office_loss_removes_office_income(self):
        held=annual_components(role='minister',personal_fixed=.25)
        unemployed=annual_components(personal_fixed=.25)
        self.assertEqual(held['fixed']-unemployed['fixed'],240)
        self.assertEqual(unemployed['fixed'],3)

    def test_rank_is_not_an_income_argument(self):
        with self.assertRaises(TypeError): annual_components(rank=9)

    def test_actual_title_tier_changes_fixed_multiplier_only(self):
        result=annual_components(role='minister',head_tier=4)
        self.assertEqual(result['fixed'],480)

    def test_funding_does_not_use_monthly_multiplier(self):
        result=annual_components(role='tongpan',funding_paid=100,monthly_mult=1)
        self.assertEqual(result['fixed'],48)
        self.assertAlmostEqual(result['funding'],240)

    def test_negative_monthly_multiplier_is_clamped(self):
        result=annual_components(role='minister',paid_tax=0,monthly_mult=-10)
        self.assertEqual(result['fixed'],0)

    def test_event_loss_and_war_cap(self):
        self.assertEqual(event_reward(dict(kind='task_failure',scale=2)),-60)
        self.assertEqual(event_reward(dict(kind='war',fame=3000,winner_scale=1)),1000)

    def test_building_is_per_actual_completion(self):
        self.assertEqual(event_reward(dict(kind='building',development=20,estate_bonus=.5)),120)

    def test_exam_reward_and_cap_are_same_event(self):
        p=dict(cap=4,merit_events=[])
        e=dict(id='exam1',kind='metropolitan',score_factor=1,grade_factor=1,eligible=True)
        self.assertEqual(apply_event(p,e),400)
        self.assertEqual(p['cap'],6)
        self.assertEqual(apply_event(p,e),0)

    def test_palace_branch_is_explicit_not_annual_probability(self):
        p=dict(cap=4,merit_events=[])
        e=dict(id='exam2',kind='ai_palace_followup',eligible=True)
        self.assertEqual(apply_event(p,e),12000)
        self.assertEqual(p['cap'],9)
        self.assertEqual(apply_event(p,e),0)

    def test_ineligible_event_is_rejected(self):
        with self.assertRaises(ValueError): event_reward(dict(kind='ai_palace_followup',eligible=False))

    def test_nonfinite_or_negative_bases_rejected(self):
        for args in [dict(paid_tax=-1),dict(maa_value=float('nan')),dict(funding_paid=-1)]:
            with self.assertRaises(ValueError): annual_components(**args)

    def test_initial_exam_distribution_boundary(self):
        for u,cap in [(.05,2),(.3,4),(.7,6),(.9,9)]:
            p=dict(rank=1,cap=2,m=100,age=18)
            initialize_exams(p,lambda channel:u,learning=10)
            self.assertEqual(p['cap'],cap)
            self.assertEqual(p['m'],100 if cap==2 else 228)

    def test_initialization_is_not_repeated(self):
        p=dict(rank=1,cap=2,m=100,age=18)
        initialize_exams(p,lambda channel:.5)
        with self.assertRaises(ValueError): initialize_exams(p,lambda channel:.5)

    def test_high_starting_merit_changes_exam_state_once(self):
        p=dict(rank=5,cap=5,m=6000,age=40)
        initialize_exams(p,lambda channel:.8)
        self.assertEqual(p['cap'],6)
        self.assertEqual(p['m'],9000)

    def test_no_self_merit_reward_on_ordinary_rank_gain(self):
        with self.assertRaises(ValueError): event_reward(dict(kind='rank_gain'))


if __name__=='__main__': unittest.main()
