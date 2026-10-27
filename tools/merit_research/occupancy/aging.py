"""年龄健康研究代理：原版参数锚定，绝非原版死亡率/老年事件的精确复刻。

接口返回新dict，不原地修改。年龄是当前已满岁数；每次advance_year推进一岁、12个
月检查。五类老年发生总率、压力/骨病事件、轨道修正叠加及初始健康仍是显式假设。
make_health从合成出生状态模拟到指定年龄，拒绝途中死亡者，得到条件幸存者；
这不是自然新局的年龄/健康分布。超高龄稀有幸存者在采样上限后明确失败，不复活。
"""
from copy import deepcopy
from hashlib import blake2b
import math

VERSION='aging-proxy-v1'
SOURCE_REFS={
 'age_defines':'common/defines/00_defines.txt:325-346',
 'elder_traits':'common/traits/00_traits.txt:6039-6418',
 'elder_onset':'events/health_events.txt:11871-12867',
 'elder_progression':'common/on_action/health_on_actions.txt:57-346',
 'heart_event':'events/stress_events/stress_threshold_events.txt:106-122,163-206',
 'bone_wounds':'common/scripted_effects/20_health_effects.txt:1101-1152',
 'second_chance':'common/scripted_rules/00_rules.txt:454-463; common/on_action/death.txt:2553-2570',
 'queued_natural_death':'events/death_events/death_management_events.txt:6686-6697',
}
ASSUMPTIONS={
 'status':'全部为数学代理；未引擎验收、未按自然样本校准',
 'age_loss':'25岁起原始.075+.022*(age-25)，clamp到1为代理封顶；每次-.125来自defines',
 'natural_curve':'候选插值.25*clamp((3-health)/3,0,1)^2；非已证实引擎函数',
 'health_within_year':'先年度老化/老年变化，再12次月检查；年内健康固定，骨病伤势保留一年',
 'elder_onset_rate':.08,
 'elder_onset':'每年最多一个新病；总强度=.08*有效相对权重和/130，非原版事件池概率',
 'static_group_filter':'未复刻does_not_get_*持久过滤，也未复刻600空事件/其他有效事件的竞争',
 'heart_stress_event_probability':.25,
 'bone_injury_probability':.03,
 'stress_and_injury':'上述年概率是假设；心脏触发+25XP，骨病造成1或1.5健康伤势，不直接删人',
 'tracks':'健康轨道默认按跨过的所有阈值累加，叠加语义未引擎确认；可设state.track_health_mode=highest作对照',
 'birth_health':'Uniform(4,5)仅借随机生成健康范围作合成出生禀赋，不宣称原版新生儿分布',
 'longlife':'额外健康+1.5（好体质最高档+全身心量级），老年发生权重乘.75及一次know_thyself；组合与普及率是假设',
 'no_elder':'仍进行基础年龄健康衰减和自然死亡，只关闭五类老年新发/进展',
 'second_chance':'月粒度到期检查；340-380天延迟原参数，最大一月离散误差；正常死亡延迟15-20天也月末判定',
 'omitted':'其他疾病/战争/谋杀/治疗/压力全链/人口pool惩罚/life_expectancy和elderly_health引擎换算；不把待阙当pool',
 'initial_sampling_limit':4096,
 'random_namespace':'独立aging-v1散列，不消耗父模型的年龄/功绩/任命随机数',
}
KINDS=('infirm','withering_mind','clouded_eyes','faltering_heart','fragile_bones')
WEIGHTS=dict(zip(KINDS,(20,30,20,30,30)))


def _u(seed,pid,tick,purpose,salt=0,phase='live'):
    """分用途确定性冲击；不同进展分支不移动其他用途随机流。"""
    raw=f'aging-v1|{seed}|{pid}|{tick}|{purpose}|{salt}|{phase}'.encode()
    return (int.from_bytes(blake2b(raw,digest_size=8).digest(),'big')+.5)/(1<<64)


def aging_loss_probability(age):
    """公开defines线性增量的代理封顶，不宣称引擎实际封顶已确认。"""
    return min(1.,max(0.,.075+.022*(age-25))) if age>=25 else 0.


def monthly_natural_probability(health):
    """只是一条符合公开端点/二次注释的插值。"""
    return .25*min(1.,max(0.,(3.-health)/3.))**2


def _health(s):
    """基础健康与固定禀赋、病理修正分开，防止反复给总health加trait。"""
    tracks=s['tracks'];h=s['base_health']+s['health_bonus']-s.get('wound_penalty',0.)
    for trait,unit in [('infirm',.25),('faltering_heart',.1)]:
        if trait in tracks:
            xp=tracks[trait]
            penalties=[(100. if trait=='faltering_heart' and v==100 else unit) for v in (25,50,75,100) if xp>=v]
            track_loss=(penalties[-1] if penalties else 0.) if s['track_health_mode']=='highest' else sum(penalties)
            h-=unit+track_loss
    if 'clouded_eyes' in tracks and tracks['clouded_eyes']>=100:h-=.25
    if 'fragile_bones' in tracks:
        # 寿命-3不是健康-3；此处不伪造life_expectancy换算。
        pass
    if s['incapable']:h-=2.
    return h


def _refresh(s):
    s['health']=_health(s)
    s['infirm_xp']=s['tracks'].get('infirm',0)
    s['elder_count']=len(s['tracks'])
    return s


def _endpoints(s):
    """已确认的认知/视力转换；心脏直接事件死亡在调用方处理。"""
    if s['tracks'].get('withering_mind',0)>=100:s['incapable']=True
    if s['tracks'].get('clouded_eyes',0)>=100:
        s['blind']=True;del s['tracks']['clouded_eyes']


def _onset_weights(s):
    """硬年龄资格借原版；权重仅保留共同趋势，不是假装完整共享事件池。"""
    a=s['age'];h=_health(s);out=[]
    agefactor=(2 if a>60 else 1)*(2 if a>70 else 1)*(3 if a>80 else 1)
    hf=(2 if h<3 else .8 if a<60 else 1)*(5 if h<=1 else 1)
    for kind,w in WEIGHTS.items():
        if kind in s['tracks']:continue
        if s['incapable'] and kind!='infirm':continue
        if kind=='clouded_eyes' and s['blind']:continue
        if kind=='withering_mind':eligible=a>=50 or (a>=45 and s['stress_level']>=1) or (a>=30 and s['stress_level']>=2)
        else:eligible=a>=45 or (kind in ('infirm','faltering_heart') and a>=30 and s['weak_constitution'])
        if not eligible:continue
        if kind not in ('clouded_eyes','withering_mind') and a<60 and h>=5:continue
        weight=w*agefactor*hf*(.75 if s['profile']=='longlife' else 1)
        if kind=='infirm' and not s['tracks']:weight*=.25
        out.append((kind,weight))
    return out


def _step(s,seed,pid,tick,phase='live'):
    """推进一个年段；内部原地工作，公开入口负责复制输入。"""
    if not s['alive']:return _refresh(s)
    s['age']+=1
    salt=s['initial_sample_attempt']
    def u(p):return _u(seed,pid,tick,p,salt,phase)
    s['wound_penalty']=0.
    if u('base-health-loss')<aging_loss_probability(s['age']):s['base_health']-=.125
    if s['profile']!='no_elder':
        onset=_onset_weights(s);total=sum(w for _,w in onset)
        if total and u('elder-onset')<1-math.exp(-ASSUMPTIONS['elder_onset_rate']*total/130):
            target=u('elder-kind')*total
            for kind,w in onset:
                target-=w
                if target<=0:s['tracks'][kind]=0;break
        _endpoints(s)
        if not s['incapable']:
            if 'infirm' in s['tracks']:
                # 原版分支XP8/4/12；健康/勇武权重作最小可解释近似。
                health=_health(s);a=s['age'];prowess=max(0,12-.15*max(0,a-45))
                ws=(25+25*(not s['athletic'])+25*(a>=50)-25*(health>=3),60+prowess,max(0,50*(a>=65)-25*(health>=3)))
                target=u('infirm-progression')*sum(ws)
                delta=4
                for w,d in zip(ws,(8,4,12)):
                    target-=w
                    if target<=0:delta=d;break
                s['tracks']['infirm']=min(100,s['tracks']['infirm']+delta)
            if 'withering_mind' in s['tracks']:
                # 未建模社交/活动，固定权重替代原版相依进展池。
                r=u('cognitive-progression');delta=50 if r<.01 else 8 if r<.25 else 4
                s['tracks']['withering_mind']=min(100,s['tracks']['withering_mind']+delta)
            if 'clouded_eyes' in s['tracks']:
                r=u('vision-progression');delta=15 if r<.05 else 9 if r<.25 else 3
                s['tracks']['clouded_eyes']=min(100,s['tracks']['clouded_eyes']+delta)
            if 'fragile_bones' in s['tracks']:
                r=u('bones-progression');delta=3 if r<.25 else 6
                s['tracks']['fragile_bones']=min(100,s['tracks']['fragile_bones']+delta)
                if u('bone-injury')<ASSUMPTIONS['bone_injury_probability']:
                    s['wound_penalty']=1.5 if s['tracks']['fragile_bones']>=50 else 1.
            if 'faltering_heart' in s['tracks'] and u('heart-stress-event')<s['stress_event_probability']:
                s['tracks']['faltering_heart']=min(100,s['tracks']['faltering_heart']+25)
        _endpoints(s)
        if s['tracks'].get('faltering_heart',0)>=100:
            s['alive']=False;s['death_cause']='heart_attack_proxy';return _refresh(s)
    _refresh(s)
    for month in range(12):
        s['clock_month']+=1
        if s['death_due_month'] is not None:
            if s['clock_month']>=s['death_due_month']:
                s['alive']=False;s['death_cause']=s['pending_death_cause'];return s
            continue
        if u(f'natural-check-{month}')<monthly_natural_probability(s['health']):
            if s['know_thyself'] and not s['know_thyself_once']:
                s['know_thyself_once']=True
                days=340+40*u(f'second-chance-delay-{month}')
                cause='natural_after_second_chance_proxy'
            else:
                days=15+5*u(f'normal-death-delay-{month}')
                cause='injury_health_proxy' if s['wound_penalty'] else 'natural_health_proxy'
            s['death_due_month']=s['clock_month']+days/(365.25/12)
            s['pending_death_cause']=cause
    return s


def make_health(seed,pid,age,profile='base'):
    """从合成出生轨迹拒绝采样指定年龄幸存者；不预知将来死亡。"""
    if not isinstance(age,int) or isinstance(age,bool) or age<0 or age>120:raise ValueError('age须为0..120整数')
    if profile not in ('base','longlife','no_elder'):raise ValueError('未知健康代理profile')
    for attempt in range(ASSUMPTIONS['initial_sampling_limit']):
        birth=4+_u(seed,pid,0,'birth-health',attempt,'prehistory')
        s={'version':VERSION,'profile':profile,'age':0,'alive':True,'death_cause':None,
           'birth_health':birth,'base_health':birth,'health_bonus':1.5 if profile=='longlife' else 0.,
           'tracks':{},'incapable':False,'blind':False,'athletic':False,'weak_constitution':False,
           'stress_level':0,'stress_event_probability':ASSUMPTIONS['heart_stress_event_probability'],
           'track_health_mode':'additive','wound_penalty':0.,'clock_month':0,
           'know_thyself':profile=='longlife','know_thyself_once':False,'death_due_month':None,
           'pending_death_cause':None,'last_year':None,'initial_sample_attempt':attempt,
           'initial_sampling':'出生历史条件幸存者拒绝采样；非自然新局抽样'}
        for a in range(age):
            _step(s,seed,pid,a,'prehistory')
            if not s['alive']:break
        if s['alive']:return _refresh(s)
    raise ValueError(f'在{age}岁未取得条件幸存者；拒绝伪造复活/截断健康')


def advance_year(state,seed,pid,year):
    """同year重复调用幂等；倒序拒绝。允许首年任意整数，后续必须逐年。"""
    s=deepcopy(state)
    if not isinstance(year,int) or isinstance(year,bool):raise ValueError('year须为整数')
    if not s['alive']:return s
    previous=s.get('last_year')
    if previous is not None:
        if year==previous:return s
        if year!=previous+1:raise ValueError('健康年度必须连续且不可倒序')
    if not s['alive']:return s
    _step(s,seed,pid,year)
    s['last_year']=year
    return s
