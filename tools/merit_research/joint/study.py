"""四六目标的分阶段联合研究：功绩、资格、健康、承接与年度反馈。

仅由统一运行器在仓库外冻结目录执行。旧人口/增长与健康/任命模块为
合成代理依赖；没有引擎继任兜底或完整AI退休模型。未覆盖持有人必须
另账，不能把None叫真实空职，也不能据此声称完整原版人口已闭环。
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'merit-occupancy-study'))
import simulate as world
import capacity
import succession
spec=importlib.util.spec_from_file_location('joint_tail_reference',ROOT.parent/'merit-controller-study/study.py')
tail=importlib.util.module_from_spec(spec);spec.loader.exec_module(tail)
pr=world.pr

PILOT=[{'name':m,'mapping':m} for m in ['uniform1.5','uniform2','uniform3','tiered','transit2']]
PILOT += [dict(name=f'transit2-r{r}',mapping='transit2',r=r) for r in [.03,.06]]
PILOT += [dict(name=f'transit2-gain{k}',mapping='transit2',gain=k) for k in [.2,.6]]
# 温度不随人数拟合；所有候选固定相同温度，独立留出时才比较其反例。
STRESS=[{'name':'baseline'}, {'name':'empty','initial':'empty'},
 {'name':'all_bottom','initial':'bottom'}, {'name':'all_top','initial':'top'},
 {'name':'entry4','entry_mult':4}, {'name':'entry_quarter','entry_mult':.25},
 {'name':'longlife','mortality':'longlife'}, {'name':'loss','shock':'loss'},
 {'name':'mortality','shock':'mortality'}, {'name':'central','shock':'central'},
 {'name':'upper_expanded','structure':'upper_expanded'}, {'name':'retirement','shock':'retirement'},
 {'name':'income_feedback','feedback':True}, {'name':'low_growth','income':240},
 {'name':'high_growth','income':1440}, {'name':'no_middle','J':[100,0,0,5]},
 {'name':'small','J':[3,1,1,1]}, {'name':'temperature_low','temperature':.25},
 {'name':'temperature_high','temperature':1.0}]


def seals():
    """封存实际导入及研究源码，结果不能冒用另一版依赖。"""
    names=[*sorted(p.name for p in ROOT.glob('*.py')),
      '../merit-occupancy-study/simulate.py','../merit-occupancy-study/aging.py',
      '../merit-occupancy-study/appointments.py','../merit-buffer-study/model.py',
      '../merit-controller-study/study.py']
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}


def cohort_summary(cohort):
    """固定40年终点保留死亡与退出，不只报成功者。"""
    out={'n':len(cohort),'first_job40':0,'first_wait':[],'reached':[0]*9,
         'capable3':0,'capable_reached3':0,'dead_without_first40':0,'alive_without_first40':0}
    for p in cohort:
        entry=p['entry'];first=p['first_job']
        success=first is not None and first-entry<=40
        out['first_job40']+=success
        if success:out['first_wait'].append(first-entry)
        else:
            died=p.get('death_year') is not None and p['death_year']<=entry+40
            out['dead_without_first40' if died else 'alive_without_first40']+=1
        for rank,year in p['hit'].items():
            if year-entry<=40:out['reached'][rank-1]+=1
        if p['cap']>=7:
            out['capable3']+=1
            out['capable_reached3']+=7 in p['hit'] and p['hit'][7]-entry<=40
    return out


def trial(route,seed,config,years=80,observer=None,merit_gate=None,income_step=None,person_init=None):
    """每年先外部过程，再事件承接，再冻结六Q；没有隐式强制退休。

    observer(stage, year, people, context)是可选诊断入口，返回值不使用。
    每次仅传共同深拷贝快照，诊断修改不回写演算；需保留数据可直接持有。
    people为id到人物的映射：decision/after包含全在册人物，exit仅包含死者。
    decision发生于六Q冻结后、普通晋升前；context含cfg/n/target/E/raw/q/Q/
    pools/frozen/J/grant_flows。after在普通晋升及守恒断言后另含npost；
    pools成员仍是冻结来源，人物内容已是晋升后状态，须用frozen认定来源。
    exit在death_year写入、职务释放后、人物删除前，context含cfg/cause。
    默认无observer时不创建快照，不改变随机调用、数学规则或返回结果。
    merit_gate(deepcopy(person), source, threshold)仅替代候选余额达标判断，
    返回值转为bool；供反事实研究绕过门槛，不能修改硬资格或实际余额。
    默认None仍直接比较真实M；权重、收入和成功归一化始终使用真实M。
    income_step(person, current_job_or_none, year)提供本年按来源分账的净额；
    仅在非创建年、有效仕途者推进，收入对应本轮任免前的原在任职务。
    person_init(person)仅创建时调用，可提供一次性初始化余额与资格。
    两者默认None严格保留旧合成对照，不为旧研究重写来源或结果。
    """
    cfg={'mapping':'transit2','r':.04/.96,'gain':.35,'epsilon':.1,'temperature':.5,
         'structure':'base','mortality':'base','income':720,'entry_mult':1,**config}
    sk=seed+(1000000 if route=='military' else 0)
    people={};cohort=[];cohort_after=[];pid=0;series=[]
    def observe_snapshot(stage,year,observed_people,context):
        # 一次共同复制保留people与pools的内部别名，同时隔离全部演算状态。
        snapshot=copy.deepcopy((observed_people,context))
        observer(stage,year,snapshot[0],snapshot[1])
    health_profile=cfg['mortality']
    counts=list(cfg.get('J',world.JOBS[route][cfg['structure']]))
    jobs={};jid=0
    for tier,count in enumerate(counts,1):
        for index in range(count):
            central=None
            if tier==4:
                if route=='civil' and index<8:central=9 if index<2 else 8
                if route=='military' and index==0:central=9
            jobs[jid]={'id':jid,'tier':tier,'kind':'central' if central else 'admin',
                       'central_target':central,'holder':None,'prominence':10**tier*(1+.5*pr.uniform(sk,jid,0,23))}
            jid+=1
    def add(rank,merit,entry=None):
        nonlocal pid
        p=world.make_person(sk,pid,rank,merit,max(rank,pr.ceiling(sk,pid)),entry=entry,
                            health_profile=health_profile,age=18 if entry is not None else None)
        p['g']*=cfg['income']/720
        if cfg.get('all_qualified'):p['cap']=9
        p['hit']={r:entry if entry is not None else 0 for r in range(1,rank+1)}
        p['return_year']=None;people[pid]=p;pid+=1
        if person_init is not None: person_init(p)
        if entry is not None and 10<=entry<30:cohort.append(p)
        if entry is not None and 60<=entry<80:cohort_after.append(p)
        return p
    initial=cfg.get('initial','observed');scale=cfg.get('initial_scale',1)
    if initial!='empty':
        for rank,(n,e) in enumerate(zip(pr.BASE[route]['n'],pr.BASE[route]['e']),1):
            for j in range(round(n*scale)):
                a=1 if initial=='bottom' else 7 if initial=='top' else rank
                merit=pr.TH[a]+(pr.TH[min(9,a+1)]-pr.TH[a])*(1.2 if j<e else .25)
                add(a,merit)
    totals={'ordinary':0,'central':0,'external_grants':0,'deaths':0,'retired':0,'restored':0,
      'quota_star':[0.]*6,'quota_unserved':[0.]*6,'eligible':[0]*6,'awards':[0]*6,
      'top_merit_exposure':0,'top_merit_selected':0,'bottom_merit_exposure':0,'bottom_merit_selected':0,
      'appointments':[0]*4,'competitive_events':[0]*4,'high_wins_with_low':[0]*4,
      'uncovered_events':0,'transfers':0}
    def release(p,events,reason,t):
        if p['job'] is not None:
            old=p['job'];assert jobs[old]['holder']==p['id']
            jobs[old]['holder']=None;p['job']=None
            events.append({'job_id':old,'reason':reason,'event_id':[reason,t,p['id'],old]})
    for year in range(years):
        before=len(people);events=[];dead=0;arrived=0
        income_ledger={key:0. for key in ('fixed','tax','maa','funding','events')}
        income_groups={}
        if year:
            for p in list(people.values()):
                p['health']=world.aging.advance_year(p['health'],sk,p['health_pid'],year)
                world.sync_health(p)
                if cfg.get('shock')=='mortality' and year==60 and pr.uniform(sk,p['id'],year,80)<.5:
                    p['alive']=False
                if not p['alive']:
                    p['death_year']=year;release(p,events,'death',year)
                    if observer is not None:
                        observe_snapshot('exit',year,{p['id']:p},{'cfg':cfg,'cause':'death'})
                    del people[p['id']];dead+=1
                    continue
                if not p['active'] and p['return_year']==year:
                    p['active']=True;p['return_year']=None;totals['restored']+=1
                if cfg.get('shock')=='retirement' and p['active'] and p['age']>=50 and pr.uniform(sk,p['id'],year,81)<.03:
                    p['active']=False;p['return_year']=year+3;release(p,events,'retirement',year);totals['retired']+=1
            number=round(pr.BASE[route]['birth']*cfg['entry_mult'])
            for _ in range(number):add(1,100,entry=year);arrived+=1
            for p in people.values():
                if p['entry']==year or not p['active']:continue
                if income_step is None:
                    premium=1+.2*jobs[p['job']]['tier'] if cfg.get('feedback') and p['job'] is not None else 1
                    p['m']+=p['g']*premium
                else:
                    job=jobs.get(p['job'])
                    components=income_step(p,job,year)
                    assert set(components)==set(income_ledger)
                    assert all(math.isfinite(value) for value in components.values())
                    amount=sum(components.values());p['m']+=amount
                    for key,value in components.items(): income_ledger[key]+=value
                    group=f"{p['rank']}/"+(str(job['tier']) if job else 'unemployed')
                    bucket=income_groups.setdefault(group,dict(n=0,total=0.))
                    bucket['n']+=1;bucket['total']+=amount
        assert len(people)==before+arrived-dead
        totals['deaths']+=dead
        if cfg.get('shock')=='loss' and year==60:
            removed=[j for j in jobs if j%2==0]
            for j in removed:
                holder=jobs[j]['holder']
                if holder is not None:people[holder]['job']=None
                del jobs[j]
            events=[e for e in events if e['job_id'] in jobs]
        if cfg.get('shock')=='central' and year>=60 and year%4==0:
            # 人数守恒的外部越级压力输入，不冒充实际中央任命路径。
            low=[p for p in people.values() if p['active'] and p['rank']<7]
            if low:
                p=max(low,key=lambda p:p['m']);p['rank']=9;p['m']=pr.TH[9];p['central_year']=year
                for a in range(1,10):p['hit'].setdefault(a,year)
                totals['external_grants']+=1
        pending={e['job_id'] for e in events}
        for j,job in jobs.items():
            if job['holder'] is None and j not in pending:
                events.append({'job_id':j,'reason':'initial' if year==0 else 'reassessment','event_id':['reassess',year,j]})
        events.sort(key=lambda e:(jobs[e['job_id']]['tier'],jobs[e['job_id']]['prominence']),reverse=True)
        appointments=succession.resolve(people,jobs,year,sk,events)
        for flow in appointments['grant_flows']:
            p=people[flow['person_id']]
            for a in range(flow['source']+1,flow['target']+1):p['hit'].setdefault(a,year)
        if year>=20:
            totals['central']+=len(appointments['grant_flows'])
            for k in ['appointments','competitive_events','high_wins_with_low']:
                totals[k]=[a+b for a,b in zip(totals[k],appointments[k])]
            totals['uncovered_events']+=appointments['uncovered_count'];totals['transfers']+=appointments['transfer_count']
        active=[p for p in people.values() if p['active']]
        n=[sum(p['rank']==a for p in active) for a in range(1,10)]
        currentJ=[sum(j['tier']==t for j in jobs.values()) for t in range(1,5)]
        target=capacity.targets(currentJ,cfg['mapping'],r=cfg['r'],epsilon=cfg['epsilon'])
        pools={a:[p for p in active if p['rank']==a and p['age']>=16
                  and (p['m']>=pr.TH[a+1] if merit_gate is None
                       else bool(merit_gate(copy.deepcopy(p),a,pr.TH[a+1])))
                  and p['cap']>=a+1 and p['central_year']!=year] for a in range(1,7)}
        E=[len(pools[a]) for a in range(1,7)]
        n7=[*n[:6],sum(n[6:])]
        raw=tail.quota(n7,target['target'],[10**12]*6,r=cfg['r'],gain=cfg['gain']).tolist()
        q=[min(e,x) for e,x in zip(E,raw)]
        Q=[min(e,pr.balanced_round(x,pr.uniform(sk,a,year,82))) for a,(e,x) in enumerate(zip(E,q),1)]
        frozen={p['id']:p['rank'] for p in active}
        if observer is not None:
            diagnostic_context={'cfg':cfg,'n':n,'target':target,'E':E,'raw':raw,'q':q,
                                'Q':Q,'pools':pools,'frozen':frozen,'J':currentJ,
                                'grant_flows':appointments['grant_flows']}
            observe_snapshot('decision',year,people,diagnostic_context)
        for a in range(6,0,-1):
            pool=pools[a];seats=Q[a-1];B=cfg['temperature']*(pr.TH[a+1]-pr.TH[a])
            selected=sorted(pool,key=lambda p:p['m']/B*math.log(2)-math.log(-math.log(pr.uniform(sk,p['id'],year,83))),reverse=True)[:seats]
            chosen={p['id'] for p in selected}
            if year>=20:
                totals['quota_star'][a-1]+=raw[a-1];totals['quota_unserved'][a-1]+=max(0,raw[a-1]-E[a-1])
                totals['eligible'][a-1]+=E[a-1];totals['awards'][a-1]+=len(selected)
                if 0<seats<len(pool) and len(pool)>=4 and max(p['m'] for p in pool)>min(p['m'] for p in pool):
                    ordered=sorted(pool,key=lambda p:(p['m'],p['id']));half=len(pool)//2
                    for label,group in [('bottom',ordered[:half]),('top',ordered[-half:])]:
                        totals[label+'_merit_exposure']+=len(group)
                        totals[label+'_merit_selected']+=sum(p['id'] in chosen for p in group)
            for p in selected:
                assert p['rank']==a
                p['rank']=a+1;p['m']=pr.TH[a+1];p['hit'].setdefault(a+1,year)
                if year>=20:totals['ordinary']+=1
        assert all(0<=p['rank']-frozen[p['id']]<=1 for p in active)
        post=[sum(p['rank']==a for p in active) for a in range(1,10)]
        assert sum(n)==sum(post)==len(active)
        for a in range(9):
            incoming=Q[a-1] if 1<=a<=6 else 0
            outgoing=Q[a] if a<6 else 0
            assert post[a]==n[a]+incoming-outgoing
        if observer is not None:
            observe_snapshot('after',year,people,{**diagnostic_context,'npost':post})
        known=[0]*4;unknown=[0]*4;high=[0]*4
        occupied=[]
        for job in jobs.values():
            b=job['tier']-1;holder=job['holder']
            if holder is None:unknown[b]+=1
            else:
                assert holder in people and people[holder]['active'] and people[holder]['job']==job['id']
                known[b]+=1;occupied.append(holder);high[b]+=int(succession.appointments.rank_band(people[holder]['rank'])>job['tier'])
        assert len(occupied)==len(set(occupied))
        assert [a+b for a,b in zip(known,unknown)]==currentJ
        errors=[abs(sum(n[i+1:])-b)/b if b else None for i,b in enumerate(target['B'])]
        series.append({'year':year,'active':len(active),'inactive':len(people)-len(active),'J':currentJ,
          'K':target['K'],'target':target['target'],'decision_n':n,'post_n':post,'tail_error':errors,
          'q_star':raw,'E':E,'Q':Q,'known':known,'uncovered':unknown,'high':high})
        if income_step is not None:
            series[-1].update(income_ledger=income_ledger,income_groups=income_groups)
    return {'route':route,'seed':seed,'config':cfg,'years':years,'mechanism_errors':0,
            'cohort':cohort_summary(cohort),
            'post_cohort':cohort_summary(cohort_after) if years>=120 else None,
            'metric_windows':{'population':[max(0,years-40),years-1],
              'quota_and_competition':[20,years-1],'pre_cohort_entry':[10,29],
              'post_cohort_entry':[60,79] if years>=120 else None},
            'metrics':totals,'series':series}


def summarize(rows):
    """按种子汇总；未知持有人分母及九品冗余不能被整体均值吞掉。"""
    samples=[s for r in rows for s in r['series'][-min(40,r['years']):]]
    cohort_n=sum(r['cohort']['n'] for r in rows)
    eligible3=sum(r['cohort']['capable3'] for r in rows)
    ratio=lambda a,b:a/b if b else None
    sums=lambda key:sum(r['metrics'][key] for r in rows)
    out={'runs':len(rows),'decision_n_mean':[statistics.mean(s['decision_n'][i] for s in samples) for i in range(9)],
      'target_mean':[statistics.mean(s['target'][i] for s in samples) for i in range(7)],
      'tail_error_mean':[statistics.mean(s['tail_error'][i] for s in samples if s['tail_error'][i] is not None) if any(s['tail_error'][i] is not None for s in samples) else None for i in range(6)],
      'coverage':[ratio(sum(s['known'][i] for s in samples),sum(s['J'][i] for s in samples)) for i in range(4)],
      'high_known_share':[ratio(sum(s['high'][i] for s in samples),sum(s['known'][i] for s in samples)) for i in range(4)],
      'high_all_lower':[ratio(sum(s['high'][i] for s in samples),sum(s['J'][i] for s in samples)) for i in range(4)],
      'high_all_upper':[ratio(sum(s['high'][i]+s['uncovered'][i] for s in samples),sum(s['J'][i] for s in samples)) for i in range(4)],
      'cohort_n':cohort_n,'first_job40':ratio(sum(r['cohort']['first_job40'] for r in rows),cohort_n),
      'reach3_40':ratio(sum(r['cohort']['reached'][6] for r in rows),cohort_n),
      'capable3_n':eligible3,'capable_reach3_40':ratio(sum(r['cohort']['capable_reached3'] for r in rows),eligible3),
      'top_merit_selection':ratio(sums('top_merit_selected'),sums('top_merit_exposure')),
      'bottom_merit_selection':ratio(sums('bottom_merit_selected'),sums('bottom_merit_exposure')),
      'quota_shortfall':[ratio(sum(r['metrics']['quota_unserved'][i] for r in rows),sum(r['metrics']['quota_star'][i] for r in rows)) for i in range(6)],
      'ordinary':sums('ordinary'),'central':sums('central'),'external_grants':sums('external_grants'),
      'retired':sums('retired'),'restored':sums('restored'),'mechanism_errors':sum(r['mechanism_errors'] for r in rows)}
    post=[r['post_cohort'] for r in rows if r['post_cohort'] is not None]
    if post:
        n=sum(c['n'] for c in post);cap=sum(c['capable3'] for c in post)
        out.update(post_cohort_n=n,
          post_first_job40=ratio(sum(c['first_job40'] for c in post),n),
          post_reach3_40=ratio(sum(c['reached'][6] for c in post),n),
          post_capable3_n=cap,post_capable_reach3_40=ratio(sum(c['capable_reached3'] for c in post),cap),
          post_dead_without_first40=sum(c['dead_without_first40'] for c in post),
          post_alive_without_first40=sum(c['alive_without_first40'] for c in post))
    out['metric_windows']=rows[0]['metric_windows']
    waits=[w for r in rows for w in r['cohort']['first_wait']]
    out['first_wait_conditional_median']=statistics.median(waits) if waits else None
    return out


def batch(job):
    """同路同种子批量执行，复用条件健康包缓存；不同进程独立导入。"""
    phase,route,seed,configs,years=job
    rows=[]
    for cfg in configs:
        started=time.monotonic();r=trial(route,seed,cfg,years);rows.append(r)
        print('finished',phase,route,seed,cfg['name'],round(time.monotonic()-started,2),flush=True)
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['pilot','validation'],required=True)
    parser.add_argument('--workers',type=int,default=3);args=parser.parse_args()
    snapshot=seals()
    if args.phase=='pilot':configs=PILOT;seeds=[0,1];years=80
    else:
        pilot=json.loads((ROOT/'pilot.json').read_text())
        assert pilot['source_sha256']==snapshot,'先导源码变化，禁止沿用旧先导筛选'
        # 预先声明顺序：零机制错误→四级最低覆盖→最高带占员误差。
        # 不折叠生涯公平、稀缺性为任意综合分；最终推荐需连同留出失败审阅。
        ranks=[]
        for cfg in PILOT:
            gs=[pilot['groups'][route+'/'+cfg['name']] for route in ['civil','military']]
            uncovered=max(1-min(x for x in g['coverage'] if x is not None) for g in gs)
            error=max(g['tail_error_mean'][-1] for g in gs)
            ranks.append(((sum(g['mechanism_errors'] for g in gs),round(uncovered,3),error),cfg))
        ranked=sorted(ranks,key=lambda p:p[0])
        selected=copy.deepcopy(ranked[0][1])
        # 同数值时优先保留有结构周转审计的映射，避免把同结果误叫收益。
        if selected['mapping']=='uniform2' and not any(k in selected for k in ['r','gain']):selected={'name':'transit2','mapping':'transit2'}
        configs=[{**selected,**stress,'name':stress['name']} for stress in STRESS];seeds=[2,3];years=120
    jobs=[(args.phase,route,seed,configs,years) for route in ['civil','military'] for seed in seeds]
    rows=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(batch,jobs):rows.extend(result)
    groups={route+'/'+cfg['name']:summarize([r for r in rows if r['route']==route and r['config']['name']==cfg['name']]) for route in ['civil','military'] for cfg in configs}
    out={'version':'joint-proxy-v2','phase':args.phase,'source_sha256':snapshot,'configs':configs,'seeds':seeds,
      'assumptions':{'not_engine_evidence':True,'phi':.6,'top_band_aggregate':True,'initial_health_growth_caps_and_J_synthetic':True,
       'uncovered_is_kernel_failure_not_real_vacancy':True,'unknown_holders_not_added_to_population':'因此不能宣称原版全体人口完全闭环',
       'military_appointment_uses_civic_partial_score':True,'permanent_exit_baseline':'健康代理死亡，无完整AI退休；另有显式临退恢复压力',
       'central_slots':'文前2帝级示例授一品、后至8授二品；武首帝级授一品，其余不特授；非真实J测量',
       'central_stress':'按源→目标内部搬迁的人工外部越级输入，不冒充原版实际任命',
       'cohort_entry':[10,29],'post_cohort_entry':[60,79],'mechanism_errors_meaning':'已编码在线断言未失败，不代表所有引擎机制已验证','fixed_endpoint':40,'late_window':40,'seeds_are_descriptive_not_confidence_intervals':True},
      'groups':groups,'runs':rows}
    (ROOT/(args.phase+'.json')).write_text(json.dumps(out,ensure_ascii=False))
    if args.phase=='validation':
        out['pilot_groups']=pilot['groups'];out['selection_diagnostics']=[{'key':list(key),'config':cfg} for key,cfg in ranked]
        (ROOT/'results.json').write_text(json.dumps(out,ensure_ascii=False))
        (ROOT/'summary.json').write_text(json.dumps({k:v for k,v in out.items() if k!='runs'},ensure_ascii=False,indent=2))
    print('DONE',args.phase,len(rows),flush=True)

if __name__=='__main__':main()
