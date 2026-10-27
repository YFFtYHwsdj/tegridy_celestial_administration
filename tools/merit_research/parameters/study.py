"""逐带员额的逐参数、交互与独立生涯验证；不修改正式游戏。

所有参数文武共享。默认直接K=kJ；不偷偷替换成全国总预算。健康只作
外生代理，每job缓存相同完整输入的年度健康推进；命中先核对输入。
训练与留出分开，源码和结果摘要冻结，产物只写仓库外。
"""
import argparse
import copy
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from functools import partial
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
import run as runner

ANCHOR=dict(name='anchor',coefficients=[1.5]*4,phi=[.6]*3,r=.06,gain=.6,
            epsilon=.1,temperature=.5,reserve=[0]*3)


def sweeps():
    """单因素对照，不把同一组合的通过当作各参数已独立最优。"""
    configs=[{**ANCHOR,'factor':'anchor','value':None}]
    def add(factor,value,**change):
        configs.append({**ANCHOR,**change,'name':factor+'='+str(value),
                        'factor':factor,'value':value})
    for k in [.75,1,1.25,2,2.5,3]:add('common_k',k,coefficients=[k]*4)
    for b,values in [(1,[1,2,4,8]),(2,[1,2,4,8]),(3,[.75,1,2])]:
        for k in values:
            ks=ANCHOR['coefficients'][:];ks[b]=k;add('k'+str(b+1),k,coefficients=ks)
    for b,values in [(0,[.5,.7,.8]),(1,[.4,.5,.7,.8]),(2,[.4,.5,.7,.8])]:
        for phi in values:
            phis=ANCHOR['phi'][:];phis[b]=phi;add('phi'+str(b+1),phi,phi=phis)
    for r in [.02,.04,.10,.16]:add('r',r,r=r)
    for gain in [.15,.35,.9]:add('gain',gain,gain=gain)
    for tau in [.25,1,2]:add('temperature',tau,temperature=tau)
    return configs


VALIDATE=[dict(name='baseline'),dict(name='entry4',entry_pressure=4),
 dict(name='longlife',mortality='longlife'),dict(name='loss',shock='loss'),
 dict(name='mortality',shock='mortality'),dict(name='empty',initial='empty'),
 dict(name='top',initial='top'),dict(name='no_middle',J=[100,0,0,5]),
 dict(name='small',J=[3,1,1,1],explicit_entrants=1),dict(name='low_growth',income=240),
 dict(name='high_access',qualification='high'),dict(name='low_access',qualification='low'),
 dict(name='later_exams',qualification='later'),dict(name='income_feedback',feedback=True),
 dict(name='upper_heavy',J=[15,25,40,40]),dict(name='central',shock='central')]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def models(root):
    sys.path.insert(0,str(root/'merit-joint-study'))
    joint=load(root/'merit-joint-study/study.py','parameter_joint_reference')
    model=load(root/'merit-parameter-study/math_model.py','parameter_math_reference')
    calibration=load(root/'calibrate_joint.py','parameter_external_reference')
    return joint,model,calibration


@contextmanager
def health_cache(world,enabled=True):
    """同job只换政策；完整输入不等则拒绝，禁止错误复用健康反馈。"""
    original=world.aging.advance_year;cache={};stats=dict(hits=0,misses=0)
    def advance(state,seed,pid,year):
        key=(seed,pid,year)
        if key in cache:
            before,after=cache[key]
            if state!=before:raise AssertionError('健康缓存同key输入不同，外部世界不再相同')
            stats['hits']+=1;return copy.deepcopy(after)
        result=original(state,seed,pid,year)
        cache[key]=(copy.deepcopy(state),copy.deepcopy(result));stats['misses']+=1
        return result
    if enabled:world.aging.advance_year=advance
    try:yield stats
    finally:world.aging.advance_year=original


@contextmanager
def qualification_model(joint,profile):
    """资格敏感性仅是外部输入；不将代理年龄/概率加入正式晋升条件。"""
    original=joint.pr.ceiling;sync=joint.world.sync_health
    if profile in ('high','low'):
        probabilities=(.1,.3,.3,.3) if profile=='high' else (.15,.55,.27,.03)
        def ceiling(seed,pid):
            u=joint.pr.uniform(seed,pid,0,3);total=0
            for cap,p in zip((2,4,6,9),probabilities):
                total+=p
                if u<total:return cap
            return 9
        joint.pr.ceiling=ceiling
    elif profile=='later':
        def later(person):
            sync(person)
            potential=person.setdefault('potential_cap',person['cap'])
            # 人工后续考试路径：18岁先八品上限，30/40/50岁再逐步开放原潜能。
            cap=2 if person['age']<30 else 4 if person['age']<40 else 6 if person['age']<50 else 9
            person['cap']=max(person['rank'],min(potential,cap))
        joint.world.sync_health=later
    elif profile!='base':raise ValueError('未知资格敏感性')
    try:yield
    finally:joint.pr.ceiling=original;joint.world.sync_health=sync


def external_config(config,route,world,calibration):
    return calibration.external_config(config,route,world)


def batch(job):
    root,route,seed,scenario,configs,years=job;root=Path(root)
    joint,model,calibration=models(root);original=joint.capacity.targets;rows=[]
    try:
        with health_cache(joint.world) as cache,qualification_model(joint,scenario.get('qualification','base')):
            for config in configs:
                cfg=external_config({**config,**scenario},route,joint.world,calibration)
                cfg.update(policy=config['name'],mapping='direct_band')
                joint.capacity.targets=partial(model.targets,coefficients=config['coefficients'],
                    phi=config['phi'],reserve=config.get('reserve',[0]*3))
                started=time.monotonic();result=joint.trial(route,seed,cfg,years)
                rows.append(result)
                print('finished',route,seed,scenario['name'],config['name'],round(time.monotonic()-started,2),flush=True)
        return dict(runs=rows,cache=cache)
    finally:joint.capacity.targets=original


def metrics(joint,rows):
    """跟踪误差与队列分项报告；九品冗余不用于奖励抬高员额。"""
    base=joint.summarize(rows)
    if rows[0]['config'].get('qualification')=='later':
        # 后续考试改变cap，旧摘要的期末cap分母不再代表原潜能固定队列。
        for key in ['capable3_n','capable_reach3_40','post_capable3_n','post_capable_reach3_40']:
            base[key]=None
    states=[s for r in rows for s in r['series'][-40:]]
    bands=lambda s:[sum(s['decision_n'][2*b:2*b+2]) for b in range(3)]+[sum(s['decision_n'][6:])]
    goals=lambda s:[sum(s['target'][2*b:2*b+2]) for b in range(3)]+[s['target'][6]]
    actual=[bands(s) for s in states];target=[goals(s) for s in states]
    ratio=[statistics.mean(a[b]/t[b] for a,t in zip(actual,target) if t[b]) if any(t[b] for t in target) else None for b in range(4)]
    # 目标低于3人时用绝对人数误差，避免一个人改变而百分比压倒所有大池。
    band_error=statistics.mean(abs(a[b]-t[b])/max(3,t[b]) for a,t in zip(actual,target) for b in [1,2,3])
    tail_errors=[]
    for s in states:
        n=s['decision_n'];t=s['target']
        tail_errors.extend(abs(sum(n[i+1:])-sum(t[i+1:]))/max(3,sum(t[i+1:])) for i in range(6))
    top=[a[3] for a in actual]
    out={**base,'band_mean':[statistics.mean(a[b] for a in actual) for b in range(4)],
         'band_goal':[statistics.mean(t[b] for t in target) for b in range(4)],
         'band_ratio':ratio,'band_tracking':band_error,'tail_tracking':statistics.mean(tail_errors),
         'budget_per_title':statistics.mean(sum(s['K'])/sum(s['J']) if sum(s['J']) else 0 for s in states),
         'top_zero_share':statistics.mean(x==0 for x in top),
         'top_p10_p90':[sorted(top)[round((len(top)-1)*p)] for p in [.1,.9]],
         'zero_Q_given_E':[sum(s['E'][i]>0 and s['Q'][i]==0 for s in states)/sum(s['E'][i]>0 for s in states)
                           if any(s['E'][i]>0 for s in states) else None for i in range(6)],
         'tail_excess_area':[sum(max(0,sum(s['decision_n'][i+1:])-sum(s['target'][i+1:])) for s in states)/len(rows) for i in range(6)],
         'tail_deficit_area':[sum(max(0,sum(s['target'][i+1:])-sum(s['decision_n'][i+1:])) for s in states)/len(rows) for i in range(6)]}
    if rows[0]['config'].get('shock'):
        recovery=[]
        for row in rows:
            series=row['series'];found=None
            for y in range(60,len(series)-14):
                if all(all(abs(sum(s['decision_n'][i+1:])-sum(s['target'][i+1:]))<=max(2,.25*sum(s['target'][i+1:])) for i in range(6)) for s in series[y:y+15]):
                    found=y-60;break
            recovery.append(found)
        out['all_tail_first15_within_tolerance_after60']=recovery
    return out


def summarize(root,rows):
    joint,_,_=models(root);groups={}
    for route,scenario,policy in sorted({(r['route'],r['config']['name'],r['config']['policy']) for r in rows}):
        selected=[r for r in rows if (r['route'],r['config']['name'],r['config']['policy'])==(route,scenario,policy)]
        groups['/'.join((route,scenario,policy))]=metrics(joint,selected)
    return groups


def diagnostic_rank(groups,configs):
    """只排跟踪误差供缩减候选；不将预算/仕途偏好合成福利分数。"""
    ranked=[]
    for c in configs:
        gs=[g for k,g in groups.items() if k.endswith('/'+c['name'])]
        tracking=statistics.mean((g['band_tracking']+g['tail_tracking'])/2 for g in gs)
        ranked.append(dict(config=c,tracking=tracking,
            worst_tracking=max((g['band_tracking']+g['tail_tracking'])/2 for g in gs),
            budget=statistics.mean(g['budget_per_title'] for g in gs)))
    return sorted(ranked,key=lambda x:x['tracking'])


def interactions(sweep):
    common=[r for r in sweep['ranking'] if r['config']['factor'] in ('anchor','common_k')]
    k=common[0]['config']['coefficients'][0]
    configs=[]
    for index,ks in enumerate([[k]*4,[k,2,4,1.5],[k,4,8,1.5],[k,2,4,1]]):
        for phi in [[.6,.6,.6],[.6,.7,.7],[.6,.7,.8]]:
            for r,gain in [(.04,.35),(.06,.6)]:
                name=f'joint{index}-phi{phi[1]}{phi[2]}-r{r}'
                configs.append({**ANCHOR,'name':name,'coefficients':ks,'phi':phi,'r':r,'gain':gain,
                    'factor':'interaction','value':None})
    return configs


def shortlist(interaction):
    """跟踪最佳，以及误差增加不超过5个百分点时的最低预算，各自保留。"""
    ranked=interaction['ranking'];best=ranked[0]
    low=min([x for x in ranked if x['tracking']<=best['tracking']+.05],key=lambda x:(x['budget'],x['tracking']))
    out=[best['config']]
    if low['config']['name']!=best['config']['name']:out.append(low['config'])
    return out


def hashes(root):
    manifest=json.loads((root/'source-manifest.json').read_text())
    names=[*manifest,'calibrate_joint.py','runner_reference.py',
           *['merit-parameter-study/'+p.name for p in ROOT.glob('*.py')]]
    return {n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names}


def verify(root):
    runner.verify_snapshot(root,runner.selection('joint'),[])
    for p in ROOT.glob('*.py'):assert p.read_bytes()==(root/'merit-parameter-study'/p.name).read_bytes(),p.name
    for repo,frozen in [(ROOT.parent/'calibrate_joint.py',root/'calibrate_joint.py'),
                        (ROOT.parent/'run.py',root/'runner_reference.py')]:assert repo.read_bytes()==frozen.read_bytes()


def check(root):
    verify(root);counts={}
    for phase in ('sweep','interaction','validation'):
        path=root/(phase+'-results.json')
        if not path.exists():continue
        d=json.loads(path.read_text());assert d['source_sha256']==hashes(root)
        expected=len(d['configs'])*len(d['scenarios'])*len(d['seeds'])*2
        assert len(d['runs'])==expected
        for row in d['runs']:
            cfg=row['config'];assert 'military_low' not in cfg
            for s in row['series']:
                assert sum(s['decision_n'])==sum(s['post_n'])==s['active']
                assert all(0<=q<=e for q,e in zip(s['Q'],s['E']))
                assert all(abs(k-c*j)<1e-7 for k,c,j in zip(s['K'],cfg['coefficients'],s['J']))
                assert abs(sum(s['target'])-(1+cfg['epsilon'])*sum(s['K']))<1e-7
        counts[phase]=expected
    assert counts
    return counts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['sweep','interaction','validation','check','cache_check'])
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args();root=runner.outside_repository(args.output_dir)
    if args.phase=='sweep':
        runner.prepare(root,runner.selection('joint'));folder=root/'merit-parameter-study';folder.mkdir()
        for p in ROOT.glob('*.py'):shutil.copyfile(p,folder/p.name)
        shutil.copyfile(ROOT.parent/'calibrate_joint.py',root/'calibrate_joint.py')
        shutil.copyfile(ROOT.parent/'run.py',root/'runner_reference.py')
    else:verify(root)
    if args.phase=='check':print(check(root));return
    if args.phase=='cache_check':
        joint,model,_=models(root)
        records=[]
        for scenario in [dict(name='baseline'),dict(name='longlife',mortality='longlife'),dict(name='mortality',shock='mortality')]:
            for config in [ANCHOR,{**ANCHOR,'r':.1,'phi':[.6,.7,.8]}]:
                joint.capacity.targets=partial(model.targets,coefficients=config['coefficients'],phi=config['phi'])
                plain=joint.trial('military',99,{**config,**scenario},years=80)
                with health_cache(joint.world):
                    cached=joint.trial('military',99,{**config,**scenario},years=80)
                    cached_again=joint.trial('military',99,{**config,**scenario},years=80)
                assert plain==cached==cached_again
                records.append(dict(scenario=scenario['name'],r=config['r'],equal=True))
        (root/'cache-check.json').write_text(json.dumps(dict(source_sha256=hashes(root),records=records)))
        print('缓存开关完整输出等价',len(records));return
    output=root/(args.phase+'-results.json')
    if output.exists():raise ValueError('拒绝覆盖阶段结果')
    if args.phase=='sweep':configs=sweeps();seeds=[40,41];scenarios=[dict(name='baseline')];years=80
    elif args.phase=='interaction':
        before=json.loads((root/'sweep-results.json').read_text());assert before['source_sha256']==hashes(root)
        configs=interactions(before);seeds=[42,43];scenarios=[dict(name='baseline')];years=80
    else:
        before=json.loads((root/'interaction-results.json').read_text());assert before['source_sha256']==hashes(root)
        configs=shortlist(before);seeds=[44,45];scenarios=VALIDATE;years=120
    jobs=[(str(root),route,seed,scenario,configs,years) for route in ['civil','military'] for seed in seeds for scenario in scenarios]
    rows=[];cache_stats=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(batch,jobs):rows.extend(result['runs']);cache_stats.append(result['cache'])
    groups=summarize(root,rows)
    data=dict(version='direct-band-parameters-v1',phase=args.phase,source_sha256=hashes(root),
        configs=configs,seeds=seeds,scenarios=scenarios,years=years,runs=rows,groups=groups,
        cache_stats=cache_stats,assumptions=dict(shared_parameters=True,epsilon_is_convention=True,
            direct_band_no_hidden_reserve=True,qualifications_are_external_sensitivity=True,
            synthetic_not_engine=True,random_adjacent_rounding=True))
    if args.phase!='validation':data['ranking']=diagnostic_rank(groups,configs)
    verify(root);output.write_text(json.dumps(data,ensure_ascii=False))
    (root/(args.phase+'-summary.json')).write_text(json.dumps({k:v for k,v in data.items() if k!='runs'},ensure_ascii=False,indent=2))
    print('DONE',args.phase,len(rows),check(root),flush=True)

if __name__=='__main__':main()
