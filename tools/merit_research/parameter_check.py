"""固定共同k与四六拆品，对其余首版值作小规模核查，不搜索参数。

检查来源收入生涯、两项外部冲击、理想反馈恢复和单一温度的抽选。
固定配置、来源及逐局结果保存在仓库外，可续跑但不混签旧源码。
"""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from functools import partial
import json
import math
import multiprocessing
from pathlib import Path
import random
import shutil
import sys

import coefficient_grid as grid
import parameter_analysis as parent

ROOT=Path(__file__).resolve().parent


def plan():
    """只验证这一组参数；不同死亡率是外部敏感性，不是参数搜索。"""
    return dict(policy=dict(coefficients=[1.5]*4,phi=[.6]*3,r=.06,gain=.9,
                            epsilon=.1,temperature=.5,reserve=[0,0,0]),years=120,
        jobs=[dict(route=route,seed=seed,profile=profile,scenario='baseline')
              for route in ['civil','military'] for seed in [65,66] for profile in ['reference','high']]+
             [dict(route=route,seed=65,profile='reference',scenario=scenario)
              for route in ['civil','military'] for scenario in ['loss','mortality']])


def tag(work):return grid.job_tag(work)


def verify(root,study,income):
    income.verify(root,study)
    source=json.loads((root/'parameter-check-source.json').read_text())
    assert source==dict(driver=parent.digest(__file__),audit=parent.digest(grid.__file__),plan=plan())
    assert parent.digest(root/'parameter_check.py')==source['driver']
    assert parent.digest(root/'coefficient_grid.py')==source['audit']


def prepare(root,study,income,game):
    income.prepare(root,study,game)
    if not (root/'parameter-check-source.json').exists():
        for name in ['parameter_check.py','coefficient_grid.py']:shutil.copyfile(ROOT/name,root/name)
        grid.save(root/'parameter-check-source.json',dict(driver=parent.digest(__file__),audit=parent.digest(grid.__file__),plan=plan()))
    verify(root,study,income)


def batch(task):
    root,work=task;root=Path(root);study=parent.load_study();income=grid.load_income();verify(root,study,income)
    output=root/(tag(work)+'.json')
    if output.exists():return tag(work)
    joint,capacity,calibration=study.models(root);model=income.load_model(root);settings=plan()
    cfg=dict(settings['policy'],name=work['scenario'],policy='fixed-final-check',mapping='direct_band')
    if work['scenario']!='baseline':cfg['shock']=work['scenario']
    cfg=study.external_config(cfg,work['route'],joint.world,calibration)
    old=joint.capacity.targets
    joint.capacity.targets=partial(capacity.targets,coefficients=cfg['coefficients'],phi=cfg['phi'],reserve=cfg['reserve'])
    inputs=income.plan();seed=work['seed']+(1000000 if work['route']=='military' else 0)
    def initialize(person):
        model.initialize_exams(person,lambda channel:joint.pr.uniform(seed,person['id'],0,channel),learning=inputs['learning'])
    def credit(person,job,year):
        tier=job['tier'] if job else 0
        role='none' if job is None else 'minister' if job['central_target'] else ('civil_standard' if work['route']=='civil' else 'military')
        scale=4 if work['profile']=='high' else 1
        return model.annual_components(role=role,head_tier=tier,
            paid_tax=inputs['tax_by_tier'][tier-1]*scale if tier else 0,
            maa_value=inputs['maa_by_tier'][tier-1]*scale if tier else 0)
    try:
        row=joint.trial(work['route'],work['seed'],cfg,years=settings['years'],income_step=credit,person_init=initialize)
        row['check_world']=work
        grid.audit_row(row,joint,capacity,cfg['coefficients'],settings['years'])
        grid.save(output,row);print('SAVED',tag(work),flush=True)
    finally:joint.capacity.targets=old
    return tag(work)


def mathematical_check(model):
    """固定r/κ/τ核查；来源无限且固定退出的解析模型不能证明生涯供给。"""
    policy=plan()['policy'];scalar=[]
    for d in [.02,.04,.08]:
        equilibrium=model.scalar_equilibrium(B=100,d=d,r=policy['r'],gain=policy['gain'])
        assert 0<=equilibrium['local_multiplier']<1
        paths=[]
        for initial in [50.,200.]:
            states=[initial]
            for _ in range(120):states.append((1-d)*(states[-1]+model.quota_expectation(states[-1],100,r=policy['r'],gain=policy['gain'])))
            errors=[abs(s-equilibrium['S']) for s in states]
            assert all(b<=a+1e-9 for a,b in zip(errors,errors[1:]))
            paths.append(dict(initial=initial,first_within_target10percent=next((i for i,s in enumerate(states) if abs(s-100)<=10),None),final=states[-1]))
        scalar.append(dict(exit_rate=d,equilibrium_to_K=1.1*equilibrium['ratio'],equilibrium=equilibrium,paths=paths))
    rng=random.Random(20261026);draws=20000;wins=0
    for _ in range(draws):
        a,b=rng.random(),rng.random()
        assert 0<a<1 and 0<b<1
        wins+=math.log(2)/policy['temperature']-math.log(-math.log(a))>-math.log(-math.log(b))
    exact=1/(1+2**(-1/policy['temperature']))
    assert abs(wins/draws-exact)<=5*math.sqrt(exact*(1-exact)/draws)
    return dict(scalar=scalar,temperature=dict(value=policy['temperature'],stage_lead=1,exact=exact,empirical=wins/draws,draws=draws),
                assumptions='理想标量来源无限、比例退出恒定、无中央净流；生涯世界及极端冲击不受此收敛证明覆盖')


def check(root,study,income):
    verify(root,study,income);joint,model,_=study.models(root);rows=[];groups={}
    for work in plan()['jobs']:
        row=json.loads((root/(tag(work)+'.json')).read_text());assert row['check_world']==work
        assert row['route']==work['route'] and row['seed']==work['seed'] and row['config']['name']==work['scenario']
        for key,value in plan()['policy'].items():assert row['config'][key]==value
        assert row['config'].get('shock')==(work['scenario'] if work['scenario']!='baseline' else None)
        grid.audit_row(row,joint,model,plan()['policy']['coefficients'],plan()['years']);rows.append(row)
        key='/'.join([work['route'],work['profile'],work['scenario']]);groups.setdefault(key,[]).append(row)
    return dict(plan=plan(),mathematical=mathematical_check(model),
                checks=dict(runs=len(rows),annual_states=len(rows)*plan()['years'],synthetic_not_engine=True),
                groups={key:study.metrics(joint,rs) for key,rs in groups.items()})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--game-root',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args();study=parent.load_study();income=grid.load_income();root=study.runner.outside_repository(args.output_dir)
    prepare(root,study,income,args.game_root)
    if not args.check_only:
        sys.path.insert(0,str(study.ROOT))
        with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            for result in pool.map(batch,[(str(root),work) for work in plan()['jobs']]):print('DONE',result,flush=True)
    result=check(root,study,income);grid.save(root/'parameter-check-summary.json',result)
    print(json.dumps(result['checks']),flush=True)


if __name__=='__main__':main()
