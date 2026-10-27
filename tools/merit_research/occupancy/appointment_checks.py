"""纯研究任命层检查；不验证游戏引擎。"""
import unittest
try:
    import appointments as ap
except ImportError:
    ap = None


def person(pid=1, **kw):
    return dict(dict(id=pid, rank=1, score=100, age=40, active=True, cooldown_until=0, job=None), **kw)


def job(jid='new', **kw):
    return dict(dict(id=jid, tier=1, kind='admin', prominence=200, holder=None), **kw)


class AppointmentChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(ap, '研究任命模块尚未实现')

    def test_rank_thresholds_are_lower_bounds(self):
        for tier, minimum in enumerate([1,3,5,7], 1):
            self.assertTrue(ap.eligible(person(rank=minimum), job(tier=tier), {}, 1))
            self.assertTrue(ap.eligible(person(rank=9), job(tier=tier), {}, 1))
            if minimum > 1:
                self.assertFalse(ap.eligible(person(rank=minimum-1), job(tier=tier), {}, 1))

    def test_age_exit_cooldown_holder(self):
        for kw in [dict(age=15), dict(active=False), dict(cooldown_until=3)]:
            self.assertFalse(ap.eligible(person(**kw), job(), {}, 2))
        self.assertTrue(ap.eligible(person(age=16,cooldown_until=2),job(),{},2))
        self.assertFalse(ap.eligible(person(),job(holder=1),{},2))

    def test_current_tier_and_prominence(self):
        p=person(rank=9,job='old'); jobs={'old':job('old',tier=2,prominence=100)}
        self.assertFalse(ap.eligible(p,job(),jobs,3))
        self.assertTrue(ap.eligible(p,job(tier=2,prominence=101),jobs,3))
        self.assertFalse(ap.eligible(p,job(tier=2,prominence=100),jobs,3))
        self.assertTrue(ap.eligible(p,job(tier=3,prominence=1),jobs,3))

    def test_office_and_immobility(self):
        p=person(rank=9,job='old'); jobs={'old':job('old',prominence=1)}
        self.assertFalse(ap.eligible(p,job(kind='office'),jobs,1))
        self.assertFalse(ap.eligible(p,job(tier=2),jobs,1,mobility=False))
        self.assertTrue(ap.eligible(person(rank=3),job(kind='office',tier=2),{},1))
        self.assertFalse(ap.eligible(person(rank=9,job='missing'),job(tier=4),{},1))

    def test_ranking_modes_and_metrics(self):
        high=person(1,rank=9,score=50); low=person(2,rank=2,score=150)
        winner,m=ap.choose([low,high],job(),3,42)
        self.assertEqual(winner['id'],1)
        for key in ['winner_high_band','suitable_available','score_only_suitable','merit_advantage_proxy']:
            self.assertTrue(m[key])
        self.assertEqual(m['high_candidate_fraction'],.5)
        self.assertEqual(m['score_gap_to_best_suitable'],-100)
        for mode in ['score_only','suitable_first']:
            self.assertEqual(ap.choose([high,low],job(),3,42,mode=mode)[0]['id'],2)

    def test_empty(self):
        winner,m=ap.choose([],job(),3,42)
        self.assertIsNone(winner)
        self.assertIsNone(m['high_candidate_fraction'])
        self.assertFalse(m['merit_advantage_proxy'])

    def test_pathology_grouping(self):
        plain=ap.synthetic_score(person())
        one=ap.synthetic_score(person(elder_count=1))
        many=ap.synthetic_score(person(elder_count=5,blind=True))
        self.assertEqual(plain-one,50); self.assertEqual(one,many)
        self.assertEqual(plain-ap.synthetic_score(person(incapable=True)),150)
        self.assertEqual(plain-ap.synthetic_score(person(mental_unwell=True)),100)

    def test_age_score_and_pathology_not_eligibility(self):
        self.assertEqual(ap.synthetic_score(person(age=70)),100)
        self.assertEqual(ap.synthetic_score(person(age=80)),95)
        self.assertEqual(ap.synthetic_score(person(age=80),job(kind='central')),97)
        self.assertTrue(ap.eligible(person(rank=9,age=90,incapable=True,blind=True),job(),{},1))

    def test_stable_reordering(self):
        people=[person(i,rank=3) for i in range(8)]
        a=ap.choose(people,job(),3,42,entry='initial')[0]['id']
        self.assertEqual(a,ap.choose(list(reversed(people)),job(),3,42,entry='initial')[0]['id'])
        self.assertEqual(a,ap.choose(people,job(),3,42,entry='initial')[0]['id'])

    def test_initial_office_is_weighted_score(self):
        people=[person(1,rank=9,score=1),person(2,rank=1,score=200)]
        chosen=[ap.choose(people,job(kind='office'),y,42,entry='initial')[0]['id'] for y in range(500)]
        self.assertGreater(chosen.count(2),400); self.assertLess(chosen.count(2),500)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError): ap.choose([person()],job(),1,1,mode='bogus')
        with self.assertRaises(ValueError): ap.eligible(person(),job(tier=5),{},1)
        with self.assertRaises(ValueError): ap.choose([person(),person()],job(),1,1)


if __name__=='__main__': unittest.main()
