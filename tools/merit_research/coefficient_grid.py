"""四带系数1.5至4、步长0.5的全组合小国筛选及完整规模复核。

原样复用来源收入、资格初始化、年龄健康、任命及六关规则；粗筛只
缩小外部世界，并标准化初态。保留每个最高带系数的代表，避免小池
误差与缩小最高目标决定所有入围者。全部产物逐局压缩保存至仓库外。
"""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from functools import partial
import gzip
import importlib.util
import itertools
import json
import math
import multiprocessing
from pathlib import Path
import shutil
import statistics
import sys
import time

import numpy as np
import parameter_analysis as parent

ROOT=Path(__file__).resolve().parent
VALUES=[1.5,2.,2.5,3.,3.5,4.]


def configurations():
    """四个独立系数的笛卡尔积，不只扫描共同系数或逐项局部值。"""
    return [list(values) for values in itertools.product(VALUES,repeat=4)]


def load_income():
    spec=importlib.util.spec_from_file_location('grid_income_support',ROOT/'income/study.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def design():
    """小国文武采用同初态/人数/入仕口径，中央槽密度保持全部帝级。"""
    return dict(version='coefficient-grid-v1',values=VALUES,combinations=1296,
        policy=dict(phi=[.6,.8,.5],r=.06,gain=.9,epsilon=.1,temperature=.5,reserve=[0,0,0]),
        screen=dict(years=80,seeds=[61,62],J=[20,6,3,1],
                    initial_counts=[40,8,4,6,2,3,2,1,0],annual_entrants=2),
        validation=dict(years=120,seeds=[63,64]),
        income_profiles=['reference','high'],
        selection='每个k4层保留最差情景跟踪优胜；另保留原指定组、统一1.5/2.5/4、最低预算近优及最高实际供给代表',
        limits='小国全部组合不是完整规模全局最优；收入规模合成；继任是既有代理；两个种子不构成置信保证')


def save(path,data):
    temporary=path.with_suffix('.writing')
    temporary.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');temporary.replace(path)


def verify(root,study,income):
    income.verify(root,study)
    record=json.loads((root/'grid-source.json').read_text())
    assert record==dict(driver=parent.digest(__file__),selector=parent.digest(parent.__file__),design=design())
    assert parent.digest(root/'coefficient_grid.py')==record['driver']


def prepare(root,study,income,game):
    income.prepare(root,study,game)
    if not (root/'grid-source.json').exists():
        shutil.copyfile(__file__,root/'coefficient_grid.py')
        save(root/'grid-source.json',dict(driver=parent.digest(__file__),selector=parent.digest(parent.__file__),design=design()))
    verify(root,study,income)


def audit_row(row,joint,model,coefficients,years):
    """用独立矩阵重算额度/取整/六关守恒；不以贴合目标作为通过条件。"""
    assert row['config']['coefficients']==coefficients and row['mechanism_errors']==0
    assert len(row['series'])==years
    series=row['series'];n=np.array([s['decision_n'] for s in series]);post=np.array([s['post_n'] for s in series])
    assert all(s['year']==i for i,s in enumerate(series))
    assert np.all(n>=0) and np.all(post>=0) and np.all(n.sum(axis=1)==post.sum(axis=1))
    assert np.all(n.sum(axis=1)==[s['active'] for s in series])
    q=np.array([s['Q'] for s in series]);E=np.array([s['E'] for s in series]);raw=[]
    cache={};cfg=row['config']
    for s in series:
        key=tuple(s['J'])
        if key not in cache:cache[key]=model.targets(key,coefficients=coefficients,phi=cfg['phi'],r=cfg['r'],epsilon=cfg['epsilon'])
        target=cache[key]
        assert np.allclose(s['K'],target['K']) and np.allclose(s['target'],target['target'])
        S=np.cumsum(np.array(s['decision_n'][::-1]))[::-1][1:7]
        B=np.array(target['B']);q0=cfg['r']*B
        expected=np.where(S<=B,q0+cfg['gain']*(B-S),q0/(1+cfg['gain']*np.maximum(0,S-B)/q0))
        raw.append(expected)
        if 'income_ledger' in s:
            assert math.isclose(sum(s['income_ledger'].values()),sum(g['total'] for g in s['income_groups'].values()),abs_tol=1e-7)
    raw=np.array(raw);assert np.allclose(raw,[s['q_star'] for s in series])
    clipped=np.minimum(raw,E)
    seed=row['seed']+(1000000 if row['route']=='military' else 0)
    uniforms=np.array([[joint.pr.uniform(seed,i+1,y,82) for i in range(6)] for y in range(years)])
    assert np.array_equal(q,np.floor(clipped)+(uniforms<clipped-np.floor(clipped)))
    assert np.all(q>=0) and np.all(q<=E)
    expected=n.copy();expected[:,:6]-=q;expected[:,1:7]+=q
    assert np.array_equal(expected,post)


def metrics(study,joint,row):
    value=study.metrics(joint,[row])
    series=row['series'];earlier=series[-60:-40]
    value['previous20_top_mean']=statistics.mean(sum(s['decision_n'][6:]) for s in earlier)
    value['last20_top_mean']=statistics.mean(sum(s['decision_n'][6:]) for s in series[-20:])
    value['top_per_empire']=value['band_mean'][3]/series[-1]['J'][3]
    return value


def job_tag(work):
    return f"{work['route']}-{work['seed']}-{work['profile']}-{work['scenario']}"


def jobs(phase):
    seeds=design()['screen' if phase=='screen' else 'validation']['seeds']
    return [dict(route=route,seed=seed,profile=profile,scenario='baseline')
            for route in ['civil','military'] for seed in seeds for profile in design()['income_profiles']]


def batch(task):
    """同外部世界共用健康结果；每个政策重置余额、资格和职务状态。"""
    root,phase,work,configs=task;root=Path(root);study=parent.load_study();income=load_income()
    verify(root,study,income);joint,capacity,calibration=study.models(root);model=income.load_model(root)
    plan=design();years=plan['screen' if phase=='screen' else 'validation']['years']
    directory=root/phase/job_tag(work);directory.mkdir(parents=True,exist_ok=True)
    report=directory/'index.json';records=json.loads(report.read_text()) if report.exists() else {}
    old_counts=joint.pr.BASE[work['route']]['n'];old_E=joint.pr.BASE[work['route']]['e'];old_targets=joint.capacity.targets
    if phase=='screen':
        joint.pr.BASE[work['route']]['n']=plan['screen']['initial_counts'][:]
        joint.pr.BASE[work['route']]['e']=[0]*9
    income_plan=income.plan();seed=work['seed']+(1000000 if work['route']=='military' else 0)
    def initialize(person):
        model.initialize_exams(person,lambda channel:joint.pr.uniform(seed,person['id'],0,channel),learning=income_plan['learning'])
    def credit(person,job,year):
        tier=job['tier'] if job else 0
        role='none' if job is None else 'minister' if job['central_target'] else ('civil_standard' if work['route']=='civil' else 'military')
        scale=4 if work['profile']=='high' else 1
        return model.annual_components(role=role,head_tier=tier,
            paid_tax=income_plan['tax_by_tier'][tier-1]*scale if tier else 0,
            maa_value=income_plan['maa_by_tier'][tier-1]*scale if tier else 0)
    started=time.monotonic()
    try:
        with study.health_cache(joint.world):
            for index,coefficients in enumerate(configs):
                label='-'.join(map(str,coefficients));output=directory/(label+'.json.gz')
                if label in records:
                    assert parent.digest(output)==records[label]['sha256'];continue
                cfg=dict(plan['policy'],coefficients=coefficients,name=work['scenario'],policy=label,mapping='direct_band')
                if phase=='screen':cfg.update(J=plan['screen']['J'],explicit_entrants=plan['screen']['annual_entrants'],initial_counts=plan['screen']['initial_counts'])
                cfg=study.external_config(cfg,work['route'],joint.world,calibration)
                cache={}
                def target(J,mapping=None,r=.06,epsilon=.1):
                    key=(tuple(J),r,epsilon)
                    if key not in cache:cache[key]=capacity.targets(J,r=r,epsilon=epsilon,coefficients=coefficients,phi=cfg['phi'])
                    return cache[key]
                joint.capacity.targets=target
                result=joint.trial(work['route'],work['seed'],cfg,years=years,income_step=credit,person_init=initialize)
                audit_row(result,joint,capacity,coefficients,years)
                packed=json.dumps(result,ensure_ascii=False).encode('utf-8')
                with gzip.open(output.with_suffix('.writing'),'wb',compresslevel=1) as handle:handle.write(packed)
                output.with_suffix('.writing').replace(output)
                records[label]=dict(sha256=parent.digest(output),coefficients=coefficients,metrics=metrics(study,joint,result))
                save(report,records)
                if (index+1)%100==0 or index+1==len(configs):
                    print('PROGRESS',phase,job_tag(work),index+1,len(configs),round(time.monotonic()-started,1),flush=True)
    finally:
        joint.pr.BASE[work['route']]['n']=old_counts;joint.pr.BASE[work['route']]['e']=old_E;joint.capacity.targets=old_targets
    return dict(job=work,completed=len(records),seconds=time.monotonic()-started)


def ranking(root,phase,configs):
    """最差条件优先，情景不会互相抵消；预算和实际供给另列。"""
    records=[json.loads((root/phase/job_tag(work)/'index.json').read_text()) for work in jobs(phase)]
    expected={'-'.join(map(str,c)) for c in configs}
    assert all(set(record)==expected for record in records)
    ranked=[]
    for coefficients in configs:
        label='-'.join(map(str,coefficients));groups=[record[label]['metrics'] for record in records]
        errors=[(g['band_tracking']+g['tail_tracking'])/2 for g in groups]
        ranked.append(dict(coefficients=coefficients,worst_tracking=max(errors),mean_tracking=statistics.mean(errors),
            budget=statistics.mean(g['budget_per_title'] for g in groups),
            actual_top_per_empire=statistics.mean(g['top_per_empire'] for g in groups),
            worst_top_zero=max(g['top_zero_share'] for g in groups),groups=dict(zip(map(job_tag,jobs(phase)),groups))))
    return sorted(ranked,key=lambda r:(r['worst_tracking'],r['mean_tracking'],r['budget']))


def select(ranked):
    """最高带六个层级各保留一组，外加成本、实际供给及结构对照。"""
    chosen=[]
    def add(coefficients,reason):
        if not any(c['coefficients']==coefficients for c in chosen):chosen.append(dict(coefficients=coefficients,reason=reason))
    for top in VALUES:add(next(r['coefficients'] for r in ranked if r['coefficients'][3]==top),f'k4={top}层最差条件跟踪优胜')
    add([1.5,2.,3.,1.5],'用户指定参考')
    for value in [1.5,2.5,4.]:add([value]*4,'共同系数结构对照')
    near=[r for r in ranked if r['worst_tracking']<=ranked[0]['worst_tracking']+.05]
    add(min(near,key=lambda r:(r['budget'],r['worst_tracking']))['coefficients'],'最差跟踪差不超过.05时最低预算')
    add(max(ranked,key=lambda r:r['actual_top_per_empire'])['coefficients'],'最高实际高品供给，独立报告其预算代价')
    return chosen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['screen','validate','check'])
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--game-root',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args();study=parent.load_study();income=load_income();root=study.runner.outside_repository(args.output_dir)
    prepare(root,study,income,args.game_root)
    if args.phase=='check':
        joint,model,_=study.models(root);counts={}
        for phase in ['screen','validation']:
            summary_path=root/(phase+'-grid-summary.json')
            if not summary_path.exists():continue
            saved=json.loads(summary_path.read_text());configs=saved['configs'];assert saved['ranking']==ranking(root,phase,configs)
            total=0
            for work in jobs(phase):
                directory=root/phase/job_tag(work);index=json.loads((directory/'index.json').read_text())
                for label,record in index.items():
                    path=directory/(label+'.json.gz');assert parent.digest(path)==record['sha256']
                    with gzip.open(path,'rt',encoding='utf-8') as handle:row=json.load(handle)
                    audit_row(row,joint,model,record['coefficients'],design()['screen' if phase=='screen' else 'validation']['years'])
                    assert record['metrics']==metrics(study,joint,row)
                    total+=1
            counts[phase]=total
        assert counts;print(json.dumps(counts),flush=True);return
    phase='screen' if args.phase=='screen' else 'validation'
    if phase=='screen':configs=configurations();selection=None
    else:
        previous=json.loads((root/'screen-grid-summary.json').read_text())
        assert previous['ranking']==ranking(root,'screen',configurations())
        selection=select(previous['ranking']);configs=[c['coefficients'] for c in selection]
    sys.path.insert(0,str(study.ROOT))
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures=[pool.submit(batch,(str(root),phase,work,configs)) for work in jobs(phase)]
        for future in as_completed(futures):print('JOB',future.result(),flush=True)
    ranked=ranking(root,phase,configs)
    verify(root,study,income)
    save(root/(phase+'-grid-summary.json'),dict(configs=configs,ranking=ranked,selection=selection,
         jobs=jobs(phase),source=parent.digest(root/'grid-source.json'),not_engine_evidence=True))
    print('DONE',phase,len(configs),len(configs)*len(jobs(phase)),'BEST',ranked[0]['coefficients'],flush=True)


if __name__=='__main__':main()
