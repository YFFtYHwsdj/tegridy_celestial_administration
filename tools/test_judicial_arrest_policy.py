"""Static regression checks for payer, outcome routing and native cooldowns."""
from pathlib import Path
import unittest

from check_judicial_upstream import body, tokens

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8-sig')


def entries(seq):
    """Preserve repeated keys and distinguish participant scopes from nested blocks."""
    result, index = [], 0
    while index < len(seq):
        key, op, value = seq[index:index + 3]
        index += 3
        if value == '{':
            start, depth = index, 1
            while depth:
                depth += (seq[index] == '{') - (seq[index] == '}')
                index += 1
            value = entries(seq[start:index - 1])
        result.append((key, op, value))
    return result


class ArrestPolicyTests(unittest.TestCase):
    def setUp(self):
        script = read('common/character_interactions/tca_judicial_arrest_interactions.txt')
        self.request = entries(body(script, 'tca_request_imprison_interaction'))
        self.direct = entries(body(script, 'tca_judicial_imprison_interaction'))
        self.effects = read('common/scripted_effects/tca_judicial_prison_effects.txt')

    def test_probability_weights_and_native_cooldowns(self):
        self.assertIn(('ai_intermediary_maybe', '=', 'yes'), self.request)
        self.assertIn(('ai_maybe', '=', 'yes'), self.request)
        self.assertIn(('cooldown', '=', [('months', '=', '3')]), self.request)
        self.assertIn(('cooldown_against_recipient', '=', [('years', '=', '1')]), self.request)
        self.assertIn(('cooldown_against_recipient', '=', [('days', '=', '10')]), self.direct)
        score = next(v for k, o, v in self.request if k == 'ai_intermediary_accept')
        self.assertIn(('base', '=', '20'), score)
        legal = next(v for k, o, v in score if k == 'modifier')
        self.assertIn(('add', '=', '80'), legal)
        opinions = [v for k, o, v in score if k == 'opinion_modifier']
        self.assertIn(('multiplier', '=', '0.25'), opinions[0])
        self.assertIn(('multiplier', '=', '-0.25'), opinions[1])
        self.assertIn('value = -0.25', read('common/character_interactions/tca_judicial_arrest_interactions.txt'))

    def test_veto_charges_requester_and_sets_relationship_directions(self):
        veto = dict((k, v) for k, o, v in entries(body(self.effects, 'tca_judicial_arrest_veto_effect')))
        self.assertEqual(set(veto), {'scope:actor', 'scope:recipient'})
        actor = veto['scope:actor']
        self.assertIn(('add_prestige', '=', '-100'), actor)
        self.assertIn(('change_influence', '=', '-50'), actor)
        opinion = next(v for k, o, v in actor if k == 'add_opinion')
        self.assertIn(('target', '=', 'scope:intermediary'), opinion)
        target_opinions = [dict((k, v) for k, o, v in block) for key, op, block in veto['scope:recipient']]
        self.assertEqual(target_opinions, [
            {'target': 'scope:actor', 'modifier': 'tca_judicial_arrest_veto_requested_opinion'},
            {'target': 'scope:intermediary', 'modifier': 'tca_judicial_arrest_veto_protected_opinion'}])
        for key, amount in (('disappointed', '-15'), ('requested', '-10'), ('protected', '20')):
            definition = entries(body(read('common/opinion_modifiers/tca_judicial_arrest_opinions.txt'), f'tca_judicial_arrest_veto_{key}_opinion'))
            self.assertIn(('opinion', '=', amount), definition)
            self.assertIn(('years', '=', '3'), definition)
            self.assertIn(('stacking', '=', 'no'), definition)

    def test_penalty_only_on_valid_approval_veto_and_localized(self):
        callbacks = dict((k, v) for k, o, v in self.request if k.startswith('on_'))
        self.assertNotIn(('tca_judicial_arrest_veto_effect', '=', 'yes'), callbacks['on_decline'])
        decline = callbacks['on_intermediary_decline']
        conditional = next(v for k, o, v in decline if k == 'if')
        self.assertIn(('limit', '=', [('tca_judicial_arrest_still_valid_trigger', '=', 'yes')]), conditional)
        self.assertIn(('tca_judicial_arrest_veto_effect', '=', 'yes'), conditional)
        keys = []
        for language in ('simp_chinese', 'english'):
            text = read(f'localization/{language}/tca_judicial_arrest_l_{language}.yml')
            loc = dict(line.strip().split(':', 1) for line in text.splitlines()[1:])
            keys.append(set(loc))
            for key in ('disappointed', 'requested', 'protected'):
                self.assertIn(f'tca_judicial_arrest_veto_{key}_opinion', loc)
        self.assertEqual(keys[0], keys[1])


if __name__ == '__main__':
    unittest.main()
