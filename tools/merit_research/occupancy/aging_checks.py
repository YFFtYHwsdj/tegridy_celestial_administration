"""研究代理的边界与状态机检查；不证明CK3引擎行为。"""
import copy
import unittest
from unittest.mock import patch
import aging

class AgingChecks(unittest.TestCase):
    def test_reproducible_and_pure(self):
        a=aging.make_health(41,7,45,'base')
        self.assertEqual(a,aging.make_health(41,7,45,'base'))
        snap=copy.deepcopy(a)
        b=aging.advance_year(a,41,7,0)
        self.assertEqual(a,snap)
        self.assertEqual(b,aging.advance_year(snap,41,7,0))
        self.assertEqual(b,aging.advance_year(b,41,7,0))
        self.assertEqual(b['age'],46)
    def test_no_elder_is_not_no_aging(self):
        a=aging.make_health(4,2,65,'no_elder')
        self.assertEqual(a['elder_count'],0)
        self.assertLess(a['base_health'],a['birth_health'])
        for y in range(10):
            a=aging.advance_year(a,4,2,y)
            self.assertEqual(a['elder_count'],0)
    def test_direct_heart_death(self):
        a=aging.make_health(1,1,30,'no_elder')
        a['profile']='base';a['tracks']['faltering_heart']=100
        b=aging.advance_year(a,1,1,0)
        self.assertFalse(b['alive']);self.assertEqual(b['death_cause'],'heart_attack_proxy')
    def test_cognitive_and_vision_endpoints(self):
        a=aging.make_health(9,3,40,'base')
        a['tracks']['withering_mind']=100;a['tracks']['clouded_eyes']=100
        b=aging.advance_year(a,9,3,0)
        self.assertTrue(b['incapable']);self.assertTrue(b['blind'])
        self.assertNotIn('clouded_eyes',b['tracks'])
    def test_dead_is_absorbing(self):
        a=aging.make_health(1,1,20,'base');a['alive']=False;a['death_cause']='fixture'
        self.assertEqual(a,aging.advance_year(a,1,1,0))
    def test_no_aging_before25_and_capped_probability(self):
        self.assertEqual(aging.aging_loss_probability(24),0)
        self.assertEqual(aging.aging_loss_probability(25),.075)
        self.assertEqual(aging.aging_loss_probability(90),1)
        self.assertEqual(aging.monthly_natural_probability(3),0)
        self.assertEqual(aging.monthly_natural_probability(-10),.25)
    def test_pending_know_thyself_is_not_cancelled(self):
        a=aging.make_health(8,8,20,'longlife')
        a['know_thyself_once']=True;a['death_due_month']=a['clock_month']+.1
        a['pending_death_cause']='natural_after_second_chance_proxy'
        a['base_health']=100
        b=aging.advance_year(a,8,8,0)
        self.assertFalse(b['alive'])
        self.assertEqual(b['death_cause'],'natural_after_second_chance_proxy')
    def test_second_chance_queues_once_and_then_dies(self):
        a=aging.make_health(3,4,20,'longlife');a['base_health']=-10
        with patch.object(aging,'_u',return_value=.1):
            b=aging.advance_year(a,3,4,0)
            self.assertTrue(b['alive']);self.assertTrue(b['know_thyself_once'])
            self.assertIsNotNone(b['death_due_month'])
            c=aging.advance_year(b,3,4,1)
            self.assertFalse(c['alive'])
            self.assertEqual(c['death_cause'],'natural_after_second_chance_proxy')
    def test_infirm_progress_and_bone_injury(self):
        a=aging.make_health(2,5,45,'base');a['base_health']=20
        a['tracks']={'infirm':0,'fragile_bones':50}
        with patch.object(aging,'_u',return_value=.001):
            b=aging.advance_year(a,2,5,0)
        self.assertIn(b['infirm_xp'],(4,8,12))
        self.assertEqual(b['wound_penalty'],1.5)
        self.assertGreater(b['tracks']['fragile_bones'],50)
    def test_initial_survivor_is_not_rejuvenated(self):
        a=aging.make_health(101,3,70,'base')
        self.assertTrue(a['alive']);self.assertEqual(a['age'],70)
        self.assertLess(a['base_health'],a['birth_health'])
        self.assertEqual(a['clock_month'],840)

    def test_input_boundaries(self):
        for age in [-1,12.5]:
            with self.assertRaises(ValueError):aging.make_health(1,1,age,'base')
        with self.assertRaises(ValueError):aging.make_health(1,1,20,'unknown')
        a=aging.make_health(1,1,20,'base');b=aging.advance_year(a,1,1,3)
        with self.assertRaises(ValueError):aging.advance_year(b,1,1,2)

if __name__=='__main__':unittest.main(verbosity=2)
