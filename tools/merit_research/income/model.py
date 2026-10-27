"""按来源分账的功绩外部输入；不按品级赋予固定收入。

系数来自本机原版及模组，出处见README；税额、兵池价值、个人来源、
事件时间和身份由外部显式提供。此处的年度聚合不等于复刻引擎月结。
"""
import math


ROLES={
    'none':dict(fixed=0,tax=0,maa=0),
    'civil_standard':dict(fixed=0,tax=.8,maa=0),
    'civil_industrial':dict(fixed=0,tax=1.2,maa=0),
    'civil_metropolitan':dict(fixed=0,tax=2.4,maa=0),
    'military':dict(fixed=0,tax=0,maa=.024),
    'protectorate':dict(fixed=0,tax=0,maa=.032),
    'minister':dict(fixed=20,tax=0,maa=0),
    'tongpan':dict(fixed=2,tax=0,maa=0),
    'judicial':dict(fixed=4,tax=0,maa=0),
}


def _finite(value,name,nonnegative=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError(name+'须为有限实数')
    if nonnegative and value<0: raise ValueError(name+'不得为负')
    return value


def annual_components(role='none',personal_fixed=0,head_tier=0,monthly_mult=0,
                      paid_tax=0,maa_value=0,funding_paid=0,extra_tax_coefficient=0,
                      extra_maa_coefficient=0,gain_mult=0):
    """按十二个月聚合，税收/兵池/官署实付不混入基础月倍率。

    paid_tax为月实缴领主税额；maa_value为头衔兵士基础招募价值；
    funding_paid为月实际拨款，不是人物总国库收入或俸禄。这里只接收
    已汇总的实际个人来源和修正；不猜人人拥有庄园、弟子或特长的概率。
    gain_mult为独立change_merit收益修正，默认未附加；与月倍率分开。
    头衔倍率来自实际持有头衔层级，不使用功绩品级。
    """
    if role not in ROLES: raise ValueError('未知实际职务类别')
    if head_tier not in range(6): raise ValueError('头衔层级必须为0至5')
    for name,value in [('paid_tax',paid_tax),('maa_value',maa_value),('funding_paid',funding_paid),
                       ('extra_tax_coefficient',extra_tax_coefficient),('extra_maa_coefficient',extra_maa_coefficient)]:
        _finite(value,name,True)
    for name,value in [('personal_fixed',personal_fixed),('monthly_mult',monthly_mult),('gain_mult',gain_mult)]:
        _finite(value,name)
    source=ROLES[role]
    title_mult={3:.5,4:1}.get(head_tier,0)
    return dict(fixed=12*(source['fixed']+personal_fixed)*max(0,1+monthly_mult+title_mult),
                tax=12*(source['tax']+extra_tax_coefficient)*paid_tax,
                maa=12*(source['maa']+extra_maa_coefficient)*maa_value,
                funding=12*.2*funding_paid*max(0,1+gain_mult),events=0)


def event_reward(event):
    """单次已发生事件的净额；发生率和参与资格由调用端显式给出。

    考试score_factor/grade_factor为已按真实成绩及科等选择的倍率；
    ai_palace_followup仅表示已实际进入条件分支，绝不在这里每年抽20%。
    不把建筑/战争/任务奖励给所有人；raw只供带来源说明的显式事件。
    """
    kind=event['kind']
    if kind=='building':
        return (60+_finite(event['development'],'development',True))*(1+_finite(event.get('estate_bonus',0),'estate_bonus',True))
    if kind in ('task_success','task_failure'):
        return (60 if kind=='task_success' else -30)*_finite(event['scale'],'scale',True)
    if kind=='war':
        return min(1000,_finite(event['fame'],'fame',True)*_finite(event['winner_scale'],'winner_scale',True))
    if kind in ('metropolitan','palace'):
        if 'eligible' not in event: raise ValueError('须明确奖励身份分支')
        if not event['eligible']: return 0
        value=400*_finite(event['score_factor'],'score_factor',True)
        if kind=='palace': value+=2000+.1*_finite(event['score'],'score',True)
        return value*_finite(event['grade_factor'],'grade_factor',True)*(1.1 if event.get('promote_merit') else 1)
    if kind=='ai_palace_followup':
        if event.get('eligible') is not True: raise ValueError('该分支须已满足真实身份与考试条件')
        return 12000
    if kind=='raw':
        if not event.get('source'): raise ValueError('原始事件须注明来源')
        return _finite(event['amount'],'amount')
    raise ValueError('未知功绩事件类别')


def apply_event(person,event):
    """同人物同事件id仅结算一次；考试资格与奖励在同一步更新。

    本函数返回Merit净额，余额由调用端统一记账。既有资格可被后续
    显式考试提高；不再把初始化抽签解释为终身不可改变的潜能。
    """
    if not isinstance(event.get('id'),str) or not event['id']: raise ValueError('事件须有唯一字符串id')
    seen=person.setdefault('merit_events',[])
    if event['id'] in seen: return 0
    reward=event_reward(event)
    if event['kind']=='metropolitan': person['cap']=max(person['cap'],6)
    if event['kind'] in ('palace','ai_palace_followup'): person['cap']=max(person['cap'],9)
    seen.append(event['id'])
    return reward


def initialize_exams(person,uniform,learning=10):
    """AI原生初始化的条件分支代理，仅创建时调用一次。

    learning是显式合成输入，不伪称已采到人物学识；原生初始化使用
    余额而非核定品级判断分支。后续考试由事件输入继续改变cap。
    此代理不自动改核定等级，也不抹去已合法取得的等级。
    """
    if person.get('source_initialized'): raise ValueError('不得重复发初始化奖励')
    merit=person['m'];bonus=0
    if merit>=12000: cap=9
    elif merit>=5500: cap=9 if uniform(101)<.5 else 6
    elif merit>=2000: cap=(9 if uniform(103)<.3 else 6) if uniform(102)<.6 else 4
    else:
        u=uniform(104)
        cap=2 if u<.1 else 4 if u<.6 else 6 if u<.85 else 9
        if cap>2: bonus=100+person['age']+learning
    if 2000<=merit<12000:
        thresholds=[0,100,1000,2000,3500,5500,8500,12000,17000,23000]
        level=max(i for i in range(1,9) if merit>=thresholds[i])
        bonus=thresholds[level+1]-thresholds[level]
    person['cap']=max(person['rank'],cap)
    person['m']+=bonus
    person['source_initialized']=True
    return bonus
