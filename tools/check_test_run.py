#!/usr/bin/env python3
"""核对最新测试组覆盖，以及本次游戏启动全程的模组相关错误。"""
import argparse
from collections import Counter
from itertools import chain
import json
from pathlib import Path
import re
from check_upstream_overrides import definitions

ROOT = Path(__file__).resolve().parents[1]

# 全量运行的调试日志可达数百 MB，解析统一按行或按时间戳顺序流式完成：
# 只做一到两遍扫描，不再对整段日志按用例重复正则搜索。
_TIMESTAMP = re.compile(r'\[\d{2}:\d{2}:\d{2}\]')
# 与原先逐行 re.search 完全一致：每行只取第一个断言结果。
_RESULT = re.compile(r'TCA_TEST (BEGIN|PASS|FAIL|PRECONDITION_FAIL|CHECK_PASS|CHECK_FAIL) (\S+)(?: (\S+))?')
# 逐项统计允许同一行重复出现，故单独扫描且只消费到首个词，避免把后续标记当成参数吞掉。
_CASE_RESULT = re.compile(r'TCA_TEST (BEGIN|PASS|FAIL|PRECONDITION_FAIL|CHECK_PASS|CHECK_FAIL) (\S+)')
_CASE_ARGUMENT = re.compile(r' (\S+)')
_CASE_STEP = re.compile(r' (\d+)(?:\s|$)')
_DISPATCH = 'TCA_TEST SUITE_DISPATCH'
_STRICT_MARK = 'native Tongpan appointment differs from pre-death title preview head'


def expected_cases(root=ROOT):
    """读取直接维护的原生事件及GUI同步调用的测试夹具，绝不生成或运行游戏脚本。"""
    entries = {}
    checks = {}

    def record_check(name, step, source):
        if int(step) in checks.setdefault(name, set()):
            raise ValueError(f'{source}: duplicate assertion {name} {step}')
        checks[name].add(int(step))

    for path in sorted((root / 'events').rglob('tca_*test*_events.txt')):
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
                    record_check(*check.groups(), path.name)
    # GUI重载首帧无法等待角色事件，检查放在同步夹具中；这仍是正式断言，不另造孤立占位事件。
    for path in sorted((root / 'common' / 'scripted_effects' / 'tests').rglob('*.txt')):
        for _effect, body in definitions(path.read_text(encoding='utf-8-sig')).items():
            for index, token in enumerate(body[:-2]):
                if token != 'debug_log' or body[index + 1] != '=':
                    continue
                message = body[index + 2].strip('"')
                check = re.fullmatch(r'TCA_TEST CHECK_PASS (tca_test_\S+) (\d+)', message)
                if check:
                    record_check(*check.groups(), path.name)
    if not entries or entries.keys() != checks.keys():
        raise ValueError('Test entries and assertion names must be nonempty and match')
    for name, steps in checks.items():
        if steps != set(range(1, len(steps) + 1)):
            raise ValueError(f'{name}: assertion numbers must be consecutive')
    return {name: len(checks[name]) for name in entries}


def _engine_entries(text):
    """流式复现 re.split(r'(?=\\[\\d{2}:\\d{2}:\\d{2}\\])', text) 的错误条目分段。"""
    start = -1
    for match in _TIMESTAMP.finditer(text):
        position = match.start()
        if start < 0:
            if position:
                yield text[:position]
        elif position > start:
            yield text[start:position]
        start = position
    if start < 0:
        if text:
            yield text
    elif start < len(text):
        yield text[start:]


def _frame_function(line):
    """取脚本栈帧括号内的函数名；无函数名时返回空串。"""
    match = re.search(r'\(([^)]+)\)\s*$', line)
    return match.group(1).strip() if match else ''


def _registration_frame(frame, source_root):
    """只认可给定源码及其登记中的纯on_actions父块；缺证据一律保守拒绝。"""
    if source_root is None:
        return None
    match = re.fullmatch(r'(?:Script location: )?file: (common/on_action/[\w./-]+) line: (\d+) \((\w+)\)', frame)
    if not match:
        return None
    path, line, parent = match.groups()
    if '..' in Path(path).parts:
        return None
    source = Path(source_root)
    registry_path = source / 'tools/upstream_overrides.json'
    if not registry_path.is_file() and source.name == 'tca_main' and source.parent.name == 'mod':
        # 运行器冻结业务源码与工具分目录存放，必须是同一个run的工具快照。
        registry_path = source.parent.parent / 'tools/upstream_overrides.json'
    try:
        registry = json.loads(registry_path.read_text(encoding='utf-8'))
        entries = [item for item in registry.get('known_extensions', [])
                   if item.get('key') == parent and item.get('mod') == path
                   and item.get('vanilla', '').startswith('common/on_action/')]
        if len(entries) != 1:
            return None
        raw = (source / path).read_text(encoding='utf-8-sig')
        clean = re.sub(r'#[^\n]*', '', raw)
        heads = list(re.finditer(r'(?m)^[ \t]*' + re.escape(parent) + r'\s*=\s*', clean))
        if len(heads) != 1:
            return None
        head = heads[0]
        body = re.match(r'\{\s*on_actions\s*=\s*\{\s*(?:[A-Za-z_]\w*\s*)+\}\s*\}', clean[head.end():])
        if not body:
            return None
        # 纯块必须是解析器所见的完整父定义，不能只匹配带effect的块之前缀。
        from check_upstream_overrides import tokens
        if definitions(raw).get(parent) != tokens(body[0]):
            return None
        first_line = clean.count('\n', 0, head.start()) + 1
        last_line = clean.count('\n', 0, head.end() + body.end()) + 1
        if not first_line <= int(line) <= last_line:
            return None
        return {'classification': 'native-registration-frame', 'path': path,
                'parent': parent, 'line': int(line)}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def _runtime_character_field(detail, frames, source_root):
    """仅识别两种原生错误的人物字段；源码登记与完整脚本栈缺失时不应用。"""
    if source_root is None or not Path(source_root).is_dir() or not frames:
        return None
    source = Path(source_root)
    registry_path = source / 'tools/upstream_overrides.json'
    if not registry_path.is_file() and source.name == 'tca_main' and source.parent.name == 'mod':
        registry_path = source.parent.parent / 'tools/upstream_overrides.json'
    try:
        registry = json.loads(registry_path.read_text(encoding='utf-8'))
        if not isinstance(registry.get('known_extensions'), list):
            return None
    except (OSError, ValueError, AttributeError):
        return None
    if any(not re.fullmatch(r'(?:Script location: )?file: (?:common|events)/[\w./-]+ line: [1-9]\d* \(.+\)', frame) for frame in frames):
        return None
    # 人物格式不依赖tca前缀；以数字ID和完整固定错误语法界定字段，不做全局字符串替换。
    character = (r'(?P<character>[^()\[\]\r\n]+ of [^()\[\]\r\n]+ '
                 r'\(Internal ID:? (?P<id>[1-9]\d*)(?: - Historical ID (?P<history>[\w.-]+))?\))')
    patterns = (
        r'reverse_add_opinion effect \[ ' + character + r' is trying to add an opinion of themself \]',
        r"change_opportunities effect \[ Invalid scheme '[A-Za-z_]\w*' with owner " + character + r' and target [^\r\n]+ \]',
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, detail)
        if match:
            start, end = match.span('character')
            return (detail[:start] + '<runtime-character>' + detail[end:],
                    {'character_id': int(match['id']), 'historical_id': match['history'],
                     'display': match['character']})
    return None


def _script_stack_related(entry, owned_paths, source_root=None, diagnostics=None):
    """纯注册父帧只表示结构来源；任何实际模组执行帧或错误正文仍阻断。"""
    frames = [line.strip() for line in entry.splitlines()
              if line.strip().startswith(('file:', 'Script location:'))]
    proofs = []
    detail = re.search(r'Error: ([^\n]+)', entry)
    runtime_titles = []
    runtime_character = None
    if detail:
        # 仅扩展同一种带引擎Internal ID的人物头衔展示；不删除姓名、历史ID或其它正文。
        pattern = r'\bof [bcdkeh]_tca_\w+ (?=\(Internal ID:? \d+(?: - Historical ID [\w.-]+)?\))'
        runtime_titles = re.findall(pattern, detail[1])
        text = re.sub(pattern, 'of <runtime-title> ', detail[1])
        character_field = _runtime_character_field(detail[1], frames, source_root)
        if character_field:
            text, runtime_character = character_field
            runtime_titles = []
        old_text = re.sub(r'\bof [bcdkeh]_tca_\w+ (?=\(Internal ID: \d+\))', 'of <runtime-title> ', detail[1])
        if not runtime_character and text != old_text and (source_root is None or not Path(source_root).is_dir() or not frames):
            return True  # 新格式缺少指定源码／有效栈时，不能单凭展示格式放行。
        if 'tca_' in text or '提点刑狱司' in text:
            return True
    for index, frame in enumerate(frames):
        frame_path = re.search(r'file: ([^ ]+) line:', frame)
        in_source = bool(source_root is not None and frame_path and '..' not in Path(frame_path[1]).parts
                         and (Path(source_root) / frame_path[1]).is_file())
        if not (in_source or 'tca_' in frame or '提点刑狱司' in frame or any(path in frame for path in owned_paths)):
            continue
        proof = _registration_frame(frame, source_root) if index else None
        if proof is None:
            return True
        proofs.append(proof)
    if runtime_character and proofs:
        return True  # 此窄分类只接纳全原生执行栈，不复用纯注册帧分类来扩大边界。
    if runtime_character and diagnostics is not None:
        diagnostics.append({'classification': 'native-runtime-character',
                            'character': runtime_character, 'raw': entry})
    if proofs and diagnostics is not None:
        diagnostics.append({'classification': 'native_error_with_mod_registration',
                            'frames': proofs, 'raw': entry})
    if runtime_titles and diagnostics is not None:
        diagnostics.append({'classification': 'native-runtime-title',
                            'runtime_titles': runtime_titles, 'raw': entry})
    return False


def _inspect_engine_entries(entries, source_root=None, diagnostics=None):
    """逐条分类启动期引擎错误，返回顺序与原文逐条扫描一致。"""
    registry = json.loads((ROOT / 'tools/upstream_overrides.json').read_text(encoding='utf-8'))
    owned_paths = {entry['mod'] for section in ('overrides', 'file_overrides')
                   for entry in registry.get(section, [])}
    owned_loc_keys = {key for entry in registry.get('file_overrides', [])
                      for key in entry.get('diagnostic_localization_keys', [])}
    # 即使测试运行期间没有错误，启动阶段失败也必须计入。
    findings = Counter()
    for entry in entries:
        if 'is not a valid event ID, has to be < 10000' in entry:
            findings['Invalid numeric event ID'] += 1
            continue
        loc_error = re.search(r"Data error in loc string '([^']+)'", entry)
        if 'Script system error' in entry:
            # 脚本错误只看调用栈；正文中的头衔／角色名可能是原生运行时文本。
            related = _script_stack_related(entry, owned_paths, source_root, diagnostics)
        else:
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
        elif 'Duplicated event ID' in entry:
            findings['TCA duplicate event override priority'] += 1
        elif any(message in entry for message in ('Unexpected token:', 'Malformed token:', 'Unknown trigger:', 'Unknown effect:')):
            findings['TCA script parsing failure'] += 1
        elif any(message in entry for message in ('Error setting properties', 'is not a valid widget/type/property')):
            findings['TCA GUI property failure'] += 1
        elif 'Invalid actor & recipient' in entry and 'modify_vassal_contract interface' in entry:
            findings['TCA native contract window rejected participants'] += 1
        elif 'is marked as default but has an is_shown trigger' in entry:
            # 默认契约档必须始终可见；隐藏默认档会让整次运行的错误证据失效。
            findings['TCA contract default level visibility failure'] += 1
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


def inspect_engine_errors(errors, source_root=None, diagnostics=None):
    """纳入已审阅的整文件 GUI 覆盖，即使错误中没有 tca_ 标识。"""
    return _inspect_engine_entries(_engine_entries(errors), source_root, diagnostics)


def _debug_error_entries(debug, logged_errors):
    """流式收集调试日志中以 `[时间][E]` 开头的多行条目，并按 error.log 分块去重。"""
    start = -1
    for match in _TIMESTAMP.finditer(debug):
        position = match.start()
        if start >= 0 and position > start:
            entry = debug[start:position]
            if entry not in logged_errors:
                yield entry
        start = position if debug.startswith('[E]', match.end()) else -1
    if start >= 0 and start < len(debug):
        entry = debug[start:]
        if entry not in logged_errors:
            yield entry


class _LatestScan:
    """最新一次 SUITE_DISPATCH 之后的解析结果，供断言核对与逐项状态共用。"""

    __slots__ = ('dispatched', 'results', 'checks', 'assertion_results',
                 'strict_hit', 'aborted', 'all_passed', 'observer_last',
                 'case_begins', 'case_passes', 'case_check_passes',
                 'case_preconditions', 'case_failures')

    def __init__(self):
        self.dispatched = False
        self.results = Counter()
        self.checks = Counter()
        self.assertion_results = Counter()
        self.strict_hit = False
        self.aborted = False
        self.all_passed = False
        self.observer_last = None
        self.case_begins = Counter()
        self.case_passes = Counter()
        self.case_check_passes = Counter()
        self.case_preconditions = set()
        self.case_failures = set()


def _scan_latest(debug, strict_title_heir=False):
    """单遍解析最新派发之后的日志，替代原先的多轮整段扫描。"""
    scan = _LatestScan()
    lines = debug.splitlines()
    dispatch = -1
    dispatch_column = 0
    for index, line in enumerate(lines):
        if 'TCA_TEST' in line and _DISPATCH in line:
            dispatch = index
            dispatch_column = line.rfind(_DISPATCH)
    if dispatch < 0:
        return scan
    scan.dispatched = True
    results = scan.results
    checks = scan.checks
    assertions = scan.assertion_results
    begins = scan.case_begins
    passes = scan.case_passes
    case_checks = scan.case_check_passes
    preconditions = scan.case_preconditions
    failures = scan.case_failures
    for index in range(dispatch, len(lines)):
        line = lines[index]
        if strict_title_heir and not scan.strict_hit and _STRICT_MARK in line:
            scan.strict_hit = True
        if 'TCA_TEST' not in line:
            continue
        if not scan.aborted and 'TCA_TEST SUITE_ABORTED' in line:
            scan.aborted = True
        if not scan.all_passed and 'TCA_TEST SUITE_ALL_PASSED' in line:
            scan.all_passed = True
        if index > dispatch and ('TCA_TEST OBSERVER_ENTRY_REJECTED' in line
                                 or 'TCA_TEST OBSERVER_ENTRY_DISPATCH' in line):
            scan.observer_last = line
        match = _RESULT.search(line)
        if match:
            kind, first, second = match.groups()
            if kind.startswith('CHECK_'):
                checks[kind] += 1
                assertions[kind, first, second] += 1
            else:
                name = second if kind == 'BEGIN' else first
                results[kind, name] += 1
        # 逐项统计从派发行内最后一次派发位置之后开始，允许一行出现多条结果。
        case_line = line[dispatch_column:] if index == dispatch else line
        for mark in _CASE_RESULT.finditer(case_line):
            kind, first = mark.groups()
            if kind == 'BEGIN':
                argument = _CASE_ARGUMENT.match(case_line, mark.end())
                if argument:
                    begins[argument.group(1)] += 1
            elif kind == 'PASS':
                passes[first] += 1
            elif kind == 'PRECONDITION_FAIL':
                preconditions.add(first)
            elif kind in ('FAIL', 'CHECK_FAIL'):
                failures.add(first)
            else:  # CHECK_PASS
                step = _CASE_STEP.match(case_line, mark.end())
                if step:
                    case_checks[first, step.group(1)] += 1
    return scan


def _inspect_scan(scan, debug, errors, expected, source_root=None, diagnostics=None):
    """由单遍解析结果生成问题列表与结果汇总；文本、顺序与计数保持原样。"""
    if not scan.dispatched:
        return ['No suite dispatch found'], Counter()
    issues = []
    if scan.strict_hit:
        issues.append('Strict title succession failed: appointed officer differs from preview head')
    if scan.aborted:
        issues.append('Suite aborted: test environment invalid')
    # 较新的观察者尝试不能静默继承旧测试组的通过结果。
    if scan.observer_last is not None:
        if 'OBSERVER_ENTRY_REJECTED' in scan.observer_last:
            issues.append('Latest observer entry rejected: ' +
                          scan.observer_last.split('OBSERVER_ENTRY_REJECTED', 1)[1].strip())
        else:
            issues.append('No suite dispatch after latest observer entry')
    for name in sorted(expected):
        if scan.results['BEGIN', name] != 1 or scan.results['PASS', name] != 1:
            issues.append(f'{name}: begin={scan.results["BEGIN", name]}, pass={scan.results["PASS", name]}')
    if isinstance(expected, dict):
        for name, total in expected.items():
            for step in range(1, total + 1):
                if scan.assertion_results['CHECK_PASS', name, str(step)] != 1:
                    issues.append(f'{name}: assertion {step} missing or duplicated')
        for (kind, name, step), count in scan.assertion_results.items():
            if name not in expected or step not in {str(i) for i in range(1, expected.get(name, 0) + 1)}:
                issues.append(f'Unexpected assertion: {kind} {name} {step}')
    for (kind, name), count in scan.results.items():
        if name not in expected or kind in {'FAIL', 'PRECONDITION_FAIL'}:
            issues.append(f'{kind} {name}: {count}')
    if scan.checks['CHECK_FAIL']:
        issues.append(f'Failed assertions: {scan.checks["CHECK_FAIL"]}')
    if not scan.all_passed:
        issues.append('No SUITE_ALL_PASSED completion')
    # 原生窗口错误可能只写debug日志；保留多行上下文，并与error日志去重。
    error_entries = list(_engine_entries(errors))
    logged_errors = set(error_entries)
    issues.extend(_inspect_engine_entries(
        chain(error_entries, _debug_error_entries(debug, logged_errors)), source_root, diagnostics))
    summary = Counter({kind: sum(count for (k, _), count in scan.results.items() if k == kind)
                       for kind in ['BEGIN', 'PASS', 'FAIL', 'PRECONDITION_FAIL']})
    summary.update(scan.checks)
    return issues, summary


def inspect_run(debug, errors, expected, strict_title_heir=False, source_root=None, diagnostics=None):
    """核对一次运行：单遍解析最新派发，再逐条检查引擎错误。"""
    scan = _scan_latest(debug, strict_title_heir)
    return _inspect_scan(scan, debug, errors, expected, source_root, diagnostics)


def selected_case_expectations(entry, root=ROOT):
    all_cases = expected_cases(root)
    for path in sorted((root / 'events').rglob('tca_*test*_events.txt')):
        for event, body in definitions(path.read_text(encoding='utf-8-sig')).items():
            if event == entry:
                match = re.search(r'TCA_TEST BEGIN ' + re.escape(entry) + r' (tca_test_\S+)', ' '.join(body))
                if match:
                    name = match[1].rstrip('"')
                    return {name: all_cases[name]}
    raise ValueError(f'Unknown native test entry: {entry}')


def _case_states(scan, expected):
    """只统计最新派发轮；完整断言及唯一结果齐备才显示单项通过。"""
    states = {}
    for name, total in expected.items():
        if name in scan.case_preconditions:
            state = 'PRECONDITION_FAIL'
        elif name in scan.case_failures:
            state = 'FAIL'
        elif not scan.case_begins.get(name):
            state = 'NOT_RUN'
        else:
            passed = scan.case_passes.get(name, 0)
            begins = scan.case_begins[name]
            checks = Counter({step: count for (case, step), count in scan.case_check_passes.items()
                              if case == name})
            state = 'PASS' if passed == begins == 1 and checks == Counter(
                {str(i): 1 for i in range(1, total + 1)}) else 'NOT_VERIFIED'
        states[name] = state
    return states


def case_outcomes(debug, expected):
    """只统计最新派发轮；完整断言及唯一结果齐备才显示单项通过。"""
    return _case_states(_scan_latest(debug), expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs', type=Path, default=ROOT.parent.parent / 'logs')
    parser.add_argument('--output', type=Path, help='write verification to a separate path without modifying frozen results')
    parser.add_argument('--case', help='verify only this maintained native case')
    parser.add_argument('--strict-title-heir', action='store_true', help='fail when native appointment differs from preview head')
    parser.add_argument('--source-root', type=Path, help='exact frozen mod source used by this run')
    args = parser.parse_args()
    source = args.source_root or (args.logs.parent / 'mod/tca_main')
    proof_source = source if source.is_dir() else None
    if not source.is_dir():
        source = ROOT
        print('WARNING: no source snapshot; checking current case counts only')
    plan_path = args.logs.parent / 'selection.json'
    plan = json.loads(plan_path.read_text(encoding='utf-8')) if plan_path.is_file() else None
    if plan is not None and 'cases' in plan:
        from testing.catalog import validate_plan
        expected = validate_plan(plan, source)
        if args.case and expected != selected_case_expectations(args.case, source):
            raise ValueError('--case conflicts with frozen selection plan')
    elif isinstance(plan, dict) and set(plan) == {'case', 'stage'}:
        # 旧版单项计划的阶段号不再参与调度，验收仍按原生入口读取冻结断言。
        expected = selected_case_expectations(plan['case'], source)
        if args.case and args.case != plan['case']:
            raise ValueError('--case conflicts with legacy selection')
    elif plan is None:
        expected = selected_case_expectations(args.case, source) if args.case else expected_cases(source)
    else:
        raise ValueError('Invalid selection plan')
    debug = (args.logs / 'debug.log').read_text(encoding='utf-8', errors='replace') if (args.logs / 'debug.log').is_file() else ''
    errors = (args.logs / 'error.log').read_text(encoding='utf-8', errors='replace') if (args.logs / 'error.log').is_file() else ''
    scan = _scan_latest(debug, args.strict_title_heir)
    diagnostics = []
    issues, counts = _inspect_scan(scan, debug, errors, expected, source_root=proof_source, diagnostics=diagnostics)
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
    scope = plan.get('scope', 'legacy selection') if plan else 'selected case' if args.case else 'all current cases'
    cases = _case_states(scan, expected)
    for item in diagnostics:
        print('Native background error (' + item['classification'] + '): ' + item['raw'].strip())
    (args.output or args.logs.parent / 'verification.json').write_text(json.dumps(
        {'scope': scope, 'cases': cases, 'counts': dict(counts), 'issues': issues,
         'native_registration_diagnostics': [item for item in diagnostics if item['classification'] == 'native_error_with_mod_registration'],
         'native_runtime_title_diagnostics': [item for item in diagnostics if item['classification'] == 'native-runtime-title'],
         'native_runtime_character_diagnostics': [item for item in diagnostics if item['classification'] == 'native-runtime-character'],
         'verification_exit': int(bool(issues))}, ensure_ascii=False, indent=2) + '\n')
    print('NOT VERIFIED' if issues else f'OK: {scope} passed; no detected mod-related engine errors')
    return int(bool(issues))


if __name__ == '__main__':
    raise SystemExit(main())
