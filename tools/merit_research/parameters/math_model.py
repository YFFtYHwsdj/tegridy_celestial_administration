"""逐带员额参数的离线数学层，不是原生游戏业务实现。

J按九八、七六、五四、三二一四带给出独立竞争头衔数量。默认直接逐带
计算K=kJ；reserve只有显式传入才增加自上而下的周转储备，不引入全国
总预算再分配。标量固定点采用“本年普通流入，再比例退出”的理想时点，
只用于解释控制器参数；真实健康、候选供给和中央授品仍由生涯模型处理。
"""
from fractions import Fraction
import math
from numbers import Real

VERSION='band-parameter-math-v1'


def _number(value,name):
    """将有限实数转精确分数；布尔不作为0/1参数隐式接受。"""
    if isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(value):
        raise ValueError(f'{name}须为有限实数')
    return Fraction(str(value))


def _vector(value,size,name):
    """标量广播；序列必须恰好有指定长度，不截断或补默认值。"""
    if isinstance(value,Real):
        return [_number(value,name)]*size
    try:
        items=list(value)
    except TypeError as exc:
        raise ValueError(f'{name}须为标量或{size}项序列') from exc
    if len(items)!=size:
        raise ValueError(f'{name}须恰好{size}项')
    return [_number(v,f'{name}[{i}]') for i,v in enumerate(items)]


def policy_parameters(r=.06,gain=.6,temperature=.5):
    """集中验证年度补充、恢复和功绩温度；不把它们解释为真实退出率。"""
    rr=_number(r,'r');gg=_number(gain,'gain');tt=_number(temperature,'temperature')
    if rr<=0 or not 0<gg<=1 or tt<=0:
        raise ValueError('要求r>0、0<gain<=1、temperature>0')
    return dict(r=float(rr),gain=float(gg),temperature=float(tt))


def targets(J,unused_mapping=None,r=.06,epsilon=.1,candidate_fraction=.25,
            coefficients=1.5,phi=.6,reserve=(0,0,0)):
    """返回四带员额、七状态目标、六尾目标和必要供给诊断。

    unused_mapping仅兼容联合研究调用，不参与计算。J是非负整数序列；
    coefficients为共同标量或四带非负系数，phi为共同标量或前三带比例。
    epsilon和coefficients只通过乘积影响目标，第一带k和phi也存在乘积
    不可辨识；不能将相同目标的重复参数组合称为独立标定证据。
    candidate_fraction只作明确的离线必要条件，不改变K或年度实际E。
    reserve为三个非负系数，默认均0；从第三带向第一带取
    K_b=max(k_bJ_b, reserve_b*sum(K_above))，额外储备单独返回。
    """
    try:
        items=list(J)
    except TypeError as exc:
        raise ValueError('J须为四带序列') from exc
    if len(items)!=4:
        raise ValueError('J须恰好四带')
    slots=[_number(v,f'J[{i}]') for i,v in enumerate(items)]
    if any(v<0 or v.denominator!=1 for v in slots):
        raise ValueError('J须为非负整数头衔数')
    kk=_vector(coefficients,4,'coefficients');pp=_vector(phi,3,'phi')
    eta=_vector(reserve,3,'reserve')
    rr=_number(r,'r');ee=_number(epsilon,'epsilon');cc=_number(candidate_fraction,'candidate_fraction')
    if any(k<0 for k in kk) or any(x<0 for x in eta):
        raise ValueError('员额和储备系数不得为负')
    if any(not 0<p<1 for p in pp):
        raise ValueError('各带phi须严格位于0与1之间')
    if rr<=0 or ee<0 or not 0<cc<=1:
        raise ValueError('要求r>0、epsilon>=0、0<candidate_fraction<=1')
    base=[k*j for k,j in zip(kk,slots)];K=base[:]
    for b in range(2,-1,-1):
        K[b]=max(base[b],eta[b]*sum(K[b+1:],Fraction(0)))
    T=[(1+ee)*k for k in K]
    grade=[]
    for t,p in zip(T[:3],pp):
        grade.extend([(1-p)*t,p*t])
    grade.append(T[3])
    B=[sum(grade[i+1:],Fraction(0)) for i in range(6)]
    flow=[rr*b for b in B]
    needed=[f/n if n else Fraction(0) if not f else None for n,f in zip(grade,flow)]
    zero=[i+1 for i,(n,b) in enumerate(zip(grade,B)) if not n and b>0]
    return dict(version=VERSION,mapping='direct_band_with_explicit_reserve',J=list(map(int,slots)),
                coefficients=list(map(float,kk)),phi=list(map(float,pp)),epsilon=float(ee),r=float(rr),
                base_K=list(map(float,base)),K=list(map(float,K)),T=list(map(float,T)),
                reserve_eta=list(map(float,eta)),reserve=[float(k-b) for k,b in zip(K,base)],
                target=list(map(float,grade)),B=list(map(float,B)),
                required_annual_flow=list(map(float,flow)),
                required_candidate_fraction=[float(x) if x is not None else None for x in needed],
                candidate_fraction=float(cc),zero_source_boundaries=zero,
                feasible_at_candidate_fraction=all(x is not None and x<=cc for x in needed),
                possible_with_all_candidates=all(x is not None and x<=1 for x in needed))


def quota_expectation(S,B,r=.06,gain=.6):
    """未截来源的标量期望额度；不估计年度候选或执行人物授品。

    B=0时额度为0。实数数学下B>0、r>0且有限S意味着正期望；本函数
    的浮点可表示范围不能替代正式引擎的定点精度与chance验收。
    """
    params=policy_parameters(r,gain)
    ss=float(_number(S,'S'));bb=float(_number(B,'B'))
    if ss<0 or bb<0:
        raise ValueError('S和B不得为负')
    if bb==0:
        return 0.
    q0=params['r']*bb
    if not math.isfinite(q0):
        raise ValueError('rB超出浮点可表示范围')
    if ss<=bb:
        return q0+params['gain']*(bb-ss)
    return q0/(1+params['gain']*(ss-bb)/q0)


def scalar_equilibrium(B=100,d=.04,r=.06,gain=.6,C=0):
    """求理想S_next=(1-d)(S+q(S))+C的唯一非负固定点与局部倍率。

    假设来源无限、每次授品成功、比例退出恒定、C为退出后的非负外部
    净流入；并非真实人口的全局稳定性证明。0<d<1保证有限唯一根。
    C<0可能导致低人口处不可行，需另定义状态截断，不在本助手中暗加。
    """
    params=policy_parameters(r,gain)
    bb=float(_number(B,'B'));dd=float(_number(d,'d'));cc=float(_number(C,'C'))
    if bb<0 or not 0<dd<1 or cc<0:
        raise ValueError('要求B>=0、0<d<1、C>=0')
    def residual(s):
        return (1-dd)*(s+quota_expectation(s,bb,**{k:params[k] for k in ('r','gain')}))+cc-s
    low=0.;high=max(1.,bb,cc/dd)
    while residual(high)>0:
        high*=2
        if not math.isfinite(high):
            raise ValueError('固定点超出浮点可表示范围')
    for _ in range(100):
        middle=(low+high)/2
        if residual(middle)>0:
            low=middle
        else:
            high=middle
    point=(low+high)/2
    if bb==0:
        slope=0.
    elif point<=bb:
        slope=-params['gain']
    else:
        denominator=1+params['gain']*(point-bb)/(params['r']*bb)
        slope=-params['gain']/denominator**2
    multiplier=(1-dd)*(1+slope)
    return dict(S=point,B=bb,d=dd,r=params['r'],gain=params['gain'],C=cc,
                ratio=point/bb if bb else None,
                q=quota_expectation(point,bb,r=params['r'],gain=params['gain']),
                local_multiplier=multiplier,fixed_point_residual=residual(point),
                local_half_life=math.log(.5)/math.log(multiplier) if 0<multiplier<1 else 0.)


def rounding_moments(q):
    """相邻随机取整的精确理论矩；保留零名额年，不添加年度保底。"""
    value=float(_number(q,'q'))
    if value<0:
        raise ValueError('q不得为负')
    floor=math.floor(value);fraction=value-floor
    return dict(mean=value,variance=fraction*(1-fraction),
                zero_probability=1-fraction if floor==0 else 0.)
