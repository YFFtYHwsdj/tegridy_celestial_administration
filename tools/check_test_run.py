#!/usr/bin/env python3
"""核对最新测试组覆盖，以及本次游戏启动全程的模组相关错误。"""
import argparse
import json
from collections import Counter
from pathlib import Path
import re
from check_upstream_overrides import definitions

ROOT = Path(__file__).resolve().parents[1]


def expected_cases(root=ROOT):
    """读取直接维护的原生事件，绝不生成或运行游戏脚本。"""
    entries = {}
    checks = {}
    for path in sorted((root / 'events').glob('tca_*test*_events.txt')):
        for event, body in definitions(path.read_text(encoding='utf-8-sig')).items():
            if '.' in event and not 0 <= int(event.rsplit('.', 1)[1]) < 10000:
                raise ValueError(f'{path.name}: event ID must be below 10000: {event}')
            for index, token in enumerate(body[:-2]):
                if token != 'debug_log' or body[index + 1] != '=':
                    continue
                message = body[index + 2].strip('"')
                begin = re.fullmatch(r'TCA_TEST BEGIN (\S+) (tca_test_\S+)', message)
                check = re.fullmatch(r'TCA_TEST CHECK_PASS (tca_test_\S+) (\d+)', message)
                if begin:
                    entry, name = begin.groups()
                    if entry != event or name in entries:
                        raise ValueError(f'{path.name}: duplicate or mismatched BEGIN {name}')
                    entries[name] = event
                if check:
                    name, step = check.groups()
                    if int(step) in checks.setdefault(name, set()):
                        raise ValueError(f'{name}: duplicate assertion {step}')
                    checks[name].add(int(step))
    if not entries or entries.keys() != checks.keys():
        raise ValueError('Test entries and assertion names must be nonempty and match')
    for name, steps in checks.items():
        if steps != set(range(1, len(steps) + 1)):
            raise ValueError(f'{name}: assertion numbers must be consecutive')
    return {name: len(checks[name]) for name in entries}


def inspect_engine_errors(errors):
    """纳入已审阅的整文件 GUI 覆盖，即使错误中没有 tca_ 标识。"""
    registry = json.loads((ROOT / 'tools/upstream_overrides.json').read_text())
    owned_paths = {entry['mod'] for section in ('overrides', 'file_overrides')
                   for entry in registry.get(section, [])}
    owned_loc_keys = {key for entry in registry.get('file_overrides', [])
                      for key in entry.get('diagnostic_localization_keys', [])}
    # 即使测试运行期间没有错误，启动阶段失败也必须计入。
    findings = Counter()
    for entry in re.split(r'(?=\[\d{2}:\d{2}:\d{2}\])', errors):
        if 'is not a valid event ID, has to be < 10000' in entry:
            findings['Invalid numeric event ID'] += 1
            continue
        loc_error = re.search(r"Data error in loc string '([^']+)'", entry)
        related = ('tca_' in entry or '提点刑狱司' in entry or
                   any(path in entry for path in owned_paths) or
                   bool(loc_error and loc_error[1] in owned_loc_keys))
        if not related:
            continue
        if 'Script system error' in entry:
            detail = re.search(r'Error: ([^\n]+)', entry)
            findings[detail.group(1) if detail else 'Script system error'] += 1
        elif 'Compiling source for tca_' in entry:
            findings['Judicial modifier compilation failure'] += 1
        elif "There is more than one 'effect' defined" in entry:
            findings['TCA duplicate on_action effect'] += 1
        elif any(message in entry for message in ('Unexpected token:', 'Unknown trigger:', 'Unknown effect:')):
            findings['TCA script parsing failure'] += 1
        elif 'can not be used in event target links' in entry:
            findings['TCA invalid event target scope link'] += 1
        elif 'Value of wrong type' in entry:
            findings['TCA invalid script value type'] += 1
        elif any(message in entry for message in (
                'is used but is never set', 'is set but is never used',
                'is orphaned', 'is scripted as an orphan, but has callers')):
            # 保留标识以便定位诊断。为兼容用途刻意保留的事件
            # 应声明 orphan = yes，
            # 因此本就不会产生孤立事件诊断。
            detail = entry.split(']: ', 1)[-1].strip()
            findings[detail] += 1
        elif 'should be in utf8-bom encoding' in entry:
            findings['TCA script encoding failure'] += 1
        elif 'Exclusive send options should at least be two' in entry:
            findings['TCA interaction send-option configuration failure'] += 1
        elif 'has been queued twice' in entry:
            event = re.search(r'Event (tca_[\w.]+)', entry)
            if event:
                findings[f'{event.group(1)} queued twice'] += 1
        elif 'Key is missing localization:' in entry:
            findings['Judicial localization missing'] += 1
        elif 'Data error in loc string' in entry:
            findings['TCA localization evaluation failure'] += 1
        elif any(message in entry for message in (
                'Failed to find type', 'Could not find promote',
                'Failed converting statement', 'Could not find data system function')):
            findings['TCA localization data binding failure'] += 1
    return [f'Engine error ({count}): {label}' for label, count in findings.items()]


def inspect_run(debug, errors, expected, strict_title_heir=False):
    lines = debug.splitlines()
    starts = [i for i, line in enumerate(lines) if 'TCA_TEST SUITE_DISPATCH' in line]
    if not starts:
        return ['No suite dispatch found'], Counter()
    results = Counter()
    checks = Counter()
    assertion_results = Counter()
    for line in lines[starts[-1]:]:
        match = re.search(r'TCA_TEST (BEGIN|PASS|FAIL|PRECONDITION_FAIL|CHECK_PASS|CHECK_FAIL) (\S+)(?: (\S+))?', line)
        if not match:
            continue
        kind, first, second = match.groups()
        if kind.startswith('CHECK_'):
            checks[kind] += 1
            assertion_results[kind, first, second] += 1
        else:
            name = second if kind == 'BEGIN' else first
            results[kind, name] += 1
    issues = []
    if strict_title_heir and any('native Tongpan appointment differs from pre-death title preview head' in line for line in lines[starts[-1]:]):
        issues.append('Strict title succession failed: appointed officer differs from preview head')
    if any('TCA_TEST SUITE_ABORTED' in line for line in lines[starts[-1]:]):
        issues.append('Suite aborted: test environment invalid')
    # 较新的观察者尝试不能静默继承旧测试组的通过结果。
    observer_attempts = [line for line in lines[starts[-1] + 1:]
                         if 'TCA_TEST OBSERVER_ENTRY_REJECTED' in line
                         or 'TCA_TEST OBSERVER_ENTRY_DISPATCH' in line]
    if observer_attempts:
        if 'OBSERVER_ENTRY_REJECTED' in observer_attempts[-1]:
            issues.append('Latest observer entry rejected: ' + observer_attempts[-1].split('OBSERVER_ENTRY_REJECTED', 1)[1].strip())
        else:
            issues.append('No suite dispatch after latest observer entry')
    for name in sorted(expected):
        if results['BEGIN', name] != 1 or results['PASS', name] != 1:
            issues.append(f'{name}: begin={results["BEGIN", name]}, pass={results["PASS", name]}')
    if isinstance(expected, dict):
        for name, total in expected.items():
            for step in range(1, total + 1):
                if assertion_results['CHECK_PASS', name, str(step)] != 1:
                    issues.append(f'{name}: assertion {step} missing or duplicated')
        for (kind, name, step), count in assertion_results.items():
            if name not in expected or step not in {str(i) for i in range(1, expected.get(name, 0) + 1)}:
                issues.append(f'Unexpected assertion: {kind} {name} {step}')
    for (kind, name), count in results.items():
        if name not in expected or kind in {'FAIL', 'PRECONDITION_FAIL'}:
            issues.append(f'{kind} {name}: {count}')
    if checks['CHECK_FAIL']:
        issues.append(f'Failed assertions: {checks["CHECK_FAIL"]}')
    if not any('TCA_TEST SUITE_ALL_PASSED' in line for line in lines[starts[-1]:]):
        issues.append('No SUITE_ALL_PASSED completion')
    issues.extend(inspect_engine_errors(errors))
    summary = Counter({kind: sum(count for (k, _), count in results.items() if k == kind)
                       for kind in ['BEGIN', 'PASS', 'FAIL', 'PRECONDITION_FAIL']})
    summary.update(checks)
    return issues, summary


def selected_case_expectations(entry, root=ROOT):
    all_cases = expected_cases(root)
    for path in sorted((root / 'events').glob('tca_*test*_events.txt')):
        for event, body in definitions(path.read_text(encoding='utf-8-sig')).items():
            if event == entry:
                match = re.search(r'TCA_TEST BEGIN ' + re.escape(entry) + r' (tca_test_\S+)', ' '.join(body))
                if match:
                    name = match[1].rstrip('"')
                    return {name: all_cases[name]}
    raise ValueError(f'Unknown native test entry: {entry}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs', type=Path, default=ROOT.parent.parent / 'logs')
    parser.add_argument('--case', help='verify only this maintained native case')
    parser.add_argument('--strict-title-heir', action='store_true', help='fail when native appointment differs from preview head')
    parser.add_argument('--source-root', type=Path, help='exact frozen mod source used by this run')
    args = parser.parse_args()
    source = args.source_root or (args.logs.parent / 'mod/tca_main')
    if not source.is_dir():
        source = ROOT
        print('WARNING: no source snapshot; checking current case counts only')
    expected = selected_case_expectations(args.case, source) if args.case else expected_cases(source)
    issues, counts = inspect_run((args.logs / 'debug.log').read_text(errors='replace'),
                                (args.logs / 'error.log').read_text(errors='replace'), expected, args.strict_title_heir)
    if (args.logs.parent / 'source_manifest.json').is_file():
        from run_game_tests import verify_snapshot
        issues.extend(verify_snapshot(args.logs.parent))
        if source.resolve() != (args.logs.parent / 'mod/tca_main').resolve():
            issues.append('Selected source does not match sealed runtime snapshot')
    print(f'Expected {len(expected)} cases; observed {dict(counts)}')
    for issue in issues[:30]:
        print(issue)
    if len(issues) > 30:
        print(f'... {len(issues) - 30} further issues')
    scope = 'selected case' if args.case else 'all current cases'
    print('NOT VERIFIED' if issues else f'OK: {scope} passed; no detected mod-related engine errors')
    return int(bool(issues))


if __name__ == '__main__':
    raise SystemExit(main())
