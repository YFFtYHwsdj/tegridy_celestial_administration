"""用既有合成人群校准四带系数；不以缺自然采样阻塞研究建议。

冻结joint及依赖源码，复用其逐人生涯与授品规则；只替换头衔到K的映射。
文武严格共用参数。训练种子7，留出8/9；不改资格、功绩收入或任命规则。
基准按独立槽数统一入仕强度，固定旧入仕量作为压力对照，均属外部情景。
ε固定为.1，避免与四带系数的乘积不可辨；候选比例c仅为离线储备条件。
产物与冻结版本只写仓库外。训练排名是公开工程偏好，不称全局最优。
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import run as runner

CONFIGS=[dict(name=f'shared-{low}-{middle}',coefficients=[low,4,middle,1.5],r=.06,gain=.6)
         for low in [2,2.5,3,3.5] for middle in [6,8]]
SCENARIOS=[dict(name='baseline'),dict(name='entry4',entry_pressure=4),
 dict(name='fixed_intake',fixed_intake=True),dict(name='longlife',mortality='longlife'),
 dict(name='loss',shock='loss'),dict(name='no_middle',J=[100,0,0,5]),
 dict(name='small',J=[3,1,1,1],explicit_entrants=1),
 dict(name='upper_expanded',structure='upper_expanded')]


def external_config(config,route,world):
    """仅设外部入仕输入：每槽.075人/年，整数四舍五入，不拟合路线系数。

    头衔收缩后暂不跟着改入仕，是压力情景；小体系另显式给1人/年，
    不把舍入成0的停招混作‘入仕足够’。固定旧26/8作为独立偏载压力。
    """
    if 'military_low' in config:raise ValueError('校准禁止路线专属机制参数')
    cfg=dict(config)
    J=cfg.get('J',world.JOBS[route][cfg.get('structure','base')])
    base=world.pr.BASE[route]['birth']
    if cfg.get('fixed_intake'):entrants=base
    elif 'explicit_entrants' in cfg:entrants=cfg['explicit_entrants']
    else:entrants=round(.075*sum(J)*cfg.get('entry_pressure',1))
    cfg.update(entry_mult=entrants/base,annual_entrants=entrants,entry_rate_per_slot=.075)
    return cfg


def study_capacity_targets(K,r,epsilon,candidate_fraction):
    """复用冻结的目标拆分及必要供给条件，不保留旧映射元数据。"""
    import capacity
    return capacity._targets_from_K(K,r,epsilon,candidate_fraction)


def mapping(original,coefficients,reserve=True):
    """系数作用于四级动态J；必要时自上往下增加中间储备，不造头衔。"""
    def targets(J,unused_mapping='calibrated',r=.04/.96,candidate_fraction=.25,epsilon=.1):
        out=original(J,'uniform2',r=r,candidate_fraction=candidate_fraction,epsilon=epsilon)
        K=[Fraction(str(k))*j for k,j in zip(coefficients,J)]
        rr=Fraction(str(r));cc=Fraction(str(candidate_fraction));ee=Fraction(str(epsilon))
        if reserve:
            denominator=Fraction(2,5)*cc-Fraction(3,5)*rr
            if denominator<=0:raise ValueError('本校准仅支持正储备分母')
            eta=max(rr/denominator,rr/(Fraction(3,5)*cc))
            for b in range(2,-1,-1):K[b]=max(K[b],eta*sum(K[b+1:]))
        T=[(1+ee)*k for k in K];target=[]
        for t in T[:3]:target.extend([Fraction(2,5)*t,Fraction(3,5)*t])
        target.append(T[3])
        out=study_capacity_targets(K,rr,ee,cc)
        out.update(K=list(map(float,K)))
        return out
    return targets


def batch(job):
    """每进程独立替换映射，复用原生研究健康缓存；结束恢复模块函数。"""
    root,route,seed,configs,years=job
    sys.path.insert(0,str(Path(root)/'merit-joint-study'))
    import study
    original=study.capacity.targets
    rows=[]
    try:
        for config in configs:
            coefficients=list(config['coefficients'])
            study.capacity.targets=mapping(original,coefficients,config.get('reserve',True))
            cfg=external_config(config,route,study.world)
            started=time.monotonic();row=study.trial(route,seed,{**cfg,'mapping':'calibrated'},years)
            rows.append(row)
            print('finished',route,seed,config['name'],round(time.monotonic()-started,2),flush=True)
    finally:study.capacity.targets=original
    return rows


def summarize(root,rows,configs):
    """复用原汇总；同时保留全部候选与完整逐年结果。"""
    sys.path.insert(0,str(root/'merit-joint-study'))
    import study
    return {route+'/'+c['name']:study.summarize([r for r in rows if r['route']==route and r['config']['name']==c['name']])
            for route in ['civil','military'] for c in configs}


def run_batch(root,configs,seeds,years,workers):
    jobs=[(str(root),route,seed,configs,years) for route in ['civil','military'] for seed in seeds]
    rows=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(batch,jobs):rows.extend(result)
    return rows


def ranking(groups):
    """先比较最差四级核覆盖，再六尾误差；全部挤占、生涯指标另报。"""
    ranked=[]
    for config in CONFIGS:
        gs=[groups[route+'/'+config['name']] for route in ['civil','military']]
        key=(max(1-min(x for x in g['coverage'] if x is not None) for g in gs),
             max(max(x for x in g['tail_error_mean'] if x is not None) for g in gs))
        ranked.append(dict(key=key,config=config))
    return sorted(ranked,key=lambda x:x['key'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path);parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args();root=runner.outside_repository(args.output_dir)
    dependencies=runner.selection('joint');runner.prepare(root,dependencies)
    shutil.copyfile(__file__,root/'calibrate_joint.py')
    seal=json.loads((root/'source-manifest.json').read_text())
    own=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print('校准产物：',root,flush=True)
    train=run_batch(root,CONFIGS,[7],80,args.workers)
    train_groups=summarize(root,train,CONFIGS);ranked=ranking(train_groups)
    selected=ranked[0]['config']
    print('SELECTED',json.dumps(selected),flush=True)
    (root/'calibration-pilot.json').write_text(json.dumps(dict(groups=train_groups,runs=train,ranking=ranked),ensure_ascii=False))
    configs=[{**selected,**s} for s in SCENARIOS]
    validation=run_batch(root,configs,[8,9],120,args.workers)
    groups=summarize(root,validation,configs)
    runner.verify_snapshot(root,dependencies,[])
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==own,'运行期间校准源码改变'
    assert len(train)==16 and len(validation)==32
    assert all(r['mechanism_errors']==0 for r in train+validation)
    out=dict(version='shared-calibration-v1',source_manifest=seal,calibration_sha256=own,
             selected=selected,training_seeds=[7],validation_seeds=[8,9],
             training_runs=16,validation_runs=32,training_years=80,validation_years=120,
             assumptions={'synthetic_only':True,'epsilon':.1,'phi':.6,'candidate_fraction':.25,
                          'temperature_default':.5,'same_health_caps_and_income':True,'mechanism_parameters_shared':True,
                          'baseline_entrants_per_slot':.075,'integer_entrants_rounding':True,
                          'not_engine_evidence':True,'ranking':'最差核覆盖，再六尾最大平均相对误差；非综合福利最优'},
             ranking=ranked,training_groups=train_groups,groups=groups,runs=validation)
    (root/'calibration-results.json').write_text(json.dumps(out,ensure_ascii=False))
    (root/'calibration-summary.json').write_text(json.dumps({k:v for k,v in out.items() if k not in ['runs','source_manifest']},ensure_ascii=False,indent=2))
    print('DONE',len(train),len(validation),flush=True)

if __name__=='__main__':main()
