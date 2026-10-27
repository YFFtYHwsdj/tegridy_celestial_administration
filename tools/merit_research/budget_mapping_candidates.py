"""总员额预算内重分配的独立数学候选，不接入游戏业务。

四级J每槽只计一次；文武调用相同函数。最高带为1.5J4，可选top_extra
仅在有最高槽时生效；前三带至少保留各自J，余量同比分配或中带优先。理想储备可以
因预算压缩而不满足，输出明确保留缺口和零来源，绝不宣称结构已可达。
运行本文件只做纯数学自检，既不演算逐人生涯，也不产生入库产物。
"""
from fractions import Fraction
import math
from numbers import Real


MODES = ('surplus', 'priority8', 'priority6', 'priority10', 'pipeline')


def _number(value, name):
    """有限实数转精确分数；拒绝布尔和无穷，以免预算静默失真。"""
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f'{name}必须是有限实数')
    return Fraction(str(value))


def allocate(J, mode='priority8', budget_factor=3, top_extra=0, top_factor=1.5, base_share=.5, middle_share=.5):
    """返回四带K及预算诊断；J为四个非负整数，不修改输入。

surplus按所有前三带的理想增量同比缩放；预算富余时允许同比扩展。
priority8/6/10先满足五四、七六的理想增量，若不够则只同比压缩这两个
中带的J以上部分；最低带先保留共同管道floor，再领取余量。预算不够保基本四级
供给时直接拒绝。top_extra仅在J4>0时增加最高带存量预算，不是年度
名额保底；非零值破坏严格规模齐次。该函数不读取n/E、路线或人物健康。
"""
    if mode not in MODES:
        raise ValueError('未知预算映射候选')
    slots = [_number(v, f'J[{i}]') for i, v in enumerate(J)]
    if len(slots) != 4 or any(v < 0 or v.denominator != 1 for v in slots):
        raise ValueError('J须为四个非负整数')
    factor = _number(budget_factor, 'budget_factor')
    if factor <= 0:
        raise ValueError('budget_factor必须为正')
    extra = _number(top_extra, 'top_extra')
    if extra < 0:
        raise ValueError('top_extra不得为负')
    budget = factor * sum(slots)
    applied_extra = extra if slots[3] > 0 else Fraction(0)
    top_coefficient = _number(top_factor, 'top_factor')
    if top_coefficient < 1:
        raise ValueError('top_factor不得小于1')
    top = top_coefficient * slots[3] + applied_extra
    if mode == 'pipeline':
        # 高品可任低职，不再要求每带K>=本级J；半数本地基数加共同周转池。
        beta = _number(base_share, 'base_share')
        if not 0 <= beta <= 1:
            raise ValueError('base_share须在0与1之间')
        remainder = budget - top - beta * sum(slots[:3])
        if remainder < 0:
            raise ValueError('预算不足以支付最高带及本地基数')
        middle = _number(middle_share, 'middle_share')
        if not 0 < middle < Fraction(9, 10):
            raise ValueError('middle_share必须在0与.9之间')
        weights = [Fraction(1, 10), middle, Fraction(9, 10)-middle]
        K = [beta*j + w*remainder for j,w in zip(slots[:3],weights)] + [top]
        return dict(mode=mode,J=list(map(int,slots)),K=list(map(float,K)),
            total_budget=float(budget),budget_factor=float(factor),top_factor=float(top_coefficient),
            top_extra=float(extra),applied_top_extra=float(applied_extra),base_share=float(beta),pool_weights=list(map(float,weights)),
            strictly_scale_homogeneous=extra==0,low_floor=float(beta*slots[0]),
            source_zero=any(K[i]==0 and sum(K[i+1:])>0 for i in range(3)),
            desired_K=list(map(float,K)),wish_shortfall=[0.]*4,
            middle_wish_met=None,increment_scale=None,
            zero_transit_bands=[i+1 for i in range(3) if K[i]==0 and sum(K[i+1:])>0],
            warning='跨级任职允许各带K低于J；周转池权重为粗筛假设，不代表自然人口')
    floors = slots[:3]
    remaining = budget - top - sum(floors)
    if remaining < 0:
        raise ValueError('预算不足以保留前三带J及最高带1.5J4+有效top_extra')
    low_floor = slots[0]
    if mode != 'surplus':
        # 预算越紧最多取中层基本供给后余量的一半；有余量时保正的低带管道。
        # 正常与零中层的J1本身更大，不受此floor影响。
        low_floor = max(slots[0], min(budget / 5, (budget - top - slots[1] - slots[2]) / 2))
        floors[0] = low_floor
        remaining = budget - top - sum(floors)

    eta3 = Fraction(6 if mode == 'priority6' else 10 if mode == 'priority10' else 8)
    middle3 = max(8 * slots[2], eta3 * top)
    middle2 = max(4 * slots[1], Fraction(3, 2) * (middle3 + top))
    lower = max(3 * slots[0], Fraction(15, 16) * (middle2 + middle3 + top))
    desired = [lower, middle2, middle3, top]
    extras = [d - f for d, f in zip(desired[:3], floors)]

    if mode == 'surplus':
        total_extra = sum(extras)
        scale = remaining / total_extra if total_extra else Fraction(0)
        K = [f + scale * e for f, e in zip(floors, extras)] + [top]
        if not total_extra and remaining:
            K[0] += remaining
    else:
        wanted = extras[1] + extras[2]
        scale = min(Fraction(1), remaining / wanted) if wanted else Fraction(0)
        second = floors[1] + scale * extras[1]
        third = floors[2] + scale * extras[2]
        K = [budget - top - second - third, second, third, top]

    assert sum(K) == budget and K[3] == top
    assert all(k >= j for k, j in zip(K, slots))
    gaps = [max(Fraction(0), d - k) for d, k in zip(desired, K)]
    zero_sources = [i + 1 for i in range(3) if K[i] == 0 and sum(K[i + 1:]) > 0]
    return dict(mode=mode, J=list(map(int, slots)), K=list(map(float, K)),
                total_budget=float(budget), budget_factor=float(factor),
                top_extra=float(extra), top_factor=float(top_coefficient), applied_top_extra=float(applied_extra),
                strictly_scale_homogeneous=extra == 0,
                low_floor=float(low_floor), source_zero=bool(zero_sources),
                desired_K=list(map(float, desired)), wish_shortfall=list(map(float, gaps)),
                middle_wish_met=not any(gaps[1:3]),
                increment_scale=float(scale),
                zero_transit_bands=zero_sources,
                warning='预算内重分配；愿望缺口或零来源不等于已证明生涯可达')


def targets(J, unused_mapping=None, *, mode='priority8', budget_factor=3, top_extra=0,
            r=.06, candidate_fraction=.25, epsilon=.1, phi=.6, top_factor=1.5, base_share=.5, middle_share=.5):
    """兼容联合研究映射调用，返回K/T/七状态target/六尾B及必要条件。

unused_mapping接收既有trial传入的映射标签，实际方案由mode决定。
候选供给条件只是离线必要性诊断；缺口不改变预算，也不自动放宽。
"""
    out = allocate(J, mode, budget_factor, top_extra, top_factor, base_share, middle_share)
    rr = _number(r, 'r')
    cc = _number(candidate_fraction, 'candidate_fraction')
    ee = _number(epsilon, 'epsilon')
    if rr < 0 or not 0 < cc <= 1 or ee < 0:
        raise ValueError('要求r>=0、0<candidate_fraction<=1、epsilon>=0')
    pp = _number(phi, 'phi')
    if not 0 < pp < 1:
        raise ValueError('phi必须在0与1之间')
    K = [Fraction(str(k)) for k in out['K']]
    T = [(1 + ee) * k for k in K]
    per_grade = []
    for t in T[:3]:
        per_grade.extend([(1 - pp) * t, pp * t])
    per_grade.append(T[3])
    B = [sum(per_grade[i + 1:]) for i in range(6)]
    flows = [rr * b for b in B]
    required = [flow / n if n else Fraction(0) if not flow else None
                for flow, n in zip(flows, per_grade)]
    out.update(T=list(map(float, T)), target=list(map(float, per_grade)), B=list(map(float, B)),
               required_annual_flow=list(map(float, flows)),
               required_candidate_fraction=[float(v) if v is not None else None for v in required],
               feasible_at_candidate_fraction=all(v is not None and v <= cc for v in required),
               possible_with_all_candidates=all(v is not None and v <= 1 for v in required))
    return out


def self_check():
    """确定性审计边界、同总量形状、比例缩放及基本职位供给，不跑生涯。"""
    cases = [[0, 0, 0, 0], [100, 0, 0, 5], [75, 20, 5, 5],
             [0, 0, 0, 5], [100, 0, 0, 0], [0, 0, 5, 0],
             [0, 5, 0, 0], [3, 1, 1, 1], [348, 59, 15, 8], [63, 19, 3, 1]]
    checks = 0
    for mode in [m for m in MODES if m != 'pipeline']:
        for J in cases:
            result = targets(J, mode=mode)
            scaled = targets([7 * j for j in J], mode=mode)
            assert math.isclose(sum(result['K']), 3 * sum(J), abs_tol=1e-9)
            assert all(k >= j for k, j in zip(result['K'], J))
            assert result['K'][3] == 1.5 * J[3]
            assert math.isclose(sum(result['target']), 3.3 * sum(J), abs_tol=1e-9)
            for a, b in zip(result['K'], scaled['K']):
                assert math.isclose(7 * a, b, abs_tol=1e-9)
            checks += 8
        assert targets(cases[1], mode=mode)['total_budget'] == targets(cases[2], mode=mode)['total_budget']
        checks += 1
    assert targets([100, 0, 0, 5])['K'] == [146.25, 101.25, 60., 7.5]
    assert targets([0, 0, 0, 5])['zero_transit_bands'] == []
    assert not targets([0, 0, 0, 5])['feasible_at_candidate_fraction']
    for J in [[1, 2, 3], [-1, 0, 0, 0], [True, 0, 0, 0], [.5, 0, 0, 0]]:
        try:
            targets(J)
        except ValueError:
            pass
        else:
            raise AssertionError('非法J未拒绝')
    try:
        targets([0, 0, 0, 1], budget_factor=1)
    except ValueError:
        pass
    else:
        raise AssertionError('基本职位预算不足未拒绝')
    no_top = targets([10, 2, 1, 0], top_extra=1)
    assert no_top['K'][3] == 0 and no_top['applied_top_extra'] == 0
    assert targets([0, 0, 0, 0], top_extra=1)['K'] == [0.] * 4
    small = targets([3, 1, 1, 1], top_extra=1)
    assert math.isclose(sum(small['K']), 18., abs_tol=1e-9) and small['K'][3] == 2.5
    assert all(k >= j for k, j in zip(small['K'], [3, 1, 1, 1]))
    assert not small['strictly_scale_homogeneous']
    normal = targets([348, 59, 15, 8], top_extra=1)
    assert normal['K'] == [921., 236., 120., 13.]
    assert targets([100, 0, 0, 5], mode='priority10')['K'] == [108.75, 123.75, 75., 7.5]
    top_only = targets([0, 0, 0, 1], top_extra=1)
    assert top_only['low_floor'] == .25 and all(k > 0 for k in top_only['K'])
    assert not top_only['source_zero'] and not top_only['possible_with_all_candidates']
    top_heavy = targets([15, 25, 40, 40])
    assert top_heavy['low_floor'] == 72. and not top_heavy['source_zero']
    assert math.isclose(sum(top_heavy['K']), 360., abs_tol=1e-9)
    assert max(top_heavy['required_candidate_fraction'][:2]) <= .7
    for kwargs in [dict(top_extra=-1), dict(top_extra=1, budget_factor=2)]:
        try:
            targets([0, 0, 0, 1], **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError('非法最高带额外预算或基本预算不足未拒绝')
    return checks + 22


if __name__ == '__main__':
    import json
    print(json.dumps(dict(checks=self_check(), cases={mode:targets([100, 0, 0, 5], mode=mode)
                                                    for mode in MODES}), ensure_ascii=False, indent=2))
