"""检验方程与封存计数，不验证原生游戏规则。"""
import hashlib
import json
import unittest
from pathlib import Path
import numpy as np
from study import quota
ROOT=Path(__file__).resolve().parent

class ControllerChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'results.json').read_text())

    def test_seal_and_coverage(self):
        self.assertEqual(hashlib.sha256((ROOT/'study.py').read_bytes()).hexdigest(),self.data['source_sha256'])
        self.assertEqual(len(self.data['cases']),20)
        self.assertEqual(len(self.data['runs']),260)

    def test_exact_fixed_point(self):
        t=np.array(self.data['target'])
        q=quota(t,t,np.full(6,100000))
        tails=np.cumsum(t[::-1])[::-1][1:]
        np.testing.assert_allclose(.96*(tails+q),tails,rtol=1e-12)

    def test_positive_decreasing_soft_tail(self):
        b=10.;r=.04/.96;k=.35
        values=[r*b/(1+k*(s-b)/(r*b)) for s in [b,1.2*b,2*b,100*b,100000*b]]
        self.assertTrue(all(x>0 for x in values))
        self.assertTrue(all(a>b for a,b in zip(values,values[1:])))
        self.assertLess(values[-1],1e-5)

    def test_nonnegative_source_bound(self):
        rng=np.random.default_rng(42)
        for _ in range(1000):
            n=rng.integers(0,10000,size=7);t=rng.uniform(0,100,size=7);e=rng.binomial(n[:6],.3)
            q=quota(n,t,e)
            self.assertTrue(np.all(q>=0) and np.all(q<=e))
            whole=np.floor(q).astype(int);actual=whole+(rng.random(6)<q-whole)
            self.assertTrue(np.all(actual<=e))

    def test_zero_target_and_no_source(self):
        np.testing.assert_array_equal(quota(np.ones(7),np.zeros(7),np.ones(6)),np.zeros(6))
        np.testing.assert_array_equal(quota(np.ones(7),np.ones(7),np.zeros(6)),np.zeros(6))

    def test_source_sufficient_initial_states(self):
        for name in ['baseline','initial=empty','initial=bottom','initial=top','initial=high_top']:
            self.assertLess(self.data['groups'][name]['deterministic']['late_tail_max_error_mean'],1e-3)

    def test_expansion_does_not_hide_total_excess(self):
        g=self.data['groups']['entry=10']
        self.assertLess(g['deterministic']['late_tail_max_error_mean'],1e-3)
        self.assertGreater(g['stochastic']['late_population_mean'],9*sum(self.data['target']))

    def test_no_exit_cannot_be_stable(self):
        s=10.;b=10.;r=.04/.96;k=.35
        for _ in range(10000):
            q=r*b if s<=b else r*b/(1+k*(s-b)/(r*b))
            previous=s;s+=q
            self.assertGreater(s,previous)
        self.assertGreater(s,50)

    def test_recorded_deterministic_ledgers(self):
        for run in self.data['runs']:
            if run['seed'] is not None:continue
            self.assertEqual(len(run['series']),400)
            for row in run['series']:
                self.assertAlmostEqual(sum(row['n']),row['population'],places=7)
                self.assertTrue(all(x>=0 for x in row['n']))

if __name__=='__main__':unittest.main()
