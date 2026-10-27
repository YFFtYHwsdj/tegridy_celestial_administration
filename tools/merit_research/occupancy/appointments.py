"""纯研究用的职务资格与任命近似，不接入CK3，不宣称复刻引擎。

本次主研究按用户要求抽象为伯/公/王/帝四级可继承竞争槽数量，
不是具体县、公国或任何真实头衔对象；main统一使用kind=admin。
本模块保留office初次补位支持作为可选接口，不自动混入主情景。

依据：原版defines APPOINTMENT_MERIT_TIER；succession_appointment的
lower_or_equal/cooldown；游戏概念的Merit等级优先、分数次序及同tier
prominence限制。本模组首次/纠错官署补位按正候选分加权。

边界：每人至多一个独立实职；不把附属领地/家门当独立岗位。
choose只接收调用者已eligible过滤的候选，不维护任命/卸任/冷却。
自然任命的两键排序是文案支持的研究假设，尚未全矩阵引擎验证。
score是人工基础分，年龄和病理仅加局部已知项，不是完整原生评分。
"""
import hashlib
import json
import math

MIN_RANK = {1: 1, 2: 3, 3: 5, 4: 7}
MODES = frozenset({'merit_first', 'score_only', 'suitable_first'})
INITIAL_ENTRIES = frozenset({'initial', 'initial_office', 'repair', 'initial_repair'})
SOURCE_REFS = {
    'threshold': 'game/common/defines/00_defines.txt:NAdministrative.APPOINTMENT_MERIT_TIER',
    'qualification': 'game/common/succession_appointment/_succession_appointment.info',
    'ordering': 'game/localization/english/dlc/tgp/dlc_tgp_china_game_concepts_l_english.yml:game_concept_merit_pool_desc',
    'score_groups': 'game/common/script_values/07_appointment_values.txt:appointment_score_base,appointment_score_civic',
    'age': 'game/common/succession_appointment/celestial_governor.txt,celestial_minister.txt',
    'initial_office': 'mod/common/scripted_effects/tca_tongpan_effects.txt,tca_judicial_appointment_effects.txt',
}
ASSUMPTIONS = {
    'adult_age': 16,
    'default_retirement_age': 70,
    'one_independent_job_per_person': True,
    'mode_changes_qualification': False,
    'pathology_disqualifies': False,
    'natural_tie_break': '稳定哈希平分；原生同分规则未验证',
    'military_score': '未复刻军政评分；如需军政，请调用者提供人工基础与score_delta并明确情景',
}


def _tier(job):
    tier = job['tier']
    if tier not in MIN_RANK:
        raise ValueError('研究岗位tier必须为1..4')
    return tier


def rank_band(rank):
    """原生等级映射四带；不读实际职务等级。"""
    if rank not in range(1, 10):
        raise ValueError('已入品研究人物rank必须为1..9')
    return min(4, (rank + 1) // 2)


def eligible(person, job, jobs, year, mobility=True):
    """只判断研究资格，不修改人物/岗位；jobs为id到岗位的映射。

    active表示愿意参加新任命。拒任仍在职者由外层保留holder，
    本函数不因active=False卸职。cooldown_until与year同单位；
    year恰等于到期值即允许。mobility=False为禁止在任迁任的控制情景。
    """
    tier = _tier(job)
    rank = person['rank']
    if rank not in range(1, 10):
        return False
    if (not person.get('active', True) or not person.get('alive', True)
            or person.get('age', 0) < ASSUMPTIONS['adult_age']
            or year < person.get('cooldown_until', 0)
            or rank < MIN_RANK[tier] or job.get('holder') == person['id']):
        return False
    current_id = person.get('job')
    if current_id is None:
        return True
    if not mobility or job.get('kind') == 'office':
        return False
    current = jobs.get(current_id)
    if current is None:
        # 悬空指针不能解释成无职，避免产生虚假的迁任机会。
        return False
    current_tier = _tier(current)
    if current_tier > tier:
        return False
    if current_tier == tier:
        return job.get('prominence', 0) > current.get('prominence', 0)
    return True


def _round_away(value):
    """研究用最近整数，半点远离0；不采用Python银行家舍入。"""
    return math.floor(value + .5) if value >= 0 else math.ceil(value - .5)


def score_components(person, job=None):
    """返回人工基础分及局部delta；不能解释为完整原生候选评分。

    地方/官署使用文官近似；central仅采用原版中央年龄项，不加civic精神项。
    elderly ailments属于一组−50，不按病数累计。incapable的−50和
    地方civic的−100来自不同块，可以叠加；不因此取消候选资格。
    """
    central = (job or {}).get('kind') == 'central'
    age = person.get('age', 40)
    retirement = person.get('retirement_age', ASSUMPTIONS['default_retirement_age'])
    if retirement is not None and age >= retirement:
        age_delta = _round_away((retirement-age)/(4 if central else 2))
    elif age >= 40:
        age_delta = 10 if central else 15
    elif age < 30:
        age_delta = -5 if central else -10
    else:
        age_delta = 0
    grouped = any((person.get('blind'), person.get('incapable'), person.get('inbred'),
                   person.get('age_related_ailment'), person.get('elder_count', 0) > 0))
    mental = person.get('incapable') or person.get('mental_unwell')
    return {
        'base': float(person.get('score', 0)),
        'age': age_delta,
        'grouped_pathology': -50 if grouped else 0,
        'civic_mental': -100 if mental and not central else 0,
        'scenario_delta': float(person.get('score_delta', 0)),
    }


def synthetic_score(person, job=None):
    """人工分数＋明确局部修正，只用于职务分配研究。"""
    value = sum(score_components(person, job).values())
    if not math.isfinite(value):
        raise ValueError('人工评分必须为有限数')
    return value


def _uniform(seed, year, job_id, entry, purpose, person_id=None):
    """无共享状态的计数器式随机；新增其他随机调用不改变已有结果。"""
    payload = json.dumps([seed, year, job_id, entry, purpose, person_id],
                         ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    number = int.from_bytes(hashlib.sha256(payload.encode('utf-8')).digest()[:8], 'big')
    return (number + .5) / 2**64


def choose(candidates, job, year, seed, mode='merit_first', entry='natural'):
    """返回(原候选dict或None,研究指标)；候选必须已按相同资格过滤。

    natural：文案支持的Merit/score词典序假设；score_only与suitable_first
    仅作固定候选集反事实，不改变资格。initial/repair官署用max(1,score)
    正权抽取；适品优先对照先限适品集合再使用相同入口机制。
    metrics中的merit_advantage_proxy仅是同次机会下的排序敏感性，非因果证据。
    """
    tier = _tier(job)
    if mode not in MODES or entry not in INITIAL_ENTRIES | {'natural'}:
        raise ValueError('未知研究选择模式或入口')
    people = sorted(candidates, key=lambda p: (str(type(p['id'])), str(p['id'])))
    if len({p['id'] for p in people}) != len(people):
        raise ValueError('候选id不能重复')
    suitable = [p for p in people if rank_band(p['rank']) == tier]
    scores = {p['id']: synthetic_score(p, job) for p in people}
    weighted = job.get('kind') == 'office' and entry in INITIAL_ENTRIES

    def select(pool, policy):
        if not pool:
            return None
        if policy == 'suitable_first':
            fitting = [p for p in pool if rank_band(p['rank']) == tier]
            pool = fitting or pool
        if weighted:
            # 同一随机分位数给对照使用；候选顺序稳定，不借用全局RNG。
            weights = [max(1., scores[p['id']]) for p in pool]
            threshold = _uniform(seed, year, job['id'], entry, 'weighted_draw') * sum(weights)
            cumulative = 0.
            for p, weight in zip(pool, weights):
                cumulative += weight
                if threshold < cumulative:
                    return p
            return pool[-1]
        # 先比较确定性主键；只有完全并列者才需要原有哈希平分。
        # 保持pool次序及原hash输入，故包括hash碰撞时的首项规则也不变。
        best_key = None
        tied = []
        for p in pool:
            key = (p['rank'] if policy != 'score_only' else 0, scores[p['id']])
            if best_key is None or key > best_key:
                best_key, tied = key, [p]
            elif key == best_key:
                tied.append(p)
        if len(tied) == 1:
            return tied[0]
        return max(tied, key=lambda p:
                   _uniform(seed, year, job['id'], entry, 'tie', p['id']))

    winner = select(people, mode)
    counterfactual = select(people, 'score_only')
    high = winner is not None and rank_band(winner['rank']) > tier
    score_only_suitable = counterfactual is not None and rank_band(counterfactual['rank']) == tier
    best_fitting = max((scores[p['id']] for p in suitable), default=None)
    winner_score = None if winner is None else scores[winner['id']]
    return winner, {
        'candidate_count': len(people),
        'suitable_count': len(suitable),
        'suitable_available': bool(suitable),
        'winner_high_band': high,
        'winner_band': None if winner is None else rank_band(winner['rank']),
        'winner_score': winner_score,
        'score_only_winner_id': None if counterfactual is None else counterfactual['id'],
        'score_only_suitable': score_only_suitable,
        'merit_advantage_proxy': bool(mode == 'merit_first' and not weighted and high and score_only_suitable),
        'high_candidate_fraction': (sum(rank_band(p['rank']) > tier for p in people)/len(people)
                                    if people else None),
        'best_suitable_score': best_fitting,
        'score_gap_to_best_suitable': (winner_score-best_fitting
                                       if winner is not None and best_fitting is not None else None),
        'mode': mode, 'entry': entry,
        'selection_assumption': 'positive_score_weight' if weighted else 'lexicographic_research_assumption',
        'causal_evidence': False,
    }
