"""统一预算内梯队分配的定稿研究；源码在库内，产物只写仓库外。

不改资格、Merit、健康、原生任命代理与一年一升。梯队权重训练种子32/33，
留出34/35；未来实际人口不用于缩目标，死亡冲击不会被预算自动抹平。
‘全候选即授’仅作当前固定增长/外生健康条件下的供给包络，不是政策。
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
import run as runner

COARSE_CONFIGS=[
 dict(name='surplus',mode='surplus',budget_factor=3,top_extra=0,r=.06,gain=.6),
 dict(name='priority6',mode='priority6',budget_factor=3,top_extra=0,r=.06,gain=.6),
 dict(name='priority8',mode='priority8',budget_factor=3,top_extra=0,r=.06,gain=.6),
 dict(name='priority10',mode='priority10',budget_factor=3,top_extra=0,r=.06,gain=.6),
 dict(name='priority8-buffer',mode='priority8',budget_factor=3,top_extra=1,r=.06,gain=.6),
 dict(name='priority10-buffer',mode='priority10',budget_factor=3,top_extra=1,r=.06,gain=.6),
 dict(name='compact',mode='priority10',budget_factor=2.75,top_extra=1,r=.06,gain=.6),
 dict(name='wide',mode='priority10',budget_factor=3.25,top_extra=1,r=.06,gain=.6),
 dict(name='responsive',mode='priority10',budget_factor=3,top_extra=1,r=.06,gain=.8),
 dict(name='responsive-r04',mode='priority10',budget_factor=3,top_extra=1,r=.04,gain=.8),
]
CONFIGS=[
 dict(name=f'pipeline{k}-middle{middle}-r{r}',mode='pipeline',budget_factor=k,
      top_extra=0,top_factor=1,base_share=.25,middle_share=middle,r=r,gain=.6,phi=.8)
 for k in [1.5,2] for middle in [.6,.7] for r in [.08,.12]
]


TRAIN=[dict(name='baseline'),dict(name='no_middle',J=[100,0,0,5])]
VALIDATE=[dict(name='baseline'),dict(name='no_middle',J=[100,0,0,5]),
 dict(name='thin_middle',J=[100,1,1,5]),dict(name='shape_reference',J=[75,20,5,5]),
 dict(name='upper_expanded',structure='upper_expanded'),dict(name='entry4',entry_pressure=4),
 dict(name='longlife',mortality='longlife'),dict(name='loss',shock='loss'),
 dict(name='mortality',shock='mortality'),dict(name='empty',initial='empty'),
 dict(name='bottom',initial='bottom'),dict(name='top',initial='top'),
 dict(name='small',J=[3,1,1,1],explicit_entrants=1),dict(name='fixed_intake',fixed_intake=True),
 dict(name='low_growth',income=240),dict(name='upper_heavy',J=[15,25,40,40]),
 dict(name='only_upper',J=[0,0,0,5],explicit_entrants=1),dict(name='no_top',J=[100,20,5,0])]
SHADOW_NAMES={'baseline','no_middle','thin_middle','shape_reference','upper_expanded',
              'small','low_growth','upper_heavy','only_upper','no_top'}


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def models(root):
    sys.path.insert(0,str(root/'merit-joint-study'))
    joint=load(root/'merit-joint-study/study.py','budget_joint_reference')
    mapping=load(root/'budget_mapping_candidates.py','budget_candidates_reference')
    calibration=load(root/'calibrate_joint.py','budget_inputs_reference')
    return joint,mapping,calibration


def batch(job):
    """每次恢复共享模块；没有路线专属机制参数，也没有干预原版资格。"""
    root,route,seed,scenario,configs,years,shadow=job;root=Path(root)
    joint,mapping,calibration=models(root);original=joint.capacity.targets;quota=joint.tail.quota
    rows=[]
    try:
        for config in configs:
            cfg=calibration.external_config({**config,**scenario},route,joint.world)
            cfg['policy']=config['name'];cfg['mapping']='budget'
            joint.capacity.targets=partial(mapping.targets,mode=config['mode'],
                budget_factor=config['budget_factor'],top_extra=config['top_extra'],phi=config.get('phi',.6),top_factor=config.get('top_factor',1.5),base_share=config.get('base_share',.5),middle_share=config.get('middle_share',.5))
            if shadow:
                # trial随后仍取min(E,raw)，所以每个合格者只在本年升一级。
                joint.tail.quota=lambda n,t,e,**kwargs:quota(n,t,e,**kwargs)*0+10**9
            started=time.monotonic();result=joint.trial(route,seed,cfg,years=years)
            result['budget_diagnostics']=joint.capacity.targets(result['series'][-1]['J'],r=cfg['r'],epsilon=result['config']['epsilon'])
            result['shadow']=shadow;rows.append(result)
            print('finished','shadow' if shadow else 'policy',route,seed,scenario['name'],config['name'],round(time.monotonic()-started,2),flush=True)
    finally:joint.capacity.targets=original;joint.tail.quota=quota
    return rows


def extra_metrics(rows):
    """年度分位数与均值并报；小池报告绝对误差，不把均值当窄幅稳定。"""
    states=[s for r in rows for s in r['series'][-40:]]
    bands=lambda s:[sum(s['decision_n'][2*b:2*b+2]) for b in range(3)]+[sum(s['decision_n'][6:])]
    n=[bands(s) for s in states];T=[[sum(s['target'][2*b:2*b+2]) for b in range(3)]+[s['target'][6]] for s in states]
    percent=lambda xs,p:sorted(xs)[round((len(xs)-1)*p)]
    ratios=[[a[b]/t[b] for a,t in zip(n,T) if t[b]>0] for b in range(4)]
    errs=[[abs(a[b]-t[b]) for a,t in zip(n,T)] for b in range(4)]
    mean_ratio=[statistics.mean(x) if x else None for x in ratios]
    out=dict(band_mean=[statistics.mean(x[b] for x in n) for b in range(4)],
        band_goal=[statistics.mean(x[b] for x in T) for b in range(4)],band_mean_ratio=mean_ratio,
        band_ratio_p10=[percent(x,.1) if x else None for x in ratios],
        band_ratio_p90=[percent(x,.9) if x else None for x in ratios],
        band_absolute_error=[statistics.mean(x) for x in errs],
        top_zero_year_share=statistics.mean(x[3]==0 for x in n),
        bottom_mean=statistics.mean(s['decision_n'][0] for s in states),
        zero_quota_given_candidates=[sum(s['Q'][i]==0 and s['E'][i]>0 for s in states)/sum(s['E'][i]>0 for s in states)
             if any(s['E'][i]>0 for s in states) else None for i in range(6)])
    if rows[0]['config'].get('shock'):
        times=[]
        for r in rows:
            series=r['series'];start=60;found=None
            for index in range(start,len(series)-4):
                if all(s['tail_error'][-1] is not None and s['tail_error'][-1]<=.25 for s in series[index:index+5]):
                    found=index-start;break
            times.append(found)
        out['top_first5_within25_after60']=times
    return out


def summarize(root,rows):
    joint,_,_=models(root);groups={}
    for route,scenario,policy in sorted({(r['route'],r['config']['name'],r['config']['policy']) for r in rows}):
        selected=[r for r in rows if (r['route'],r['config']['name'],r['config']['policy'])==(route,scenario,policy)]
        groups['/'.join([route,scenario,policy])]={**joint.summarize(selected),**extra_metrics(selected)}
    return groups


def ranking(groups,configs=CONFIGS):
    """先比较最差最高带缺口，再总体带偏差；预算与余量不同不得靠路线拟合。

    平均最高带低于目标75%记可观的缺员。先减少此类结构数，再比较
    最差缺口、四带平均偏差与零人年。全部数值保留，排序不是福利最优。
    """
    ranked=[]
    for config in configs:
        gs=[g for key,g in groups.items() if key.endswith('/'+config['name'])]
        # 九品入仕不能由升品控制；不以第一带贴合度奖励抬高总预算。
        ratios=[g['band_mean_ratio'][b] for g in gs for b in [1,2,3]]
        worst=max(abs(x-1) for x in ratios)
        key=(sum(x<.65 or x>1.5 for x in ratios),math.ceil(worst*4)/4,
             config['budget_factor'],statistics.mean(abs(x-1) for x in ratios))
        ranked.append(dict(config=config,key=key))

    return sorted(ranked,key=lambda x:x['key'])


def seal(root):
    manifest=json.loads((root/'source-manifest.json').read_text())
    names=[*manifest,'budget_mapping_candidates.py','calibrate_joint.py','runner_reference.py',
           *[str(Path('merit-budget-study')/p.name) for p in ROOT.glob('*.py')]]
    return {n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names}


def verify(root):
    runner.verify_snapshot(root,runner.selection('joint'),[])
    for p in ROOT.glob('*.py'):assert p.read_bytes()==(root/'merit-budget-study'/p.name).read_bytes(),p.name
    for name in ['budget_mapping_candidates.py','calibrate_joint.py']:
        assert (ROOT.parent/name).read_bytes()==(root/name).read_bytes(),name
    assert (ROOT.parent/'run.py').read_bytes()==(root/'runner_reference.py').read_bytes()


def check(root):
    verify(root);counts={}
    for phase,expected in [('pilot',None),('validation',72),('shadow',40)]:
        path=root/(phase+'-results.json')
        if not path.exists():continue
        data=json.loads(path.read_text())
        if expected is None:expected=len(data['ranking'])*8
        assert data['source_sha256']==seal(root)
        assert len(data['runs'])==expected
        assert len({(r['route'],r['seed'],r['config']['name'],r['config']['policy']) for r in data['runs']})==expected
        for r in data['runs']:
            cfg=r['config'];assert 'military_low' not in cfg
            for s in r['series']:
                assert sum(s['decision_n'])==sum(s['post_n'])==s['active']
                assert all(0<=q<=e for q,e in zip(s['Q'],s['E']))
                assert math.isclose(sum(s['K']),cfg['budget_factor']*sum(s['J']),abs_tol=1e-7)
                assert math.isclose(sum(s['target']),1.1*sum(s['K']),abs_tol=1e-7)
                if cfg['mode']!='pipeline':assert all(k>=j-1e-8 for k,j in zip(s['K'],s['J']))
                assert s['K'][3]==0 if s['J'][3]==0 else s['K'][3]>=cfg.get('top_factor',1.5)*s['J'][3]
                for b in range(3):
                    assert math.isclose(s['target'][2*b+1],cfg.get('phi',.6)*sum(s['target'][2*b:2*b+2]),abs_tol=1e-7)
                if s['J'][3]==0 and not r['shadow']:assert s['Q'][5]==0
                if r['shadow']:assert s['Q']==s['E']
        counts[phase]=expected
    if 'shadow' in counts:
        policy=json.loads((root/'validation-results.json').read_text())
        fast=json.loads((root/'shadow-results.json').read_text())
        for r in fast['runs']:
            paired=next(x for x in policy['runs'] if (x['route'],x['seed'],x['config']['name'])==(r['route'],r['seed'],r['config']['name']))
            for a,b in zip(paired['series'],r['series']):
                assert sum(a['decision_n'][6:])<=sum(b['decision_n'][6:]),'最快合格即授供给包络未包住政策'
    assert counts
    return counts


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['pilot','validation','shadow','check'])
    parser.add_argument('--output-dir',type=Path,required=True);parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--coarse',action='store_true',help='复算初始四六粗筛，不作当前推荐')
    args=parser.parse_args();root=runner.outside_repository(args.output_dir)
    if args.phase=='pilot':
        runner.prepare(root,runner.selection('joint'));folder=root/'merit-budget-study';folder.mkdir()
        for p in ROOT.glob('*.py'):shutil.copyfile(p,folder/p.name)
        for name in ['budget_mapping_candidates.py','calibrate_joint.py']:shutil.copyfile(ROOT.parent/name,root/name)
        shutil.copyfile(ROOT.parent/'run.py',root/'runner_reference.py')
    else:verify(root)
    print('产物：',root,flush=True)
    if args.phase=='check':print(json.dumps(check(root)));return
    if (root/(args.phase+'-results.json')).exists():raise ValueError('拒绝覆盖已存在阶段结果')
    if args.phase=='pilot':
        configs=COARSE_CONFIGS if args.coarse else CONFIGS;scenarios=TRAIN
        seeds=[12,13] if args.coarse else [32,33];years=80
        grid='coarse' if args.coarse else 'pipeline-budget'
    else:
        pilot=json.loads((root/'pilot-results.json').read_text());assert pilot['source_sha256']==seal(root)
        configs=[pilot['ranking'][0]['config']];scenarios=VALIDATE
        grid=pilot['grid'];seeds=[14,15] if grid=='coarse' else [34,35];years=120
        if args.phase=='shadow':scenarios=[s for s in scenarios if s['name'] in SHADOW_NAMES]
    jobs=[(str(root),route,seed,scenario,configs[i:i+5],years,args.phase=='shadow')
          for route in ['civil','military'] for seed in seeds for scenario in scenarios for i in range(0,len(configs),5)]
    rows=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(batch,jobs):rows.extend(result)
    groups=summarize(root,rows);data=dict(version='budget-v2',phase=args.phase,grid=grid,source_sha256=seal(root),runs=rows,groups=groups,
        assumptions=dict(synthetic_only=True,shared_parameters=True,epsilon=.1,phi='按候选配置，文武共用',temperature=.5,
             integer_random_rounding=True,no_annual_floor=True,no_population_target_shrink=True))
    if args.phase=='pilot':data['ranking']=ranking(groups,configs)
    verify(root)
    (root/(args.phase+'-results.json')).write_text(json.dumps(data,ensure_ascii=False))
    (root/(args.phase+'-summary.json')).write_text(json.dumps({k:v for k,v in data.items() if k!='runs'},ensure_ascii=False,indent=2))
    print('DONE',args.phase,len(rows),flush=True);print(json.dumps(check(root)),flush=True)

if __name__=='__main__':main()
