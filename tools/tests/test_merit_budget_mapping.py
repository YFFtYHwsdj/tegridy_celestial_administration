"""离线员额映射的守恒、形状与非法输入；不复制原生晋升业务。"""
import importlib.util
import math
from pathlib import Path
import unittest

_source = Path(__file__).resolve().parents[1] / 'merit_research/budget_mapping_candidates.py'
_spec = importlib.util.spec_from_file_location('merit_budget_math_reference', _source)
mapping = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mapping)


def candidate(J, **kwargs):
    """本轮共同预算参数；局部覆盖只用于边界检查。"""
    config = dict(mode='pipeline', budget_factor=1.5, top_factor=1,
                  base_share=.25, middle_share=.6, phi=.8, r=.08)
    config.update(kwargs)
    return mapping.targets(J, **config)


class MeritBudgetMappingTests(unittest.TestCase):
    def test_conservation_splitting_and_scale(self):
        for J in ([0,0,0,0], [100,0,0,5], [348,59,15,8],
                  [63,19,3,1], [0,0,0,5], [100,20,5,0]):
            for k in (1.25,1.5,2):
                with self.subTest(J=J,k=k):
                    a=candidate(J,budget_factor=k)
                    b=candidate([7*j for j in J],budget_factor=k)
                    self.assertTrue(all(x>=0 for x in a['K']))
                    self.assertAlmostEqual(sum(a['K']),k*sum(J))
                    self.assertAlmostEqual(sum(a['target']),1.1*k*sum(J))
                    self.assertTrue(all(math.isclose(7*x,y) for x,y in zip(a['K'],b['K'])))
                    for band in range(3):
                        self.assertAlmostEqual(a['target'][2*band+1],.8*a['T'][band])

    def test_high_grade_can_compete_for_lower_titles(self):
        a=candidate([100,0,0,5])
        self.assertLess(a['K'][0],100)
        self.assertGreater(a['K'][1],0)
        self.assertGreater(a['K'][2],0)

    def test_local_title_shape_remains_visible(self):
        a=candidate([100,0,0,5]);b=candidate([75,20,5,5])
        self.assertEqual(a['total_budget'],b['total_budget'])
        self.assertNotEqual(a['K'][:3],b['K'][:3])
        self.assertEqual(a['K'][3],b['K'][3])

    def test_zero_titles_do_not_create_a_top_target(self):
        self.assertEqual(candidate([0,0,0,0])['target'],[0.]*7)
        self.assertEqual(candidate([100,20,5,0])['B'][5],0)

    def test_reject_invalid_pipeline_parameters(self):
        for kwargs in (dict(base_share=-.1),dict(base_share=1.1),
                       dict(middle_share=0),dict(middle_share=.9),
                       dict(phi=0),dict(phi=1),dict(top_factor=.5)):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                candidate([100,0,0,5],**kwargs)

if __name__=='__main__':
    unittest.main()
