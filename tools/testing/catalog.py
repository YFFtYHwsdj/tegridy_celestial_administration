"""读取原生模块登记，选择测试范围；不生成测试或模拟游戏规则。"""
from pathlib import Path
import re
from check_upstream_overrides import definitions

ROOT = Path(__file__).resolve().parents[2]
# 普通登记顺序为 EVENT CASE DELAYED GROUP EXCLUSIVE；独立入口另带WORLD。
# GROUP/EXCLUSIVE 是单实例并行（lane）元数据；迁移窗口内容忍旧式三参数行，
# 由 verify_registration_metadata()/check_test_parallel.py 强制要求显式携带。
_REGISTRATION = re.compile(
    r'tca_test_visit_(independent_)?case_effect = \{ EVENT = (\S+) CASE = (\S+) DELAYED = (yes|no)'
    r'(?: GROUP = (\S+) EXCLUSIVE = (yes|no))?(?: WORLD = (\S+))? \}')
_GROUP = re.compile(r'[a-z0-9_]+')


def catalog_path(root):
    """递归定位唯一原生目录入口，兼容旧快照布局，拒绝重复定义。"""
    paths = list((Path(root) / 'common/scripted_effects').rglob('tca_test_catalog_effects.txt'))
    if len(paths) != 1:
        raise ValueError('Expected exactly one native test catalog')
    return paths[0]


def event_namespace(event):
    """事件 ID 前缀即测试命名空间，也是迁移期 GROUP 的默认值。"""
    return event.rsplit('.', 1)[0]


def _parse_modules(root):
    """解析模块登记文件，返回 {模块效果名: [登记行]} 与按文件顺序的登记列表。

    每条登记行同时保留声明的 GROUP/EXCLUSIVE 与实际生效值：
    GROUP 缺省按事件命名空间推导、EXCLUSIVE 缺省按 no 处理，便于工具层先于
    events/common 迁移联调；是否携带显式元数据由 `declared` 标记。
    """
    root = Path(root)
    effects = {}
    rows = []
    names = set()
    events = set()
    namespace_groups = {}
    for path in sorted((root / 'common/scripted_effects').rglob('tca_test_modules_*_effects.txt')):
        for effect, body in definitions(path.read_text(encoding='utf-8-sig')).items():
            if effect in effects:
                raise ValueError(f'Duplicate module: {effect}')
            effects[effect] = []
            suite = effect.removeprefix('tca_test_module_').removesuffix('_effect')
            text = ' '.join(body)
            registrations = _REGISTRATION.findall(text)
            if not registrations or len(re.findall(r'tca_test_visit_(?:independent_)?case_effect', text)) != len(registrations):
                raise ValueError(f'Invalid module registration: {effect}')
            for independent, event, name, delayed, group, exclusive, world in registrations:
                if bool(independent) != bool(world) or (world and (not _GROUP.fullmatch(world) or world == 'shared')):
                    raise ValueError(f'Invalid independent WORLD in {effect}: {world}')
                # 未匹配的可选分组在 findall 中返回空字符串，按缺省处理。
                group = group or None
                exclusive = exclusive or None
                if group is not None and not _GROUP.fullmatch(group):
                    raise ValueError(f'Invalid GROUP in {effect}: {group}')
                namespace = event_namespace(event)
                effective = group or namespace
                # 同一测试文件（命名空间）必须归入同一 lane；跨命名空间合并 GROUP 允许。
                if namespace_groups.setdefault(namespace, effective) != effective:
                    raise ValueError(f'Inconsistent GROUP in {namespace}: '
                                     f'{namespace_groups[namespace]} != {effective}')
                if name in names or event in events:
                    raise ValueError(f'Duplicate case: {event}')
                names.add(name)
                events.add(event)
                row = dict(suite=suite, event=event, name=name, delayed=delayed == 'yes',
                           group=effective, exclusive=exclusive == 'yes',
                           declared=group is not None, source=path.name, world=world or 'shared')
                effects[effect].append(row)
                rows.append(row)
    return effects, rows


def registration_rows(root=ROOT):
    """逐条返回模块登记与 lane 元数据；供并行静态检查器复用同一解析口径。

    解析保持宽容（缺 GROUP 时按命名空间推导），以便检查器报告待迁移清单；
    catalog()/run_game_tests 则在迁移完成后强制要求显式元数据。
    """
    return list(_parse_modules(root)[1])


def verify_registration_metadata(root=ROOT):
    """返回缺少显式 GROUP/EXCLUSIVE 的登记行；并行检查器据此提示一次性迁移。"""
    return [row for row in registration_rows(root) if not row['declared']]


def parallel_metadata(root=ROOT):
    """返回 {用例名: {'group': 并发组, 'exclusive': 是否独占}}，不改变计划格式。"""
    return {row['name']: {'group': row['group'], 'exclusive': row['exclusive']}
            for row in registration_rows(root)}


def catalog(root=ROOT):
    """按正式即时／延迟调度顺序返回登记，核对入口及断言来源。

    返回字段固定为 suite/event/name/delayed/checks，不加元数据字段，
    以保证 selection.json 与冻结计划格式不变。
    延迟属性只以登记行 DELAYED 为来源；用例体是否调用 lane 结束效果的
    一致性由 check_test_parallel.py 校验，避免依赖迁移期的旧文本。
    """
    from check_test_run import expected_cases
    root = Path(root)
    expected = expected_cases(root)
    entries = {}
    for path in (root / 'events').rglob('tca_*test*_events.txt'):
        for event, body in definitions(path.read_text(encoding='utf-8-sig')).items():
            text = ' '.join(body)
            match = re.search(r'TCA_TEST BEGIN ' + re.escape(event) + r' (tca_test_\w+)', text)
            if match:
                entries[event] = match[1]
    parsed, raw = _parse_modules(root)
    legacy = [row for row in raw if not row['declared']]
    if legacy:
        names = '、'.join(row['event'] for row in legacy[:5])
        raise ValueError('Test registration is missing GROUP/EXCLUSIVE; complete the lane '
                         f'migration first (e.g. {names})')
    effects = {}
    for effect, raw_rows in parsed.items():
        effects[effect] = []
        for row in raw_rows:
            event, name = row['event'], row['name']
            if entries.get(event) != name:
                raise ValueError(f'Mismatched case: {event} {name}')
            effects[effect].append(dict(suite=row['suite'], event=event, name=name,
                                        delayed=row['delayed'], checks=expected[name]))
    if {row['name']: row['checks'] for module in effects.values() for row in module} != expected:
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
    if len(result) != len(raw) or len({row['event'] for row in result}) != len(raw):
        raise ValueError('Module dispatch does not cover registered cases')
    return result


def world_metadata(root=ROOT):
    """从原生登记读取独立测试局标识；shared代表普通共享局。"""
    return {row['name']: row['world'] for row in registration_rows(root)}


def partition_worlds(rows, root=ROOT, isolate_suite=False):
    """按强制世界边界拆局；相同WORLD可共局，suite选项只会进一步拆分。"""
    worlds = world_metadata(root)
    batches = {}
    for row in rows:
        key = (worlds[row['name']], row['suite'] if isolate_suite else None)
        batches.setdefault(key, []).append(row)
    return list(batches.values())


def select_cases(root=ROOT, suites=(), cases=(), include_independent=False):
    """合并显式选择；无选择默认仅普通回归，独立局须选择或显式纳入。"""
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
    worlds = world_metadata(root)
    return [row for row in rows if row['event'] in selected or
            (not suites and not cases and (include_independent or worlds[row['name']] == 'shared'))]


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
    worlds = world_metadata(root)
    if len({worlds[row['name']] for row in selected}) != 1:
        raise ValueError('Selection crosses independent test world boundaries')
    if plan['scope'] == 'full' and selected != [row for row in rows if worlds[row['name']] == 'shared']:
        raise ValueError('Incomplete full regression plan')
    return {row['name']: row['checks'] for row in selected}
