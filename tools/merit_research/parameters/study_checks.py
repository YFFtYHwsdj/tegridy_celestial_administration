"""参数编排的输入隔离与比较口径；不替代原生业务回归。"""
import copy
from types import SimpleNamespace
import unittest
import study


class ParameterStudyChecks(unittest.TestCase):
    def test_health_cache_reuses_equal_inputs_and_isolates_outputs(self):
        calls=[]
        def advance(state,seed,pid,year):
            calls.append((seed,pid,year));return {'age':state['age']+1,'tracks':state['tracks'][:]}
        world=SimpleNamespace(aging=SimpleNamespace(advance_year=advance))
        state={'age':18,'tracks':[1]}
        with study.health_cache(world) as stats:
            first=world.aging.advance_year(state,3,4,5)
            first['tracks'].append(2)
            second=world.aging.advance_year(copy.deepcopy(state),3,4,5)
            self.assertEqual(second,{'age':19,'tracks':[1]})
            self.assertEqual(stats,{'hits':1,'misses':1})
            with self.assertRaises(AssertionError):
                world.aging.advance_year({'age':19,'tracks':[1]},3,4,5)
        self.assertIs(world.aging.advance_year,advance)
        self.assertEqual(len(calls),1)

    def test_health_cache_restores_after_failure(self):
        original=lambda *args:None
        world=SimpleNamespace(aging=SimpleNamespace(advance_year=original))
        with self.assertRaises(RuntimeError):
            with study.health_cache(world):raise RuntimeError('刻意失败')
        self.assertIs(world.aging.advance_year,original)

    def test_later_qualification_keeps_original_potential(self):
        original=lambda p:None
        joint=SimpleNamespace(pr=SimpleNamespace(ceiling=lambda *args:9),
                              world=SimpleNamespace(sync_health=original))
        p=dict(age=18,rank=1,cap=9)
        with study.qualification_model(joint,'later'):
            joint.world.sync_health(p);self.assertEqual(p['cap'],2)
            p['age']=35;joint.world.sync_health(p);self.assertEqual(p['cap'],4)
            p['age']=45;joint.world.sync_health(p);self.assertEqual(p['cap'],6)
            p['age']=55;joint.world.sync_health(p);self.assertEqual(p['cap'],9)
        self.assertIs(joint.world.sync_health,original)

    def test_shortlist_does_not_trade_large_error_for_low_budget(self):
        data=dict(ranking=[dict(config={'name':'best'},tracking=.2,budget=2),
                           dict(config={'name':'near'},tracking=.24,budget=1.5),
                           dict(config={'name':'bad'},tracking=.3,budget=1)])
        self.assertEqual(study.shortlist(data),[{'name':'best'},{'name':'near'}])

    def test_source_candidates_are_shared_and_direct(self):
        configs=study.sweeps()
        self.assertEqual(len({c['name'] for c in configs}),len(configs))
        self.assertTrue(all('military_low' not in c and c['reserve']==[0,0,0] for c in configs))
        for c in configs:
            if c['factor']=='phi2':
                self.assertEqual(c['phi'][0],.6)
                self.assertEqual(c['phi'][2],.6)

if __name__=='__main__':unittest.main()
