#!/usr/bin/env python3
"""Compile all TCA native test sources into opt-in event tests and one dispatcher."""
from pathlib import Path
import argparse
from check_upstream_overrides import definitions

ROOT = Path(__file__).resolve().parents[1]


def parts(body):
    i = 1
    while i < len(body) - 1:
        key = body[i]
        if body[i + 1] != '=':
            raise ValueError(f'Invalid test field: {key}')
        start = i + 2
        end = start + 1
        if body[start] == '{':
            depth = 1
            while depth:
                if body[end] == '{': depth += 1
                elif body[end] == '}': depth -= 1
                end += 1
        yield key, body[start:end]
        i = end


def block(seq):
    return ' '.join(seq[1:-1])


def increment(kind):
    return ('if = { limit = { has_character_flag = tca_test_suite_running } '
            f'change_variable = {{ name = tca_test_suite_{kind} add = 1 }} }}')


def render():
    output = {}
    dispatch = []
    delayed = []
    names = set()
    namespaces = set()
    for source in sorted((ROOT / 'tests').glob('tca_*_tests.txt')):
        namespace = source.stem.removesuffix('_tests') + '_test'
        if source.name == 'tca_court_system_tests.txt':
            namespace = 'tca_court_test'  # Preserve already-used individual IDs.
        if namespace in namespaces or namespace == 'tca_tests':
            raise ValueError(f'Duplicate or reserved namespace: {namespace}')
        namespaces.add(namespace)
        cases = definitions(source.read_text(encoding='utf-8-sig'))
        if not cases or len(cases) >= 100:
            raise ValueError(f'{source.name}: require 1-99 cases per source')
        lines = [f'# Generated from tests/{source.name} by tools/build_test_events.py.',
                 '# Explicit debug entry only; no automatic gameplay caller.',
                 f'namespace = {namespace}']
        for number, (name, body) in enumerate(cases.items(), 1):
            if name in names or not name.startswith('tca_test_'):
                raise ValueError(f'Duplicate or non-TCA test name: {name}')
            names.add(name)
            reserved = {'tca_test_suite_running', 'tca_test_case_failed', 'tca_test_delayed_case_active'}
            if any(token.startswith('tca_test_suite_') or token in reserved for token in body):
                raise ValueError(f'{name}: framework bookkeeping is reserved')
            fields = list(parts(body))
            if len(fields) < 3 or fields[0][0] != 'name' or fields[1][0] != 'assert':
                raise ValueError(f'{name}: require name, leading assert, then effect/expect')
            if not any(key == 'expect' for key, _ in fields):
                raise ValueError(f'{name}: missing expect')
            event = f'{namespace}.{number}'
            waits = [value for key, value in fields if key == 'wait_days']
            for value in waits:
                if len(value) != 1 or not value[0].isdigit() or not 1 <= int(value[0]) <= 30:
                    raise ValueError(f'{name}: wait_days must be an integer from 1 to 30')
            if len(waits) > 98:
                raise ValueError(f'{name}: too many waits')
            allowed = {'name', 'assert', 'effect', 'expect', 'wait_days'}
            if any(key not in allowed for key, _ in fields):
                raise ValueError(f'{name}: unsupported field')
            if waits:
                delayed.append(event)
            else:
                dispatch.append(event)
            entry_start = len(lines)
            lines.extend([f'\n{event} = {{', '    type = character_event', '    hidden = yes',
                          '    immediate = {', f'        debug_log = "TCA_TEST BEGIN {event} {name}"',
                          '        remove_character_flag = tca_test_case_failed', '        if = {',
                          f'            limit = {{ {block(fields[1][1])} }}'])
            step = 0
            segment = 0
            for key, value in fields[2:]:
                if key == 'effect':
                    lines.append(f'            {block(value)}')
                elif key == 'wait_days':
                    segment += 1
                    continuation = f'{namespace}.{1000 + number * 100 + segment}'
                    lines.extend(['            add_character_flag = tca_test_delayed_case_active', f'            debug_log = "TCA_TEST WAIT {name} {value[0]} days"',
                                  f'            trigger_event = {{ id = {continuation} days = {value[0]} }}',
                                  '        }', '        else = {',
                                  f'            debug_log = "TCA_TEST PRECONDITION_FAIL {name}"',
                                  '            '+increment('skipped'),
                                  '            remove_character_flag = tca_test_case_failed',
                                  '            remove_character_flag = tca_test_delayed_case_active',
                                  '            tca_test_continue_delayed_effect = yes',
                                  '        }', '    }', '}',
                                  f'\n{continuation} = {{', '    type = character_event', '    hidden = yes',
                                  '    immediate = {', '        if = {', '            limit = { always = yes }'])
                elif key == 'expect':
                    step += 1
                    lines.extend(['            if = {', f'                limit = {{ {block(value)} }}',
                                  f'                debug_log = "TCA_TEST CHECK_PASS {name} {step}"',
                                  '            }', '            else = {',
                                  '                add_character_flag = tca_test_case_failed',
                                  f'                debug_log = "TCA_TEST CHECK_FAIL {name} {step}"',
                                  '            }'])
                else:
                    raise ValueError(f'{name}: unsupported field {key}')
            lines.extend(['            if = {', '                limit = { has_character_flag = tca_test_case_failed }',
                          f'                debug_log = "TCA_TEST FAIL {name}"', '                '+increment('failed'),
                          '            }', '            else = {', f'                debug_log = "TCA_TEST PASS {name}"',
                          '                '+increment('passed'), '            }', '        }', '        else = {',
                          f'            debug_log = "TCA_TEST PRECONDITION_FAIL {name}"',
                          '            '+increment('skipped'), '        }',
                          '        remove_character_flag = tca_test_case_failed',
                          '        remove_character_flag = tca_test_delayed_case_active' if waits else '',
                          '        tca_test_continue_delayed_effect = yes' if waits else '', '    }', '}'])
            entry = '\n'.join(lines[entry_start:])
            entry = entry.replace('    immediate = {\n', '    immediate = {\n        if = { limit = { has_character_flag = tca_test_delayed_case_active } debug_log = "TCA_TEST CASE_BUSY" }\n        else = {\n', 1)
            entry = entry.replace('\n    }\n}', '\n        }\n    }\n}', 1)
            lines[entry_start:] = entry.splitlines()
        if namespace == 'tca_court_test':
            lines.extend(['\ntca_court_test.100 = {', '    type = character_event', '    hidden = yes',
                          '    immediate = { trigger_event = tca_tests.1 }', '}'])
        output[ROOT / 'events' / f'{namespace}_events.txt'] = '\n'.join(line.rstrip() for line in lines) + '\n'
    if not dispatch and not delayed:
        raise ValueError('No tests/tca_*_tests.txt cases found')
    total = len(dispatch) + len(delayed)
    lines = ['# Generated by tools/build_test_events.py; all discovered TCA test cases.',
             'namespace = tca_tests', '\ntca_tests.1 = {', '    type = character_event', '    hidden = yes',
             '    immediate = {', '        if = {',
             '            limit = { OR = { has_character_flag = tca_test_suite_running has_character_flag = tca_test_delayed_case_active } }',
             '            debug_log = "TCA_TEST SUITE_BUSY"',
             '        }', '        else = {', '        save_scope_as = tca_test_reporter',
             f'        set_variable = {{ name = tca_test_suite_expected value = {total} }}',
             '        set_variable = { name = tca_test_suite_passed value = 0 }',
             '        set_variable = { name = tca_test_suite_failed value = 0 }',
             '        set_variable = { name = tca_test_suite_skipped value = 0 }',
             '        if = {', '            limit = { debug_only = yes }',
             '            add_character_flag = tca_test_suite_running',
             f'            debug_log = "TCA_TEST SUITE_DISPATCH {total} cases"']
    lines.extend(f'            trigger_event = {event}' for event in dispatch)
    lines.extend(['            tca_test_notify_waiting_effect = yes' if delayed else '',
                  '            trigger_event = tca_tests.1000' if delayed else '            trigger_event = tca_tests.2',
                  '        }', '        else = {',
                  f'            set_variable = {{ name = tca_test_suite_skipped value = {total} }}',
                  '            debug_log = "TCA_TEST SUITE_PRECONDITION_FAIL debug mode required"',
                  '            tca_test_notify_results_effect = yes',
                  '        }', '        }', '    }', '}'])
    lines.extend(['\ntca_tests.2 = {', '    type = character_event', '    hidden = yes',
                  '    immediate = {', '        remove_character_flag = tca_test_suite_running',
                  '        remove_variable = tca_test_suite_delayed_next',
                  '        tca_test_notify_results_effect = yes', '    }', '}'])
    for index, event in enumerate(delayed):
        next_event = f'tca_tests.{1001 + index}' if index + 1 < len(delayed) else 'tca_tests.2'
        lines.extend([f'\ntca_tests.{1000 + index} = {{', '    type = character_event', '    hidden = yes',
                      '    immediate = {', f'        set_variable = {{ name = tca_test_suite_delayed_next value = {index} }}',
                      f'        trigger_event = {event}', '    }', '}'])
    # Generated control effect. Business tests may never modify suite bookkeeping.
    effect_lines = ['# Generated by tools/build_test_events.py.', 'tca_test_continue_delayed_effect = {',
                    '    if = {', '        limit = { has_character_flag = tca_test_suite_running has_variable = tca_test_suite_delayed_next }']
    for index, event in enumerate(delayed):
        next_event = f'tca_tests.{1001 + index}' if index + 1 < len(delayed) else 'tca_tests.2'
        effect_lines.extend(['        if = {' if index == 0 else '        else_if = {',
                             f'            limit = {{ var:tca_test_suite_delayed_next = {index} }}',
                             f'            trigger_event = {next_event}', '        }'])
    effect_lines.extend(['    }', '}'])
    output[ROOT / 'common/scripted_effects/tca_test_delayed_dispatch_effects.txt'] = '\n'.join(effect_lines) + '\n'
    output[ROOT / 'events/tca_tests_events.txt'] = '\n'.join(line.rstrip() for line in lines) + '\n'
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Verify generated files without writing')
    args = parser.parse_args()
    output = render()
    for path, text in output.items():
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8-sig') != text:
                raise SystemExit(f'{path.name} is stale; run tools/build_test_events.py')
        else:
            path.write_text(text, encoding='utf-8-sig')
    print(f'OK: {len(output) - 2} test groups and global dispatcher'+(' match sources' if args.check else ' generated'))


if __name__ == '__main__':
    main()
