"""Bounded static evaluation of the actual score tables and central resolver.

This is not an engine emulator: native identity/jurisdiction predicates remain
fixtures. Unknown score syntax fails instead of silently being accepted.
"""
from pathlib import Path
import operator
import unittest
from check_judicial_upstream import body, tokens
from test_judicial_arrest_policy import entries

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding='utf-8-sig')

SCORES = read('common/script_values/tca_judicial_authority_values.txt')
POLICY = read('common/scripted_triggers/tca_judicial_authority_triggers.txt')
EFFECTS = read('common/scripted_effects/tca_judicial_authority_effects.txt')
OPS = {'=': operator.eq, '>=': operator.ge, '<=': operator.le,
       '>': operator.gt, '<': operator.lt, '!=': operator.ne}


def definitions(text):
    return {key: value for key, op, value in entries(tokens(text))}

VALUES = definitions(SCORES)
TRIGGERS = definitions(POLICY)


def number(value):
    if value in VALUES:
        return number(VALUES[value])
    return float(value)


def evaluate_condition(seq, facts):
    def item(key, op, value):
        if key in ('AND', 'OR', 'NOT'):
            results = [item(*entry) for entry in value]
            return any(results) if key == 'OR' else (not all(results) if key == 'NOT' else all(results))
        if key.startswith('scope:') and isinstance(value, list):
            return key in facts and evaluate_condition(value, facts[key])
        if key in VALUES:
            return OPS[op](evaluate_value(key, facts), number(value))
        if key in ('house', 'dynasty') and isinstance(value, list):
            return key in facts and evaluate_condition(value, facts[key])
        if key == 'any_held_title':
            return any(evaluate_condition(value, title) for title in facts.get('titles', []))
        if key == 'any_councillor':
            return any(evaluate_condition(value, person) for person in facts.get('council', []))
        if key == 'has_trait_xp':
            config = dict((k, (o, v)) for k, o, v in value)
            comparison, boundary = config['value']
            return OPS[comparison](facts.get('confucian_xp', 0), number(boundary))
        if key == 'has_trait':
            return value in facts.get('traits', set())
        if key == 'exists':
            return value in facts
        if key == 'tca_has_official_relative_trigger':
            kind = dict((k, v) for k, o, v in value)['CLASS']
            return kind in facts.get('official_relatives', set())
        if key in ('house', 'dynasty') and isinstance(value, str):
            return False
        if key == 'tier':
            tiers = {'tier_barony': 1, 'tier_county': 2, 'tier_duchy': 3, 'tier_kingdom': 4, 'tier_empire': 5}
            return OPS[op](facts.get('tier', 0), tiers[value])
        if key in ('is_lowborn', 'is_house_head', 'is_dominant_family', 'is_powerful_family',
                   'is_alive', 'is_imprisoned') or key.startswith('tgp_passed_'):
            return facts.get(key, False) == (value == 'yes')
        if key == 'has_council_position':
            return facts.get('position') == value
        if key in ('merit_level', 'prestige_level', 'piety_level', 'dynasty_prestige_level'):
            return OPS[op](facts.get(key, 0), number(value))
        if key.startswith('tca_') and value in ('yes', 'no'):
            # Native-backed identities/jurisdictions are explicit fixtures.
            if key in facts:
                result = facts[key]
            elif key in TRIGGERS and key.startswith(('tca_has_available_', 'tca_is_available_')):
                result = evaluate_condition(TRIGGERS[key], facts)
            else:
                result = False
            return result == (value == 'yes')
        if key in ('house', 'dynasty'):
            return False  # cross-scope equality, absent for non-royal fixtures
        raise AssertionError(f'Unsupported condition: {key} {op} {value}')
    return all(item(*entry) for entry in seq)


def evaluate_value(name, facts):
    definition = VALUES[name]
    if not isinstance(definition, list):
        return number(definition)
    total, selected = 0, False
    for key, op, value in definition:
        if key == 'value':
            total = evaluate_value(value, facts) if value in VALUES else number(value)
        elif key == 'add':
            if isinstance(value, list):
                payload = dict((k, v) for k, o, v in value)
                total += evaluate_value(payload['value'], facts)
            else:
                total += evaluate_value(value, facts) if value in VALUES else number(value)
        elif key in ('if', 'else_if'):
            if key == 'if':
                selected = False
            payload = dict((k, v) for k, o, v in value)
            if not selected and evaluate_condition(payload['limit'], facts):
                total += number(payload['add'])
                selected = True
        else:
            raise AssertionError(f'Unsupported score operator: {key}')
    return total


def select_central(council):
    """Interpret the actual resolver's condition/selection branches."""
    seq = entries(body(EFFECTS, 'tca_resolve_central_judicial_authority_effect'))
    court = {'council': council}
    for key, op, branch in seq:
        payload = dict((k, v) for k, o, v in branch)
        if key == 'else':
            return 'emperor'
        if evaluate_condition(payload['limit'], court):
            pick = dict((k, v) for k, o, v in payload['random_councillor'])
            candidates = [person for person in council if evaluate_condition(pick['limit'], person)]
            assert len(candidates) == 1
            assert pick['save_scope_as'] == 'tca_approver'
            return candidates[0]['name']
    raise AssertionError('Missing imperial fallback')


class JudicialAuthorityTests(unittest.TestCase):
    def test_county_duchy_and_non_administrative_titles(self):
        for tier, admin, expected in [(2, True, 30), (3, True, 35), (3, False, 0), (2, False, 0)]:
            with self.subTest(tier=tier, admin=admin):
                facts = {'titles': [{'tier': tier, 'tca_is_local_administrative_title_trigger': admin}]}
                self.assertEqual(evaluate_value('tca_judicial_office_score', facts), expected)
        rule = dict((k, v) for k, o, v in TRIGGERS['tca_is_local_administrative_title_trigger'])
        self.assertEqual(rule['is_landless_type_title'], 'no')
        self.assertEqual(rule['is_noble_family_title'], 'no')
        holder = dict((k, v) for k, o, v in rule['holder'])
        self.assertEqual(holder['government_has_flag'], 'government_is_celestial')

    def test_high_office_and_imperial_close_kin_cannot_drop_below_central(self):
        for flag in ('tca_has_central_office_trigger', 'tca_has_regional_office_trigger', 'tca_is_emperor_first_degree_kin_trigger'):
            facts = {'is_lowborn': True, flag: True}
            self.assertGreaterEqual(evaluate_value('tca_judicial_authority_score', facts), number('tca_judicial_central_threshold'))

    def test_confucian_experience_boundaries(self):
        for xp, expected in [(0,1),(19,1),(20,3),(39,3),(40,6),(59,6),(60,12),(79,12),(80,20),(99,20),(100,30)]:
            self.assertEqual(evaluate_value('tca_judicial_confucian_score', {'traits': {'confucian_education'}, 'confucian_xp': xp}), expected)
        self.assertEqual(evaluate_value('tca_judicial_confucian_score', {}), 0)

    def test_piety_and_fame_are_nonlinear_and_capped_without_negative_discount(self):
        for item in ('piety', 'prestige'):
            for level, expected in [(-1,0),(0,0),(1,1),(2,3),(3,6),(4,10),(5,15),(8,15)]:
                self.assertEqual(evaluate_value(f'tca_judicial_{item}_score', {f'{item}_level': level}), expected)

    def test_family_and_exam_tiers_do_not_stack(self):
        facts = {'house': {'is_dominant_family': True, 'is_powerful_family': True}, 'tca_has_noble_family_trigger': True, 'is_lowborn': False}
        self.assertEqual(evaluate_value('tca_judicial_family_score', facts), 35)
        exams = {f'tgp_passed_{exam}_examination': True for exam in ('children','provincial','metropolitan','palace')}
        self.assertEqual(evaluate_value('tca_judicial_exam_score', exams), 15)

    def test_official_kin_takes_highest_relation_class(self):
        facts = {'official_relatives': {'tca_has_central_office_trigger','tca_has_regional_office_trigger','tca_has_state_office_trigger'}}
        self.assertEqual(evaluate_value('tca_judicial_official_kin_score', facts), 30)

    def test_sage_and_accumulated_non_official_standing(self):
        facts = {'is_lowborn': True, 'traits': {'confucian_education'}, 'confucian_xp': 100}
        self.assertEqual(evaluate_value('tca_judicial_authority_score', facts), 30)
        facts.update({'house': {'is_powerful_family': True}, 'tgp_passed_palace_examination': True, 'prestige_level': 4})
        self.assertEqual(evaluate_value('tca_judicial_authority_score', facts), 80)

    def test_direct_authority_boundaries_use_actual_predicate(self):
        # Merit25 + piety3 = 28; add fame1 = 29; piety6 = 31.
        for facts, expected in [
            ({'is_lowborn': True, 'merit_level': 9, 'piety_level': 2, 'prestige_level': 1}, True),
            ({'is_lowborn': True, 'traits': {'confucian_education'}, 'confucian_xp': 100}, False),
            ({'is_lowborn': True, 'house': {'is_powerful_family': True}, 'tgp_passed_palace_examination': True, 'traits': {'confucian_education'}, 'confucian_xp': 100, 'prestige_level': 4}, False),
        ]:
            for commissioner in (False, True):
                context = {'scope:recipient': dict(facts, **{'scope:actor': {'tca_is_judicial_commissioner_trigger': commissioner}})}
                score = evaluate_value('tca_judicial_authority_score', facts)
                direct = evaluate_condition(TRIGGERS['tca_judicial_direct_authorized_trigger'], context)
                self.assertEqual(direct, score < 30 or (commissioner and score < 80))
                if not commissioner:
                    self.assertEqual(direct, expected)

    def test_subordinate_jurisdiction_does_not_use_circuit_for_governor(self):
        branches = TRIGGERS['tca_judicial_actor_has_jurisdiction_trigger']
        alternative = next(v for k,o,v in branches if k == 'trigger_else')
        local = next(v for k,o,v in alternative if k == 'scope:actor')
        titles = next(v for k,o,v in local if k == 'any_held_title')
        target = next(v for k,o,v in titles if k == 'scope:recipient')
        self.assertIn(('tca_is_target_in_administrative_title_trigger','=', [('TITLE','=','prev')]), target)
        self.assertNotIn('CIRCUIT', repr(local))

    def test_central_fallback_order_and_unavailable_office(self):
        people = [{'name': name, 'position': position, 'is_alive': True} for name,position in [('justice','minister_justice'),('censor','councillor_spymaster'),('chancellor','councillor_chancellor')]]
        self.assertEqual(select_central(people), 'justice')
        people[0]['is_imprisoned'] = True
        self.assertEqual(select_central(people), 'censor')
        people[1]['is_alive'] = False
        self.assertEqual(select_central(people), 'chancellor')
        self.assertEqual(select_central([]), 'emperor')

    def test_saved_roles_and_custody_are_independent_of_approver(self):
        native = read('common/scripted_effects/tca_judicial_arrest_native_effects.txt')
        success = entries(body(native, 'tca_judicial_arrest_success_native_effect'))
        custodian = next(v for k,o,v in success if k == 'scope:puppet_or_actor' and ('save_scope_as','=','tca_custodian') in v)
        self.assertIn(('imprison_tyranny_effect','=','yes'), custodian)
        guard = next(v for k,o,v in success if k == 'if' and ('scope:recipient','=', [('tca_register_judicial_prisoner_effect','=','yes')]) in v)
        self.assertIn(('limit','=', [('scope:puppet_or_actor','=', [('tca_is_judicial_commissioner_trigger','=','yes')])]), guard)
        context = read('common/scripted_triggers/tca_judicial_arrest_triggers.txt')
        self.assertIn('tca_is_current_central_approver_trigger = { COURT = scope:actor.top_liege }', context)
        self.assertIn('tca_judicial_direct_authorized_trigger = no', context)

    def test_ordinary_and_diarch_arrests_have_no_office_bypass(self):
        override = read('common/scripted_triggers/zz_tca_judicial_imprison_permission_triggers.txt')
        rule = body(override, 'imprison_neutral_is_valid_showing_failures_only_triggers_trigger')
        self.assertNotIn('is_diarch_of_target', rule)
        self.assertIn('tca_uses_judicial_arrest_trigger', rule)

    def test_backend_roles_cannot_force_four_portrait_ui(self):
        self.assertNotIn('save_scope_as = secondary_actor', EFFECTS)
        self.assertNotIn('save_scope_as = secondary_recipient', EFFECTS)
        self.assertIn('save_scope_as = intermediary', EFFECTS)
        context = read('common/scripted_triggers/tca_judicial_arrest_triggers.txt')
        self.assertIn('save_temporary_scope_as = tca_checked_circuit', context)
        self.assertNotIn('save_temporary_scope_as = tca_circuit', context)

    def test_score_display_does_not_require_interaction_actor(self):
        self.assertNotIn('scope:puppet_or_actor', SCORES)
        for name in ('tca_has_official_relative_trigger','tca_is_emperor_first_degree_kin_trigger'):
            self.assertNotIn('scope:actor', repr(TRIGGERS[name]))
            self.assertNotIn('scope:puppet_or_actor', repr(TRIGGERS[name]))

    def test_invalid_reply_does_not_restore_missing_circuit(self):
        restore = entries(body(read('common/scripted_effects/tca_judicial_prison_effects.txt'), 'tca_restore_judicial_arrest_context_effect'))
        actor = [v for k,o,v in restore if k == 'scope:actor'][-1]
        branch = next(v for k,o,v in actor if k == 'if')
        limit = next(v for k,o,v in branch if k == 'limit')
        self.assertIn(('exists','=','scope:tca_circuit'), limit)
        context = entries(body(read('common/scripted_triggers/tca_judicial_arrest_triggers.txt'), 'tca_judicial_arrest_context_valid_trigger'))
        governor = next(v for k,o,v in context if k == 'trigger_else')
        def circuit_checks(seq):
            count = 0
            for k,o,v in seq:
                if not isinstance(v,list):
                    continue
                if ('tca_is_judicial_circuit_trigger','=','yes') in v:
                    self.assertIn(('NOT','=', [('has_variable','=','tca_judicial_disabled')]),v)
                    count += 1
                count += circuit_checks(v)
            return count
        self.assertEqual(circuit_checks(governor),2)

    def test_localization_keys_and_bom(self):
        keys=[]
        for language in ('simp_chinese','english'):
            path=ROOT/f'localization/{language}/tca_judicial_arrest_l_{language}.yml'
            self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf'))
            text=path.read_text(encoding='utf-8-sig')
            parsed=[line.strip().split(':',1)[0] for line in text.splitlines()[1:]]
            self.assertEqual(len(parsed),len(set(parsed)))
            keys.append(set(parsed))
            self.assertIn('[intermediary.GetTitledFirstName]', text)
            self.assertIn("[recipient.Custom('tca_judicial_approval_route')]", text)
        self.assertEqual(keys[0],keys[1])

if __name__ == '__main__':
    unittest.main()
