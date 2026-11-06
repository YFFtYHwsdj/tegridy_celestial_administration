#!/usr/bin/env python3
"""比较两次测试运行的逐用例结果与断言计数；不启动游戏、不修改运行证据。

输入可以是 run 目录（读取其 verification.json）或 verification.json 文件。
`--ignore` 接受逗号分隔或重复的用例名，用于排除已确认的 flaky 项。
逐用例结果或计数有差异时退出码为 1，全部一致为 0。
"""
import argparse
import json
from pathlib import Path
import sys


def verification_path(path):
    """接受 run 目录或 verification.json 文件，统一返回证据文件路径。"""
    path = Path(path)
    if path.is_dir():
        return path / 'verification.json'
    return path


def load_verification(path):
    """读取冻结的 verification.json；缺少必要字段时明确失败。"""
    path = verification_path(path)
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'Invalid verification file: {path}')
    cases = data.get('cases')
    counts = data.get('counts', {})
    if not isinstance(cases, dict) or not isinstance(counts, dict):
        raise ValueError(f'Verification is missing cases/counts: {path}')
    return {'path': str(path), 'cases': dict(cases),
            'counts': {str(key): int(value) for key, value in counts.items()}}


def _parse_ignore(values):
    """把可重复的 --ignore 参数展开为逗号分隔的用例名集合。"""
    names = set()
    for value in values or ():
        names.update(part.strip() for part in value.split(',') if part.strip())
    return names


def compare(first, second, ignore=()):
    """比较两个 verification.json，返回逐用例差异、计数差异与总体结论。"""
    left = load_verification(first)
    right = load_verification(second)
    ignored = _parse_ignore(ignore)
    names = sorted(set(left['cases']) | set(right['cases']))
    differences, ignored_differences = [], []

    def state(cases, name):
        # 只出现在一次运行中的用例用 <missing> 标出，避免 None 与真实状态混淆。
        return cases.get(name, '<missing>')

    for name in names:
        if name in ignored:
            if state(left['cases'], name) != state(right['cases'], name):
                ignored_differences.append({'case': name,
                                            'first': state(left['cases'], name),
                                            'second': state(right['cases'], name)})
            continue
        if state(left['cases'], name) != state(right['cases'], name):
            differences.append({'case': name,
                                'first': state(left['cases'], name),
                                'second': state(right['cases'], name)})
    kinds = sorted(set(left['counts']) | set(right['counts']))
    count_differences = []
    counts = {}
    for kind in kinds:
        before = left['counts'].get(kind, 0)
        after = right['counts'].get(kind, 0)
        counts[kind] = {'first': before, 'second': after}
        if before != after:
            count_differences.append({'kind': kind, 'first': before, 'second': after})
    ok = not differences and not count_differences
    return {'format': 1, 'first': left['path'], 'second': right['path'],
            'ignore': sorted(ignored), 'cases': {'first': left['cases'],
                                                 'second': right['cases'],
                                                 'differences': differences,
                                                 'ignored': ignored_differences},
            'counts': counts, 'count_differences': count_differences,
            'differences': [f'{item["case"]}: {item["first"]} -> {item["second"]}'
                            for item in differences],
            'total_differences': len(differences) + len(count_differences),
            'ok': ok}


def format_report(result):
    """把比较结果渲染为人类可读差异表。"""
    lines = [f'比较 {result["first"]}', f'   与 {result["second"]}']
    if result['ignore']:
        lines.append(f'忽略用例：{", ".join(result["ignore"])}')
    differences = result['cases']['differences']
    if differences:
        lines.append('逐用例差异：')
        width = max(len(item['case']) for item in differences) + 2
        for item in differences:
            lines.append(f'  {item["case"]:<{width}}{str(item["first"]):<20}{item["second"]}')
    else:
        lines.append('逐用例结果一致')
    if result['count_differences']:
        lines.append('断言计数差异：')
        for item in result['count_differences']:
            lines.append(f'  {item["kind"]}: {item["first"]} -> {item["second"]}')
    else:
        lines.append('断言计数一致')
    if result['cases']['ignored']:
        lines.append(f'已忽略差异 {len(result["cases"]["ignored"])} 项')
    lines.append('OK: 两次运行可逐项对齐' if result['ok']
                 else f'FAILED: {result["total_differences"]} 处差异')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path, help='基线 run 目录或 verification.json')
    parser.add_argument('second', type=Path, help='对照 run 目录或 verification.json')
    parser.add_argument('--ignore', action='append', default=[],
                        help='忽略的用例名，可重复或逗号分隔')
    parser.add_argument('--json', type=Path, help='把完整比较结果写成 JSON')
    args = parser.parse_args(argv)
    try:
        result = compare(args.first, args.second, args.ignore)
    except (OSError, ValueError) as error:
        print(f'比较失败：{error}', file=sys.stderr)
        return 1
    print(format_report(result))
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
