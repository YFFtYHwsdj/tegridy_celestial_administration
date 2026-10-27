"""独立竞争槽到员额的候选数学映射；不执行或复制游戏晋升业务。

J按九八、七六、五四、三二一四带给出可独立任命/继承的槽数量；一个槽只归一带。
不能将旧在职需求D=516直接视作J。前三带目标固定低品40%/高品60%，最高带合计。
reserve仅表示递归修正超过映射基础K的额外梯队储备；K-J另由staff_over_slots报告。
本文件只拥有映射与必要供给条件，不改变年度控制器、功绩抽选或健康模型。
"""
from fractions import Fraction
import math
from numbers import Real

MAPPINGS=('uniform1.5','uniform2','uniform3','tiered','transit2')
PHI=Fraction(3,5)
VERSION='capacity-candidate-v1'


def _number(value,name):
    """拒绝非有限、布尔和非数字输入，避免非法参数混入JSON或暗套默认。"""
    if isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(value):
        raise ValueError(f'{name}必须是有限数字')
    return Fraction(str(value))


def _targets_from_K(K,r,epsilon,candidate_fraction):
    """从带总量拆唯一目标；供审计作等总量对照，不属于游戏运行接口。"""
    T=[(1+epsilon)*k for k in K]
    per_grade=[]
    for t in T[:3]:per_grade.extend(((1-PHI)*t,PHI*t))
    per_grade.append(T[3])
    B=[sum(per_grade[i+1:],Fraction(0)) for i in range(6)]
    flows=[r*b for b in B]
    required=[flow/per_grade[i] if per_grade[i]>0 else Fraction(0) if flow==0 else None for i,flow in enumerate(flows)]
    feasible=all(x is not None and x<=candidate_fraction for x in required)
    return {'T':list(map(float,T)),'target':list(map(float,per_grade)),
            'B':list(map(float,B)),'required_annual_flow':list(map(float,flows)),
            'required_candidate_fraction':[float(x) if x is not None else None for x in required],
            'feasible_at_candidate_fraction':feasible,
            'possible_with_all_candidates':all(x is not None and x<=1 for x in required)}


def targets(J,mapping='transit2',r=.04/.96,candidate_fraction=.25,epsilon=.1):
    """返回候选K/T/七状态target/六尾B及必要供给比例，不修改输入。

    r是固定离线周转参数，不是已识别的原版死亡率；candidate_fraction是人工条件。
    transit2从2J出发、自上而下补储备：低品供给需
    (.4c-.6r)T >= rU，高品供给需 .6cT >= rU。
    取eta=max(r/(.4c-.6r),r/(.6c))，Kb=max(2Jb,eta*sum(Kabove))。
    若分母非正且有需求，则没有有限储备可满足该四六目标，明确拒绝此配置。
    正常返回的可达标记只证明上述必要供给不等式，不能保证真实Merit/资格/动态可达。
    """
    if mapping not in MAPPINGS:raise ValueError('未知员额映射')
    try:items=list(J)
    except TypeError as exc:raise ValueError('J必须是四带数量序列') from exc
    if len(items)!=4:raise ValueError('J必须正好四带')
    slots=[_number(v,f'J[{i}]') for i,v in enumerate(items)]
    if any(v<0 or v.denominator!=1 for v in slots):raise ValueError('J必须是非负整数槽数量')
    rr=_number(r,'r');cc=_number(candidate_fraction,'candidate_fraction');ee=_number(epsilon,'epsilon')
    if rr<0:raise ValueError('r不得为负')
    if not 0<cc<=1:raise ValueError('candidate_fraction须在(0,1]')
    if ee<0:raise ValueError('epsilon不得为负')
    coefficients={'uniform1.5':[Fraction(3,2)]*4,'uniform2':[Fraction(2)]*4,
                  'uniform3':[Fraction(3)]*4,'tiered':[Fraction(5,2),Fraction(3,2),Fraction(3,2),Fraction(3)],
                  'transit2':[Fraction(2)]*4}[mapping]
    base=[k*j for k,j in zip(coefficients,slots)];K=base[:];eta=None
    if mapping=='transit2':
        denominator=(1-PHI)*cc-PHI*rr
        if denominator<=0:
            if any(slots):raise ValueError('四六目标的低品供给分母非正，无有限周转储备可满足')
        else:
            eta=max(rr/denominator,rr/(PHI*cc))
            for b in range(2,-1,-1):K[b]=max(base[b],eta*sum(K[b+1:],Fraction(0)))
    out=_targets_from_K(K,rr,ee,cc)
    out.update({'version':VERSION,'mapping':mapping,'J':list(map(int,slots)),
                'K':list(map(float,K)),'base_K':list(map(float,base)),
                'reserve':[float(k-b) for k,b in zip(K,base)],
                'staff_over_slots':[float(k-j) for k,j in zip(K,slots)],
                'transit_eta':float(eta) if eta is not None else None,
                'r':float(rr),'candidate_fraction':float(cc),'epsilon':float(ee),'phi':float(PHI),
                'assumptions':['J为给定独立槽，未从旧探针D识别','r与候选可用率是人工离线条件，非原版实测',
                               '共同epsilon允许在递归储备不等式中约去','供给条件必要而非真实动态可达充分条件',
                               'target末状态是三二一合计，不拆最高三品内部比例']})
    return out
