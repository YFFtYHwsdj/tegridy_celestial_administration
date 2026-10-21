"""读取原生模块登记，选择测试范围；不生成测试或模拟游戏规则。"""
from pathlib import Path
import re
from check_upstream_overrides import definitions

ROOT = Path(__file__).resolve().parents[2]


def catalog_path(root):
    """递归定位唯一原生目录入口，兼容旧快照布局，拒绝重复定义。"""
    paths = list((Path(root) / 'common/scripted_effects').rglob('tca_test_catalog_effects.txt'))
    if len(paths) != 1:
        raise ValueError('Expected exactly one native test catalog')
    return paths[0]


def catalog(root=ROOT):
    """按正式即时／延迟调度顺序返回登记，核对入口及断言来源。"""
    from check_test_run import expected_cases
    root = Path(root)
    expected = expected_cases(root)
    entries = {}
    for path in (root / 'events').rglob('tca_*test*_events.txt'):
        for event, body in definitions(path.read_text(encoding='utf-8-sig')).items():
            text = ' '.join(body)
            match = re.search(r'TCA_TEST BEGIN ' + re.escape(event) + r' (tca_test_\w+)', text)
            if match:
                entries[event] = (match[1], 'add_character_flag = tca_test_delayed_case_active' in text)
    effects = {}
    rows = {}
    for path in sorted((root / 'common/scripted_effects').rglob('tca_test_modules_*_effects.txt')):
        for effect, body in definitions(path.read_text(encoding='utf-8-sig')).items():
            if effect in effects:
                raise ValueError(f'Duplicate module: {effect}')
            effects[effect] = []
            suite = effect.removeprefix('tca_test_module_').removesuffix('_effect')
            text = ' '.join(body)
            pattern = r'tca_test_visit_case_effect = \{ EVENT = (\S+) CASE = (\S+) DELAYED = (yes|no) \}'
            registrations = re.findall(pattern, text)
            if not registrations or text.count('tca_test_visit_case_effect') != len(registrations):
                raise ValueError(f'Invalid module registration: {effect}')
            for event, name, delayed in registrations:
                if name in rows or any(row['event'] == event for row in rows.values()):
                    raise ValueError(f'Duplicate case: {event}')
                if entries.get(event) != (name, delayed == 'yes'):
                    raise ValueError(f'Mismatched case: {event} {name}')
                rows[name] = dict(suite=suite, event=event, name=name,
                                  delayed=delayed == 'yes', checks=expected[name])
                effects[effect].append(rows[name])
    if {name: row['checks'] for name, row in rows.items()} != expected:
        raise ValueError('Native registration does not match test sources')
    text = ' '.join(definitions(catalog_path(root).read_text(encoding='utf-8-sig'))['tca_test_catalog_effect'])
    # 目录只有延迟分支和其他阶段分支；读取顺序与原生执行保持一致。
    delayed_text, immediate_text = text.split('else =', 1)
    result = []
    for segment, delayed in ((immediate_text, False), (delayed_text, True)):
        names = re.findall(r'(tca_test_module_\w+_effect) = yes', segment)
        if len(names) != len(set(names)) or any(name not in effects for name in names):
            raise ValueError('Invalid module dispatch')
        result.extend(row for name in names for row in effects[name] if row['delayed'] == delayed)
    if len(result) != len(rows) or len({row['event'] for row in result}) != len(rows):
        raise ValueError('Module dispatch does not cover registered cases')
    return result


def select_cases(root=ROOT, suites=(), cases=()):
    """合并模块及入口选择并去重；无选择代表完整回归。"""
    rows = catalog(root)
    selected = set()
    for suite in suites:
        matches = [row for row in rows if row['suite'] == suite or row['suite'].startswith(suite + '_')]
        if not matches:
            raise ValueError(f'Unknown suite: {suite}')
        selected.update(row['event'] for row in matches)
    for event in cases:
        if not any(row['event'] == event for row in rows):
            raise ValueError(f'Unknown native test entry: {event}')
        selected.add(event)
    return [row for row in rows if not selected or row['event'] in selected]


def validate_plan(plan, root=ROOT):
    """计划必须精确引用冻结登记；拒绝伪造计数、重复及不完整全组。"""
    rows = catalog(root)
    selected = plan.get('cases', [])
    if plan.get('scope') not in ('full', 'selection') or not selected:
        raise ValueError('Invalid selection plan')
    canonical = {row['event']: row for row in rows}
    if any(not isinstance(row, dict) or row != canonical.get(row.get('event')) for row in selected):
        raise ValueError('Selection does not match frozen native registration')
    events = [row['event'] for row in selected]
    if len(events) != len(set(events)) or selected != [row for row in rows if row['event'] in events]:
        raise ValueError('Selection order or uniqueness invalid')
    if plan['scope'] == 'full' and selected != rows:
        raise ValueError('Incomplete full regression plan')
    return {row['name']: row['checks'] for row in selected}
