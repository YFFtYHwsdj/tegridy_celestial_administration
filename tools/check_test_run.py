#!/usr/bin/env python3
"""Check latest suite coverage plus mod-related errors throughout this game launch."""
import argparse
from collections import Counter
from pathlib import Path
import re
from check_upstream_overrides import definitions

ROOT = Path(__file__).resolve().parents[1]


def inspect_run(debug, errors, expected):
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
    # Startup failures matter even when no errors occur during the suite itself.
    findings = Counter()
    for entry in re.split(r'(?=\[\d{2}:\d{2}:\d{2}\])', errors):
        related = 'tca_' in entry or '提点刑狱司' in entry
        if not related:
            continue
        if 'Script system error' in entry:
            detail = re.search(r'Error: ([^\n]+)', entry)
            findings[detail.group(1) if detail else 'Script system error'] += 1
        elif 'Compiling source for tca_' in entry:
            findings['Judicial modifier compilation failure'] += 1
        elif 'has been queued twice' in entry:
            event = re.search(r'Event (tca_[\w.]+)', entry)
            if event:
                findings[f'{event.group(1)} queued twice'] += 1
        elif 'Key is missing localization:' in entry:
            findings['Judicial localization missing'] += 1
    issues.extend(f'Engine error ({count}): {label}' for label, count in findings.items())
    summary = Counter({kind: sum(count for (k, _), count in results.items() if k == kind)
                       for kind in ['BEGIN', 'PASS', 'FAIL', 'PRECONDITION_FAIL']})
    summary.update(checks)
    return issues, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs', type=Path, default=ROOT.parent.parent / 'logs')
    args = parser.parse_args()
    from build_test_events import parts
    expected = {}
    for source in (ROOT / 'tests').glob('tca_*_tests.txt'):
        for name, body in definitions(source.read_text(encoding='utf-8-sig')).items():
            expected[name] = sum(key == 'expect' for key, _ in parts(body))
    issues, counts = inspect_run((args.logs / 'debug.log').read_text(errors='replace'),
                                (args.logs / 'error.log').read_text(errors='replace'), expected)
    print(f'Expected {len(expected)} cases; observed {dict(counts)}')
    for issue in issues[:30]:
        print(issue)
    if len(issues) > 30:
        print(f'... {len(issues) - 30} further issues')
    print('NOT VERIFIED' if issues else 'OK: all current cases passed; no detected mod-related engine errors')
    return int(bool(issues))


if __name__ == '__main__':
    raise SystemExit(main())
