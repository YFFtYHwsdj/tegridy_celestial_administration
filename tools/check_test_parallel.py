#!/usr/bin/env python3
"""静态检查单实例内并行（lane）改造的安全性；不启动游戏、不修改测试源。

检查项对应 `.agents/teamwork/2026-11-06-single-instance-parallel/design.md`
第 6 节：
1. 注册元数据：登记必须带 GROUP/EXCLUSIVE，GROUP 合法且同命名空间一致，
   延迟用例必须登记 GROUP；登记的 DELAYED 必须与用例体的 lane 结束调用一致。
2. 用例体不得使用裸全局失败 flag、裸延迟续接与裸延迟活跃 flag。
3. lane flag／lane 结束调用的 GROUP 必须与用例注册 GROUP 一致。
4. 报告者作用域状态名不得跨 GROUP 冲突；白名单条目必须写明理由。
5. 共享作用域（title:h_china、title:h_china.holder、全局变量）上的状态只在
   被两个及以上不同 GROUP 的“延迟且非独占”用例写入时才构成并发冲突；
   独占用例与其它延迟用例互斥、同 GROUP 的延迟用例串行、即时用例在同步
   阶段先于延迟阶段执行，因此这三类都不参与冲突集合（夹具间接写入按调用
   点作用域归属到调用用例）。
6. 失败 flag 必须在全仓同时存在写入与读取，避免改名后失败不再被主用例读取。
7. 从每个用例的 BEGIN 事件沿 trigger_event 链核对失败 flag 与 lane 结束 GROUP，
   并拒绝被多个 GROUP 共用且引用这些标识的链事件。
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys

from check_upstream_overrides import definitions
from testing.catalog import registration_rows

ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK_EVENT = 'tca_tests_events.txt'
WHITELIST = Path('tools/testing/parallel_whitelist.json')
# design.md §5.6：迁移后用例体不得再出现的裸全局标识。
BARE_GLOBALS = frozenset({'tca_test_case_failed', 'tca_test_continue_delayed_effect',
                          'tca_test_delayed_case_active'})
# 报告者角色上的全局 flag：只有框架文件与显式白名单允许直接引用。
SHARED_SCOPES = frozenset({'title:h_china', 'title:h_china.holder'})
LANE_END = 'tca_test_lane_end_effect'
_LANE_FLAG = re.compile(r'tca_test_lane_([a-z0-9_$]+)_active')
_VARIABLE_WRITES = frozenset({'set_variable', 'change_variable', 'remove_variable'})
_GLOBAL_VARIABLE_WRITES = frozenset({'set_global_variable', 'change_global_variable',
                                     'remove_global_variable'})
_FLAG_WRITES = frozenset({'add_character_flag', 'remove_character_flag'})
# 未列入 shared/other 的 `X = {` 块（if/limit/参数块等）继承父作用域。
# 迭代器与显式角色／头衔作用域写入的是其它对象，不计入报告者状态。
_SCOPE_OTHER_PREFIXES = ('any_', 'every_', 'random_', 'ordered_')
_SCOPE_OTHER = frozenset({'root', 'this', 'liege', 'holder', 'ruler', 'father', 'mother',
                          'employer', 'host', 'actor', 'recipient'})


def load_whitelist(path=None):
    """读取状态名与只读全局 flag 白名单；每条必须带非空理由，避免静默压制冲突。"""
    path = Path(path) if path is not None else ROOT / WHITELIST
    result = {'variables': {}, 'character_flags': {}, 'bare_global_references': {}}
    if not path.is_file():
        return result
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('format') != 1:
        raise ValueError('Unsupported parallel whitelist format')
    for key in result:
        entries = data.get(key, [])
        if not isinstance(entries, list):
            raise ValueError(f'Whitelist section must be a list: {key}')
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f'Invalid whitelist entry: {entry!r}')
            name = entry.get('name')
            reason = entry.get('reason')
            if not isinstance(name, str) or not name or not isinstance(reason, str) or not reason.strip():
                raise ValueError(f'白名单条目缺少 name 或理由: {entry!r}')
            if key == 'bare_global_references':
                if name not in BARE_GLOBALS or not entry.get('file'):
                    raise ValueError(f'裸全局标识白名单必须引用已知标识与文件: {entry!r}')
                result[key][(entry['file'], name)] = reason.strip()
            else:
                result[key][name] = reason.strip()
    return result


def _test_events(root):
    """返回 events/tests 下的用例事件体，排除框架入口文件。

    每个事件记录所属文件命名空间；同一文件（命名空间）内所有用例共用一个 lane。
    """
    root = Path(root)
    events = {}
    for path in sorted((root / 'events').rglob('tca_*test*_events.txt')):
        if path.name == FRAMEWORK_EVENT:
            continue
        parsed = definitions(path.read_text(encoding='utf-8-sig'))
        event_ids = [key for key in parsed if '.' in key]
        if not event_ids:
            continue
        namespace = (parsed.get('namespace') or [''])[0] or event_ids[0].rsplit('.', 1)[0]
        for event in event_ids:
            events[event] = {'body': parsed[event], 'namespace': namespace, 'file': path.name}
    return events


def _fixtures(root):
    """返回共享用例夹具效果体；框架与模块登记文件不在检查范围。"""
    root = Path(root)
    tests = root / 'common/scripted_effects/tests'
    paths = sorted((tests / 'fixtures').rglob('*.txt'))
    extra = tests / 'tca_office_multimonth_test_effects.txt'
    if extra.is_file():
        paths.append(extra)
    fixtures = {}
    for path in paths:
        for effect, body in definitions(path.read_text(encoding='utf-8-sig')).items():
            fixtures[effect] = {'body': body, 'file': path.name}
    return fixtures


def _trigger_targets(body):
    """提取事件体触发的后续事件 ID；只做静态声明分析，不模拟运行。"""
    targets = set()
    for index, token in enumerate(body):
        if token != 'trigger_event' or index + 2 >= len(body) or body[index + 1] != '=':
            continue
        position = index + 2
        if body[position] != '{':
            targets.add(body[position])
            continue
        for scan in range(position, len(body)):
            if body[scan] == '}':
                break
            if body[scan] == 'id' and scan + 2 < len(body) and body[scan + 1] == '=':
                targets.add(body[scan + 2])
                break
    return targets


def _case_roots(events, registered):
    """计算每个事件被哪些已登记用例根事件触发（含注册事件自身）。

    延迟续接事件通常未逐条登记，归属到触发它的注册根用例，才能核对
    lane flag、共享写入与 EXCLUSIVE 要求。
    """
    edges = {event: _trigger_targets(info['body']) for event, info in events.items()}
    roots = {event: set() for event in events}
    for root in sorted(registered):
        if root not in events:
            continue
        stack, seen = [root], set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            roots[current].add(root)
            stack.extend(target for target in edges.get(current, ())
                         if target in events and target not in seen)
    return roots


def _scope_kind(label):
    """返回块作用域类型：shared/other 或 None（继承父作用域）。"""
    if label is None:
        return None
    if label in SHARED_SCOPES or label.startswith('global_var:'):
        return 'shared'
    if ':' in label or '$' in label:
        # 参数化或显式作用域（如 $CHARACTER$ = {、scope:x = {）写入的是其它对象。
        return 'other'
    if label in _SCOPE_OTHER or label.startswith(_SCOPE_OTHER_PREFIXES):
        return 'other'
    return None


def _named_value(body, index, key):
    """读取 `effect = { key = 目标 ... }` 或 `effect = 目标` 的目标名。"""
    position = index + 1
    if position >= len(body) or body[position] != '=':
        return None
    position += 1
    if position >= len(body):
        return None
    if body[position] != '{':
        return body[position]
    depth = 0
    for scan in range(position, len(body)):
        if body[scan] == '{':
            depth += 1
        elif body[scan] == '}':
            depth -= 1
            if depth == 0:
                return None
        elif body[scan] == key and scan + 2 < len(body) and body[scan + 1] == '=':
            return body[scan + 2]
    return None


def _scan(body):
    """遍历事件体或夹具体，产出写入与 scripted effect 调用。

    产出 `('write', 状态类型, 名字, 作用域)` 与 `('call', 效果名, 作用域)`。
    作用域为 reporter/shared/other：顶层块视为测试报告者；title:h_china、
    title:h_china.holder 与全局变量视为共享写入；其它 saved scope、迭代器
    与 random_vassal 等视为 other，不参与报告者状态冲突检测。
    """
    stack = []
    current = 'reporter'
    for index, token in enumerate(body):
        if token == '{':
            label = body[index - 2] if index >= 2 and body[index - 1] in ('=', '?=') else None
            pushed = _scope_kind(label) or current
            stack.append(pushed)
            current = pushed
        elif token == '}':
            if stack:
                stack.pop()
            current = stack[-1] if stack else 'reporter'
        elif token in _VARIABLE_WRITES or token in _GLOBAL_VARIABLE_WRITES:
            name = _named_value(body, index, 'name')
            if name:
                scope = 'shared' if token in _GLOBAL_VARIABLE_WRITES else current
                yield 'write', 'variable', name, scope
        elif token in _FLAG_WRITES:
            name = _named_value(body, index, 'flag')
            if name:
                yield 'write', 'character_flag', name, current
        # 效果调用以 `name =` 出现在当前作用域；用于把共享夹具写入归属到调用者。
        # 与写入共用四元组形状：('call', 效果名, '', 作用域)。
        if index + 1 < len(body) and body[index + 1] == '=' and index + 2 < len(body):
            yield 'call', token, '', current


def _writes(body):
    """返回 [(状态类型, 名字, 作用域)]，供报告者冲突与共享写入检查使用。"""
    return [(kind, name, scope) for operation, kind, name, scope in _scan(body)
            if operation == 'write']


def _call_sites(body):
    """返回 [(被调用效果名, 调用作用域)]；只记录 `效果 = ...` 形态。"""
    return [(effect, scope) for operation, effect, _kind, scope in _scan(body)
            if operation == 'call']


def _compose(parent, called):
    """组合夹具调用链的作用域：共享保持共享，子级显式作用域覆盖父级。"""
    if called == 'other' or parent == 'other':
        return 'other'
    if called == 'shared' or parent == 'shared':
        return 'shared'
    return 'reporter'


def _fixture_contexts(events, fixtures):
    """返回 {夹具: {(入口事件, 调用作用域)}}；把夹具间调用传播到固定点。

    夹具可能被事件在不同作用域调用（顶层报告者、title 共享作用域或其它
    角色），也可能被其它夹具调用；只有调用作用域为报告者的顶层写入才会
    参与跨 GROUP 状态冲突检测。
    """
    contexts = {name: set() for name in fixtures}
    edges = defaultdict(list)
    for event, info in events.items():
        for effect, scope in _call_sites(info['body']):
            if effect in fixtures:
                contexts[effect].add((event, scope))
    for caller, info in fixtures.items():
        for effect, scope in _call_sites(info['body']):
            if effect in fixtures:
                edges[caller].append((effect, scope))
    changed = True
    while changed:
        changed = False
        for caller, callees in edges.items():
            for callee, scope in callees:
                added = {(event, _compose(parent, scope))
                         for event, parent in contexts[caller]}
                before = len(contexts[callee])
                contexts[callee] |= added
                changed = changed or len(contexts[callee]) != before
    return contexts


_FAILURE_FLAG = re.compile(r'tca_test_[a-z0-9_]*case_failed')


def _failure_flags(body):
    """返回 {失败 flag: {'write', 'read'}}；只认 add/remove/has_character_flag 直接赋值。

    参数化名字（含 `$...$`）在静态阶段无法解析，调用方需自行跳过。
    """
    refs = defaultdict(set)
    for index, token in enumerate(body):
        if index < 2 or body[index - 1] != '=' or not _FAILURE_FLAG.fullmatch(token):
            continue
        effect = body[index - 2]
        if effect in ('add_character_flag', 'remove_character_flag'):
            refs[token].add('write')
        elif effect == 'has_character_flag':
            refs[token].add('read')
    return refs


def _brief(items, limit=6):
    """压缩较长的来源清单，保持报告可读且不丢关键冲突。"""
    ordered = sorted(items)
    if len(ordered) <= limit:
        return ', '.join(ordered)
    return ', '.join(ordered[:limit]) + f' 等 {len(ordered)} 处'


def _lane_end_groups(body):
    """提取 `tca_test_lane_end_effect = { GROUP = ... }` 的 GROUP 参数。"""
    groups = []
    for index, token in enumerate(body):
        if token != LANE_END or index + 3 >= len(body) or body[index + 1] != '=' \
                or body[index + 2] != '{':
            continue
        for scan in range(index + 3, len(body)):
            if body[scan] == '}':
                break
            if body[scan] == 'GROUP' and scan + 2 < len(body) and body[scan + 1] == '=':
                groups.append(body[scan + 2])
                break
    return groups


def _lane_flags(body):
    """提取用例体中出现的 lane flag 的 GROUP 片段。"""
    groups = []
    for token in body:
        match = _LANE_FLAG.fullmatch(token)
        if match:
            groups.append(match.group(1))
    return groups


def _namespace_groups(registrations):
    """命名空间 → 该命名空间所有登记用例的 GROUP 集合。"""
    mapping = defaultdict(set)
    for row in registrations:
        mapping[row['event'].rsplit('.', 1)[0]].add(row['group'])
    return mapping


def inspect(root=ROOT, whitelist_path=None):
    """运行全部静态检查，返回违规清单与统计信息。

    违规条目格式：{'check': 1-7, 'message': 中文说明, 'subject': 定位标识}。
    注册解析本身失败（结构性损坏、GROUP 非法或同名命名空间冲突）时，
    作为检查 1 违规返回，继续完成不依赖注册的源码扫描。
    """
    root = Path(root)
    whitelist = load_whitelist(whitelist_path)
    violations = []
    parse_error = None
    try:
        registrations = registration_rows(root)
    except ValueError as error:
        registrations = []
        parse_error = str(error)
    if parse_error:
        violations.append({'check': 1, 'subject': 'registration',
                           'message': f'注册解析失败：{parse_error}'})
    by_event = {row['event']: row for row in registrations}
    namespace_groups = _namespace_groups(registrations)
    events = _test_events(root)
    fixtures = _fixtures(root)
    roots = _case_roots(events, set(by_event))
    contexts = _fixture_contexts(events, fixtures)

    def add(check, subject, message):
        violations.append({'check': check, 'subject': subject, 'message': message})

    trigger_edges = {event: _trigger_targets(info['body']) for event, info in events.items()}
    closure_cache = {}

    def case_closure(event):
        """注册用例根的静态触发闭包；延迟续接事件通常未登记，需一起核对。"""
        if event not in closure_cache:
            seen, stack = set(), [event]
            while stack:
                current = stack.pop()
                if current in seen or current not in events:
                    continue
                seen.add(current)
                stack.extend(target for target in trigger_edges[current] if target in events)
            closure_cache[event] = seen
        return closure_cache[event]

    def event_groups(event):
        """事件应归属的 GROUP 集合：优先注册根用例，其次文件命名空间。"""
        info = events[event]
        groups = {by_event[root]['group'] for root in roots.get(event, ()) if root in by_event}
        if groups:
            return groups
        # 纯续接文件可能没有本命名空间的注册；只有在命名空间确有注册时才回退，
        # 否则无法判断 lane 归属，交由触发链规则（检查 7）负责。
        return set(namespace_groups.get(info['namespace'], ()))

    def fixture_groups(name):
        """夹具应归属的 GROUP 集合：所有调用入口事件的 GROUP 并集。"""
        groups = set()
        for event, _scope in contexts.get(name, ()):
            groups |= event_groups(event)
        return groups

    # 检查 1：显式元数据、命名空间一致性与 DELAYED／lane 结束调用一致。
    missing = defaultdict(list)
    for row in registrations:
        if not row['declared']:
            missing[row['event'].rsplit('.', 1)[0]].append(row['name'])
    for namespace, names in sorted(missing.items()):
        add(1, namespace, f'{namespace}: {len(names)} 条注册缺少 GROUP/EXCLUSIVE '
                          f'（延迟用例必须登记 GROUP）；请按迁移规则补全后重跑')
    for row in registrations:
        closure = case_closure(row['event'])
        has_end = any(LANE_END in events[event]['body'] for event in closure)
        if row['delayed'] and closure and not has_end:
            add(1, row['name'], f'{row["name"]}（{row["event"]}）登记为延迟用例，'
                               f'但用例触发闭包内未调用 {LANE_END}')
        if not row['delayed'] and has_end:
            add(1, row['name'], f'{row["name"]}（{row["event"]}）登记为即时用例，'
                               f'用例触发闭包内不应调用 {LANE_END}')

    # 检查 2：裸全局失败 flag、裸延迟续接与裸延迟活跃 flag。
    for kind, sources in (('事件', events), ('夹具', fixtures)):
        for subject, info in sources.items():
            for token in info['body']:
                if token not in BARE_GLOBALS:
                    continue
                if (info['file'], token) in whitelist['bare_global_references']:
                    continue
                add(2, subject, f'{kind} {info["file"]} 仍直接使用裸全局标识 {token}；'
                                f'请按命名空间迁移或改调 lane 结束效果')

    # 检查 3：lane flag／lane 结束调用的 GROUP 必须与注册一致。
    for kind, sources, resolve in (('事件', events, event_groups),
                                   ('夹具', fixtures, fixture_groups)):
        for subject, info in sources.items():
            allowed = resolve(subject)
            if not allowed:
                continue
            for group in _lane_flags(info['body']):
                if '$' in group:
                    continue
                if group not in allowed:
                    add(3, subject, f'{kind} {info["file"]} 引用了 lane flag '
                                    f'tca_test_lane_{group}_active，但所属 GROUP 为 '
                                    f'{", ".join(sorted(allowed))}')
            for group in _lane_end_groups(info['body']):
                if '$' in group:
                    continue
                if group not in allowed:
                    add(3, subject, f'{kind} {info["file"]} 的 {LANE_END} GROUP = {group} '
                                    f'与注册 GROUP {", ".join(sorted(allowed))} 不一致')

    # 检查 4：报告者作用域状态名跨 GROUP 冲突。
    state_groups = defaultdict(set)
    state_sources = defaultdict(set)

    def collect_reporter(subject, info, groups):
        for state_kind, name, scope in _writes(info['body']):
            if scope != 'reporter' or '$' in name:
                continue
            state_groups[(state_kind, name)] |= groups
            state_sources[(state_kind, name)].add(subject)

    for event, info in events.items():
        collect_reporter(f'事件:{event}', info, event_groups(event))
    for name, info in fixtures.items():
        merged = set()
        for event, scope in contexts.get(name, ()):
            if scope == 'reporter':
                merged |= event_groups(event)
        if merged:
            collect_reporter(f'夹具:{name}', info, merged)
    for (state_kind, name), groups in sorted(state_groups.items()):
        if len(groups) < 2:
            continue
        whitelisted = whitelist['variables'] if state_kind == 'variable' else whitelist['character_flags']
        if name in whitelisted:
            continue
        label = '变量' if state_kind == 'variable' else '角色 flag'
        add(4, name, f'报告者{label} {name} 被多个 GROUP 写入：'
                     f'{_brief(groups, 12)}；建议合并这些 GROUP，'
                     f'或把状态名改为按 GROUP 命名空间化（来源：'
                     f'{_brief(state_sources[state_kind, name])}）')

    # 检查 5：共享状态写-写冲突。
    # 共享状态指 title:h_china、title:h_china.holder 或全局变量上的变量与角色
    # flag，按（状态类型, 名字）聚合写入者。只有被两个及以上不同 GROUP 的
    # “延迟且非独占”用例写入时才构成并发冲突：独占用例在途时不会派发其它延迟
    # 用例，同 GROUP 的延迟用例串行执行，即时用例在同步阶段先于延迟阶段完成，
    # 因此这三类都不参与冲突集合。夹具间接写入按调用点作用域组合归属到调用
    # 用例（夹具内部写共享作用域时恒记；夹具顶层写报告者时仅在共享作用域调用
    # 点才转成共享写入）。
    variables = whitelist['variables']
    flags = whitelist['character_flags']
    shared_groups = defaultdict(set)   # (状态类型, 名字) -> {写入它的 GROUP}
    shared_cases = defaultdict(set)    # (状态类型, 名字) -> {用例名（事件）}

    def filter_shared(entries):
        return [(kind, name) for kind, name in entries
                if '$' not in name and name not in (variables if kind == 'variable' else flags)]

    def delayed_roots(event):
        return [root for root in roots.get(event, ())
                if root in by_event and by_event[root]['delayed'] and not by_event[root]['exclusive']]

    def collect_shared(roots, shared):
        for root in roots:
            row = by_event[root]
            for kind, name in shared:
                shared_groups[(kind, name)].add(row['group'])
                shared_cases[(kind, name)].add(f'{row["name"]}（{row["event"]}）')

    for event, info in events.items():
        shared = filter_shared((kind, name) for kind, name, scope in _writes(info['body'])
                               if scope == 'shared')
        if shared:
            collect_shared(delayed_roots(event), shared)
    for name, info in fixtures.items():
        internal = filter_shared((kind, state) for kind, state, scope in _writes(info['body'])
                                 if scope == 'shared')
        top = filter_shared((kind, state) for kind, state, scope in _writes(info['body'])
                            if scope == 'reporter')
        for event, scope in contexts.get(name, ()):
            shared = internal + (top if scope == 'shared' else [])
            if shared:
                collect_shared(delayed_roots(event), shared)
    for (kind, name), groups in sorted(shared_groups.items()):
        if len(groups) < 2:
            continue
        label = '变量' if kind == 'variable' else '角色 flag'
        add(5, name, f'共享{label} {name} 被多个 GROUP 的延迟非独占用例写入：'
                     f'{_brief(groups, 12)}；并发运行会互相覆盖，'
                     f'请把这些 GROUP 合并为同一 lane，或让写该状态的用例保持 '
                     f'EXCLUSIVE = yes（涉及用例：{_brief(shared_cases[kind, name])}）')

    # 检查 6：失败 flag 必须在全仓同时有写入与读取，避免改 namespace 后失败被掩盖。
    flag_writes = defaultdict(int)
    flag_reads = defaultdict(int)
    flag_files = defaultdict(set)
    for base in (root / 'events/tests', root / 'common/scripted_effects/tests'):
        for path in sorted(base.rglob('*.txt')):
            try:
                parsed = definitions(path.read_text(encoding='utf-8-sig'))
            except (OSError, ValueError):
                continue
            for body in parsed.values():
                for name, kinds in _failure_flags(body).items():
                    if '$' in name:
                        continue
                    flag_files[name].add(path.name)
                    if 'write' in kinds:
                        flag_writes[name] += 1
                    if 'read' in kinds:
                        flag_reads[name] += 1
    for name in sorted(set(flag_writes) | set(flag_reads)):
        if flag_writes.get(name) and flag_reads.get(name):
            continue
        missing = '读取' if flag_writes.get(name) else '写入'
        add(6, name, f'失败 flag {name} 缺少{missing}：写 {flag_writes.get(name, 0)} 处、'
                     f'读 {flag_reads.get(name, 0)} 处；涉及文件 {_brief(flag_files[name])}')

    # 检查 7：跨文件触发链必须把失败与 lane 结束回报到发起用例。
    for row in registrations:
        closure = case_closure(row['event'])
        expected = set()
        for event in closure:
            expected |= {name for name, kinds in _failure_flags(events[event]['body']).items()
                         if 'read' in kinds and '$' not in name}
        if len(expected) > 1:
            add(7, row['name'], f'用例 {row["name"]} 的触发链出现多个失败 flag'
                               f'（{_brief(expected)}），无法确定失败归属')
        for event in sorted(closure):
            body = events[event]['body']
            for name in _failure_flags(body):
                if '$' in name or not expected or name in expected:
                    continue
                add(7, f'{event}:{name}',
                    f'用例 {row["name"]} 的触发链事件 {event} 使用失败 flag {name}，'
                    f'与链内主用例失败 flag {_brief(expected)} 不一致')
            for group in _lane_end_groups(body):
                if '$' in group or group == row['group']:
                    continue
                add(7, f'{event}:{group}',
                    f'用例 {row["name"]} 的触发链事件 {event} 的 {LANE_END} '
                    f'GROUP = {group}，与注册 GROUP {row["group"]} 不一致')
    for event, event_roots in sorted(roots.items()):
        groups = {by_event[root]['group'] for root in event_roots if root in by_event}
        if len(groups) < 2:
            continue
        body = events[event]['body']
        names = {name for name in _failure_flags(body) if '$' not in name}
        lane_groups = {group for group in _lane_end_groups(body) if '$' not in group}
        if names or lane_groups:
            add(7, event, f'事件 {event} 被多个 GROUP（{_brief(groups, 8)}）的用例链共用'
                         f'且引用失败／lane 标识；无法安全共享，请拆分事件或合并 GROUP')

    return {'root': str(root), 'registrations': len(registrations),
            'groups': sorted({row['group'] for row in registrations}),
            'events': len(events), 'fixtures': len(fixtures),
            'violations': violations}


def _summary(report):
    """按检查项汇总违规数量，供人类可读报告逐项显示 PASS/FAIL。"""
    counts = defaultdict(int)
    for item in report['violations']:
        counts[item['check']] += 1
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='模组根目录（默认仓库根）')
    parser.add_argument('--whitelist', type=Path, help='状态名白名单路径')
    parser.add_argument('--json', type=Path, help='同时写出 JSON 结果')
    args = parser.parse_args(argv)
    try:
        report = inspect(args.root, args.whitelist)
    except (OSError, ValueError) as error:
        print(f'检查无法完成：{error}', file=sys.stderr)
        return 1
    counts = _summary(report)
    titles = {
        1: '注册元数据与 DELAYED 一致性',
        2: '用例体裸全局标识',
        3: 'lane flag／结束调用 GROUP 一致性',
        4: '报告者状态跨 GROUP 冲突',
        5: '共享状态跨 GROUP 写冲突（延迟非独占用例）',
        6: '失败 flag 的写入与读取配对',
        7: '触发链失败归属与 lane 结束一致性',
    }
    print(f'并行静态检查：{report["registrations"]} 条注册；'
          f'{len(report["groups"])} 个 GROUP；{report["events"]} 个用例事件；'
          f'{report["fixtures"]} 个共享夹具')
    for check in sorted(titles):
        count = counts.get(check, 0)
        print(f'[{"PASS" if count == 0 else "FAIL"}] 检查{check} {titles[check]}'
              + ('' if count == 0 else f'（{count} 处）'))
    if report['violations']:
        print('问题清单：')
        for item in report['violations']:
            print(f'- [检查{item["check"]}] {item["message"]}')
    print('OK: 未发现并行安全违规' if not report['violations']
          else f'FAILED: {len(report["violations"])} 处并行安全违规')
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
    return int(bool(report['violations']))


if __name__ == '__main__':
    raise SystemExit(main())
