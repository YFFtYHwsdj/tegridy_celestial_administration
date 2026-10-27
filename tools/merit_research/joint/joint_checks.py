"""联合研究必须保留冻结来源、四六目标和双向人数账。"""
import unittest
from unittest.mock import patch
import study

class JointChecks(unittest.TestCase):
    def test_small_world_and_source_limit(self):
        result=study.trial('civil',0,{'mapping':'transit2','J':[3,1,1,1],'initial_scale':.025},years=8)
        self.assertEqual(result['years'],8)
        self.assertEqual(result['mechanism_errors'],0)
        self.assertEqual(len(result['series']),8)
        for row in result['series']:
            self.assertEqual(sum(row['post_n']),row['active'])
            self.assertEqual(sum(row['known'])+sum(row['uncovered']),sum(row['J']))
            self.assertTrue(all(x>=0 for x in row['post_n']))

    def test_empty_population_is_not_fake_filled(self):
        result=study.trial('military',1,{'mapping':'uniform2','J':[1,0,0,1],'initial':'empty','entry_mult':0},years=3)
        for row in result['series']:
            self.assertEqual(row['active'],0)
            self.assertEqual(row['known'],[0,0,0,0])
            self.assertEqual(row['uncovered'],[1,0,0,1])

    def test_fixed_endpoint_distinguishes_death_and_late_job(self):
        people=[dict(entry=60,first_job=None,death_year=99,cap=9,hit={1:60}),
                dict(entry=60,first_job=101,death_year=None,cap=9,hit={1:60,7:101}),
                dict(entry=79,first_job=119,death_year=None,cap=9,hit={1:79,7:119})]
        result=study.cohort_summary(people)
        self.assertEqual(result['n'],3)
        self.assertEqual(result['first_job40'],1)
        self.assertEqual(result['dead_without_first40'],1)
        self.assertEqual(result['alive_without_first40'],1)
        self.assertEqual(result['capable_reached3'],1)

    def test_observer_snapshots_cover_stages_without_changing_trial(self):
        config={'mapping':'uniform2','J':[2,1,0,0],'initial_scale':.01}
        records=[]
        original=study.world.aging.advance_year
        def force_exit(state,seed,pid,year):
            state=original(state,seed,pid,year)
            if year==1:state['alive']=False
            return state
        def observe(stage,year,people,context):
            records.append((stage,year))
            if stage=='exit':
                self.assertEqual(context['cause'],'death')
                self.assertEqual(len(people),1)
                person=next(iter(people.values()))
                self.assertFalse(person['alive'])
                self.assertEqual(person['death_year'],year)
                self.assertIsNone(person['job'])
            else:
                self.assertIn(stage,['decision','after'])
                self.assertEqual(sum(context['n']),sum(p['active'] for p in people.values()))
                self.assertEqual(context['E'],[len(context['pools'][a]) for a in range(1,7)])
                if stage=='decision':
                    for pid,rank in context['frozen'].items():
                        self.assertEqual(people[pid]['rank'],rank)
                    for pool in context['pools'].values():
                        for person in pool:
                            self.assertIs(person,people[person['id']])
                else:
                    self.assertEqual(sum(context['npost']),sum(context['n']))
            # 主动污染快照，证明诊断不取得演算状态的写权限。
            for person in people.values():person['rank']=99
            context['cfg']['r']=999
            if 'Q' in context:context['Q'][:]=[999]*6
            if 'pools' in context:context['pools'].clear()
        with patch.object(study.world.aging,'advance_year',side_effect=force_exit):
            expected=study.trial('civil',3,config,years=6)
            observed=study.trial('civil',3,config,years=6,observer=observe)
        self.assertEqual(expected,observed)
        self.assertEqual([year for stage,year in records if stage=='decision'],list(range(6)))
        self.assertEqual([year for stage,year in records if stage=='after'],list(range(6)))
        self.assertTrue(any(stage=='exit' for stage,year in records))

    def test_merit_gate_only_bypasses_threshold_on_an_isolated_person(self):
        config={'mapping':'uniform2','J':[3,1,1,1],'initial':'empty','entry_mult':1/26}
        snapshots=[];calls=[]
        def observe(stage,year,people,context):
            if stage=='decision':
                snapshots.append((year,context['E']))
                for a,pool in context['pools'].items():
                    self.assertTrue(all(p['rank']==a and p['cap']>=a+1 for p in pool))
            if stage=='after':
                self.assertTrue(all(p['cap']==2 and p['rank']<=2 and p['age']>=18
                                    and p['m']<1e99 for p in people.values()))
        def bypass(person,source,threshold):
            calls.append((person['rank'],source,threshold))
            self.assertEqual(person['rank'],source)
            self.assertEqual(threshold,study.pr.TH[source+1])
            # 即使回调篡改硬资格与余额，副本也不能影响正式来源及归一化。
            person.update(rank=9,cap=9,age=0,m=1e99)
            return True
        with patch.object(study.pr,'ceiling',return_value=2):
            expected=study.trial('civil',13,config,years=5)
            default=study.trial('civil',13,config,years=5,merit_gate=None)
            observed=study.trial('civil',13,config,years=5,observer=observe,merit_gate=bypass)
        self.assertEqual(expected,default)
        self.assertTrue(calls)
        self.assertEqual(snapshots[1],(1,[1,0,0,0,0,0]))
        self.assertEqual(expected['series'][1]['E'],[0]*6)
        self.assertGreater(sum(sum(s['Q']) for s in observed['series']),
                           sum(sum(s['Q']) for s in expected['series']))
        self.assertTrue(all(s['Q'][1:]==[0]*5 for s in observed['series']))
        self.assertEqual(observed['series'][1]['post_n'],[0,1,0,0,0,0,0,0,0])

    def test_deterministic_replay(self):
        config={'mapping':'uniform2','J':[2,1,0,0],'initial_scale':.01}
        self.assertEqual(study.trial('civil',3,config,years=6),study.trial('civil',3,config,years=6))

if __name__=='__main__':unittest.main()
