"""预算候选的边界，以及供给和随机小池的报告口径。"""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import budget_mapping_candidates as mapping
import study


class BudgetChecks(unittest.TestCase):
    def test_mapping_math_suite(self):
        self.assertGreaterEqual(mapping.self_check(),300)

    def test_small_top_reserve_is_population_not_annual_quota(self):
        a=mapping.targets([63,19,3,1],mode='priority10',top_extra=1)
        self.assertEqual(a['K'][3],2.5)
        self.assertAlmostEqual(sum(a['target']),3.3*86)
        self.assertFalse(a['strictly_scale_homogeneous'])
        self.assertEqual(mapping.targets([63,19,3,0],top_extra=1)['K'][3],0)

    def test_report_does_not_equate_mean_and_small_pool_stability(self):
        rows=[]
        for year,high in enumerate([0,2]*20):
            rows.append(dict(decision_n=[10]*6+[high,0,0],target=[10]*6+[1],
                Q=[0]*6,E=[1]*6))
        result=study.extra_metrics([dict(series=rows,config={})])
        self.assertEqual(result['band_mean_ratio'][3],1)
        self.assertEqual(result['top_zero_year_share'],.5)
        self.assertEqual(result['band_ratio_p10'][3],0)
        self.assertEqual(result['band_ratio_p90'][3],2)

if __name__=='__main__':unittest.main()
