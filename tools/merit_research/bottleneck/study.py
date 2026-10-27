"""定位零中层的逐级供给瓶颈；仅离线反事实，不改变正式机制。

第一阶段逐项解除资格/达标/首次三品前后死亡；第二阶段同J同入仕
只加厚梯队。功绩门槛干预保留真实余额、权重与成功归一化。
所有参数文武共享。保护死亡只针对原潜在cap>=7的新入仕者，年龄照常增长。
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
import run as runner
from observe import Observer

BASE=dict(J=[100,0,0,5],coefficients=[3,4,8,1.5],r=.06,gain=.6)
DIAGNOSE=[dict(name='control'),dict(name='all_qualified',all_qualified=True),
          dict(name='ignore_merit',ignore_merit=True),
          dict(name='both',all_qualified=True,ignore_merit=True),
          dict(name='protect_pre',protect='pre'),dict(name='protect_post',protect='post'),
          dict(name='structure_reference',J=[75,20,5,5])]
BRIDGE=[dict(name='bridge4',reserve_eta=[.9375,1.5,4]),
        dict(name='bridge8',reserve_eta=[.9375,1.5,8]),
        dict(name='bridge8_qualified',reserve_eta=[.9375,1.5,8],all_qualified=True),
        dict(name='bridge8_merit',reserve_eta=[.9375,1.5,8],ignore_merit=True)]
SEEDS=[10,11]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def models(root):
    """只从本次冻结的数学依赖导入，避免其他study/model同名污染。"""
    sys.path.insert(0,str(root/'merit-joint-study'))
    joint=load(root/'merit-joint-study/study.py','bottleneck_joint_reference')
    calibration=load(root/'calibrate_joint.py','bottleneck_mapping_reference')
    return joint,calibration


def reserve_mapping(joint,calibration,eta):
    """只改变必要梯队储备下限；仍保持共同k、四六比例及最高带合计。"""
    def targets(J,unused,r=.06,candidate_fraction=.25,epsilon=.1):
        from fractions import Fraction
        K=[Fraction(str(k))*j for k,j in zip(BASE['coefficients'],J)]
        for b in range(2,-1,-1):K[b]=max(K[b],Fraction(str(eta[b]))*sum(K[b+1:]))
        out=joint.capacity._targets_from_K(K,Fraction(str(r)),Fraction(str(epsilon)),Fraction(str(candidate_fraction)))
        out['K']=list(map(float,K));return out
    return targets


def batch(job):
    """一因子干预每次恢复原函数；死亡保护读取上年真实品级，避免冻结年龄。"""
    root,route,seed,cases=job;root=Path(root)
    joint,calibration=models(root);original=joint.capacity.targets
    advance=joint.world.aging.advance_year;rows=[]
    for variant in cases:
        cfg=calibration.external_config({**BASE,**variant},route,joint.world)
        cfg['mapping']='bottleneck'
        joint.capacity.targets=(reserve_mapping(joint,calibration,cfg['reserve_eta']) if 'reserve_eta' in cfg
            else calibration.mapping(original,BASE['coefficients']))
        observer=Observer(route,seed,joint.pr);previous={};suppressed=[]
        namespace=seed+(1000000 if route=='military' else 0)
        def observe(stage,year,people,context):
            observer(stage,year,people,context)
            if stage=='after':
                previous.clear()
                previous.update({p['health_pid']:dict(entry=p['entry'],rank=p['rank'],
                    natural_cap=joint.pr.ceiling(namespace,p['id'])) for p in people.values()})
        def protect(state,sk,pid,year):
            info=previous.get(pid);eligible=(info is not None and info['entry'] is not None and info['natural_cap']>=7)
            selected=eligible and ((cfg.get('protect')=='pre' and info['rank']<7) or
                                   (cfg.get('protect')=='post' and info['rank']>=7))
            if not selected:return advance(state,sk,pid,year)
            # 保留年龄/病理与增长，仅屏蔽死亡；跨过首次三品后重新服从所选阶段。
            out=advance(state,sk,pid,year)
            if not out['alive']:suppressed.append(dict(year=year,pid=pid,rank=info['rank'],entry=info['entry'],natural_cap=info['natural_cap']))
            out['alive']=True;out['death_due_month']=None;out['pending_death_cause']=None
            out.pop('death_cause',None)
            return out
        if cfg.get('protect'):joint.world.aging.advance_year=protect
        try:
            started=time.monotonic()
            gate=(lambda person,source,threshold:True) if cfg.get('ignore_merit') else None
            result=joint.trial(route,seed,cfg,years=120,observer=observe,merit_gate=gate)
            result['diagnostic']=observer.result();result['suppressed_death_checks']=suppressed
            rows.append(result)
            print('finished',route,seed,cfg['name'],round(time.monotonic()-started,2),flush=True)
        finally:
            joint.capacity.targets=original;joint.world.aging.advance_year=advance
    return rows


def sources(root):
    """封存本组、驱动和全部实际数学依赖，不重新签旧产物。"""
    manifest=json.loads((root/'source-manifest.json').read_text())
    names=[*manifest,'calibrate_joint.py','runner_reference.py',
           *[str(Path('merit-bottleneck-study')/p.name) for p in ROOT.glob('*.py')]]
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}


def verify(root):
    runner.verify_snapshot(root,runner.selection('joint'),[])
    for p in ROOT.glob('*.py'):
        assert p.read_bytes()==(root/'merit-bottleneck-study'/p.name).read_bytes(),p.name
    assert (ROOT.parent/'calibrate_joint.py').read_bytes()==(root/'calibrate_joint.py').read_bytes()
    assert (ROOT.parent/'run.py').read_bytes()==(root/'runner_reference.py').read_bytes()


def check(root):
    """逐年四格、E/Q和固定40年队列必须闭合，干预失败不伪装机制通过。"""
    verify(root);counts={}
    for phase in ['diagnose','bridge']:
        path=root/(phase+'-results.json')
        if not path.exists():continue
        data=json.loads(path.read_text());assert data['source_sha256']==sources(root)
        expected=len(DIAGNOSE if phase=='diagnose' else BRIDGE)*4
        assert len(data['runs'])==expected
        assert len({(r['route'],r['seed'],r['config']['name']) for r in data['runs']})==expected
        for row in data['runs']:
            assert len(row['diagnostic']['years'])==120 and row['mechanism_errors']==0
            for state,observed in zip(row['series'],row['diagnostic']['years']):
                assert state['year']==observed['year']
                for a,d in enumerate(observed['stages']):
                    assert d['n']==state['decision_n'][a]
                    assert d['eligible']==state['E'][a] and d['Q']==state['Q'][a]
                    assert d['n']==sum(d[k] for k in ['cap_no_merit_no','cap_no_merit_yes','cap_yes_merit_no','cap_yes_merit_yes'])
            for suppressed in row['suppressed_death_checks']:
                assert suppressed['entry'] is not None and suppressed['natural_cap']>=7
                assert (suppressed['rank']<7)==(row['config']['protect']=='pre')
            for c in row['diagnostic']['cohort'].values():
                assert c['n']==sum(c['deaths_by_rank'])+sum(c['alive_by_rank'])
                assert c['reached3']<=c['n']
        counts[phase]=expected
    assert 'diagnose' in counts
    return counts


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['diagnose','bridge','check'])
    parser.add_argument('--output-dir',required=True,type=Path);parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args();root=runner.outside_repository(args.output_dir)
    if args.phase=='diagnose':
        runner.prepare(root,runner.selection('joint'));target=root/'merit-bottleneck-study';target.mkdir()
        for p in ROOT.glob('*.py'):shutil.copyfile(p,target/p.name)
        shutil.copyfile(ROOT.parent/'calibrate_joint.py',root/'calibrate_joint.py')
        shutil.copyfile(ROOT.parent/'run.py',root/'runner_reference.py')
    else:verify(root)
    print('产物：',root,flush=True)
    if args.phase=='check':print(json.dumps(check(root)));return
    if (root/(args.phase+'-results.json')).exists():raise ValueError('本阶段结果已存在，不覆盖')
    cases=DIAGNOSE if args.phase=='diagnose' else BRIDGE
    jobs=[(str(root),route,seed,cases) for route in ['civil','military'] for seed in SEEDS]
    rows=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for batch_rows in pool.map(batch,jobs):rows.extend(batch_rows)
    joint,_=models(root)
    groups={route+'/'+c['name']:joint.summarize([r for r in rows if r['route']==route and r['config']['name']==c['name']])
            for route in ['civil','military'] for c in cases}
    data=dict(version='bottleneck-v1',phase=args.phase,source_sha256=sources(root),runs=rows,groups=groups,
        assumptions=dict(not_engine_evidence=True,paired_exogenous_ids_within_route=True,
            cohort_entry=[20,59],endpoint_years=40,late_population_window=[80,119],
            no_gate_keeps_actual_merit_weights_and_reset=True,
            protected_deaths_only_natural_high_cap_newcomers=True))
    verify(root)
    (root/(args.phase+'-results.json')).write_text(json.dumps(data,ensure_ascii=False))
    (root/(args.phase+'-summary.json')).write_text(json.dumps({k:v for k,v in data.items() if k!='runs'},ensure_ascii=False,indent=2))
    print('DONE',args.phase,len(rows),flush=True)
    print(json.dumps(check(root)),flush=True)

if __name__=='__main__':main()
