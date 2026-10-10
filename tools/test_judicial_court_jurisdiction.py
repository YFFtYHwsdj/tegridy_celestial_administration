"""Evaluate real jurisdiction branches over a bounded title/court fixture.

Native host/liege relationships are fixtures, not verified engine semantics.
Unknown syntax fails; this does not simulate arrest outcomes or interaction UI.
"""
import unittest
from test_judicial_authority import TRIGGERS, read, definitions


class CourtFixture:
    def __init__(self):
        self.scopes = {}
        self.rules = dict(TRIGGERS)
        self.rules.update(definitions(read('common/scripted_triggers/tca_judicial_arrest_triggers.txt')))

    def resolve(self, path, current, previous):
        parts = path.split('.')
        first = parts.pop(0)
        obj = current if first == 'this' else previous if first == 'prev' else self.scopes.get(first[6:]) if first.startswith('scope:') else current.get(first)
        for part in parts:
            obj = obj.get(part) if obj else None
        return obj

    def run(self, name, current, previous=None, params=None):
        def substitute(seq):
            result = []
            for k, o, v in seq:
                for param, ref in (params or {}).items():
                    k = k.replace('$'+param+'$', ref)
                    if isinstance(v, str):
                        v = v.replace('$'+param+'$', ref)
                result.append((k, o, substitute(v) if isinstance(v, list) else v))
            return result
        return self.evaluate(substitute(self.rules[name]), current, previous)

    def evaluate(self, seq, current, previous):
        chain = False
        results = []
        for key, op, value in seq:
            if key == 'trigger_if':
                limit = next(v for k,o,v in value if k == 'limit')
                chain = self.evaluate(limit, current, previous)
                result = not chain or self.evaluate([e for e in value if e[0] != 'limit'], current, previous)
            elif key == 'trigger_else':
                result = chain or self.evaluate(value, current, previous)
            elif key in ('AND','OR','NOT'):
                if key == 'OR':
                    result = any(self.evaluate([e], current, previous) for e in value)
                else:
                    result = self.evaluate(value, current, previous)
                    if key == 'NOT': result = not result
            elif key == 'save_temporary_scope_as':
                self.scopes[value] = current
                result = True
            elif key == 'exists':
                result = self.resolve(value, current, previous) is not None
            elif key == 'any_held_title':
                result = any(self.evaluate(value, title, current) for title in current.get('titles', []))
            elif key.startswith('tca_') and key in current:
                result = current[key] == (value == 'yes')
            elif key in self.rules:
                if isinstance(value, list):
                    params = {}
                    for k,o,v in value:
                        ref = 'scope:fixture_parameter_'+k
                        self.scopes[ref[6:]] = self.resolve(v, current, previous)
                        params[k] = ref
                    result = self.run(key, current, previous, params)
                else:
                    result = self.run(key, current, previous) == (value == 'yes')
            elif isinstance(value, list):
                obj = self.resolve(key, current, previous)
                result = obj is not None and self.evaluate(value, obj, current)
            elif key in ('target_is_de_facto_liege_or_above','target_is_liege_or_above'):
                wanted = self.resolve(value, current, previous)
                obj = current.get('liege')
                result = False
                while obj is not None:
                    if obj is wanted:
                        result = True
                        break
                    obj = obj.get('liege')
            elif key in ('is_spouse_of','is_parent_of','is_child_of'):
                result = current.get(key) is self.resolve(value, current, previous) and key in current
            elif key == 'is_foreign_court_or_pool_guest_of':
                result = current.get('host') is self.resolve(value, current, previous) and (current.get('is_pool_guest', False) or current.get('is_foreign_court_guest', False))
            elif key == 'basic_allowed_to_imprison_character_trigger':
                raise AssertionError('Native trigger needs an explicit fixture')
            elif value in ('yes','no'):
                result = current.get(key, False) == (value == 'yes')
            else:
                lhs = self.resolve(key, current, previous)
                rhs = self.resolve(value, current, previous)
                result = lhs is rhs if op == '=' else lhs is not rhs
            results.append(result)
        return all(results)


class CourtJurisdictionTests(unittest.TestCase):
    def setUp(self):
        self.f = CourtFixture()
        self.emperor = {'is_alive': True}
        self.foreign = {'is_alive': True}
        self.circuit = self.title(None)
        self.duchy = self.title(self.circuit)
        self.county = self.title(self.duchy)
        self.peer = self.title(self.circuit)
        self.other_circuit = self.title(None)
        self.actors = {}
        for name, title in [('route',self.circuit),('duke',self.duchy),('county',self.county),('peer',self.peer),('other',self.other_circuit)]:
            self.actors[name] = {'is_alive':True, 'is_ruler':True, 'primary_title':title, 'titles':[title], 'top_liege':self.emperor, 'tca_is_judicial_governor_trigger':True, 'tca_is_judicial_commissioner_trigger':False}
            title['holder'] = self.actors[name]
        self.actors['duke']['liege'] = self.actors['route']
        self.actors['county']['liege'] = self.actors['duke']
        self.actors['peer']['liege'] = self.actors['route']
        self.actors['route']['liege'] = self.emperor
        self.commissioner = {'is_alive':True, 'top_liege':self.emperor, 'tca_is_judicial_commissioner_trigger':True, 'primary_title':{'var:song_judicial_circuit':self.circuit}}

    def title(self, liege):
        return {'liege':liege, 'tca_is_local_administrative_title_trigger':True}

    def courtier(self, owner):
        return {'is_alive':True, 'liege_or_court_owner':owner, 'top_liege':self.emperor}

    def guest(self, host, pool=False):
        return {'is_alive':True, 'host':host, 'top_liege':self.foreign, 'is_pool_guest':pool, 'is_foreign_court_guest':not pool}

    def allowed(self, actor, target):
        self.f.scopes.update(actor=actor,recipient=target)
        return self.f.run('tca_judicial_actor_has_jurisdiction_trigger', {})

    def test_governor_includes_own_and_subordinate_courts_only(self):
        for owner in ('route','duke','county','peer','other'):
            for actor, expected in [('route',owner != 'other'),('duke',owner in ('duke','county')),('county',owner == 'county')]:
                with self.subTest(actor=actor,owner=owner):
                    self.assertEqual(self.allowed(self.actors[actor],self.courtier(self.actors[owner])),expected)

    def test_commissioner_includes_governor_and_entire_circuit_courts(self):
        self.assertTrue(self.allowed(self.commissioner,self.actors['route']))
        for owner in ('route','duke','county','peer','other'):
            self.assertEqual(self.allowed(self.commissioner,self.courtier(self.actors[owner])),owner != 'other')
        self.assertFalse(self.allowed(self.actors['duke'],self.actors['route']))
        self.assertFalse(self.allowed(self.actors['route'],self.actors['route']))
        self.assertFalse(self.allowed(self.commissioner,self.emperor))

    def test_foreign_and_pool_guests_follow_actual_host(self):
        for pool in (False,True):
            target = self.guest(self.actors['county'],pool)
            for actor in ('route','duke','county'):
                self.assertTrue(self.allowed(self.actors[actor],target))
            self.assertTrue(self.allowed(self.commissioner,target))
            self.assertFalse(self.allowed(self.actors['peer'],target))
            target['host'] = self.actors['other']
            self.assertFalse(self.allowed(self.actors['route'],target))
            self.assertFalse(self.allowed(self.commissioner,target))
            target.pop('host')
            self.assertFalse(self.allowed(self.commissioner,target))

    def test_physical_presence_never_grants_jurisdiction(self):
        traveler = self.courtier(self.actors['other'])
        traveler['location'] = self.county
        traveler['host'] = self.actors['county']
        self.assertFalse(self.allowed(self.actors['route'],traveler))
        self.assertFalse(self.allowed(self.commissioner,traveler))

    def test_guest_royal_protection_uses_host_emperor(self):
        target = self.guest(self.actors['county'])
        target['is_child_of'] = self.emperor
        self.assertTrue(self.f.run('tca_is_emperor_first_degree_kin_trigger',target))
        target['is_child_of'] = self.foreign
        self.assertFalse(self.f.run('tca_is_emperor_first_degree_kin_trigger',target))
        ordinary = self.courtier(self.actors['county'])
        ordinary['is_child_of'] = self.emperor
        self.assertTrue(self.f.run('tca_is_emperor_first_degree_kin_trigger',ordinary))

    def test_guest_official_kin_uses_host_realm(self):
        self.f.scopes['target'] = self.guest(self.actors['county'])
        for emperor, expected in [(self.emperor,True),(self.foreign,False)]:
            candidate = {'top_liege':emperor}
            self.assertEqual(self.f.run('tca_is_in_scored_target_realm_trigger',candidate,params={'TARGET':'scope:target'}),expected)
        self.f.scopes['target'] = self.courtier(self.actors['county'])
        self.assertTrue(self.f.run('tca_is_in_scored_target_realm_trigger',{'top_liege':self.emperor},params={'TARGET':'scope:target'}))

    def test_subordinate_guest_basic_affiliation_keeps_native_branch(self):
        # Replace only native basic eligibility with a fixture; execute the actual wrapper.
        self.f.rules['basic_allowed_to_imprison_character_trigger'] = [('fixture_native_basic','=','yes')]
        self.f.scopes['target'] = self.guest(self.actors['county'])
        for name, expected in [('route',True),('duke',True),('county',True),('peer',False)]:
            self.assertEqual(self.f.run('tca_basic_allowed_to_arrest_character_trigger',self.actors[name],params={'CHARACTER':'scope:target'}),expected)
        self.f.scopes['target'] = self.courtier(self.actors['other'])
        self.assertFalse(self.f.run('tca_basic_allowed_to_arrest_character_trigger',self.actors['route'],params={'CHARACTER':'scope:target'}))
        self.actors['route']['fixture_native_basic'] = True
        self.assertTrue(self.f.run('tca_basic_allowed_to_arrest_character_trigger',self.actors['route'],params={'CHARACTER':'scope:target'}))
        arrest = read('common/scripted_triggers/tca_judicial_arrest_triggers.txt')
        self.assertIn('advanced_allowed_to_imprison_character_trigger',arrest)
        self.assertIn('tca_judicial_arrest_native_common_valid_trigger = yes',arrest)
        self.assertNotIn('basic_allowed_to_imprison_character_trigger =',arrest)

if __name__ == '__main__':
    unittest.main()
