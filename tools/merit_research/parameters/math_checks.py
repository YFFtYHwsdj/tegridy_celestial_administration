"""逐带参数研究的恒等式、可辨识性与理想标量动力学边界。"""
import math
import unittest

import math_model as model


class MappingChecks(unittest.TestCase):
    def test_direct_band_capacity_and_split(self):
        out=model.targets([10,4,2,1], coefficients=[1.5,2,2.5,1],
                          phi=[.6,.7,.8],epsilon=.1,r=.06)
        self.assertEqual(out['base_K'],[15,8,5,1])
        self.assertEqual(out['K'],out['base_K'])
        self.assertEqual(out['reserve'],[0,0,0,0])
        self.assertEqual(out['target'],[6.6,9.9,2.64,6.16,1.1,4.4,1.1])
        for index,tail in enumerate(out['B']):
            self.assertAlmostEqual(tail,sum(out['target'][index+1:]))

    def test_single_values_expand_without_a_total_budget(self):
        out=model.targets([8,4,2,1],coefficients=1.5,phi=.6)
        self.assertEqual(out['K'],[12,6,3,1.5])
        self.assertEqual(out['phi'],[.6]*3)
        self.assertEqual(out['reserve_eta'],[0]*3)

    def test_first_band_product_is_not_separately_identifiable(self):
        first=model.targets([100,20,5,2],coefficients=[1.5,2,2,1],phi=[.6,.6,.6])
        second=model.targets([100,20,5,2],coefficients=[1.125,2,2,1],phi=[.8,.6,.6])
        self.assertNotEqual(first['target'][0],second['target'][0])
        self.assertEqual(first['target'][1:],second['target'][1:])
        self.assertEqual(first['B'],second['B'])

    def test_epsilon_and_coefficients_have_exact_product_equivalence(self):
        first=model.targets([100,20,5,2],coefficients=1.5,epsilon=.1)
        second=model.targets([100,20,5,2],coefficients=1.375,epsilon=.2)
        self.assertEqual(first['T'],second['T'])
        self.assertEqual(first['target'],second['target'])
        self.assertEqual(first['B'],second['B'])

    def test_zero_middle_reports_missing_source(self):
        out=model.targets([100,0,0,5],coefficients=1.5,r=.06)
        self.assertEqual(out['K'],[150,0,0,7.5])
        self.assertTrue(any(x is None for x in out['required_candidate_fraction']))
        self.assertFalse(out['possible_with_all_candidates'])
        self.assertEqual(out['zero_source_boundaries'],[3,4,5,6])

    def test_reserve_is_explicit_and_applied_from_top(self):
        out=model.targets([100,0,0,5],coefficients=1.5,reserve=[.5,1,2])
        self.assertEqual(out['K'],[150,22.5,15,7.5])
        self.assertEqual(out['base_K'],[150,0,0,7.5])
        self.assertEqual(out['reserve'],[0,22.5,15,0])

    def test_zero_titles_and_scale(self):
        self.assertEqual(model.targets([0]*4)['B'],[0]*6)
        first=model.targets([12,3,1,1],coefficients=[1.25,1.5,2,1],reserve=.5)
        second=model.targets([84,21,7,7],coefficients=[1.25,1.5,2,1],reserve=.5)
        self.assertTrue(all(math.isclose(7*a,b) for a,b in zip(first['target'],second['target'])))

    def test_reject_invalid_mapping_inputs(self):
        for bad in ([1,2,3],[-1,0,0,0],[True,0,0,0],[.5,0,0,0],None):
            with self.subTest(J=bad),self.assertRaises(ValueError):
                model.targets(bad)
        for kwargs in (dict(coefficients=-1),dict(coefficients=[1,2]),dict(phi=0),dict(phi=1),
                       dict(phi=True),dict(epsilon=-.1),dict(r=0),dict(r=float('inf')),
                       dict(reserve=[0,-1,0]),dict(candidate_fraction=0)):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                model.targets([1]*4,**kwargs)


class ScalarChecks(unittest.TestCase):
    def test_positive_finite_congestion_expectation(self):
        values=[model.quota_expectation(s,100,r=.06,gain=.6) for s in (0,80,100,120,1000,1000000)]
        self.assertTrue(all(q>0 for q in values))
        self.assertTrue(all(a>b for a,b in zip(values,values[1:])))
        self.assertEqual(model.quota_expectation(3,0),0)

    def test_calibrated_r_has_target_as_fixed_point(self):
        d=.04
        out=model.scalar_equilibrium(B=100,d=d,r=d/(1-d),gain=.6)
        self.assertAlmostEqual(out['S'],100,places=8)
        self.assertAlmostEqual(out['local_multiplier'],(1-d)*(1-.6))
        self.assertAlmostEqual(out['fixed_point_residual'],0,places=8)

    def test_high_r_moves_ideal_equilibrium_above_target(self):
        out=model.scalar_equilibrium(B=100,d=.04,r=.08,gain=.6)
        self.assertGreater(out['S'],100)
        self.assertLess(out['local_multiplier'],1)
        self.assertGreater(out['local_multiplier'],0)

    def test_inflow_changes_fixed_point_and_zero_target_does_not_hide_it(self):
        zero=model.scalar_equilibrium(B=0,d=.1,r=.06,gain=.6,C=2)
        self.assertAlmostEqual(zero['S'],20)
        out=model.scalar_equilibrium(B=100,d=.04,r=.06,gain=.6,C=2)
        self.assertGreater(out['S'],model.scalar_equilibrium(B=100,d=.04,r=.06,gain=.6)['S'])

    def test_rounding_moments_are_exact_and_no_annual_floor(self):
        self.assertEqual(model.rounding_moments(.25),{'mean':.25,'variance':.1875,'zero_probability':.75})
        self.assertEqual(model.rounding_moments(3),{'mean':3.,'variance':0.,'zero_probability':0.})
        self.assertEqual(model.rounding_moments(0)['zero_probability'],1)

    def test_reject_invalid_scalar_parameters(self):
        for kwargs in (dict(r=0),dict(gain=0),dict(gain=1.1),dict(temperature=0),dict(temperature=True)):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                model.policy_parameters(**kwargs)
        for kwargs in (dict(d=0),dict(d=1),dict(B=-1),dict(C=-1)):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                model.scalar_equilibrium(**kwargs)
        with self.assertRaises(ValueError):model.rounding_moments(-1)

if __name__=='__main__':unittest.main()
