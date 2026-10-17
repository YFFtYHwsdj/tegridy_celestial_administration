#!/usr/bin/env python3
"""Build office assets from vanilla landed titles; never generate test events/baselines."""
import argparse
from pathlib import Path
import re
from check_upstream_overrides import tokens

ROOT = Path(__file__).resolve().parents[1]
# This title ID collides with a Workshop gte_contest.1013.bold.failure in Jomini localization.
TITLE_NAME_KEYS = {'c_tca_tongpan_yingzhou_2': 'tca_tongpan_name_yingzhou_2'}
DEFAULT_GAME = Path.home() / 'Library/Application Support/Steam/steamapps/common/Crusader Kings III/game'


def counties_in(text):
    seq = tokens(text)
    result = set()
    for i in range(len(seq) - 2):
        if not re.fullmatch(r'c_[a-zA-Z0-9_]+', seq[i]) or seq[i + 1:i + 3] != ['=', '{']:
            continue
        depth, end = 1, i + 3
        while end < len(seq) and depth:
            depth += (seq[end] == '{') - (seq[end] == '}')
            end += 1
        if depth:
            raise ValueError('unclosed county ' + seq[i])
        if 'province' in seq[i + 3:end - 1]:
            result.add(seq[i])
    return result


def write_assets(game_dir, mod_dir, reserve_count):
    if not 1 <= reserve_count <= 4096:
        raise ValueError('reserve count must be 1..4096')
    counties = set()
    for path in sorted((game_dir / 'common/landed_titles').glob('*.txt')):
        if not path.name.startswith('_'):
            counties.update(counties_in(path.read_text(encoding='utf-8-sig')))
    if not counties:
        raise ValueError('no vanilla counties found')
    counties = sorted(counties)
    titles = ['# Generated office assets. Run tools/build_tongpan_catalog.py to rebuild.']
    effects = ['# Generated fixed lookup and reserve inventory; no appointments or tests.',
               'tca_initialize_tongpan_catalog_effect = {',
               '    if = {', '        limit = { NOT = { has_global_variable = tca_tongpan_catalog_v1 } }']
    loc = {'english': ['l_english:'], 'simp_chinese': ['l_simp_chinese:']}
    for county in counties:
        office = 'c_tca_tongpan_' + county[2:]
        titles.append(f'{office} = {{ capital = {county} color = {{ 110 125 145 }} landless = yes allow_domicile = no no_automatic_claims = yes definite_form = yes can_be_named_after_dynasty = no destroy_on_succession = no delete_on_destroy = no }}')
        effects.append(f'        title:{county} ?= {{ set_variable = {{ name = tca_tongpan_static_office value = title:{office} }} }}')
        name_key = TITLE_NAME_KEYS.get(office, office)
        loc['english'].append(f' {name_key}: "[GetTitleByKey(\'{county}\').GetNameNoTierNoTooltip] Tongpan Office"')
        loc['simp_chinese'].append(f' {name_key}: "[GetTitleByKey(\'{county}\').GetNameNoTierNoTooltip]通判司"')
    for number in range(1, reserve_count + 1):
        office = f'c_tca_tongpan_reserve_{number:03}'
        titles.append(f'{office} = {{ capital = c_bianzhou color = {{ 110 125 145 }} landless = yes allow_domicile = no no_automatic_claims = yes definite_form = yes can_be_named_after_dynasty = no destroy_on_succession = no delete_on_destroy = no }}')
        effects.append(f'        title:{office} = {{ add_to_global_variable_list = {{ name = tca_tongpan_reserve target = this }} }}')
        loc['english'].append(f' {office}: "Tongpan Office"')
        loc['simp_chinese'].append(f' {office}: "通判司"')
    effects += ['        set_global_variable = { name = tca_tongpan_catalog_v1 value = yes }', '    }', '}']
    # Explicit title lists keep office names out of ordinary county flavourization.
    office_ids = [line.split(' = ', 1)[0] for line in titles[1:]]
    flavors = ['# Generated holder names for fixed offices and the reserve pool.']
    for gender in ('male', 'female'):
        flavors += [f'tca_tongpan_holder_{gender} = {{', '    type = character',
                    f'    gender = {gender}', '    special = holder', '    tier = county',
                    '    priority = 500', '    governments = { celestial_government }',
                    '    titles = {', *['        ' + office for office in office_ids], '    }',
                    '    flavourization_rules = { only_vassals = yes only_holder = yes spouse_takes_title = no top_liege = no }', '}']
    effects += ['tca_repair_tongpan_name_effect = {']
    for office, name_key in TITLE_NAME_KEYS.items():
        if office in office_ids:
            effects.append(f'    if = {{ limit = {{ this = title:{office} }} set_title_name = {name_key} }}')
    effects += ['}']
    outputs = {
        'common/landed_titles/tca_tongpan_catalog.txt': titles,
        'common/flavorization/tca_tongpan_holder_flavorization.txt': flavors,
        'common/scripted_effects/tca_tongpan_catalog_effects.txt': effects,
        **{f'localization/{lang}/tca_tongpan_catalog_l_{lang}.yml': lines for lang, lines in loc.items()},
    }
    for name, lines in outputs.items():
        path = mod_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8-sig')
    return len(counties)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, default=DEFAULT_GAME)
    parser.add_argument('--reserve-count', type=int, default=128)
    args = parser.parse_args()
    count = write_assets(args.game_dir, ROOT, args.reserve_count)
    print(f'Wrote {count} fixed county offices and {args.reserve_count} reserve offices; no tests or baselines changed.')


if __name__ == '__main__':
    main()
