"""员额映射的数学边界检查；不是CK3业务行为回归。"""
import math
import unittest
from capacity import targets

class CapacityChecks(unittest.TestCase):
    def test_uniform_and_single_allocation(self):
        out=targets([10,4,2,1],mapping='uniform2')
        self.assertEqual(out['K'],[20,8,4,2])
        self.assertEqual(len(out['target']),7)
        self.assertAlmostEqual(sum(out['target']),sum(out['T']))
        for b in range(3):
            self.assertAlmostEqual(sum(out['target'][2*b:2*b+2]),out['T'][b])
            self.assertAlmostEqual(out['target'][2*b+1]/out['T'][b],.6)
        self.assertEqual(out['target'][-1],out['T'][-1])
    def test_exact_tail_and_supply_ratio(self):
        out=targets([10,4,2,1],mapping='uniform2')
        for i in range(6):
            self.assertAlmostEqual(out['B'][i],sum(out['target'][i+1:]))
            self.assertAlmostEqual(out['required_candidate_fraction'][i],(.04/.96)*out['B'][i]/out['target'][i])
    def test_transit_closes_zero_middle_hole(self):
        out=targets([100,0,0,5],mapping='transit2')
        self.assertGreater(out['K'][1],0);self.assertGreater(out['K'][2],0)
        self.assertTrue(out['feasible_at_candidate_fraction'])
        self.assertTrue(all(c is not None and c<=.25+1e-12 for c in out['required_candidate_fraction']))
        self.assertAlmostEqual(out['transit_eta'],5/9)
        self.assertGreater(out['reserve'][1],0)
        plain=targets([100,0,0,5],mapping='uniform2')
        self.assertFalse(plain['feasible_at_candidate_fraction'])
        self.assertIsNone(plain['required_candidate_fraction'][2])
    def test_structural_minimum_one_ninth(self):
        out=targets([0,0,0,5],mapping='transit2',candidate_fraction=1,epsilon=0)
        self.assertAlmostEqual(out['transit_eta'],1/9)
        self.assertAlmostEqual(sum(out['K'])/out['K'][3],(10/9)**3)
    def test_zero_and_small_fractional_targets(self):
        out=targets([0,0,0,0])
        self.assertEqual(out['target'],[0]*7);self.assertEqual(out['B'],[0]*6)
        self.assertEqual(out['required_candidate_fraction'],[0]*6)
        self.assertTrue(out['feasible_at_candidate_fraction'])
        small=targets([0,0,0,1],candidate_fraction=1)
        self.assertGreater(small['K'][0],0);self.assertLess(small['K'][0],1)
    def test_mapping_parameters_not_hidden_rounding(self):
        self.assertEqual(targets([1,1,1,1],'tiered',epsilon=0)['K'],[2.5,1.5,1.5,3])
        for mapping,factor in [('uniform1.5',1.5),('uniform2',2),('uniform3',3)]:
            self.assertEqual(targets([1,2,3,4],mapping,epsilon=0)['K'],[factor*i for i in [1,2,3,4]])
    def test_homogeneous_scaling_and_epsilon_invariance(self):
        a=targets([9,0,1,2]);b=targets([27,0,3,6],epsilon=.5)
        for x,y in zip(a['K'],b['K']):self.assertAlmostEqual(y,3*x)
        for x,y in zip(a['required_candidate_fraction'],b['required_candidate_fraction']):self.assertAlmostEqual(x,y)
    def test_infeasible_transit_denominator_is_not_silently_relaxed(self):
        with self.assertRaises(ValueError):targets([0,0,0,1],r=.2,candidate_fraction=.25)
        out=targets([0,0,0,0],r=.2,candidate_fraction=.25)
        self.assertTrue(out['feasible_at_candidate_fraction'])
    def test_zero_turnover(self):
        out=targets([2,0,0,1],r=0)
        self.assertEqual(out['K'],[4,0,0,2]);self.assertEqual(out['reserve'],[0]*4)
        self.assertEqual(out['required_candidate_fraction'],[0]*6)
    def test_validation(self):
        invalid=[[-1,0,0,0],[1,2,3],[1,2,3,4,5],[1,2,float('nan'),0],[1,2,float('inf'),0],[True,0,0,0],[.5,0,0,0]]
        for j in invalid:
            with self.subTest(J=j):
                with self.assertRaises(ValueError):targets(j)
        for kwargs in [{'mapping':'missing'},{'candidate_fraction':0},{'candidate_fraction':1.1},{'r':-.1},{'r':math.inf},{'epsilon':-.1}]:
            with self.assertRaises(ValueError):targets([1,1,1,1],**kwargs)

if __name__=='__main__':unittest.main(verbosity=2)
