"""联合研究的职位事件边界；不验证原生游戏继任。"""
import importlib.util
import json
import random
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

try:
    su=load(ROOT/'succession.py','joint_succession_checks_target')
except FileNotFoundError:
    su=None


def person(pid,**kw):
    return dict(dict(id=pid,rank=1,m=100,score=100,age=40,active=True,alive=True,
                     cooldown_until=0,job=None,first_job=None,central_year=-1),**kw)


def job(jid,**kw):
    return dict(dict(id=jid,tier=1,kind='admin',holder=None,prominence=200),**kw)


class SuccessionChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(su,'新职位事件模块尚未实现')

    def test_event_assigns_and_sets_first_job_cooldown(self):
        people={1:person(1)};jobs={5:job(5)}
        result=su.resolve(people,jobs,10,7,[dict(job_id=5,reason='initial',event_id='a')])
        self.assertEqual(jobs[5]['holder'],1)
        self.assertEqual(people[1]['job'],5)
        self.assertEqual(people[1]['first_job'],10)
        self.assertEqual(people[1]['first_job_rank'],1)
        self.assertEqual(people[1]['first_job_tier'],1)
        self.assertEqual(people[1]['cooldown_until'],15)
        self.assertEqual(result['appointments'],[1,0,0,0])
        self.assertEqual(result['grant_flows'],[])

    def test_repeated_external_event_is_idempotent_even_after_release(self):
        people={1:person(1)};jobs={5:job(5)};event=dict(job_id=5,reason='death',event_id='a')
        su.resolve(people,jobs,1,7,[event,event])
        jobs[5]['holder']=None;people[1]['job']=None;people[1]['cooldown_until']=0
        result=su.resolve(people,jobs,2,7,[event])
        self.assertEqual(result['appointments'],[0]*4)
        self.assertIsNone(jobs[5]['holder'])

    def test_distinct_events_same_slot_same_year(self):
        people={1:person(1,rank=2),2:person(2)};jobs={5:job(5)}
        su.resolve(people,jobs,1,7,[dict(job_id=5,reason='initial',event_id='a')])
        people[1].update(alive=False,job=None);jobs[5]['holder']=None
        result=su.resolve(people,jobs,1,7,[dict(job_id=5,reason='death',event_id='b')])
        self.assertEqual(result['appointments'],[1,0,0,0])
        self.assertEqual(jobs[5]['holder'],2)

    def test_auto_ids_are_new_across_calls(self):
        people={};jobs={5:job(5)};event=dict(job_id=5,reason='reassessment')
        a=su.resolve(people,jobs,1,7,[event]);b=su.resolve(people,jobs,1,7,[event])
        self.assertNotEqual(a['uncovered_events'][0]['event_id'],b['uncovered_events'][0]['event_id'])

    def test_transfer_creates_real_replacement_event(self):
        people={1:person(1,rank=3,job=1,first_job=0),2:person(2)}
        jobs={1:job(1,holder=1,prominence=100),2:job(2,tier=2,prominence=1000)}
        result=su.resolve(people,jobs,8,7,[dict(job_id=2,reason='death',event_id='start')])
        self.assertEqual(jobs[2]['holder'],1)
        self.assertEqual(jobs[1]['holder'],2)
        self.assertEqual(result['appointments'],[1,1,0,0])
        self.assertEqual(result['transfer_count'],1)
        self.assertEqual(people[1]['first_job'],0)

    def test_long_transfer_chain_has_bounded_stable_event_tokens(self):
        original=su._identity
        lengths=[]
        def bounded_identity(j,event):
            token=original(j,event)
            lengths.append(len(token))
            self.assertLess(len(token),256,'迁任事件不应递归转义完整父标识')
            return token
        su._identity=bounded_identity
        try:
            results=[]
            for _ in range(2):
                people={i:person(i,score=i,job=i,first_job=0) for i in range(30)}
                jobs={i:job(i,holder=i if i<30 else None,prominence=i) for i in range(31)}
                result=su.resolve(people,jobs,8,7,[dict(job_id=30,reason='death',event_id='start')])
                self.assertEqual(result['transfer_count'],30)
                self.assertEqual(result['uncovered_count'],1)
                self.assertEqual(len(result['processed_events']),31)
                results.append(result)
            self.assertEqual(results[0],results[1])
            self.assertEqual(len(lengths),62)
        finally:
            su._identity=original

    def test_uncovered_is_not_reported_as_engine_vacancy(self):
        people={1:person(1,rank=1)};jobs={5:job(5,tier=4)}
        result=su.resolve(people,jobs,1,7,[dict(job_id=5,reason='initial')])
        self.assertTrue(jobs[5]['uncovered'])
        self.assertIsNone(jobs[5]['holder'])
        self.assertEqual(result['uncovered_count'],1)
        self.assertEqual(result['appointments'],[0]*4)
        self.assertNotIn('vacant_years',result)
        people[1]['rank']=7
        result=su.resolve(people,jobs,2,7,[dict(job_id=5,reason='reassessment')])
        self.assertFalse(jobs[5]['uncovered'])
        self.assertEqual(result['appointments'],[0,0,0,1])
        self.assertEqual(people[1]['rank'],7)

    def test_only_explicit_central_target_grants_and_returns_flow(self):
        for target in [None,8,9]:
            people={1:person(1,rank=7,m=15000)};j=job(5,tier=4)
            if target:j['central_target']=target
            result=su.resolve(people,{5:j},4,7,[dict(job_id=5,reason='initial')])
            self.assertEqual(people[1]['rank'],target or 7)
            self.assertEqual(len(result['grant_flows']),int(target is not None))
            if target:
                self.assertEqual(people[1]['m'],su.TH[target])
                self.assertEqual(people[1]['central_year'],4)
                self.assertEqual(result['grant_flows'][0]['source'],7)
                self.assertEqual(result['grant_flows'][0]['target'],target)

    def test_higher_central_incumbent_not_truncated(self):
        people={1:person(1,rank=9,m=99999)};jobs={5:job(5,tier=4,central_target=8)}
        result=su.resolve(people,jobs,1,7,[dict(job_id=5,reason='initial')])
        self.assertEqual(people[1]['m'],99999)
        self.assertEqual(result['grant_flows'],[])

    def test_held_slot_is_not_reshuffled_and_no_event_means_no_change(self):
        people={1:person(1,job=5),2:person(2,rank=9)};jobs={5:job(5,holder=1)}
        self.assertEqual(su.resolve(people,jobs,1,7,[])['appointments'],[0]*4)
        self.assertEqual(su.resolve(people,jobs,1,7,[dict(job_id=5,reason='reassessment')])['appointments'],[0]*4)
        self.assertEqual(jobs[5]['holder'],1)

    def test_same_event_randomness_repeatable_but_distinct_events_have_distinct_keys(self):
        people={i:person(i) for i in range(8)};jobs={5:job(5)}
        first=su.resolve(people,jobs,1,7,[dict(job_id=5,reason='initial',event_id='a')])
        event_a=first['processed_events'][0]['random_seed']
        winner=jobs[5]['holder'];people[winner].update(job=None,cooldown_until=0);jobs[5]['holder']=None
        second=su.resolve(people,jobs,1,7,[dict(job_id=5,reason='initial',event_id='b')])
        self.assertNotEqual(event_a,second['processed_events'][0]['random_seed'])

    def test_serialized_event_ledger_keeps_idempotence(self):
        people={1:person(1)};jobs={5:job(5)}
        event=dict(job_id=5,reason='initial',event_id='stable')
        su.resolve(people,jobs,1,7,[event])
        people={int(k):v for k,v in json.loads(json.dumps(people)).items()}
        jobs={int(k):v for k,v in json.loads(json.dumps(jobs)).items()}
        jobs[5]['holder']=None;people[1].update(job=None,cooldown_until=0)
        result=su.resolve(people,jobs,3,7,[event])
        self.assertEqual(len(result['duplicate_events']),1)
        self.assertEqual(result['appointments'],[0]*4)

    def test_fast_choice_matches_reference_random_scores_and_ties(self):
        self.assertTrue(hasattr(su, '_choose_cached'), '等价缓存选择尚未实现')
        rng=random.Random(81931)
        for case in range(140):
            people=[person(i,rank=rng.randint(1,9),score=rng.choice([50,50,80,100,rng.random()*100]),
                           age=rng.choice([20,40,70,85]),blind=bool(rng.randrange(2)),
                           incapable=bool(rng.randrange(2)),elder_count=rng.randrange(3))
                    for i in range(rng.randrange(30))]
            rng.shuffle(people)
            for kind in ['admin','central']:
                j=job(case,tier=1+case%4,kind=kind)
                cache={}
                for mode in sorted(su.appointments.MODES):
                    expected=su.appointments.choose(people,j,case%9,1234,mode)
                    actual=su._choose_cached(people,j,case%9,1234,mode,cache)
                    self.assertEqual(actual,expected,(case,kind,mode))
                self.assertEqual(len(cache),len(people))

    def test_fast_choice_hash_collision_keeps_reference_stable_order(self):
        self.assertTrue(hasattr(su, '_choose_cached'), '等价缓存选择尚未实现')
        original=su.appointments._uniform
        su.appointments._uniform=lambda *args,**kw: .25
        try:
            people=[person(i,rank=3) for i in [2,10,1,20]]
            for mode in sorted(su.appointments.MODES):
                j=job(1,tier=2)
                expected=su.appointments.choose(people,j,1,2,mode)
                self.assertEqual(su._choose_cached(people,j,1,2,mode,{}),expected)
                self.assertEqual(expected[0]['id'],1)
        finally:
            su.appointments._uniform=original

    def test_cached_score_reuses_across_rank_grant_but_separates_kind(self):
        people=[person(1,rank=7,age=80,incapable=True),person(2,rank=8)]
        cache={}
        for kind in ['admin','central']:
            j=job(1,tier=4,kind=kind)
            self.assertEqual(su._choose_cached(people,j,1,2,'merit_first',cache),
                             su.appointments.choose(people,j,1,2))
        self.assertEqual(len(cache),4)
        people[0]['rank']=9
        for kind in ['admin','central']:
            j=job(1,tier=4,kind=kind)
            for mode in sorted(su.appointments.MODES):
                self.assertEqual(su._choose_cached(people,j,1,2,mode,cache),
                                 su.appointments.choose(people,j,1,2,mode))
        self.assertEqual(len(cache),4)

    def test_isolated_frozen_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);joint=root/'merit-joint-study';joint.mkdir()
            shutil.copyfile(ROOT/'succession.py',joint/'succession.py')
            source_root=ROOT.parent
            for packed,source,files in [('merit-occupancy-study','occupancy',['appointments.py']),('merit-buffer-study','buffers',['model.py'])]:
                dest=root/packed;dest.mkdir()
                original=source_root/source
                if not original.exists():original=source_root/packed
                for filename in files:shutil.copyfile(original/filename,dest/filename)
            frozen=load(joint/'succession.py','joint_frozen_fixture')
            people={1:person(1)};jobs={5:job(5)}
            self.assertEqual(frozen.resolve(people,jobs,1,7,[dict(job_id=5,reason='initial')])['appointments'],[1,0,0,0])


if __name__=='__main__':unittest.main()
