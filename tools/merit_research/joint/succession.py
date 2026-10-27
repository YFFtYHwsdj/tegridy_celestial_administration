"""联合研究的事件式职务承接；不是原生继任或实际空职的引擎模型。

调用者先释放死亡/卸职的holder及人物job，再提供事件。模块只在事件中
调用旧研究的资格与选择核；无人可选记uncovered，不能解释为天朝无人持职。
已处理事件标识保存在岗位上，兼容JSON封存。无event_id的请求视作新的事件；
需要跨调用幂等的调用者必须传稳定event_id。年度日期只是研究聚合时点。
"""
from collections import deque
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _reference(folder, frozen, filename, module_name):
    """同时支持库内研究布局与仓库外原相邻目录名，不修改sys.path。"""
    for path in (ROOT.parent / frozen / filename, ROOT.parent / folder / filename):
        if path.is_file():
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise FileNotFoundError(f'缺少研究依赖：{frozen}/{filename}')


appointments = _reference('occupancy', 'merit-occupancy-study', 'appointments.py',
                          'joint_succession_appointments_reference')
TH = tuple(_reference('buffers', 'merit-buffer-study', 'model.py',
                      'joint_succession_buffer_reference').TH)


def _identity(job, event):
    """外部id跨年份保持相同；自动id随同岗位的持久序号递增。"""
    if 'event_id' in event:
        parts = ['explicit', event['event_id']]
    else:
        sequence = job.get('_succession_sequence', 0) + 1
        job['_succession_sequence'] = sequence
        parts = ['auto', job['id'], sequence]
    return json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _choose_cached(candidates, job, year, seed, mode, score_cache):
    """天然任命核的精确等价选择；同resolve内分数不变，rank可变。

    只缓存人工局部分数，不缓存资格、品级或获选结果。完整并列仍用旧
    hash输入，hash碰撞仍取旧稳定排序的首项；避免每事件排序全候选。
    本辅助函数仅替代resolve使用的natural入口，不处理首次官署加权入口。
    """
    if mode not in appointments.MODES:
        raise ValueError('未知研究选择模式或入口')
    tier = appointments._tier(job)
    kind = job.get('kind')
    seen = set()
    tie_hash = {}
    best_merit = best_score = best_suitable = None
    merit_key = suitable_key = None
    score_max = best_suitable_score = None
    count = fitting = high_count = 0

    def tie(p, previous):
        # 只有完全并列才求hash；同一个候选在两种对照里共用同一值。
        for candidate in (p, previous):
            pid = candidate['id']
            if pid not in tie_hash:
                tie_hash[pid] = appointments._uniform(seed, year, job['id'], 'natural', 'tie', pid)
        new_hash, old_hash = tie_hash[p['id']], tie_hash[previous['id']]
        if new_hash != old_hash:
            return p if new_hash > old_hash else previous
        new_order = (str(type(p['id'])), str(p['id']))
        old_order = (str(type(previous['id'])), str(previous['id']))
        return p if new_order < old_order else previous

    for person in candidates:
        pid = person['id']
        if pid in seen:
            raise ValueError('候选id不能重复')
        seen.add(pid)
        cache_key = (pid, kind)
        if cache_key not in score_cache:
            score_cache[cache_key] = appointments.synthetic_score(person, job)
        score = score_cache[cache_key]
        primary = (person['rank'], score)
        band = appointments.rank_band(person['rank'])
        count += 1
        high_count += band > tier
        if merit_key is None or primary > merit_key:
            best_merit, merit_key = person, primary
        elif primary == merit_key:
            best_merit = tie(person, best_merit)
        if score_max is None or score > score_max:
            best_score, score_max = person, score
        elif score == score_max:
            best_score = tie(person, best_score)
        if band == tier:
            fitting += 1
            if best_suitable_score is None or score > best_suitable_score:
                best_suitable_score = score
            if suitable_key is None or primary > suitable_key:
                best_suitable, suitable_key = person, primary
            elif primary == suitable_key:
                best_suitable = tie(person, best_suitable)
    winner = (best_score if mode == 'score_only' else
              (best_suitable or best_merit) if mode == 'suitable_first' else best_merit)
    high = winner is not None and appointments.rank_band(winner['rank']) > tier
    score_only_suitable = best_score is not None and appointments.rank_band(best_score['rank']) == tier
    winner_score = None if winner is None else score_cache[(winner['id'], kind)]
    return winner, {
        'candidate_count': count, 'suitable_count': fitting,
        'suitable_available': bool(fitting), 'winner_high_band': high,
        'winner_band': None if winner is None else appointments.rank_band(winner['rank']),
        'winner_score': winner_score,
        'score_only_winner_id': None if best_score is None else best_score['id'],
        'score_only_suitable': score_only_suitable,
        'merit_advantage_proxy': bool(mode == 'merit_first' and high and score_only_suitable),
        'high_candidate_fraction': high_count/count if count else None,
        'best_suitable_score': best_suitable_score,
        'score_gap_to_best_suitable': (winner_score-best_suitable_score
            if winner is not None and best_suitable_score is not None else None),
        'mode': mode, 'entry': 'natural',
        'selection_assumption': 'lexicographic_research_assumption', 'causal_evidence': False,
    }


def resolve(people, jobs, year, seed, events, mode='merit_first'):
    """原位更新人物和岗位，返回实际承接、迁任、未覆盖及中央授品流。

    people/jobs为id映射；人物字段沿旧appointments，Merit余额字段为m。
    每人至多一个研究实职。死亡、退休和辞谢判定由调用者拥有；本函数不
    根据年龄/病理卸职。只给实际声明central_target=8/9的岗位事后授品，
    普通帝级槽没有默认特授。Q/功绩年度抽选不在本模块内。
    """
    if mode not in appointments.MODES:
        raise ValueError('未知任命研究模式')
    for job in jobs.values():
        if job.get('central_target') not in (None, 8, 9):
            raise ValueError('中央示例目标只能为8或9')
        if job.get('central_target') is not None and job['tier'] != 4:
            raise ValueError('中央示例岗位必须是帝级竞争槽')
    queue = deque(dict(event) for event in events)
    score_cache = {}
    result = {key: [0]*4 for key in ('appointments', 'high_wins_with_low',
               'competitive_events', 'high_new', 'merit_advantage', 'transfer_release')}
    result.update(transfers=[], uncovered_events=[], grant_flows=[],
                  processed_events=[], duplicate_events=[], held_events=[],
                  transfer_count=0, uncovered_count=0)
    while queue:
        event = queue.popleft()
        jid = event['job_id']
        job = jobs[jid]
        token = _identity(job, event)
        record = dict(job_id=jid, reason=event['reason'], event_id=token, year=year)
        seen = job.setdefault('_succession_seen', [])
        if token in seen:
            result['duplicate_events'].append(record)
            continue
        seen.append(token)
        # 不因重评请求把有效现任者拿下，只有调用者已释放的岗位可承接。
        if job.get('holder') is not None:
            result['held_events'].append(record)
            continue
        event_seed = int.from_bytes(hashlib.sha256(json.dumps(
            [seed, year, jid, token, 'succession'], ensure_ascii=False,
            sort_keys=True, separators=(',', ':')).encode()).digest()[:8], 'big')
        record['random_seed'] = event_seed
        result['processed_events'].append(record)
        candidates = [p for p in people.values()
                      if appointments.eligible(p, job, jobs, year)]
        winner, metrics = _choose_cached(candidates, job, year, event_seed, mode, score_cache)
        if winner is None:
            job['uncovered'] = True
            result['uncovered_events'].append(record)
            result['uncovered_count'] += 1
            continue
        b = job['tier'] - 1
        result['appointments'][b] += 1
        result['competitive_events'][b] += int(metrics['suitable_available'])
        result['high_wins_with_low'][b] += int(metrics['winner_high_band'] and metrics['suitable_available'])
        result['high_new'][b] += int(metrics['winner_high_band'])
        result['merit_advantage'][b] += int(metrics['merit_advantage_proxy'])
        old = winner.get('job')
        if old is not None:
            old_job = jobs[old]
            if old_job.get('holder') != winner['id']:
                raise ValueError('迁任来源持有人与人物job指针不一致')
            old_job['holder'] = None
            winner['job'] = None
            flow = dict(person_id=winner['id'], source=old, target=jid,
                        year=year, event_id=token)
            result['transfers'].append(flow)
            result['transfer_count'] += 1
            result['transfer_release'][old_job['tier']-1] += 1
            # 新释放构成新事件，而不是本年度已处理过该槽就永久跳过。
            # 只引用父标识的稳定摘要，避免迁任链逐代JSON转义产生指数膨胀。
            # 完整父标识仍保存在本次transfers/processed_events中供诊断。
            parent_digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
            queue.append(dict(job_id=old, reason='transfer',
                              event_id=['transfer', jid, parent_digest, winner['id'], old]))
        winner['job'] = jid
        winner['cooldown_until'] = year + 5
        job['holder'] = winner['id']
        job['uncovered'] = False
        if winner.get('first_job') is None:
            winner['first_job'] = year
            winner['first_job_rank'] = winner['rank']
            winner['first_job_tier'] = job['tier']
        target = job.get('central_target')
        if target is not None and winner['rank'] < target:
            source = winner['rank']
            before = winner.get('m', 0)
            winner['rank'] = target
            winner['m'] = TH[target]
            winner['central_year'] = year
            result['grant_flows'].append(dict(person_id=winner['id'], source=source,
                target=target, job_id=jid, year=year, event_id=token,
                merit_before=before, merit_after=TH[target]))
    return result
